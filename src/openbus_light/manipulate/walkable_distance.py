from __future__ import annotations

from datetime import timedelta
from itertools import combinations
from typing import Collection

from ..model import Station, WalkableDistance
from ..plan import LinePlanningParameters
from .point import calculate_distance_in_m


def find_all_walkable_distances(
    stations: Collection[Station], parameters: LinePlanningParameters
) -> tuple[WalkableDistance, ...]:
    """
    Get all walkable distances between pairs of stations.
    :param stations: Collection[Station], collection of bus stations
    :param parameters: LinePlanningParameters, parameters of line planning problem, including walking speed
        and maximal walking distances
    :return: tuple[WalkableDistance, ...], WalkableDistance between pairs of stations
    """
    return tuple(
        WalkableDistance(first, second, timedelta(seconds=distance / parameters.walking_speed_between_stations))
        for first, second in combinations(stations, r=2)
        if (distance := calculate_distance_in_m(first.center_position, second.center_position))
        < parameters.maximal_walking_distance
    )
