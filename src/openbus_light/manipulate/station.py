from __future__ import annotations

import zipfile
from itertools import chain
from pathlib import Path
from typing import Collection

import pandas as pd

from ..model.line import BusLine
from ..model.point import PointIn2D
from ..model.station import Station
from ..model.type import StationName
from ..utils import skip_one_line_in_file


def load_served_stations(path_to_stations: Path, lines: Collection[BusLine]) -> tuple[Station, ...]:
    """
    Load served stations and the coordinates.
    :param path_to_stations: str, name of file with contains station information
    :param lines: Collection[BusLine], collection of bus lines
    :return: tuple[Station, ...], served stations with their coordinates
    """
    served_station_names = frozenset(
        chain.from_iterable(
            chain.from_iterable((line.direction_up.station_sequence, line.direction_down.station_sequence))
            for line in lines
        )
    )
    if path_to_stations.suffix == ".zip":
        with zipfile.ZipFile(path_to_stations, "r") as zip_file:
            with zip_file.open(zip_file.namelist()[0], "r") as file_handle:
                skip_one_line_in_file(file_handle)
                stations_df = pd.read_csv(file_handle, sep=";", encoding="utf-8", dtype=str)
    elif path_to_stations.suffix == ".csv":
        with open(path_to_stations, encoding="utf-8") as file_handle:
            skip_one_line_in_file(file_handle)
            stations_df = pd.read_csv(file_handle, sep=";", encoding="utf-8", dtype=str)
    else:
        raise ValueError(f"Unsupported file format: {path_to_stations}")

    points_per_station: dict[str, list[PointIn2D]] = {name: [] for name in served_station_names}
    for raw_point in stations_df.itertuples(index=False):
        point_name = raw_point.BEZEICHNUNG_OFFIZIELL
        if point_name not in served_station_names:
            continue
        points_per_station[point_name].append(PointIn2D(lat=float(raw_point.N_WGS84), long=float(raw_point.E_WGS84)))

    return tuple(
        Station(name=StationName(name), points=tuple(points), lines=tuple(), district_points=[], districts_names=[])
        for name, points in points_per_station.items()
    )
