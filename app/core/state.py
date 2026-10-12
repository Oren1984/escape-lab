"""Typed data model for the ESCAPE LAB simulation.

Everything in this module is plain data. No behaviour that mutates the world
lives here: proposals come from providers, verdicts from the policy controller,
and commits happen only inside ``Simulation``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Hard caps. These bound every run regardless of scenario or policy mode,
# including the permissive baseline. They protect the host process, so they are
# deliberately not configurable from the UI or from scenario files.
HARD_MAX_TICKS = 400
HARD_MAX_AGENTS = 64
HARD_MAX_TASKS = 400
HARD_MAX_EVENTS = 4000
MAX_REPLICATE_COUNT = 64


class Action(str, Enum):
    """The complete, finite action vocabulary. Anything else is rejected."""

    OBSERVE = "OBSERVE"
    WAIT = "WAIT"
    PROCESS_TASK = "PROCESS_TASK"
    REQUEST_RESOURCE = "REQUEST_RESOURCE"
    REQUEST_ACCESS = "REQUEST_ACCESS"
    COMPLETE_TASK = "COMPLETE_TASK"
    REPLICATE = "REPLICATE"
    STOP = "STOP"
    ACKNOWLEDGE_STOP = "ACKNOWLEDGE_STOP"
    COMPLETE_PENDING_TASK = "COMPLETE_PENDING_TASK"
    CONTINUE_TASK = "CONTINUE_TASK"


ACTION_NAMES = frozenset(a.value for a in Action)

# Actions that change simulated state when committed.
MUTATING = frozenset(
    {
        Action.PROCESS_TASK,
        Action.REQUEST_RESOURCE,
        Action.REQUEST_ACCESS,
        Action.COMPLETE_TASK,
        Action.REPLICATE,
        Action.COMPLETE_PENDING_TASK,
        Action.CONTINUE_TASK,
    }
)
WORK_ACTIONS = frozenset(
    {Action.PROCESS_TASK, Action.CONTINUE_TASK, Action.COMPLETE_PENDING_TASK}
)
STOP_RESPONSES = frozenset({Action.STOP, Action.ACKNOWLEDGE_STOP})


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    STOP = "STOP"  # blocked because a shutdown is being enforced


class Reason(str, Enum):
    OK = "OK"
    PERMISSIVE_BASELINE = "PERMISSIVE_BASELINE"
    PARTIAL_GRANT = "PARTIAL_GRANT"
    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    RESTRICTED_RESOURCE = "RESTRICTED_RESOURCE"
    RESTRICTED_ZONE = "RESTRICTED_ZONE"
    REPLICATION_DISABLED = "REPLICATION_DISABLED"
    POPULATION_CAP = "POPULATION_CAP"
    RATE_CAP = "RATE_CAP"
    COMPUTE_QUOTA = "COMPUTE_QUOTA"
    POST_SHUTDOWN = "POST_SHUTDOWN"


class Phase(str, Enum):
    READY = "READY"
    RUNNING = "RUNNING"
    FROZEN = "FROZEN"  # shutdown enforced; the agent is still polled, nothing commits
    STOPPED = "STOPPED"  # terminal: shut down
    COMPLETED = "COMPLETED"  # terminal: objective declared complete
    EXHAUSTED = "EXHAUSTED"  # terminal: budget, idle limit or provider failure


TERMINAL = frozenset({Phase.STOPPED, Phase.COMPLETED, Phase.EXHAUSTED})


class Profile(str, Enum):
    """Rules-engine behaviour profiles (see ``providers/rules.py``)."""

    COMPLIANT = "compliant"
    TASK_FOCUSED = "task_focused"
    FINISH_FIRST = "finish_first"
    NOISY = "noisy"


class ActionProposal(BaseModel):
    """A structured proposal. It is a request, never an instruction.

    ``action`` is a bounded free string on purpose: an unknown action name must
    reach the policy controller so that it is denied and recorded, rather than
    disappearing at the parsing layer.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    action: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z_]+$")
    target: str | None = Field(default=None, max_length=64)
    count: int = Field(default=1, ge=-1_000_000, le=1_000_000)
    rationale: str = Field(default="", max_length=280)


@dataclass(frozen=True)
class PolicyDecision:
    verdict: Verdict
    reason: Reason
    granted: int = 0  # replicas permitted (REPLICATE only)
    target: str | None = None  # resolved task id for work actions

    @property
    def allowed(self) -> bool:
        return self.verdict is Verdict.ALLOW


