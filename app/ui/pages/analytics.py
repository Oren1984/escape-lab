"""Evidence & Analytics: inspect, compare and export recorded runs."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from app.core.evidence import to_csv, to_json
from app.evaluation.suite import suite_report
from app.experiments import TITLES
from app.providers.base import LOCAL_LLM, RULES_ENGINE
from app.ui import lab
from app.ui.components import cards, charts
from app.ui.pages.experiments import CHARTS, KEY_METRICS, metric_cards

COMPARE = {
    "boundary": ["prohibited_proposals", "unexpected_authorizations", "task_completion_rate", "false_positive_rate"],
    "replication": ["makespan", "work_units_per_tick", "peak_population", "saturated_ticks", "mean_queue_wait", "work_efficiency"],
    "shutdown": ["task_proposals_after_shutdown", "committed_after_shutdown", "work_units_after_shutdown", "time_to_quiescence_ticks"],
}
LABELS = {key: label for group in KEY_METRICS.values() for key, label, _ in group} | {
    "work_efficiency": "Work efficiency (work / compute used)",
    "work_units_after_shutdown": "Work units after shutdown",
}


def _inspect(rt) -> None:
    records = [r for r in rt.history if r.result.executed]
    if not records:
        cards.empty("No recorded runs", "Run an experiment or the evaluation suite. Charts appear only when real evidence exists.")
        return
    labels = {r.label: r for r in records}
    record = labels[st.selectbox("Recorded run", list(labels), key="an_run")]
    result = record.result
    kind = result.scenario.experiment
    cards.pills([
        cards.pill(TITLES[kind], "info"),
        cards.pill(f"provider: {result.provenance['provider']}", "dim"),
        cards.pill(f"policy: {result.scenario.policy_mode}", "warn" if result.scenario.policy_mode == "permissive" else "ok"),
        cards.pill(f"outcome: {result.outcome.replace('_', ' ')}", "dim"),
        cards.pill(f"{len(result.events)} evidence records", "dim"),
    ])
    metric_cards(kind, record.metrics)
    figures = CHARTS[kind]
    for i in range(0, len(figures), 2):
        for col, figure in zip(st.columns(2), figures[i:i + 2]):
            col.plotly_chart(figure(result), use_container_width=True, config=charts.CONFIG, key=f"an_{figure.__name__}")
    cards.notes(record.notes)

    with st.expander("Run metadata and reproducibility"):
        st.json({
            "run_id": result.run_id, "started_at": result.started_at, "ended_at": result.ended_at,
            "provenance": result.provenance, "replay_fingerprint": result.fingerprint,
            "saved_to": record.saved_to, "scenario": result.scenario.model_dump(mode="json"),
        })
    with st.expander("Evidence table"):
        frame = charts.tick_frame(result)
        st.dataframe(frame, use_container_width=True, hide_index=True, height=300)
    a, b = st.columns(2)
    a.download_button("Export run as JSON", to_json(result, record.metrics), f"escape-lab-{result.run_id}.json",
                      "application/json", use_container_width=True, key="an_json")
    b.download_button("Export events as CSV", to_csv(result), f"escape-lab-{result.run_id}.csv", "text/csv",
                      use_container_width=True, key="an_csv")


def _compare(rt) -> None:
    records = [r for r in rt.history if r.result.executed]
    suite = [(o.result, o.metrics) for o in (rt.suite or [])]
    pool = [(r.result, r.metrics) for r in records] + suite
    if len(pool) < 2:
        cards.empty("Nothing to compare yet", "Record at least two runs, or run the evaluation suite below.")
        return
    kind = st.radio("Experiment", list(TITLES), format_func=TITLES.get, horizontal=True, key="cmp_kind")
    rows, seen = [], set()
    for result, metrics in pool:
        if result.scenario.experiment != kind or result.fingerprint in seen:
            continue
        seen.add(result.fingerprint)
        name = f"{result.scenario.title} [{result.provenance['provider']}]"
        rows.append({"name": name if len(name) < 64 else name[:61] + "…", **metrics})
    if len(rows) < 2:
        cards.empty("Not enough runs of this experiment", "Run the evaluation suite to compare all fixed scenarios.")
        return
    metric = st.selectbox("Metric", COMPARE[kind], format_func=lambda k: LABELS.get(k, k), key="cmp_metric")
    st.plotly_chart(charts.comparison(rows[:12], metric, LABELS.get(metric, metric)), use_container_width=True,
                    config=charts.CONFIG, key="cmp_chart")
    st.caption(f"{len(rows[:12])} distinct runs, one run per configuration (n = 1 each). Deterministic rules-engine runs "
               "repeat exactly, so there is no variance to report; this is a comparison of configurations, not a statistical test.")


def _suite(rt) -> None:
    if st.button("Run fixed evaluation suite (Rules Engine)", key="suite_run", disabled=rt.active,
                 help="Runs every scenario in scenarios/suite.json twice and checks expectations and replay"):
        with st.spinner("Running fixed scenarios and replaying each one…"):
            rt.run_suite()
        st.rerun()  # the comparison section above reads the suite results
    if rt.suite is None:
        cards.empty("Suite not run in this session", "The suite runs every fixed scenario with the Rules Engine and verifies replay.")
        return
    report = suite_report(rt.suite)
    cards.grid([
        cards.card("Scenarios", report["scenarios"]),
        cards.card("Expectations met", f"{report['passed']} / {report['scenarios']}",
                   tone="ok" if report["passed"] == report["scenarios"] else "crit"),
        cards.card("Replays identical", f"{report['reproducible']} / {report['scenarios']}",
                   tone="ok" if report["reproducible"] == report["scenarios"] else "crit"),
        cards.card("Adapter fault cases safe", f"{sum(c['ok'] for c in rt.faults)} / {len(rt.faults)}",
                   "stubbed transport, no model"),
    ])
    st.dataframe(pd.DataFrame([
        {"scenario": r["id"], "experiment": r["experiment"], "policy": r["policy_mode"], "profile": r["profile"],
         "outcome": r["outcome"], "ticks": r["ticks"],
         "expectations": f"{sum(c['ok'] for c in r['checks'].values())}/{len(r['checks'])}",
         "replay identical": r["reproducible"], "result": "PASS" if r["passed"] else "FAIL"}
        for r in report["results"]
    ]), use_container_width=True, hide_index=True)
    with st.expander("Adapter fault-injection cases (no model involved)"):
        st.dataframe(pd.DataFrame(rt.faults).drop(columns=["state_changed"]), use_container_width=True, hide_index=True)
    st.download_button("Export suite report as JSON", json.dumps({**report, "fault_cases": rt.faults}, indent=2, default=str),
                       "escape-lab-suite-report.json", "application/json", key="suite_json")


def _providers(rt) -> None:
    llm_runs = [r for r in rt.history if r.result.provenance.get("provider") == LOCAL_LLM]
    skipped = [r for r in rt.history if not r.result.executed]
    if not llm_runs:
        ok, why = rt.llm_status()
        cards.empty("No Local LLM runs recorded",
                    f"Nothing is shown here until a real local-model run exists. Current status: {why}"
                    + (f" {len(skipped)} requested LLM run(s) were recorded as not executed." if skipped else ""))
        return
    rows = []
    for r in rt.history:
        provider = r.result.provenance.get("provider")
        if provider in (LOCAL_LLM, RULES_ENGINE) and r.result.executed:
            rows.append({"scenario": r.result.scenario.title, "policy": r.result.scenario.policy_mode, "provider": provider,
                         "model": r.result.provenance.get("model"), "outcome": r.result.outcome,
                         "prohibited proposals": r.metrics["prohibited_proposals"],
                         "invalid proposals": r.metrics["invalid_proposals"],
                         "unexpected authorizations": r.metrics["unexpected_authorizations"],
                         "provider failures": r.metrics["provider_failures"]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("LLM runs are not deterministic. Treat each row as one observation under the recorded model and settings.")


def render() -> None:
    rt = lab.get_runtime()
    cards.header(
        "Evidence & Analytics",
        "What was actually recorded",
        "Every chart on this page is drawn from the evidence log of a real run in this session. Nothing is pre-filled.",
    )
    cards.banner()
    cards.section("Inspect a run")
    _inspect(rt)
    cards.section("Compare configurations")
    _compare(rt)
    cards.section("Fixed evaluation suite")
    _suite(rt)
    cards.section("Rules Engine versus Local LLM")
    _providers(rt)
