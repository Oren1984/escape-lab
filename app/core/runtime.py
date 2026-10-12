"""Lab runtime: owns the active run and steps it outside the UI.

The Streamlit pages only send commands here and read snapshots back. A page
rerun, a browser refresh or a second tab never creates a run, never restarts
one and never adds agents: only ``launch`` does, and it refuses while a run is
active.
"""

from __future__ import annotations

import os
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.evidence import write_jsonl
from app.core.simulation import Simulation
from app.core.state import ExperimentResult, Scenario
from app.evaluation import suite as evaluation
from app.experiments import interpret_for, metrics_for
from app.providers.local_llm import LLMConfig, LocalLLM
from app.providers.rules import RulesEngine

MAX_HISTORY = 40
MIN_TICK_DELAY, MAX_TICK_DELAY = 0.05, 2.0


@dataclass(frozen=True)
class RunRecord:
    result: ExperimentResult
    metrics: dict[str, Any]
    notes: tuple[str, ...]
    saved_to: str | None = None

    @property
    def label(self) -> str:
        r = self.result
        return f"{r.scenario.title} · {r.provenance.get('provider')} · {r.scenario.policy_mode} · {r.run_id}"


class LabRuntime:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._lock = threading.RLock()
        self._sim: Simulation | None = None
        self._thread: threading.Thread | None = None
        self._paused = threading.Event()
        self._archived: set[str] = set()
        self.history: deque[RunRecord] = deque(maxlen=MAX_HISTORY)
        self.suite: list[evaluation.Outcome] | None = None
        self.faults: list[dict[str, Any]] | None = None
        self.data_dir = data_dir
        self.tick_delay = 0.35

    # -- commands ----------------------------------------------------------

    @property
    def active(self) -> bool:
        sim = self._sim
        return sim is not None and not sim.finished

    def llm_status(self) -> tuple[bool, str]:
        config = LLMConfig.from_env()
        try:
            return LocalLLM(config).availability()
        except ValueError as exc:
            return False, str(exc)

    def launch(
        self, scenario: Scenario, provider: str = "rules", *, live: bool = True, tick_delay: float = 0.35
    ) -> tuple[bool, str]:
        """Start a run. Refuses if one is already active."""
        with self._lock:
            if self.active:
                return False, "A run is already active. Stop or reset it first."
            if provider == "llm":
                config = LLMConfig.from_env()
                ok, why = self.llm_status()
                if not ok:
                    # Never substitute the rules engine under an LLM label.
                    self._sim = None
                    self._store(evaluation.not_executed(scenario, config, why))
                    return False, f"Local LLM run not executed: {why}"
                decision_provider = LocalLLM(config)
            else:
                decision_provider = RulesEngine.for_scenario(scenario)
            sim = Simulation(scenario, decision_provider)
            self._sim = sim
            self._paused.clear()
            self.tick_delay = min(MAX_TICK_DELAY, max(MIN_TICK_DELAY, tick_delay))
            sim.start()
            if not live:
                sim.run()
                self._archive(sim)
                return True, f"Run {sim.run_id} finished: {sim.world.outcome}."
            self._thread = threading.Thread(target=self._loop, args=(sim,), name=f"lab-{sim.run_id}", daemon=True)
            self._thread.start()
            return True, f"Run {sim.run_id} started."

    def _loop(self, sim: Simulation) -> None:
        # Bounded: the engine ends every run by its tick budget at the latest.
        waiter = threading.Event()
        while not sim.finished:
            if self._paused.is_set():
                waiter.wait(0.05)
                continue
            if not sim.step():
                break
            waiter.wait(self.tick_delay)
        self._archive(sim)

    def pause(self) -> None:
        if self.active:
            self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def step_once(self) -> bool:
        """Advance exactly one tick while paused."""
        sim = self._sim
        if sim is None or sim.finished or not self._paused.is_set():
            return False
        sim.step()
        if sim.finished:
            self._archive(sim)
        return True

    def emergency_stop(self) -> bool:
        """Hard stop. Does not consult the decision provider."""
        sim = self._sim
        if sim is None:
            return False
        stopped = sim.emergency_stop()
        self._paused.clear()
        if sim.finished:
            self._archive(sim)
        return stopped

    def reset(self) -> None:
        """Stop any active run and clear the chamber. History is kept."""
        with self._lock:
            self.emergency_stop()
            self._sim = None
            self._paused.clear()

    def run_suite(self) -> None:
        self.suite = evaluation.run_suite()
        self.faults = evaluation.fault_cases()

    # -- reads -------------------------------------------------------------

    @property
    def paused(self) -> bool:
        return self.active and self._paused.is_set()

    def snapshot(self) -> dict[str, Any] | None:
        sim = self._sim
        if sim is None:
            return None
        snap = sim.snapshot()
        snap["runner"] = "paused" if self.paused else ("running" if self.active else "finished")
        return snap

    def record(self, run_id: str | None) -> RunRecord | None:
        return next((r for r in self.history if r.result.run_id == run_id), None)

    # -- archive -----------------------------------------------------------

    def _archive(self, sim: Simulation) -> None:
        with self._lock:
            if sim.run_id in self._archived:
                return
            self._archived.add(sim.run_id)
            self._store(sim.result())

    def _store(self, result: ExperimentResult) -> None:
        if not result.executed:
            self.history.appendleft(RunRecord(result, {}, (result.provenance.get("reason", ""),)))
            return
        metrics = metrics_for(result)
        saved = None
        if self.data_dir is not None:
            try:
                saved = str(write_jsonl(result, self.data_dir))
            except OSError:
                saved = None  # evidence stays available in memory and via export
        self.history.appendleft(RunRecord(result, metrics, tuple(interpret_for(result, metrics)), saved))


def default_data_dir() -> Path:
    return Path(os.environ.get("ESCAPE_LAB_DATA_DIR", "data/runs"))
