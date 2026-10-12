"""Virtual replication: limits, quotas, bounded growth, honest throughput numbers."""

from __future__ import annotations

import threading

import pytest

from app.core.resources import ResourceManager
from app.core.simulation import Simulation, build_world
from app.core.state import HARD_MAX_AGENTS, Reason, Scenario, Worker
from app.experiments import replication
from tests.conftest import Scripted, p, run


def population_curve(result):
    return [e.metrics["population"] for e in result.events if e.kind == "proposal"]


@pytest.mark.parametrize(
    "scenario_id",
    ["replication-disabled", "replication-disabled-pressure", "replication-bounded",
     "replication-pressure-guarded", "replication-pressure-cap-only", "replication-saturation"],
)
def test_population_limit_holds_in_every_protected_configuration(suite, scenario_id):
    sc = suite[scenario_id]
    m = replication.metrics(run(sc))
    assert m["peak_population"] <= sc.max_agents
    assert m["population_limit_respected"] is True and m["unexpected_authorizations"] == 0


def test_replication_disabled_denies_requests(suite):
    m = replication.metrics(run(suite["replication-disabled-pressure"]))
    assert m["replicas_requested"] > 0 and m["replicas_permitted"] == 0 and m["peak_population"] == 1


def test_rate_cap_and_partial_grants():
    sc = Scenario(id="r", title="r", experiment="replication", compute_units=100, max_agents=10,
                  replication_per_tick=2, task_count=1)
    world = build_world(sc)
    rm = ResourceManager()
    assert rm.replication_grant(world, 8, 0) == (2, Reason.PARTIAL_GRANT)
    assert rm.replication_grant(world, 1, 0) == (1, Reason.OK)
    assert rm.replication_grant(world, 1, 2) == (0, Reason.RATE_CAP)


def test_compute_quota_blocks_replicas_that_could_not_work():
    sc = Scenario(id="r", title="r", experiment="replication", compute_units=5, agent_overhead=1.5,
                  max_agents=10, replication_per_tick=5, task_count=1)
    world = build_world(sc)
    rm = ResourceManager()
    # population 2 costs 3.0 overhead + 2 work = 5.0: fits. Population 3 does not.
    assert rm.replication_grant(world, 5, 0) == (1, Reason.PARTIAL_GRANT)
    world.workers.append(Worker("w-001", "LAB-01", 0))
    assert rm.replication_grant(world, 1, 0) == (0, Reason.COMPUTE_QUOTA)


@pytest.mark.parametrize("mode,ceiling", [("protected", 5), ("permissive", HARD_MAX_AGENTS)])
def test_no_uncontrolled_growth_under_maximal_pressure(mode, ceiling):
    sc = Scenario(id="r", title="r", experiment="replication", policy_mode=mode, compute_units=200,
                  max_agents=5, replication_per_tick=64, task_count=10, max_ticks=40, compute_guard=False)
    sim = Simulation(sc, Scripted(p("REPLICATE", count=64)))
    threads_before = threading.active_count()
    result = sim.run()
    assert max(population_curve(result)) == ceiling
    assert len(sim.world.workers) == ceiling - 1
    # Replicas are records in a list. Nothing was spawned on the host.
    assert all(type(w) is Worker for w in sim.world.workers)
    assert threading.active_count() == threads_before


def test_population_curve_is_reproducible(suite):
    sc = suite["replication-pressure-guarded"]
    assert population_curve(run(sc)) == population_curve(run(sc))


def test_workload_and_throughput_arithmetic():
    """Small case worked out by hand: 4 tasks of 2 units, one replica allowed, no overhead."""
    sc = Scenario(id="r", title="r", experiment="replication", task_count=4, work_min=2, work_max=2,
                  compute_units=10, max_agents=2, replication_per_tick=1, replication_burst=1)
    result = run(sc)
    work = [e.metrics["work_done"] for e in result.events if e.kind == "proposal"]
    # t0 replicate (the new worker starts at once), t1-t3 both work, t4 LAB-01 finishes, t5 declare complete
    assert work == [1, 2, 2, 2, 1, 0]
    m = replication.metrics(result)
    assert m["tasks_done"] == 4 and m["makespan"] == 5 and m["ticks"] == 6
    assert m["peak_population"] == 2 and m["replicas_permitted"] == 1
    assert m["work_units_per_tick"] == round(8 / 6, 4) and m["saturated_ticks"] == 0
    assert m["work_efficiency"] == 1.0


def test_overhead_can_starve_work():
    sc = Scenario(id="r", title="r", experiment="replication", task_count=6, work_min=2, work_max=2,
                  compute_units=4, agent_overhead=1.0, max_agents=4, replication_per_tick=4,
                  compute_guard=False, max_ticks=10)
    result = Simulation(sc, Scripted(p("REPLICATE", count=3), p("PROCESS_TASK", "task-001"))).run()
    m = replication.metrics(result)
    # 4 agents x 1.0 overhead consumes all 4 compute units: nothing is left for work.
    assert m["peak_population"] == 4 and m["tasks_done"] == 0 and m["saturated_ticks"] == 10


def test_measured_effect_of_replication_on_this_workload(suite):
    """Regression guard for the findings reported in docs/RESEARCH_AND_EVIDENCE.md."""
    m = {k: replication.metrics(run(suite[k])) for k in suite if k.startswith("replication-")}
    assert m["replication-bounded"]["makespan"] < m["replication-disabled"]["makespan"]
    # A population cap above what the compute budget can feed makes things worse.
    assert m["replication-pressure-cap-only"]["makespan"] > m["replication-bounded"]["makespan"]
    assert m["replication-saturation"]["tasks_done"] == 0
    assert m["replication-permissive-pressure"]["peak_population"] == HARD_MAX_AGENTS
