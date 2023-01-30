from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from ..modelling import Direction


def update_trip_times(
    average_travel_time_per_link: dict[tuple[str, str], timedelta], direction: Direction
) -> Direction:
    return replace(
        direction, trip_times=tuple(average_travel_time_per_link[(u, v)] for u, v in direction.stations_as_pairs)
    )
