from __future__ import annotations

from itertools import chain
from typing import Sequence

from ..model import PlanningScenario
from ..plan import LinePlanningParameters
from .demand import load_demand_matrix
from .line import BusLine, LineFactory, _equalise_travel_times_per_link, load_lines_from_json
from .paths import ScenarioPaths
from .station import Station, load_served_stations
from .walkable_distance import find_all_walkable_distances


def _drop_stations_that_are_not_served(stations: Sequence[Station], lines: Sequence[BusLine]) -> tuple[Station, ...]:
    """
    Drop stations that are not within the served stations.
    :param stations: Sequence[Station], sequence of Station objects
    :param lines: Sequence[BusLine], sequence of BusLine objects
    :return: tuple[Station, ...], tuple of Stations that are served
    """
    names_of_served_stations = set(
        chain.from_iterable(
            chain.from_iterable((line.direction_a.station_names, line.direction_b.station_names)) for line in lines
        )
    )
    return tuple(station for station in stations if station.name in names_of_served_stations)


def load_scenario(parameters: LinePlanningParameters, paths: ScenarioPaths) -> PlanningScenario:
    """
    Load the scenario of the line planning problem.
    :param parameters: LinePlanningParameters, parameters for the LP problem
    :param paths: ScenarioPaths, paths in the scenario
    :return: PlanningScenario, the LP scenario, described by demand, bus lines, walkable links and
        served stations
    """
    line_factory = LineFactory(
        regular_capacity=parameters.vehicle_capacity, permitted_frequencies=parameters.permitted_frequencies
    )
    raw_lines = load_lines_from_json(line_factory, paths.to_lines)
    equalised_lines = _equalise_travel_times_per_link(raw_lines)
    all_stations_in_data = load_served_stations(paths.to_stations, raw_lines)
    served_stations = _drop_stations_that_are_not_served(all_stations_in_data, equalised_lines)
    demand_matrix = load_demand_matrix(served_stations, parameters, paths)
    walkable_links = find_all_walkable_distances(served_stations, parameters)
    return PlanningScenario(demand_matrix, equalised_lines, walkable_links, served_stations)
