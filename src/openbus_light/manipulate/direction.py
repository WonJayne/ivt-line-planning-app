from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from ..model import Direction
from ..model.type import StationName


def update_trip_times(
    average_travel_time_per_link: dict[tuple[StationName, StationName], timedelta], direction: Direction
) -> Direction:
    """
    Update the trip times based on the average travel between stations of each link
    :param average_travel_time_per_link: dict[tuple[str, str], timedelta], average travel
        time between consecutive stations of each link
    :param direction: Direction, direction of link
    :return: Direction, direction with updated trip times
    """
    return replace(
        direction, trip_times=tuple(average_travel_time_per_link[(u, v)] for u, v in direction.station_names_as_pairs)
    )
