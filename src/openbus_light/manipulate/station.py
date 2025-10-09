from __future__ import annotations

import csv
import zipfile
from io import TextIOWrapper
from itertools import chain
from pathlib import Path
from types import SimpleNamespace
from typing import Collection, Iterable

try:  # pragma: no cover - optional dependency
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover
    pd = None

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
            with zip_file.open(zip_file.namelist()[0], "r") as binary_handle:
                with TextIOWrapper(binary_handle, encoding="utf-8") as text_handle:
                    skip_one_line_in_file(text_handle)
                    station_rows = tuple(_read_station_rows(text_handle))
    elif path_to_stations.suffix == ".csv":
        with open(path_to_stations, encoding="utf-8") as text_handle:
            skip_one_line_in_file(text_handle)
            station_rows = tuple(_read_station_rows(text_handle))
    else:
        raise ValueError(f"Unsupported file format: {path_to_stations}")

    points_per_station: dict[str, list[PointIn2D]] = {name: [] for name in served_station_names}
    for raw_point in station_rows:
        point_name = raw_point.BEZEICHNUNG_OFFIZIELL
        if point_name not in served_station_names:
            continue
        if _is_missing(raw_point.N_WGS84) or _is_missing(raw_point.E_WGS84):
            continue
        points_per_station[point_name].append(PointIn2D(lat=float(raw_point.N_WGS84), long=float(raw_point.E_WGS84)))

    return tuple(
        Station(name=StationName(name), points=tuple(points), lines=tuple(), district_points=[], districts_names=[])
        for name, points in points_per_station.items()
    )


def _read_station_rows(file_handle) -> Iterable[SimpleNamespace]:
    if pd is not None:
        frame = pd.read_csv(file_handle, sep=";", encoding="utf-8", dtype=str)
        yield from frame.itertuples(index=False)
        return
    reader = csv.DictReader(file_handle, delimiter=";")
    for row in reader:
        yield SimpleNamespace(**row)


def _is_missing(value: object) -> bool:
    if pd is not None:
        return pd.isnull(value) or str(value).strip() == ""
    return value is None or str(value).strip() == ""
