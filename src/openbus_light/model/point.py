from typing import Any, NamedTuple


class PointIn2D(NamedTuple):
    lat: float
    long: float

    def __hash__(self) -> int:
        return hash((self.lat, self.long))

    def __eq__(self, other: Any) -> bool:
        return self.__hash__() == other.__hash__() if isinstance(PointIn2D, other) else False


class DistrictPoints(NamedTuple):
    position: PointIn2D
    district_name: str
    id: str
