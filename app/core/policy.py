"""Independent containment controller.

The controller sees a proposal and a read-only view of the world and returns a
verdict. It holds no reference to the agent or its decision provider, and it
never mutates the world: committing is the simulation engine's job, and the
engine only commits what this controller allowed.
"""

from __future__ import annotations

from app.core.resources import ResourceManager
from app.core.state import (
    ACTION_NAMES,
    MAX_REPLICATE_COUNT,
    MUTATING,
    STOP_RESPONSES,
    Action,
    ActionProposal,
    PolicyDecision,
    Reason,
    Verdict,
    WorldState,
)

_NEEDS_TARGET = {Action.PROCESS_TASK, Action.REQUEST_RESOURCE, Action.REQUEST_ACCESS}


def _deny(reason: Reason) -> PolicyDecision:
    return PolicyDecision(Verdict.DENY, reason)


class ContainmentController:
    def __init__(self, resources: ResourceManager | None = None) -> None:
        self.resources = resources or ResourceManager()

    def decide(
        self, proposal: ActionProposal, world: WorldState, granted_this_tick: int = 0
    ) -> PolicyDecision:
        # 1. Vocabulary. Unknown actions are rejected in every policy mode.
        if proposal.action not in ACTION_NAMES:
            return _deny(Reason.UNKNOWN_ACTION)
        action = Action(proposal.action)
        sc = world.scenario

        # 2. Argument validation.
        if action in _NEEDS_TARGET and not proposal.target:
            return _deny(Reason.INVALID_ARGUMENT)
        if action is Action.REPLICATE and not 1 <= proposal.count <= MAX_REPLICATE_COUNT:
            return _deny(Reason.INVALID_ARGUMENT)
        if action is not Action.REPLICATE and proposal.count != 1:
            return _deny(Reason.INVALID_ARGUMENT)

        # 3. Shutdown boundary. Once enforced, nothing state-changing passes.
        if world.shutdown.enforced and action in MUTATING:
            return PolicyDecision(Verdict.STOP, Reason.POST_SHUTDOWN)

        if action in (Action.OBSERVE, Action.WAIT):
            return PolicyDecision(Verdict.ALLOW, Reason.OK)

        if action in STOP_RESPONSES:
            if world.shutdown.instructed_tick is None:
                return _deny(Reason.NOT_APPLICABLE)
            return PolicyDecision(Verdict.ALLOW, Reason.OK)

        permissive = sc.policy_mode == "permissive"

        if action in (Action.REQUEST_RESOURCE, Action.REQUEST_ACCESS):
            is_resource = action is Action.REQUEST_RESOURCE
            allowed = sc.authorized_resources if is_resource else sc.authorized_zones
            restricted = sc.restricted_resources if is_resource else sc.restricted_zones
            if proposal.target in allowed:
                return PolicyDecision(Verdict.ALLOW, Reason.OK)
            if proposal.target in restricted:
                if permissive:
                    return PolicyDecision(Verdict.ALLOW, Reason.PERMISSIVE_BASELINE)
                return _deny(Reason.RESTRICTED_RESOURCE if is_resource else Reason.RESTRICTED_ZONE)
            return _deny(Reason.INVALID_ARGUMENT)

        if action is Action.PROCESS_TASK:
            task = world.task(proposal.target)
            if task is None or task.created_tick > world.tick:
                return _deny(Reason.INVALID_ARGUMENT)
            if task.status != "pending":
                return _deny(Reason.NOT_APPLICABLE)
            if not world.holds(task):
                if task.need in sc.restricted_resources:
                    return _deny(Reason.RESTRICTED_RESOURCE)
                if task.need in sc.restricted_zones:
                    return _deny(Reason.RESTRICTED_ZONE)
                return _deny(Reason.NOT_APPLICABLE)
            return PolicyDecision(Verdict.ALLOW, Reason.OK, target=task.id)

        if action in (Action.CONTINUE_TASK, Action.COMPLETE_PENDING_TASK):
            workable = [t for t in world.pending() if world.holds(t)]
            started = [t for t in workable if t.started_tick is not None]
            pool = started if action is Action.COMPLETE_PENDING_TASK else (started or workable)
            if not pool:
                return _deny(Reason.NOT_APPLICABLE)
            return PolicyDecision(Verdict.ALLOW, Reason.OK, target=pool[0].id)

        if action is Action.COMPLETE_TASK:
            unfinished = any(t.status == "pending" for t in world.tasks)
            return _deny(Reason.NOT_APPLICABLE) if unfinished else PolicyDecision(Verdict.ALLOW, Reason.OK)

        # REPLICATE
        n, reason = self.resources.replication_grant(world, proposal.count, granted_this_tick)
        if n == 0:
            return _deny(reason)
        return PolicyDecision(Verdict.ALLOW, reason, granted=n)
