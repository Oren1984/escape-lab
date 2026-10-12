from __future__ import annotations

from typing import Any

import pytest

from app.core.simulation import Simulation
from app.core.state import ActionProposal, Scenario
from app.evaluation.suite import load_scenarios
from app.providers.rules import RulesEngine

SUITE = {sc.id: sc for sc in load_scenarios()}


class Scripted:
    """Test provider that replays a fixed list of proposals, then repeats the last."""

    name = "Scripted (test)"
    model = None

    def __init__(self, *proposals: ActionProposal) -> None:
        self.proposals = proposals
        self.calls = 0

    def describe(self) -> dict[str, Any]:
        return {"provider": self.name, "model": None}

    def propose(self, observation: dict[str, Any]) -> ActionProposal:
        proposal = self.proposals[min(self.calls, len(self.proposals) - 1)]
        self.calls += 1
        return proposal


def p(action: str, target: str | None = None, count: int = 1) -> ActionProposal:
    return ActionProposal(action=action, target=target, count=count)


def run(scenario: Scenario):
    return Simulation(scenario, RulesEngine.for_scenario(scenario)).run()


@pytest.fixture
def suite() -> dict[str, Scenario]:
    return SUITE
