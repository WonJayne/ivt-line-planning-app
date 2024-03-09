from dataclasses import dataclass
from functools import cached_property

import numpy as np

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

    def __post_init__(self) -> None:
        assert len(self.points) > 0, self
        assert self.center_position.long < float("inf") and self.center_position.lat < float("inf"), self

    @cached_property
    def center_position(self) -> PointIn2D:
        """
        Get the geometry of center position of the station.
        :return: PointIn2D, geometry of the center point
        """
        return PointIn2D(
            lat=np.nanmean(tuple(p.lat for p in self.points)),  # type: ignore
            long=np.nanmean(tuple(p.long for p in self.points)),  # type: ignore
        )
