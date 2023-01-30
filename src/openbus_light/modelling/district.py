from dataclasses import dataclass

from .point import DistrictPoints, PointIn2D


@dataclass(frozen=True)
class District:
    name: str
    center_position: PointIn2D
    points: tuple[DistrictPoints, ...]
