from collections.abc import Mapping
from dataclasses import dataclass

from openbus_light.model.type import StationName


@dataclass(frozen=True)
class DemandMatrix:
    matrix: Mapping[StationName, Mapping[StationName, float]]

    def all_origins(self) -> tuple[StationName, ...]:
        """
        Get all the origins of the demand matrix.
        :return: tuple[str, ...], tuple of the names of origins
        """
        return tuple(self.matrix.keys())

    def between(self, origin: StationName, destination: StationName) -> float:
        """
        Get the demand between two certain stations.
        :param origin: str, the origin station
        :param destination: str, the destined station
        :return: the demand between the stations
        """
        return self.matrix[origin][destination]

    def starting_from(self, origin: StationName) -> float:
        """
        Calculate the total demand starting from the given origin.
        :param origin: str, the origin station
        :return: the total demand from the origin
        """
        return sum(self.matrix[origin].values())

    def arriving_at(self, destination: StationName) -> float:
        """
        Calculate the total demand arriving at the given destination.
        :param destination: str, the destined station
        :return: the total demand arriving at the destination
        """
        return sum(destinations[destination] for destinations in self.matrix.values() if destination in destinations)

    def all_od_pairs(self) -> tuple[tuple[StationName, StationName, float], ...]:
        """
        Get all the origin-destination pairs in the demand matrix.
        :return: tuple[tuple[str, str], ...], tuple of origin-destination pairs
        """
        return tuple(
            (origin, destination, flow) for origin in self.matrix for destination, flow in self.matrix[origin].items()
        )
