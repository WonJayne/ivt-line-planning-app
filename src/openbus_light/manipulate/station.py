from __future__ import annotations

from itertools import chain
from typing import Collection

import pandas as pd

from ..model import BusLine, PointIn2D, Station
from ..utils import skip_one_line_in_file


def load_served_stations(path_to_stations: str, lines: Collection[BusLine]) -> tuple[Station, ...]:
    """
    Load served stations and the coordinates.
    :param path_to_stations: str, name of file with contains station information
    :param lines: Collection[BusLine], collection of bus lines
    :return: tuple[Station, ...], served stations with their coordinates
    """
    served_station_names = set(
        chain.from_iterable(
            chain.from_iterable((line.direction_a.station_names, line.direction_b.station_names)) for line in lines
        )
    )
    with open(path_to_stations, encoding="utf-8") as file_handle:
        skip_one_line_in_file(file_handle)
        stations_df = pd.read_csv(file_handle, sep=";", encoding="utf-8", dtype=str)

    points_per_station: dict[str, list[PointIn2D]] = {name: [] for name in served_station_names}
    for raw_point in stations_df.itertuples(index=False):
        point_name = raw_point.BEZEICHNUNG_OFFIZIELL
        if point_name not in served_station_names:
            continue
        points_per_station[point_name].append(PointIn2D(lat=float(raw_point.N_WGS84), long=float(raw_point.E_WGS84)))

    return tuple(
        Station(name=name, points=tuple(points), lines=tuple(), district_points=[], districts_names=[])
        for name, points in points_per_station.items()
    )
