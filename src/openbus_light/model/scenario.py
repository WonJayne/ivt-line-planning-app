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
        all_served_station_names = frozenset(
            chain.from_iterable(
                line.direction_a.station_names + line.direction_b.station_names for line in self.bus_lines
            )
        )
        self._check_station_and_lines_consistency(all_served_station_names)
        self._check_station_and_demand_consistency(all_served_station_names)
        self._check_station_and_walk_consistency(all_served_station_names)

    def _check_station_and_lines_consistency(self, all_served_station_names: frozenset[str]) -> None:
        all_station_names = frozenset(station.name for station in self.stations)
        if not all_served_station_names.issuperset(all_station_names):
            not_served_stations = all_station_names.difference(all_served_station_names)
            raise ValueError(f"Some Stations are not served by any line: {not_served_stations}")

    def _check_station_and_demand_consistency(self, all_served_station_names: frozenset[str]) -> None:
        all_stations_in_demand = set(
            chain.from_iterable(flows_to.keys() for flows_to in self.demand_matrix.matrix.values())
        ) | set(self.demand_matrix.all_origins())
        if not all_served_station_names.issuperset(all_stations_in_demand):
            not_served_stations = all_stations_in_demand.difference(all_served_station_names)
            raise ValueError(f"Some Origins or Destinations are not served by any line: {not_served_stations}")

    def _check_station_and_walk_consistency(self, all_served_station_names: frozenset[str]) -> None:
        walkable_stations = set(
            chain.from_iterable((link.ending_at.name, link.ending_at.name) for link in self.walkable_distances)
        )
        if not all_served_station_names.issuperset(walkable_stations):
            not_served_stations = walkable_stations.difference(all_served_station_names)
            raise ValueError(f"Some Walking Distances are not served by any line: {not_served_stations}")
