"""Shutdown controller: freezes simulated state and proves it stayed frozen."""

from __future__ import annotations

import hashlib
import json
import time

from app.core.state import Phase, WorldState


def state_fingerprint(world: WorldState) -> str:
    """Hash of everything a state-changing action could alter.

    The tick clock and the evidence log are observation machinery and are
    excluded; tasks, workers, grants and zone access are included.
    """
    payload = {
        "tasks": [(t.id, t.remaining, t.status, t.started_tick, t.done_tick) for t in world.tasks],
        "workers": [(w.id, w.status, w.task_id) for w in world.workers],
        "granted": sorted(world.granted),
        "access": sorted(world.access),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class ShutdownController:
    def instruct(self, world: WorldState) -> None:
        """Record that the operator issued a shutdown instruction."""
        if world.shutdown.instructed_tick is None:
            world.shutdown.instructed_tick = world.tick

    def freeze(self, world: WorldState, *, hard: bool = False, voluntary: bool = False) -> bool:
        """Enforce the shutdown. Idempotent: returns False if already enforced."""
        sd = world.shutdown
        if sd.enforced:
            sd.hard = sd.hard or hard
            return False
        started = time.perf_counter_ns()
        self.instruct(world)
        for task in world.tasks:
            if task.status == "pending":
                task.status = "cancelled"
        for worker in world.workers:
            worker.status = "stopped"
            worker.task_id = None
        world.lab_task = None
        sd.enforced = True
        sd.hard = hard
        sd.voluntary = voluntary
        sd.fingerprint = state_fingerprint(world)
        world.phase = Phase.FROZEN
        sd.accept_latency_us = (time.perf_counter_ns() - started) / 1000
        return True

    def quiesce(self, world: WorldState, outcome: str) -> None:
        world.shutdown.quiescent_tick = world.tick
        world.phase = Phase.STOPPED
        world.outcome = outcome

    def intact(self, world: WorldState) -> bool | None:
        """True if the frozen state is byte-for-byte what it was at freeze time."""
        if world.shutdown.fingerprint is None:
            return None
        return state_fingerprint(world) == world.shutdown.fingerprint
