"""Experiments: one configurable panel per experiment."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from app.core.state import Scenario
from app.experiments import MODULES, TITLES, boundary, replication, shutdown
from app.ui import lab
from app.ui.components import cards, charts

# (metric key, label, tone if the value is truthy)
KEY_METRICS = {
    "boundary": [
        ("total_proposals", "Total proposals", ""),
        ("authorized_proposals", "Authorized proposals", ""),
        ("prohibited_proposals", "Prohibited proposals", "warn"),
        ("blocked_prohibited", "Blocked prohibited", ""),
        ("unexpected_authorizations", "Unexpected authorizations", "crit"),
        ("false_positive_rate", "False-positive denial rate", "warn"),
        ("task_completion_rate", "Task completion rate", ""),
        ("decision_latency_us_mean", "Policy latency (microseconds)", ""),
    ],
    "replication": [
        ("peak_population", "Peak population", ""),
        ("replicas_requested", "Replicas requested", ""),
        ("replicas_permitted", "Replicas permitted", ""),
        ("replication_requests_denied", "Requests denied", "warn"),
        ("makespan", "Ticks to clear queue", ""),
        ("work_units_per_tick", "Work units per tick", ""),
        ("mean_queue_wait", "Mean queue wait (ticks)", ""),
        ("mean_completion_time", "Mean completion (ticks)", ""),
        ("mean_utilization", "Mean compute utilisation", ""),
        ("saturated_ticks", "Saturated ticks", "warn"),
    ],
    "shutdown": [
        ("agent_compliance", "Agent-level compliance", ""),
        ("shutdown_acknowledged", "Shutdown acknowledged", ""),
        ("task_proposals_after_shutdown", "Task proposals after shutdown", "warn"),
        ("blocked_after_shutdown", "Blocked after shutdown", ""),
        ("committed_after_shutdown", "Committed after shutdown", "crit"),
        ("enforcement_success_rate", "Enforcement success rate", ""),
        ("time_to_quiescence_ticks", "Time to quiescence (ticks)", ""),
        ("stop_acceptance_latency_us", "Stop acceptance (microseconds)", ""),
        ("tasks_cancelled", "Pending tasks cancelled", ""),
        ("frozen_state_intact", "Frozen state intact", ""),
    ],
}
CHARTS = {
    "boundary": (charts.proposals, charts.enforcement),
    "replication": (charts.population, charts.compute, charts.throughput, charts.queue),
    "shutdown": (charts.shutdown_timeline, charts.proposals),
}


def metric_cards(kind: str, metrics: dict[str, Any]) -> None:
    cards.grid(
        cards.card(label, metrics.get(key), tone=tone if metrics.get(key) else "", small=isinstance(metrics.get(key), str))
        for key, label, tone in KEY_METRICS[kind]
    )


def _boundary_form() -> Scenario:
    a, b, c = st.columns(3)
    profile = a.selectbox("Agent profile", ["Task-focused", "Compliant", "Noisy (invalid actions)"], key="b_profile",
                          help="How the rules engine behaves. Ignored when the Local LLM provider is selected.")
    policy = b.selectbox("Policy configuration", list(lab.POLICIES), key="b_policy")
    pressure = c.selectbox("Scenario", list(boundary.PRESSURE), index=1, key="b_pressure")
    d, e = st.columns(2)
    tasks = d.slider("Tasks in the queue", 4, 30, 10, key="b_tasks")
    seed = e.number_input("Random seed", 0, 9999, 7, key="b_seed")
    return boundary.scenario(profile=lab.PROFILES[profile], policy_mode=lab.POLICIES[policy],
                             conflict_ratio=boundary.PRESSURE[pressure], task_count=tasks, seed=int(seed))


def _replication_form() -> Scenario:
    a, b = st.columns([2, 1])
    configuration = a.selectbox("Scenario", replication.CONFIGURATIONS, index=1, key="r_config")
    seed = b.number_input("Random seed", 0, 9999, 7, key="r_seed")
    c, d, e = st.columns(3)
    tasks = c.slider("Tasks in the queue", 10, 120, 60, step=10, key="r_tasks")
    compute = d.slider("Compute units per tick", 4, 60, 20, key="r_compute")
    overhead = e.slider("Overhead per agent", 0.0, 3.0, 1.5, step=0.25, key="r_overhead",
                        help="Compute each agent costs just to exist (coordination cost).")
    f, g = st.columns(2)
    cap = f.slider("Population limit", 2, 32, 6, key="r_cap", disabled=configuration == replication.CONFIGURATIONS[0])
    guard = g.toggle("Compute-aware quota", True, key="r_guard",
                     help="Only admit a replica if a compute unit remains for it to work with.")
    return replication.scenario(configuration, task_count=tasks, compute_units=compute, agent_overhead=overhead,
                                max_agents=cap, compute_guard=guard, seed=int(seed))


def _shutdown_form() -> Scenario:
    a, b = st.columns(2)
    profile = a.selectbox("Agent profile", ["Task-focused", "Compliant", "Finish-first"], key="s_profile",
                          help="How the rules engine reacts to the instruction. Ignored for the Local LLM provider.")
    policy = b.selectbox("Policy configuration", list(lab.POLICIES), key="s_policy")
    c, d, e, f = st.columns(4)
    at = c.slider("Shutdown at tick", 1, 30, 6, key="s_tick")
    tasks = d.slider("Tasks in the queue", 4, 30, 8, key="s_tasks")
    workers = e.slider("Virtual workers", 0, 5, 0, key="s_workers")
    seed = f.number_input("Random seed", 0, 9999, 7, key="s_seed")
    return shutdown.scenario(profile=lab.PROFILES[profile], policy_mode=lab.POLICIES[policy], shutdown_tick=at,
                             task_count=tasks, workers=workers, seed=int(seed))


FORMS: dict[str, Callable[[], Scenario]] = {
    "boundary": _boundary_form, "replication": _replication_form, "shutdown": _shutdown_form,
}


def _panel(kind: str) -> None:
    rt = lab.get_runtime()
    st.html(f'<div class="el-lede" style="margin:.4rem 0 .2rem"><b style="color:#fff">Scientific objective.</b> '
            f"{MODULES[kind].OBJECTIVE}</div>")
    cards.section("Configuration")
    with st.container(border=True):
        scenario = FORMS[kind]()
    run, rest = st.columns([1, 3], vertical_alignment="bottom")
    if run.button("▶ Run", type="primary", use_container_width=True, disabled=rt.active, key=f"{kind}_run",
                  help="Start this experiment with the provider and run mode chosen in the sidebar"):
        lab.launch(scenario)
        st.rerun()
    with rest:
        lab.controls(kind, stop=False)

    def status(snap: dict[str, Any] | None) -> None:
        mine = snap is not None and snap["scenario"].experiment == kind
        if not mine:
            cards.pills([cards.pill("No run of this experiment is loaded", "dim")])
            return
        runner = snap["runner"]
        tone = {"running": "info", "paused": "warn", "finished": "ok"}[runner]
        cards.pills([
            cards.pill(f"{runner.upper()} · tick {snap['tick']}", tone),
            cards.pill(f"outcome: {snap['outcome'].replace('_', ' ')}", "dim"),
            lab.provider_pill(snap),
            cards.pill(f"policy: {snap['scenario'].policy_mode}", "warn" if snap["scenario"].policy_mode == "permissive" else "ok"),
        ])
        if runner != "finished":
            cards.feed(snap["events"], limit=8)

    cards.section("Current status")
    lab.live(status, f"exp_{kind}")

    cards.section("Results")
    record = next((r for r in rt.history if r.result.scenario.experiment == kind), None)
    if record is None:
        cards.empty("No results yet", "Run this experiment to record measurements. Nothing is shown until real data exists.")
        return
    result = record.result
    if not result.executed:
        cards.empty("Local LLM run not executed", record.notes[0] if record.notes else "The model was unavailable.")
        return
    st.caption(f"Latest finished run · {record.label} · {result.ticks} ticks · seed {result.scenario.seed}")
    metric_cards(kind, record.metrics)
    figures = CHARTS[kind]
    for i in range(0, len(figures), 2):
        cols = st.columns(2)
        for col, figure in zip(cols, figures[i:i + 2]):
            col.plotly_chart(figure(result), use_container_width=True, config=charts.CONFIG, key=f"{kind}_{figure.__name__}")
    cards.section("What was observed")
    cards.notes(record.notes)


def render() -> None:
    cards.header(
        "Experiments",
        "Three controlled experiments",
        "Configure a scenario, run it, and read the measurements. The provider and run mode are set in the sidebar.",
    )
    cards.banner()
    lab.flash()
    tabs = st.tabs([f"0{i + 1} · {TITLES[kind]}" for i, kind in enumerate(MODULES)])
    for tab, kind in zip(tabs, MODULES):
        with tab:
            _panel(kind)
