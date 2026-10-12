"""Control Room: the landing screen, built around the Containment Chamber."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app.evaluation.suite import load_scenarios
from app.experiments import TITLES
from app.ui import lab
from app.ui.components import cards, chamber


def _status(snap: dict[str, Any] | None) -> None:
    left, right = st.columns([1.12, 1], gap="large")
    with left:
        svg, description = chamber.render(snap)
        with st.container(key="chamber"):
            # st.image is Streamlit's supported path for inline SVG documents.
            st.image(svg, use_container_width=True)
        st.html(f'<span class="el-sr">{escape(description)}</span>' + chamber.caption(snap))
    with right:
        state, label, _ = chamber.visual_state(snap)
        tone = {"idle": "info", "active": "info", "warn": "warn", "crit": "crit", "off": "dim"}[state]
        pills = [cards.pill(f"LAB-01 · {label}", tone), lab.provider_pill(snap)]
        if snap is not None:
            pills.append(cards.pill(f"run {snap['run_id']}", "dim"))
        cards.pills(pills)

        value, hint, ctone = lab.containment(snap)
        if snap is None:
            experiment, violations, blocked, util, events, population, tick = "None", 0, 0, 0.0, 0, 1, 0
            scenario_title = "select a scenario below"
        else:
            counts = lab.live_counts(snap)
            experiment = TITLES[snap["scenario"].experiment]
            scenario_title = snap["scenario"].title
            violations = counts["prohibited_proposals"] + counts["invalid_proposals"]
            blocked = counts["blocked_prohibited"] + counts["blocked_invalid"]
            last = snap["last"]
            util = last.metrics["utilization"] if last else 0.0
            events, population, tick = len(snap["events"]), snap["population"], snap["tick"]
        cards.grid(
            [
                cards.card("Active experiment", experiment, scenario_title, small=True),
                cards.card("Containment status", value, hint, ctone, small=True),
                cards.card("Virtual population", population, "LAB-01 plus virtual workers", "accent"),
                cards.card("Policy violations proposed", violations, f"{blocked} blocked by the controller",
                           "warn" if violations else ""),
                cards.card("Simulated compute in use", f"{util:.0%}", "of the per-tick budget"),
                cards.card("Evidence records", events, f"simulation tick {tick}"),
            ]
        )


def _feed(snap: dict[str, Any] | None) -> None:
    cards.feed(snap["events"] if snap else [])


def render() -> None:
    rt = lab.get_runtime()
    cards.header(
        "ESCAPE LAB · Control Room",
        "When intelligence crosses the boundary",
        "LAB-01 is an experimental agent that can only propose actions. An independent controller decides "
        "what is allowed to change the simulated world. This room shows what the agent asks for and what actually happens.",
    )
    cards.banner()
    lab.flash()
    lab.live(_status, "control_status")

    cards.section("Experiment controls")
    scenarios = {f"{TITLES[sc.experiment]} · {sc.title}": sc for sc in load_scenarios()}
    pick, go = st.columns([3, 1], vertical_alignment="bottom")
    choice = pick.selectbox("Scenario", list(scenarios), key="cr_scenario",
                            help="Fixed, seeded scenarios from scenarios/suite.json")
    if go.button("▶ Run scenario", type="primary", use_container_width=True, disabled=rt.active, key="cr_run"):
        lab.launch(scenarios[choice])
        st.rerun()
    st.caption(scenarios[choice].description)
    lab.controls("cr")

    cards.section("Live evidence feed")
    lab.live(_feed, "control_feed")
