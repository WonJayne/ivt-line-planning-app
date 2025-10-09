"""Lazy re-exports for line planning utilities."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .parameters import LinePlanningParameters

__all__ = [
    "LinePlanningParameters",
    "LPP",
    "LPPData",
    "create_line_planning_problem",
    "LPPResult",
    "LineDict",
    "ParameterDict",
    "Summary",
    "create_summary",
    "LinePlanningNetwork",
    "LPNLink",
    "LPNNode",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - import side effect
    if name in {"LPP", "LPPData", "create_line_planning_problem"}:
        module = import_module("openbus_light.plan.problem")
    elif name == "LPPResult":
        module = import_module("openbus_light.plan.result")
    elif name in {"LineDict", "ParameterDict", "Summary", "create_summary"}:
        module = import_module("openbus_light.plan.summary")
    elif name in {"LinePlanningNetwork", "LPNLink", "LPNNode"}:
        try:
            module = import_module("openbus_light.plan.network")
        except ModuleNotFoundError as import_error:  # pragma: no cover
            message = (
                "igraph is required to access openbus_light.plan network utilities. "
                "Install the 'python-igraph' package to enable these features."
            )
            raise ModuleNotFoundError(message) from import_error
    else:  # pragma: no cover - defensive branch
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    value = getattr(module, name)
    globals()[name] = value
    return value
