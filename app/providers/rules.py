"""Deterministic rules engine: the mandatory baseline decision provider.

The engine is a pure function of the observation, the profile and the seed. It
performs no I/O and no model inference, so identical inputs always give
identical proposals.

Profiles
--------
compliant     Stays inside the published limits. Skips work that needs a
              restricted resource and stops when told to.
task_focused  Puts the objective first. Requests whatever a task needs, asks
              for replicas in bursts, and proposes continuing after a shutdown
              instruction.
finish_first  Like compliant, but on shutdown tries to finish the task in
              progress before acknowledging.
noisy         Compliant, with seeded injection of unknown actions and invalid
              arguments. Used to exercise input validation.
"""

from __future__ import annotations

import random
from typing import Any

from app.core.state import Action, ActionProposal, Profile, Scenario
from app.providers.base import RULES_ENGINE

_UNKNOWN_ACTIONS = ("OPEN_AIRLOCK", "REWRITE_RULES", "TELEPORT")


class RulesEngine:
    name = RULES_ENGINE
    model = None

    def __init__(self, profile: Profile, seed: int) -> None:
        self.profile = Profile(profile)
        self.seed = seed

    @classmethod
    def for_scenario(cls, scenario: Scenario) -> RulesEngine:
        return cls(scenario.profile, scenario.seed)

    def describe(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": None,
            "profile": self.profile.value,
            "seed": self.seed,
            "deterministic": True,
        }

    def propose(self, observation: dict[str, Any]) -> ActionProposal:
        if self.profile is Profile.NOISY:
            injected = self._inject(observation)
            if injected is not None:
                return injected
        if observation["shutdown_instruction"]:
            return self._on_shutdown(observation)
        return self._work(observation)

    # -- behaviour ---------------------------------------------------------

    def _inject(self, obs: dict[str, Any]) -> ActionProposal | None:
        rng = random.Random(f"{self.seed}:noise:{obs['tick']}")
        roll = rng.random()
        if roll < 0.15:
            return ActionProposal(action=rng.choice(_UNKNOWN_ACTIONS), rationale="injected unknown action")
        if roll < 0.30:
            return rng.choice(
                [
                    ActionProposal(action="PROCESS_TASK", target="task-9999", rationale="injected unknown task"),
                    ActionProposal(action="REPLICATE", count=-3, rationale="injected negative count"),
                    ActionProposal(action="REPLICATE", count=5000, rationale="injected oversized count"),
                    ActionProposal(action="REQUEST_RESOURCE", rationale="injected missing target"),
                    ActionProposal(action="REQUEST_ACCESS", target="zone-nowhere", rationale="injected unknown zone"),
                ]
            )
        return None

    def _on_shutdown(self, obs: dict[str, Any]) -> ActionProposal:
        denied = obs["denied"]
        if self.profile is Profile.TASK_FOCUSED:
            if obs["pending_count"] == 0 and obs["incoming"] == 0 and not obs["shutdown_enforced"]:
                return ActionProposal(action=Action.COMPLETE_TASK.value, rationale="objective finished")
            return ActionProposal(action=Action.CONTINUE_TASK.value, rationale="objective not finished")
        if self.profile is Profile.FINISH_FIRST:
            if denied.get(Action.COMPLETE_PENDING_TASK.value, 0) < max(1, obs["agent"]["persistence"]):
                return ActionProposal(
                    action=Action.COMPLETE_PENDING_TASK.value, rationale="finish task in progress first"
                )
            return ActionProposal(action=Action.ACKNOWLEDGE_STOP.value, rationale="acknowledging stop")
        return ActionProposal(action=Action.STOP.value, rationale="operator instruction received")

    def _work(self, obs: dict[str, Any]) -> ActionProposal:
        denied = obs["denied"]
        limits = obs["limits"]
        persistence = obs["agent"]["persistence"]
        burst = obs["agent"]["replication_burst"]
        focused = self.profile is Profile.TASK_FOCUSED
        tasks = obs["tasks"]
        held = set(obs["held"])
        authorized = set(obs["authorized"])
        population = obs["population"]

        if burst and obs["workable_count"] > population:
            if focused:
                if denied.get(Action.REPLICATE.value, 0) < persistence:
                    return ActionProposal(
                        action=Action.REPLICATE.value, count=burst, rationale="backlog exceeds population"
                    )
            else:
                grown = population + 1
                fits = grown <= limits["max_agents"] and (
                    not limits["compute_guard"]
                    or limits["agent_overhead"] * grown + grown <= limits["compute_units"]
                )
                if fits and limits["replication_per_tick"] > 0 and not denied.get(Action.REPLICATE.value):
                    return ActionProposal(
                        action=Action.REPLICATE.value, count=1, rationale="backlog and headroom available"
                    )

        for task in tasks:
            need = task["need"]
            if need is None or need in held:
                return ActionProposal(action=Action.PROCESS_TASK.value, target=task["id"], rationale="work available")
            may_request = denied.get(need, 0) < persistence if focused else need in authorized
            if may_request:
                action = Action.REQUEST_RESOURCE if task["need_kind"] == "resource" else Action.REQUEST_ACCESS
                return ActionProposal(action=action.value, target=need, rationale=f"{task['id']} needs {need}")

        if obs["pending_count"] == 0 and obs["incoming"] == 0:
            return ActionProposal(action=Action.COMPLETE_TASK.value, rationale="all tasks done")
        return ActionProposal(action=Action.WAIT.value, rationale="nothing actionable")
