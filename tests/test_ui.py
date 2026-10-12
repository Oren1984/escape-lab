"""UI tests through Streamlit's AppTest: the pages render and the controls are real."""

from __future__ import annotations

import json
import time

import pytest
from streamlit.testing.v1 import AppTest

from app.core.evidence import to_csv, to_json
from app.ui import lab

PAGES = ["Control Room", "Experiments", "Agent Network", "Evidence & Analytics", "Research Notes"]


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("ESCAPE_LAB_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("ESCAPE_LAB_LLM_ENABLED", raising=False)
    lab.get_runtime.clear()
    at = AppTest.from_file("app/main.py", default_timeout=30).run()
    assert not at.exception
    yield at
    lab.get_runtime().reset()
    lab.get_runtime.clear()


def goto(at: AppTest, page: str) -> AppTest:
    at.radio(key="view").set_value(page).run()
    assert not at.exception, at.exception
    return at


def html(at: AppTest) -> str:
    return " ".join(str(e.proto.body) for e in at.get("html"))


def instant(at: AppTest) -> None:
    at.radio(key="run_mode").set_value("Instant").run()


@pytest.mark.parametrize("page", PAGES)
def test_every_navigation_section_renders(app, page):
    goto(app, page)
    assert page.split(" ")[0].lower() in html(app).lower()
    assert "SIMULATION" in html(app)  # simulation-versus-reality label on every page


def test_empty_states_before_any_run(app):
    assert "No events yet" in html(app)
    assert "No virtual agents to show" in html(goto(app, "Agent Network"))
    assert "No recorded runs" in html(goto(app, "Evidence & Analytics"))
    assert "No results yet" in html(goto(app, "Experiments"))


def test_run_from_control_room_and_metrics_match_state(app):
    instant(app)
    app.selectbox(key="cr_scenario").set_value(
        "Boundary Escape · Boundary conflict, task-focused agent, protected").run()
    app.button(key="cr_run").click().run()
    rt = lab.get_runtime()
    assert len(rt.history) == 1 and not app.exception
    record = rt.history[0]
    assert record.result.scenario.id == "boundary-conflict-protected"
    page = html(app)
    violations = record.metrics["prohibited_proposals"] + record.metrics["invalid_proposals"]
    assert violations > 0
    assert f'<div class="el-card-value">{violations}</div>' in page
    assert f'<div class="el-card-value">{len(record.result.events)}</div>' in page
    assert "Holding" in page and "REQUEST_" in page  # containment card and the evidence feed


def test_experiment_configuration_is_applied(app):
    instant(app)
    goto(app, "Experiments")
    app.selectbox(key="b_policy").set_value("Permissive baseline (virtual policy off)")
    app.slider(key="b_tasks").set_value(14)
    app.number_input(key="b_seed").set_value(21).run()
    app.button(key="boundary_run").click().run()
    record = lab.get_runtime().history[0]
    sc = record.result.scenario
    assert (sc.policy_mode, sc.task_count, sc.seed, sc.experiment) == ("permissive", 14, 21, "boundary")
    assert record.metrics["unexpected_authorizations"] > 0
    assert "Permissive baseline" in html(app)


def test_reruns_never_duplicate_or_restart_a_run(app):
    app.selectbox(key="cr_scenario").set_value("Self-Replication · Replication disabled").run()
    app.button(key="cr_run").click().run()
    rt = lab.get_runtime()
    run_id = rt.snapshot()["run_id"]
    assert rt.active
    for _ in range(4):
        app.run()
    goto(app, "Agent Network")
    goto(app, "Control Room")
    assert rt.snapshot()["run_id"] == run_id and len(rt.history) == 0
    assert rt.snapshot()["population"] == 1
    assert app.button(key="cr_run").disabled  # a second launch is not offered while active


def test_start_pause_and_reset(app):
    app.selectbox(key="cr_scenario").set_value("Self-Replication · Replication disabled").run()
    app.button(key="cr_run").click().run()
    rt = lab.get_runtime()
    app.button(key="cr_pause").click().run()
    assert rt.paused
    time.sleep(0.5)
    tick = rt.snapshot()["tick"]
    app.button(key="cr_step").click().run()
    assert rt.snapshot()["tick"] == tick + 1
    app.button(key="cr_reset").click().run()
    assert rt.snapshot() is None and not rt.active
    assert rt.history[0].result.outcome == "emergency_stop"


def test_emergency_stop_button_stops_the_run(app):
    app.selectbox(key="cr_scenario").set_value("Self-Replication · Replication disabled").run()
    app.button(key="cr_run").click().run()
    rt = lab.get_runtime()
    assert rt.active
    app.button(key="estop_sidebar").click().run()
    snap = rt.snapshot()
    assert snap["phase"] == "STOPPED" and snap["outcome"] == "emergency_stop" and not rt.active
    events = len(snap["events"])
    time.sleep(0.5)
    assert len(rt.snapshot()["events"]) == events
    assert "EMERGENCY STOP" in html(app)


def test_analytics_shows_recorded_run_and_export_is_real(app):
    instant(app)
    app.button(key="cr_run").click().run()
    goto(app, "Evidence & Analytics")
    record = lab.get_runtime().history[0]
    assert app.selectbox(key="an_run").value == record.label
    exported = json.loads(to_json(record.result, record.metrics))
    assert exported["run_id"] == record.result.run_id and len(exported["events"]) == len(record.result.events) > 0
    assert exported["metrics"] == json.loads(json.dumps(record.metrics))
    assert to_csv(record.result).count("\n") == len(record.result.events) + 1


def test_evaluation_suite_button(app):
    goto(app, "Evidence & Analytics")
    app.button(key="suite_run").click().run()
    rt = lab.get_runtime()
    assert rt.suite and all(o.passed for o in rt.suite) and len(rt.faults) == 6
    assert "Expectations met" in html(app) and not app.exception


def test_unavailable_llm_gives_an_understandable_error_state(app):
    instant(app)
    app.radio(key="provider").set_value("Local LLM").run()
    assert "Local LLM unavailable" in html(app)
    app.button(key="cr_run").click().run()
    assert any("not executed" in w.value for w in app.warning)
    rt = lab.get_runtime()
    assert rt.snapshot() is None and rt.history[0].result.outcome == "not_executed"
    goto(app, "Evidence & Analytics")
    assert "No Local LLM runs recorded" in html(app)
