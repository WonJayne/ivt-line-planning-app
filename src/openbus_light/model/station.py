from dataclasses import dataclass
from functools import cached_property
from statistics import mean

from .district import DistrictPoint
from .point import PointIn2D
from .type import DistrictName, LineNr, StationName


@dataclass(frozen=True)
class Station:
    name: StationName
    points: tuple[PointIn2D, ...]
    lines: tuple[LineNr, ...]
    district_points: list[DistrictPoint]
    districts_names: list[DistrictName]

    @cached_property
    def center_position(self) -> PointIn2D:
        """
        Get the geometry of center position of the station.
        :return: PointIn2D, geometry of the center point
        """
        return PointIn2D(lat=mean(p.lat for p in self.points), long=mean(p.long for p in self.points))
