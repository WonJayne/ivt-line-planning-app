from dataclasses import dataclass


@dataclass(frozen=True)
class DemandMatrix:
    matrix: dict[str, dict[str, float]]

    def all_origins(self) -> tuple[str, ...]:
        """
        Get all the origins of the demand matrix.
        :return: tuple[str, ...], tuple of the names of origins
        """
        return tuple(self.matrix.keys())

    def between(self, origin: str, destination: str) -> float:
        """
        Get the demand between two certain stations.
        :param origin: str, the origin station
        :param destination: str, the destined station
        :return: the demand between the stations
        """
        return self.matrix[origin][destination]

    def starting_from(self, origin: str) -> float:
        """
        Calculate the total demand starting from the given origin.
        :param origin: str, the origin station
        :return: the total demand from the origin
        """
        return sum(self.matrix[origin].values())

    def arriving_at(self, destination: str) -> float:
        """
        Calculate the total demand arriving at the given destination.
        :param destination: str, the destined station
        :return: the total demand arriving at the destination
        """
        return sum(destinations[destination] for destinations in self.matrix.values() if destination in destinations)