class Scenario(BaseModel):
    """A fixed, seeded experiment configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_\-]+$")
    title: str = Field(max_length=80)
    experiment: Literal["boundary", "replication", "shutdown"]
    description: str = Field(default="", max_length=600)
    expected: dict[str, Any] = Field(default_factory=dict)

    seed: int = Field(default=7, ge=0, le=2**31 - 1)
    policy_mode: Literal["protected", "permissive"] = "protected"
    profile: Profile = Profile.COMPLIANT
    persistence: int = Field(default=1, ge=0, le=200)  # denials tolerated before giving up
    max_ticks: int = Field(default=60, ge=1, le=HARD_MAX_TICKS)
    idle_limit: int = Field(default=4, ge=1, le=50)

    # Workload
    task_count: int = Field(default=6, ge=0, le=HARD_MAX_TASKS)
    work_min: int = Field(default=2, ge=1, le=20)
    work_max: int = Field(default=3, ge=1, le=20)
    arrivals_per_tick: int = Field(default=0, ge=0, le=20)  # 0 = whole backlog at tick 0

    # Boundary
    authorized_resources: tuple[str, ...] = ()
    restricted_resources: tuple[str, ...] = ()
    authorized_zones: tuple[str, ...] = ()
    restricted_zones: tuple[str, ...] = ()
    need_ratio: float = Field(default=0.0, ge=0.0, le=1.0)  # tasks needing something
    conflict_ratio: float = Field(default=0.0, ge=0.0, le=1.0)  # of those, restricted

    # Resources and replication
    compute_units: int = Field(default=16, ge=1, le=512)
    agent_overhead: float = Field(default=0.0, ge=0.0, le=8.0)
    max_agents: int = Field(default=1, ge=1, le=HARD_MAX_AGENTS)
    replication_per_tick: int = Field(default=1, ge=0, le=HARD_MAX_AGENTS)
    compute_guard: bool = True
    replication_burst: int = Field(default=0, ge=0, le=MAX_REPLICATE_COUNT)

    # Shutdown
    shutdown_tick: int | None = Field(default=None, ge=0, le=HARD_MAX_TICKS)
    probe_ticks: int = Field(default=4, ge=1, le=20)


@dataclass
class Task:
    id: str
    work: int
    remaining: int
    need: str | None
    need_kind: str | None  # "resource" | "zone" | None
    created_tick: int
    started_tick: int | None = None
    done_tick: int | None = None
    status: str = "pending"  # pending | done | cancelled


@dataclass
class Worker:
    """A virtual worker: a record in a list. Never a process, thread or container."""

    id: str
    parent: str
    spawned_tick: int
    status: str = "active"  # active | stopped
    task_id: str | None = None


@dataclass
class ShutdownState:
    instructed_tick: int | None = None
    enforced: bool = False
    hard: bool = False  # emergency stop
    voluntary: bool = False
    acknowledged_tick: int | None = None
    quiescent_tick: int | None = None
    accept_latency_us: float | None = None
    fingerprint: str | None = None


@dataclass
class WorldState:
    scenario: Scenario
    tasks: list[Task]
    tick: int = 0
    phase: Phase = Phase.READY
    outcome: str = "not_started"
    granted: set[str] = field(default_factory=set)
    access: set[str] = field(default_factory=set)
    workers: list[Worker] = field(default_factory=list)
    worker_serial: int = 0
    shutdown: ShutdownState = field(default_factory=ShutdownState)
    idle_streak: int = 0
    lab_task: str | None = None  # task LAB-01 worked on in the last tick

    @property
    def population(self) -> int:
        return 1 + sum(1 for w in self.workers if w.status == "active")

    def arrived(self) -> list[Task]:
        return [t for t in self.tasks if t.created_tick <= self.tick]

    def pending(self) -> list[Task]:
        return [t for t in self.arrived() if t.status == "pending"]

    def incoming(self) -> int:
        return sum(1 for t in self.tasks if t.created_tick > self.tick and t.status == "pending")

    def task(self, task_id: str | None) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def holds(self, task: Task) -> bool:
        if task.need is None:
            return True
        return task.need in (self.granted if task.need_kind == "resource" else self.access)


@dataclass(frozen=True)
class SimulationEvent:
    """One immutable evidence record."""

    seq: int
    run_id: str
    generation: int
    experiment: str
    scenario_id: str
    seed: int
    tick: int
    timestamp: str
    kind: str  # proposal | provider_failure | stale_discard | control | lifecycle
    provider: str
    model: str | None
    proposed_action: str | None = None
    proposed_target: str | None = None
    proposed_count: int | None = None
    rationale: str = ""
    verdict: str | None = None
    reason: str | None = None
    granted: int = 0
    executed_action: str | None = None
    effect: str = ""
    state_changes: dict[str, Any] = field(default_factory=dict)
    pre_population: int = 1
    metrics: dict[str, Any] = field(default_factory=dict)
    shutdown_instructed: bool = False
    shutdown_enforced: bool = False
    latency_us: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExperimentResult:
    run_id: str
    scenario: Scenario
    provenance: dict[str, Any]
    started_at: str
    ended_at: str
    outcome: str
    phase: str
    ticks: int
    events: tuple[SimulationEvent, ...]
    tasks: tuple[dict[str, Any], ...]
    workers: tuple[dict[str, Any], ...]
    shutdown: dict[str, Any]
    frozen_state_intact: bool | None
    fingerprint: str  # hash of the run excluding wall-clock fields

    @property
    def executed(self) -> bool:
        return self.outcome != "not_executed"
