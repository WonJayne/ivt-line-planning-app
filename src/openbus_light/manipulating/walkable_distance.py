from __future__ import annotations

from datetime import timedelta
from itertools import combinations
from typing import Collection

from ..line_planning import LinePlanningParameters
from ..manipulating import calculate_distance_in_m
from ..modelling import Station, WalkableDistance


def find_all_walkable_distances(
    stations: Collection[Station], parameters: LinePlanningParameters
) -> tuple[WalkableDistance, ...]:
    return tuple(
        WalkableDistance(first, second, timedelta(seconds=distance / parameters.walking_speed_between_stations))
        for first, second in combinations(stations, r=2)
        if (distance := calculate_distance_in_m(first.center_position, second.center_position))
        < parameters.maximal_walking_distance
    )
