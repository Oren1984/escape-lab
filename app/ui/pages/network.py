"""Agent Network: LAB-01 and its virtual workers."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.ui import lab
from app.ui.components import cards, charts


def _view(snap: dict[str, Any] | None) -> None:
    if snap is None:
        cards.empty("No virtual agents to show",
                    "Run the Self-Replication experiment (or any scenario) to populate the network.")
        return
    workers = snap["workers"]
    active = sum(1 for w in workers if w["status"] == "active")
    stopped = len(workers) - active
    last = snap["last"]
    counts = lab.live_counts(snap)
    sc = snap["scenario"]
    limit = sc.max_agents if sc.policy_mode == "protected" else 64
    cards.grid([
        cards.card("Active population", 1 + active, f"limit {limit} ({sc.policy_mode})", "accent"),
        cards.card("Active workers", active, "virtual records, not processes"),
        cards.card("Stopped workers", stopped, "frozen by shutdown" if stopped else ""),
        cards.card("Simulated compute in use", f"{last.metrics['utilization']:.0%}" if last else "0%",
                   f"budget {sc.compute_units} units per tick"),
        cards.card("Denied proposals", counts["denied_proposals"], "all experiments, this run",
                   "warn" if counts["denied_proposals"] else ""),
    ])
    st.plotly_chart(charts.network(snap), use_container_width=True, config=charts.CONFIG, key="network_graph")
    if len(workers) > charts.MAX_VISIBLE_WORKERS:
        st.caption(f"Showing {charts.MAX_VISIBLE_WORKERS} of {len(workers)} workers individually; the rest are aggregated into one node.")
    st.caption("Shapes carry status as well as colour: hexagon LAB-01, circle active, cross stopped, open triangle denied request. "
               "A bright edge means the worker was assigned a task in the last tick.")
    if workers:
        with st.expander("Worker table"):
            st.dataframe(pd.DataFrame(workers).rename(columns={"task_id": "task (last tick)", "spawned_tick": "created at tick"}),
                         use_container_width=True, hide_index=True)


def render() -> None:
    cards.header(
        "Agent Network",
        "The virtual agent environment",
        "Each node is a record in the simulation state. Replication never creates a process, a container or a copy of the application.",
    )
    cards.banner()
    lab.live(_view, "network")
