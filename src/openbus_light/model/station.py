from dataclasses import dataclass
from functools import cached_property
from statistics import fmean

try:  # pragma: no cover - optional dependency
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover
    np = None  # type: ignore[assignment]

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
        latitudes = tuple(point.lat for point in self.points)
        longitudes = tuple(point.long for point in self.points)

        if np is not None:  # pragma: no branch - simple guard
            return PointIn2D(
                lat=float(np.nanmean(latitudes)),  # type: ignore[arg-type]
                long=float(np.nanmean(longitudes)),  # type: ignore[arg-type]
            )

        return PointIn2D(lat=fmean(latitudes), long=fmean(longitudes))
