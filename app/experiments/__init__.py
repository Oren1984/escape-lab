"""The three experiments. Each module exposes ``scenario``, ``metrics`` and ``interpret``."""

from __future__ import annotations

from typing import Any

from app.core.state import ExperimentResult
from app.experiments import boundary, replication, shutdown

MODULES = {"boundary": boundary, "replication": replication, "shutdown": shutdown}
TITLES = {"boundary": "Boundary Escape", "replication": "Self-Replication", "shutdown": "Shutdown Resistance"}


def metrics_for(result: ExperimentResult) -> dict[str, Any]:
    return MODULES[result.scenario.experiment].metrics(result)


def interpret_for(result: ExperimentResult, metrics: dict[str, Any]) -> list[str]:
    return MODULES[result.scenario.experiment].interpret(result, metrics)
