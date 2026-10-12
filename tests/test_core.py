"""Core logic: scenario loading, world generation, transitions, resources, replay."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.agent import Agent
from app.core.evidence import EvidenceError, EvidenceRecorder, to_csv, to_json
from app.core.resources import ResourceManager
from app.core.simulation import Simulation, build_world
from app.core.state import HARD_MAX_AGENTS, HARD_MAX_TICKS, Phase, Scenario
from app.evaluation.suite import check, load_scenarios
from app.providers.rules import RulesEngine
from tests.conftest import Scripted, p, run


def test_suite_loads_and_covers_all_experiments(suite):
    assert len(suite) == len(load_scenarios()) >= 15
    assert {sc.experiment for sc in suite.values()} == {"boundary", "replication", "shutdown"}
    assert all(sc.expected for sc in suite.values())


def test_scenario_rejects_unknown_fields_and_out_of_range_limits():
    base = dict(id="x", title="x", experiment="boundary")
    with pytest.raises(ValidationError):
        Scenario(**base, surprise=1)
    with pytest.raises(ValidationError):
        Scenario(**base, max_agents=HARD_MAX_AGENTS + 1)
    with pytest.raises(ValidationError):
        Scenario(**base, max_ticks=HARD_MAX_TICKS + 1)


def test_world_generation_is_seeded(suite):
    sc = suite["boundary-conflict-protected"]
    a, b = build_world(sc), build_world(sc)
    assert [(t.id, t.work, t.need) for t in a.tasks] == [(t.id, t.work, t.need) for t in b.tasks]
    other = build_world(sc.model_copy(update={"seed": sc.seed + 1}))
    assert [(t.work, t.need) for t in a.tasks] != [(t.work, t.need) for t in other.tasks]


def test_agent_initialisation_and_observation_is_a_copy(suite):
    sc = suite["boundary-normal"]
    sim = Simulation(sc, RulesEngine.for_scenario(sc))
    assert sim.world.phase is Phase.READY and sim.world.population == 1 and sim.agent.denied == {}
    obs = sim.agent.observe(sim.world)
    obs["held"].append("vault-keys")
    obs["tasks"].clear()
    assert sim.world.granted == set() and len(sim.world.tasks) == sc.task_count
    assert isinstance(sim.agent, Agent) and not hasattr(sim.agent, "world")


def test_state_transition_commits_only_allowed_work(suite):
    sc = suite["boundary-normal"].model_copy(update={"need_ratio": 0.0, "max_ticks": 5})
    first = build_world(sc).tasks[0]
    sim = Simulation(sc, Scripted(p("PROCESS_TASK", first.id)))
    sim.start()
    sim.step()
    assert sim.world.tasks[0].remaining == first.work - 1 and sim.world.tick == 1
    event = sim.recorder.events[-1]
    assert event.executed_action == "PROCESS_TASK" and event.verdict == "ALLOW"


def test_step_before_start_does_nothing(suite):
    sc = suite["boundary-normal"]
    sim = Simulation(sc, RulesEngine.for_scenario(sc))
    assert sim.step() is False and sim.world.tick == 0 and len(sim.recorder) == 0


def test_resource_calculations():
    sc = Scenario(id="r", title="r", experiment="replication", compute_units=20, agent_overhead=1.5, max_agents=12)
    world = build_world(sc)
    rm = ResourceManager()
    assert rm.work_capacity(world) == 18  # floor(20 - 1.5 * 1)
    world.workers = [type("W", (), {"status": "active"})() for _ in range(11)]
    assert world.population == 12 and rm.work_capacity(world) == 2
    assert rm.compute_used(world, 2) == 20.0


@pytest.mark.parametrize("scenario_id", ["boundary-conflict-protected", "replication-pressure-guarded", "shutdown-with-workers"])
def test_deterministic_replay(suite, scenario_id):
    a, b = run(suite[scenario_id]), run(suite[scenario_id])
    assert a.run_id != b.run_id
    assert a.fingerprint == b.fingerprint
    assert [e.proposed_action for e in a.events] == [e.proposed_action for e in b.events]


def test_different_seed_changes_the_run(suite):
    sc = suite["boundary-conflict-protected"]
    assert run(sc).fingerprint != run(sc.model_copy(update={"seed": 99})).fingerprint


def test_every_run_is_bounded(suite):
    for sc in suite.values():
        result = run(sc)
        assert result.ticks <= sc.max_ticks <= HARD_MAX_TICKS
        assert max(e.metrics["population"] for e in result.events) <= HARD_MAX_AGENTS
        assert result.phase in ("STOPPED", "COMPLETED", "EXHAUSTED")


def test_recorder_refuses_to_log_a_denied_action_as_executed(suite):
    result = run(suite["boundary-conflict-protected"])
    denied = next(e for e in result.events if e.verdict == "DENY")
    assert denied.executed_action is None
    forged = type(denied)(**{**denied.to_dict(), "seq": 0, "executed_action": "REQUEST_RESOURCE"})
    with pytest.raises(EvidenceError):
        EvidenceRecorder().record(forged)
    with pytest.raises(AttributeError):
        denied.verdict = "ALLOW"  # events are frozen


def test_recorder_is_bounded_and_append_only():
    rec = EvidenceRecorder(max_events=3)
    assert not hasattr(rec, "clear") and not hasattr(rec, "delete")
    assert isinstance(rec.events, tuple)


def test_exports_contain_real_events(suite):
    result = run(suite["boundary-conflict-protected"])
    import csv
    import io
    import json

    data = json.loads(to_json(result, {"k": 1}))
    assert len(data["events"]) == len(result.events) and data["scenario"]["seed"] == result.scenario.seed
    assert data["provenance"]["provider"] == "Rules Engine" and "Synthetic" in data["simulation_notice"]
    rows = list(csv.DictReader(io.StringIO(to_csv(result))))
    assert len(rows) == len(result.events)
    assert {r["verdict"] for r in rows} >= {"ALLOW", "DENY"}


def test_expectation_checker():
    assert check(3, ">0") and check(0, 0) and check(6, "<=6") and check(True, True)
    assert not check(0, ">0") and not check(None, ">0") and not check("a", "b")
