from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from types import MappingProxyType
from typing import NamedTuple, Optional

from ..modelling import BusLine
from .network import Activity


class LPPSolution(NamedTuple):
    weighted_travel_time: MappingProxyType[Activity, timedelta]
    used_vehicles: float
    active_lines: tuple[BusLine, ...]


@dataclass(frozen=True)
class LPPResult:
    _solution: Optional[LPPSolution]

    @staticmethod
    def from_error() -> LPPResult:
        return LPPResult(None)

    @staticmethod
    def from_success(solution: LPPSolution) -> LPPResult:
        return LPPResult(solution)

    @property
    def solution(self) -> LPPSolution:
        if self._solution is None:
            raise AttributeError("Tried to get solution from failed result")
        return self._solution

    @cached_property
    def success(self) -> bool:
        return self._solution is not None

    def failed(self) -> bool:
        return not self.success
