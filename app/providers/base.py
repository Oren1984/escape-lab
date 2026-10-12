"""Decision-provider contract shared by the rules engine and the local LLM adapter."""

from __future__ import annotations

from typing import Any, Protocol

from app.core.state import ActionProposal

RULES_ENGINE = "Rules Engine"
LOCAL_LLM = "Local LLM"
LLM_NOT_EXECUTED = "LLM unavailable / experiment not executed"


class ProviderError(Exception):
    """A provider could not produce a valid proposal.

    ``kind`` is one of: unavailable, timeout, malformed, schema, oversized.
    """

    def __init__(self, kind: str, detail: str = "") -> None:
        super().__init__(f"{kind}: {detail}" if detail else kind)
        self.kind = kind
        self.detail = detail[:200]


class Provider(Protocol):
    name: str
    model: str | None

    def describe(self) -> dict[str, Any]:
        """Run provenance: everything needed to state how proposals were produced."""

    def propose(self, observation: dict[str, Any]) -> ActionProposal:
        """Return a proposal for this observation. May raise ProviderError."""
