from typing import NamedTuple

from .point import PointIn2D
from .type import DistrictName, DistrictPointId


class DistrictPoint(NamedTuple):
    position: PointIn2D
    district_name: DistrictName
    id: DistrictPointId


class District(NamedTuple):
    name: DistrictName
    center_position: PointIn2D
    points: tuple[DistrictPoint, ...]
