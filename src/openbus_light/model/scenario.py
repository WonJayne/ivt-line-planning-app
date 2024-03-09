from itertools import chain
from typing import NamedTuple

from .demand import DemandMatrix
from .line import BusLine
from .station import Station
from .walkable_distance import WalkableDistance


class PlanningScenario(NamedTuple):
    demand_matrix: DemandMatrix
    bus_lines: tuple[BusLine, ...]
    walkable_distances: tuple[WalkableDistance, ...]
    stations: tuple[Station, ...]

    def check_consistency(self) -> None:
        """
        Check consistency, whether stations involved in the Scenario are covered by
            the set of stations that are served by bus lines.
        """
        all_served_station_names = frozenset(
            chain.from_iterable(
                line.direction_a.station_sequence + line.direction_b.station_sequence for line in self.bus_lines
            )
        )
        self._check_station_and_lines_consistency(all_served_station_names)
        self._check_station_and_demand_consistency(all_served_station_names)
        self._check_station_and_walk_consistency(all_served_station_names)

    def _check_station_and_lines_consistency(self, all_served_station_names: frozenset[str]) -> None:
        """
        Check the consistency between stations and lines. If any stations in the Scenario are not served
            at least one line, raise error.
        :param all_served_station_names: frozenset[str], names of all stations that are served by bus lines
        """
        all_station_names = frozenset(station.name for station in self.stations)
        if not all_served_station_names.issuperset(all_station_names):
            not_served_stations = all_station_names.difference(all_served_station_names)
            raise ValueError(f"Some Stations are not served by any line: {not_served_stations}")

    def _check_station_and_demand_consistency(self, all_served_station_names: frozenset[str]) -> None:
        """
        Check the consistency between station and demand. If any stations involved in the demand matrix
            are not within the stations served by lines, raise error.
        :param all_served_station_names: frozenset[str], names of all stations that are served by bus lines
        """
        all_stations_in_demand = set(
            chain.from_iterable(flows_to.keys() for flows_to in self.demand_matrix.matrix.values())
        ) | set(self.demand_matrix.all_origins())
        if not all_served_station_names.issuperset(all_stations_in_demand):
            not_served_stations = all_stations_in_demand.difference(all_served_station_names)
            raise ValueError(f"Some Origins or Destinations are not served by any line: {not_served_stations}")

    def _check_station_and_walk_consistency(self, all_served_station_names: frozenset[str]) -> None:
        """
        Check the consistency of stations of walkable distance. If stations involved in the
            ``walkable_distances`` are not within the stations served by lines, raise error.
        :param all_served_station_names: frozenset[str], names of all stations that are served by bus lines
        """
        walkable_stations = set(
            chain.from_iterable((link.ending_at.name, link.ending_at.name) for link in self.walkable_distances)
        )
        if not all_served_station_names.issuperset(walkable_stations):
            not_served_stations = walkable_stations.difference(all_served_station_names)
            raise ValueError(f"Some Walking Distances are not served by any line: {not_served_stations}")
