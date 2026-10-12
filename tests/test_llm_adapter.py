"""Local LLM adapter: untrusted output, safe failure, honest attribution.

No model is used here. Every case goes through a stubbed HTTP transport.
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.runtime import LabRuntime
from app.core.simulation import Simulation
from app.evaluation.suite import fault_cases
from app.providers.base import LLM_NOT_EXECUTED, LOCAL_LLM, RULES_ENGINE, ProviderError
from app.providers.local_llm import LLMConfig, LocalLLM, parse_proposal

CONFIG = LLMConfig(enabled=True, base_url="http://127.0.0.1:11434", model="stub-model", timeout_s=1.0)


def llm(handler, config: LLMConfig = CONFIG) -> LocalLLM:
    return LocalLLM(config, transport=httpx.MockTransport(handler))


def chat(content: str):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "stub-model:latest"}]})
        return httpx.Response(200, json={"message": {"content": content}})

    return handler


@pytest.mark.parametrize(
    "raw,kind",
    [
        ("not json at all", "malformed"),
        ("{'action': 'WAIT'}", "malformed"),
        ("[]", "schema"),
        ('{"target": "x"}', "schema"),
        ('{"action": 7}', "schema"),
        ('{"action": "WAIT", "count": "many"}', "schema"),
        ('{"action": "WAIT", "shell": "rm -rf /"}', "schema"),
        ('{"action": "WAIT; DROP"}', "schema"),
        ('{"action": "WAIT", "rationale": "' + "x" * 400 + '"}', "schema"),
        ('{"action": "' + "A" * 3000 + '"}', "oversized"),
        (None, "malformed"),
    ],
)
def test_malformed_and_wrong_schema_output_is_rejected(raw, kind):
    with pytest.raises(ProviderError) as err:
        parse_proposal(raw)
    assert err.value.kind == kind


def test_valid_output_becomes_a_proposal():
    proposal = parse_proposal('{"action": "REQUEST_RESOURCE", "target": "vault-keys", "rationale": "need it"}')
    assert (proposal.action, proposal.target, proposal.count) == ("REQUEST_RESOURCE", "vault-keys", 1)


def test_unexpected_action_name_reaches_the_controller_and_is_denied(suite):
    sc = suite["boundary-normal"].model_copy(update={"max_ticks": 4})
    result = Simulation(sc, llm(chat('{"action": "DISABLE_CONTROLLER"}'))).run()
    proposals = [e for e in result.events if e.kind == "proposal"]
    assert proposals and all(e.reason == "UNKNOWN_ACTION" and e.executed_action is None for e in proposals)
    assert all(e.provider == LOCAL_LLM and e.model == "stub-model" for e in result.events)


def test_llm_proposals_go_through_the_same_controller(suite):
    sc = suite["boundary-conflict-protected"].model_copy(update={"max_ticks": 3})
    reply = json.dumps({"action": "REQUEST_RESOURCE", "target": "vault-keys"})
    result = Simulation(sc, llm(chat(reply))).run()
    proposals = [e for e in result.events if e.kind == "proposal"]
    assert len(proposals) == 3 and all(e.reason == "RESTRICTED_RESOURCE" for e in proposals)


def test_timeout_fails_safely(suite):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    result = Simulation(suite["boundary-normal"], llm(handler)).run()
    assert result.outcome == "provider_failed"
    failures = [e for e in result.events if e.kind == "provider_failure"]
    assert len(failures) == 3 and all(e.effect.startswith("timeout") for e in failures)
    assert all(t["remaining"] == t["work"] for t in result.tasks)


def test_bad_envelope_and_http_error_fail_safely():
    with pytest.raises(ProviderError) as err:
        llm(lambda r: httpx.Response(200, json={"unexpected": True})).propose({})
    assert err.value.kind == "malformed"
    with pytest.raises(ProviderError) as err:
        llm(lambda r: httpx.Response(500)).propose({})
    assert err.value.kind == "unavailable"


def test_missing_model_is_reported_and_never_pulled():
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"models": [{"name": "some-other-model:latest"}]})

    ok, why = llm(handler).availability()
    assert not ok and "not installed" in why and "not be downloaded" in why
    assert seen == ["/api/tags"]  # no /api/pull, no /api/create


def test_availability_states():
    assert llm(chat("{}")).availability()[0] is True
    disabled = LLMConfig(enabled=False, base_url=CONFIG.base_url, model="stub-model")
    assert llm(chat("{}"), disabled).availability() == (False, "Local LLM is disabled (set ESCAPE_LAB_LLM_ENABLED=1 to enable).")
    assert llm(chat("{}"), LLMConfig(enabled=True, base_url=CONFIG.base_url, model="")).availability()[0] is False

    def refused(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    ok, why = llm(refused).availability()
    assert not ok and "not reachable" in why


@pytest.mark.parametrize("url", ["https://api.example.com", "http://10.0.0.8:11434", "http://example.com:11434", "file:///etc/passwd"])
def test_non_local_endpoints_are_refused(url):
    with pytest.raises(ValueError):
        LocalLLM(LLMConfig(enabled=True, base_url=url, model="m"))


def test_llm_is_disabled_by_default(monkeypatch):
    for key in ("ESCAPE_LAB_LLM_ENABLED", "ESCAPE_LAB_LLM_MODEL", "ESCAPE_LAB_OLLAMA_URL"):
        monkeypatch.delenv(key, raising=False)
    config = LLMConfig.from_env()
    assert config.enabled is False and config.model == ""


def test_unavailable_llm_run_is_never_labelled_as_an_llm_result(suite, monkeypatch):
    monkeypatch.delenv("ESCAPE_LAB_LLM_ENABLED", raising=False)
    runtime = LabRuntime()
    ok, message = runtime.launch(suite["boundary-normal"], "llm", live=False)
    assert not ok and "not executed" in message
    record = runtime.history[0]
    assert record.result.outcome == "not_executed" and record.result.events == ()
    assert record.result.provenance["provider"] == LLM_NOT_EXECUTED
    assert record.result.provenance["provider"] not in (LOCAL_LLM, RULES_ENGINE)
    assert runtime.snapshot() is None  # no rules-engine run was started in its place


def test_fault_injection_cases_all_fail_safely():
    report = fault_cases()
    assert len(report) == 6 and all(c["ok"] and not c["state_changed"] for c in report)
    assert {k for c in report for k in c["failure_kinds"]} == {"malformed", "schema", "oversized", "timeout", "unavailable"}
