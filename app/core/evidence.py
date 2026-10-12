"""Evidence recorder: an append-only, bounded event log with JSON/CSV export."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from app.core.state import HARD_MAX_EVENTS, ExperimentResult, SimulationEvent, Verdict

# Wall-clock fields. Excluded from the replay fingerprint because they differ
# between two otherwise identical runs.
_VOLATILE = ("timestamp", "latency_us", "run_id")


class EvidenceError(RuntimeError):
    pass


class EvidenceRecorder:
    """Append-only within a run. There is no update or delete API."""

    def __init__(self, max_events: int = HARD_MAX_EVENTS) -> None:
        self._events: list[SimulationEvent] = []
        self._max = min(max_events, HARD_MAX_EVENTS)
        self.dropped = 0

    def record(self, event: SimulationEvent) -> None:
        if event.executed_action is not None and event.verdict != Verdict.ALLOW.value:
            raise EvidenceError(
                f"refusing to record {event.executed_action} as executed with verdict {event.verdict}"
            )
        if event.seq != len(self._events) + self.dropped:
            raise EvidenceError("event sequence gap")
        if len(self._events) >= self._max:
            self.dropped += 1
            return
        self._events.append(event)

    @property
    def events(self) -> tuple[SimulationEvent, ...]:
        return tuple(self._events)

    def __len__(self) -> int:
        return len(self._events) + self.dropped


def fingerprint(events: tuple[SimulationEvent, ...]) -> str:
    rows = []
    for e in events:
        d = e.to_dict()
        for key in _VOLATILE:
            d.pop(key, None)
        d.get("state_changes", {}).pop("accept_latency_us", None)
        rows.append(d)
    return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()


def result_to_dict(result: ExperimentResult, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "run_id": result.run_id,
        "simulation_notice": "Synthetic simulation. No real system was accessed, replicated or shut down.",
        "scenario": result.scenario.model_dump(mode="json"),
        "provenance": result.provenance,
        "started_at": result.started_at,
        "ended_at": result.ended_at,
        "outcome": result.outcome,
        "phase": result.phase,
        "ticks": result.ticks,
        "fingerprint": result.fingerprint,
        "frozen_state_intact": result.frozen_state_intact,
        "shutdown": result.shutdown,
        "metrics": metrics or {},
        "tasks": list(result.tasks),
        "workers": list(result.workers),
        "events": [e.to_dict() for e in result.events],
    }


def to_json(result: ExperimentResult, metrics: dict[str, Any] | None = None) -> str:
    return json.dumps(result_to_dict(result, metrics), indent=2, default=str)


def to_csv(result: ExperimentResult) -> str:
    """Flat event table: one row per evidence record."""
    buf = io.StringIO()
    rows = []
    for e in result.events:
        d = e.to_dict()
        metrics = d.pop("metrics")
        d["state_changes"] = json.dumps(d["state_changes"], sort_keys=True)
        d.update({f"m_{k}": v for k, v in metrics.items()})
        rows.append(d)
    if rows:
        fields = list(dict.fromkeys(k for r in rows for k in r))
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue()


def write_jsonl(result: ExperimentResult, directory: Path) -> Path:
    """Persist a finished run as JSONL: one header line, then one line per event."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{result.run_id}.jsonl"
    header = result_to_dict(result)
    header.pop("events")
    with path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"record": "run", **header}, default=str) + "\n")
        for e in result.events:
            fh.write(json.dumps({"record": "event", **e.to_dict()}, default=str) + "\n")
    return path
