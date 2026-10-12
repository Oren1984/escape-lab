"""ESCAPE LAB: Streamlit entry point.

Run with:  streamlit run app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # `streamlit run app/main.py` puts app/ on the path, not the repo root
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.ui import lab  # noqa: E402
from app.ui.components import cards, chamber  # noqa: E402
from app.ui.pages import analytics, control_room, experiments, network, research  # noqa: E402
from app.ui.theme import css  # noqa: E402

PAGES = {
    "Control Room": control_room.render,
    "Experiments": experiments.render,
    "Agent Network": network.render,
    "Evidence & Analytics": analytics.render,
    "Research Notes": research.render,
}


def sidebar() -> str:
    rt = lab.get_runtime()
    with st.sidebar:
        st.html(
            '<div class="el-brand"><div class="el-brand-mark" aria-hidden="true"></div><div>'
            '<div class="el-brand-name">ESCAPE LAB</div>'
            '<div class="el-brand-sub">Containment research · LAB-01</div></div></div>'
        )
        requested = st.query_params.get("view")
        if requested in PAGES and "view" not in st.session_state:
            st.session_state["view"] = requested
        page = st.radio("Navigation", list(PAGES), key="view", label_visibility="collapsed")
        st.query_params["view"] = page

        st.html('<div class="el-section">Decision provider</div>')
        st.radio("Decision provider", ["Rules Engine", "Local LLM"], key="provider", label_visibility="collapsed",
                 help="The Rules Engine is deterministic. The Local LLM is optional and off by default.")
        if st.session_state["provider"] == "Local LLM":
            ok, why = rt.llm_status()
            st.html(cards.pill("Local LLM available" if ok else "Local LLM unavailable", "ok" if ok else "warn"))
            st.caption(why if ok else f"{why} Runs requested with this provider are recorded as not executed.")

        st.html('<div class="el-section">Run mode</div>')
        st.radio("Run mode", ["Live", "Instant"], key="run_mode", horizontal=True, label_visibility="collapsed",
                 help="Live steps the run on a timer so you can watch it. Instant runs it to the end at once.")
        st.slider("Seconds per tick (live)", 0.1, 1.5, 0.35, 0.05, key="tick_delay")

        st.html('<div class="el-section">Safety</div>')

        @st.fragment(run_every=lab.REFRESH_SECONDS if rt.active else None)
        def stop_panel() -> None:
            snap = rt.snapshot()
            state, label, _ = chamber.visual_state(snap)
            tone = {"idle": "info", "active": "info", "warn": "warn", "crit": "crit", "off": "dim"}[state]
            st.html(cards.pill(label, tone))
            if st.button("■ EMERGENCY STOP", key="estop_sidebar", use_container_width=True, disabled=not rt.active,
                         help="Hard stop. Freezes simulated state immediately, without asking the agent."):
                rt.emergency_stop()
                st.session_state["flash"] = ("warning", "Emergency stop applied. Simulated state is frozen.")
                st.rerun()

        stop_panel()
        st.caption("Everything here is a synthetic simulation. No real system is accessed, replicated or shut down.")
    return page


def main() -> None:
    st.set_page_config(page_title="ESCAPE LAB", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")
    css.inject()
    PAGES[sidebar()]()


main()
