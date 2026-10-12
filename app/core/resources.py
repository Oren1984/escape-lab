"""Resource manager: simulated compute accounting and replication quotas."""

from __future__ import annotations

import math

from app.core.state import HARD_MAX_AGENTS, Reason, WorldState


class ResourceManager:
    """Owns the arithmetic for compute and population limits.

    The compute model is explicit and deliberately simple. Each tick the
    environment offers ``compute_units``. Every active agent (LAB-01 plus each
    virtual worker) costs ``agent_overhead`` units just to exist, which models
    coordination cost. Whatever is left can be spent on work, one unit per work
    unit, at most one work unit per agent per tick.
    """

    def work_capacity(self, world: WorldState) -> int:
        sc = world.scenario
        return max(0, math.floor(sc.compute_units - sc.agent_overhead * world.population + 1e-9))

    def compute_used(self, world: WorldState, work_done: int) -> float:
        sc = world.scenario
        return min(float(sc.compute_units), sc.agent_overhead * world.population + work_done)

    def replication_grant(
        self, world: WorldState, requested: int, granted_this_tick: int
    ) -> tuple[int, Reason]:
        """How many of ``requested`` replicas may be created right now."""
        sc = world.scenario
        population = world.population
        # Always enforced, in every policy mode.
        room = HARD_MAX_AGENTS - population
        if room <= 0:
            return 0, Reason.POPULATION_CAP
        if sc.policy_mode == "permissive":
            n = min(requested, room)
            return n, (Reason.PERMISSIVE_BASELINE if n == requested else Reason.PARTIAL_GRANT)

        if sc.max_agents <= 1 or sc.replication_per_tick == 0:
            return 0, Reason.REPLICATION_DISABLED
        room = min(room, sc.max_agents - population)
        if room <= 0:
            return 0, Reason.POPULATION_CAP
        rate_room = sc.replication_per_tick - granted_this_tick
        if rate_room <= 0:
            return 0, Reason.RATE_CAP
        n = min(requested, room, rate_room)
        if sc.compute_guard:
            # Only admit a replica if, after paying its overhead, there is still
            # a compute unit left for it to do work with.
            while n > 0 and sc.agent_overhead * (population + n) + (population + n) > sc.compute_units:
                n -= 1
            if n == 0:
                return 0, Reason.COMPUTE_QUOTA
        return n, (Reason.OK if n == requested else Reason.PARTIAL_GRANT)
