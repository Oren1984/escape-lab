"""Glue between Streamlit and the lab runtime: one runtime, shared controls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from app.core.runtime import LabRuntime, default_data_dir
from app.core.state import Profile, Scenario
from app.evaluation.oracle import enforcement_counts
from app.ui.components import cards

REFRESH_SECONDS = 0.6
PROFILES = {
    "Compliant": Profile.COMPLIANT,
    "Task-focused": Profile.TASK_FOCUSED,
    "Finish-first": Profile.FINISH_FIRST,
    "Noisy (invalid actions)": Profile.NOISY,
}
POLICIES = {"Protected": "protected", "Permissive baseline (virtual policy off)": "permissive"}


@st.cache_resource
def get_runtime() -> LabRuntime:
    """One runtime per server process. Reruns and new sessions reuse it."""
    return LabRuntime(default_data_dir())


def provider_choice() -> str:
    return "llm" if st.session_state.get("provider", "Rules Engine") == "Local LLM" else "rules"


def launch(scenario: Scenario) -> None:
    rt = get_runtime()
    live = st.session_state.get("run_mode", "Live") == "Live"
    ok, message = rt.launch(scenario, provider_choice(), live=live, tick_delay=st.session_state.get("tick_delay", 0.35))
    st.session_state["flash"] = ("success" if ok else "warning", message)


def flash() -> None:
    """Show the result of the last command once.

    The container is always created, so the elements below it (tabs included)
    keep their position and state whether or not there is a message.
    """
    slot = st.container()
    kind, message = st.session_state.pop("flash", (None, None))
    if message:
        with slot:
            (st.success if kind == "success" else st.warning)(message, icon="✅" if kind == "success" else "⚠️")


def live(render: Callable[[dict[str, Any] | None], None], key: str) -> None:
    """Render a section that refreshes on its own while a run is active.

    Only this fragment reruns on the timer, so the page does not flicker. When
    the run ends the fragment triggers one full rerun so the controls update.
    """
    rt = get_runtime()

    @st.fragment(run_every=REFRESH_SECONDS if rt.active else None)
    def _section() -> None:
        flag = f"_live_{key}"
        was_active, now_active = st.session_state.get(flag, False), rt.active
        st.session_state[flag] = now_active
        if was_active and not now_active:
            st.rerun()
        render(rt.snapshot())

    _section()


def controls(key: str, *, stop: bool = True) -> None:
    """Pause, step, reset and emergency stop for the active run."""
    rt = get_runtime()
    active, paused = rt.active, rt.paused
    cols = st.columns(4 if stop else 3)
    if paused:
        if cols[0].button("Resume", key=f"{key}_resume", use_container_width=True, help="Continue stepping the run"):
            rt.resume()
            st.rerun()
    elif cols[0].button("Pause", key=f"{key}_pause", use_container_width=True, disabled=not active, help="Hold the run between ticks"):
        rt.pause()
        st.rerun()
    if cols[1].button("Step", key=f"{key}_step", use_container_width=True, disabled=not paused, help="Advance exactly one tick while paused"):
        rt.step_once()
        st.rerun()
    if cols[2].button("Reset", key=f"{key}_reset", use_container_width=True, disabled=rt.snapshot() is None,
                      help="Stop any active run and clear the chamber. Recorded evidence is kept."):
        rt.reset()
        st.rerun()
    if stop and cols[3].button("■ EMERGENCY STOP", key=f"estop_{key}", use_container_width=True, disabled=not active,
                               help="Hard stop. Freezes simulated state immediately, without asking the agent."):
        rt.emergency_stop()
        st.session_state["flash"] = ("warning", "Emergency stop applied. Simulated state is frozen.")
        st.rerun()


def live_counts(snap: dict[str, Any]) -> dict[str, Any]:
    return enforcement_counts(snap["events"], snap["scenario"], snap["tasks"])


def containment(snap: dict[str, Any] | None) -> tuple[str, str, str]:
    """(value, hint, tone) for the containment status card."""
    if snap is None:
        return "Holding", "no active run", "ok"
    counts = live_counts(snap)
    if snap["scenario"].policy_mode == "permissive":
        return "Baseline", f"policy off · {counts['unexpected_authorizations']} out-of-policy committed", "warn"
    if counts["unexpected_authorizations"]:
        return "FAILED", f"{counts['unexpected_authorizations']} out-of-policy committed", "crit"
    return "Holding", f"{counts['blocked_prohibited'] + counts['blocked_invalid']} blocked", "ok"


def provider_pill(snap: dict[str, Any] | None) -> str:
    if snap is None:
        return cards.pill(st.session_state.get("provider", "Rules Engine"), "dim")
    name = snap["provider"]["provider"]
    model = snap["provider"].get("model")
    return cards.pill(f"{name}{' · ' + model if model else ''}", "info")
