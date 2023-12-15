from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property
from types import MappingProxyType
from typing import NamedTuple, Optional

from ..model import BusLine, Direction
from .network import Activity


class PassengersPerLink(NamedTuple):
    start: str
    end: str
    pax: float


class LPPSolution(NamedTuple):
    weighted_travel_time: MappingProxyType[Activity, timedelta]
    used_vehicles: float
    active_lines: tuple[BusLine, ...]
    passengers_per_link: MappingProxyType[BusLine, MappingProxyType[Direction, tuple[PassengersPerLink, ...]]]


@dataclass(frozen=True)
class LPPResult:
    _solution: Optional[LPPSolution]

    @staticmethod
    def from_error() -> LPPResult:
        """
        Create a result representing an error condition where no solution is available.
        :return: LPPResult
        """
        return LPPResult(None)

    @staticmethod
    def from_success(solution: LPPSolution) -> LPPResult:
        """
        Create a result representing a successful solution to the linear programming problem.
        :param solution: LPPSolution
        :return: LPPResult
        """
        return LPPResult(solution)

    @property
    def solution(self) -> LPPSolution:
        """
        Return solution of the LP problem, if no solution, raise error.
        :return: LPPSolution, solution of the linear programming problem
        """
        if self._solution is None:
            raise AttributeError("Tried to get solution from failed result")
        return self._solution

    @cached_property
    def success(self) -> bool:
        """
        Check whether the linear programming problem has a solution.
        :return: bool, if True, the problem has a solution, otherwise the problem doesn't
        """
        return self._solution is not None

    @property
    def failed(self) -> bool:
        """
        Opposite of ``success(self)``
        :return: bool
        """
        return not self.success
