from dataclasses import dataclass
from functools import cached_property
from statistics import mean

from .point import DistrictPoints, PointIn2D


@dataclass(frozen=True)
class Station:
    name: str
    points: tuple[PointIn2D, ...]
    lines: tuple[int, ...]
    district_points: list[DistrictPoints]
    districts_names: list[str]

    @cached_property
    def center_position(self) -> PointIn2D:
        """
        Get the geometry of center position of the station.
        :return: PointIn2D, geometry of the center point
        """
        return PointIn2D(lat=mean(p.lat for p in self.points), long=mean(p.long for p in self.points))
