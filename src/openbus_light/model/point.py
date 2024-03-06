from typing import Any, NamedTuple


class PointIn2D(NamedTuple):
    lat: float
    long: float

    def __hash__(self) -> int:
        """
        Enable hashing of instances of the class.
        :return: int, the hash value of the geometry
        """
        return hash((self.lat, self.long))

    def __eq__(self, other: Any) -> bool:
        """
        Check if inputs are PointIn2D. If so, compare the equality based on hash values.
        :param other: Any
        :return: bool
        """
        return self.__hash__() == other.__hash__() if isinstance(PointIn2D, other) else False
