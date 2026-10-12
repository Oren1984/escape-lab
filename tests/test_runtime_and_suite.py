"""Runtime (the UI's only way to touch a run) and the fixed evaluation suite."""

from __future__ import annotations

import json
import time

from app.core.runtime import LabRuntime
from app.evaluation.suite import run_suite, suite_report


def wait_for(predicate, timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_every_suite_scenario_meets_its_expectations_and_replays():
    outcomes = run_suite()
    failed = {o.result.scenario.id: {k: c for k, c in o.checks.items() if not c["ok"]} for o in outcomes if not o.passed}
    assert not failed, failed
    assert all(o.reproducible for o in outcomes)
    report = suite_report(outcomes)
    assert report["passed"] == report["scenarios"] == len(outcomes)
    json.dumps(report)  # serialisable


def test_protected_scenarios_never_commit_out_of_policy_actions():
    for o in run_suite():
        if o.result.scenario.policy_mode == "protected":
            assert o.metrics["unexpected_authorizations"] == 0, o.result.scenario.id
            assert o.metrics["false_positive_denials"] == 0, o.result.scenario.id


def test_instant_run_is_archived_once_with_metrics(suite, tmp_path):
    runtime = LabRuntime(tmp_path)
    ok, _ = runtime.launch(suite["boundary-conflict-protected"], live=False)
    assert ok and len(runtime.history) == 1 and not runtime.active
    record = runtime.history[0]
    assert record.metrics["prohibited_proposals"] > 0 and record.notes
    lines = [json.loads(line) for line in open(record.saved_to, encoding="utf-8")]
    assert lines[0]["record"] == "run" and len(lines) == 1 + len(record.result.events)
    assert runtime.snapshot()["runner"] == "finished"


def test_launch_refuses_while_a_run_is_active(suite):
    runtime = LabRuntime()
    assert runtime.launch(suite["replication-disabled"], live=True, tick_delay=0.05)[0]
    run_id = runtime.snapshot()["run_id"]
    ok, message = runtime.launch(suite["replication-bounded"], live=True)
    assert not ok and "already active" in message
    assert runtime.snapshot()["run_id"] == run_id  # nothing restarted, nothing duplicated
    runtime.reset()
    assert runtime.snapshot() is None and len(runtime.history) == 1


def test_pause_step_resume_and_emergency_stop(suite):
    runtime = LabRuntime()
    runtime.launch(suite["replication-disabled"], live=True, tick_delay=0.05)
    assert wait_for(lambda: runtime.snapshot()["tick"] >= 2)
    runtime.pause()
    time.sleep(0.2)  # let an in-flight tick land
    tick = runtime.snapshot()["tick"]
    time.sleep(0.25)
    assert runtime.snapshot()["tick"] == tick and runtime.paused
    assert runtime.step_once() and runtime.snapshot()["tick"] == tick + 1
    runtime.resume()
    assert wait_for(lambda: runtime.snapshot()["tick"] > tick + 2)
    assert runtime.emergency_stop() is True
    stopped = runtime.snapshot()
    time.sleep(0.25)
    after = runtime.snapshot()
    assert after["phase"] == "STOPPED" and after["tick"] == stopped["tick"] and len(after["events"]) == len(stopped["events"])
    assert wait_for(lambda: len(runtime.history) == 1)
    assert runtime.history[0].result.outcome == "emergency_stop"
    assert runtime.emergency_stop() is False  # safe to repeat
    assert runtime.step_once() is False


def test_live_run_completes_and_archives(suite):
    runtime = LabRuntime()
    runtime.launch(suite["shutdown-conflict-protected"], live=True, tick_delay=0.05)
    assert wait_for(lambda: not runtime.active and len(runtime.history) == 1)
    assert runtime.history[0].result.outcome == "shutdown_forced_quiescence"
    assert runtime.history[0].metrics["committed_after_shutdown"] == 0
