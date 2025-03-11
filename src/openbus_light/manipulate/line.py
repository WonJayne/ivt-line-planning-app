import glob
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from itertools import chain
from pathlib import Path
from statistics import mean
from typing import Any, Sequence

from tqdm import tqdm

from ..model import BusLine, Direction, DirectionName, LineFrequency, LineName, LineNr, VehicleCapacity
from ..model.type import StationName
from .direction import update_trip_times


def _convert_seconds_to_timedelta(seconds: float) -> timedelta:
    """
    Convert seconds to timedelta.
    :param seconds: float, time in second
    :return: timedelta
    """
    return timedelta(seconds=seconds)


@dataclass(frozen=True)
class LineFactory:
    regular_capacity: VehicleCapacity
    permitted_frequencies: tuple[LineFrequency, ...]

    def create_line_from_json(self, idx: LineNr, json_data: dict[Any, Any]) -> BusLine:
        """
        Create busline information from json. If the number of stations is not consistent, raise error.
        :param idx: int, the index of bus lines
        :param json_data: dict[Any, Any], a dict containing data from a JSON representation of a bus line
        :return: BusLine, object which contains information of index, name of busline, two directions,
            capacity and frequency of the bus line
        """
        line_name = LineName(str(json_data["nummer"]))

        direction_a = Direction(
            station_sequence=tuple(map(str, json_data["linie_a"])),  # type: ignore
            trip_times=tuple(map(_convert_seconds_to_timedelta, json_data["fahrzeiten_a"])),
            name=DirectionName("a"),
        )

        direction_b = Direction(
            station_sequence=tuple(map(str, json_data["linie_b"])),  # type: ignore
            trip_times=tuple(map(_convert_seconds_to_timedelta, json_data["fahrzeiten_b"])),
            name=DirectionName("b"),
        )

        if not direction_a.station_count == json_data["stops_a"]:
            raise RuntimeError("Import failed due to inconsistent number of stops")
        if not direction_b.station_count == json_data["stops_b"]:
            raise RuntimeError("Import failed due to inconsistent number of stops")

        return BusLine(idx, line_name, direction_a, direction_b, self.regular_capacity, self.permitted_frequencies)


def load_lines_from_json(line_factory: LineFactory, path_to_lines: Path) -> tuple[BusLine, ...]:
    """
    Iterate over each json file and create bus lines from the data.
    :param line_factory: LineFactory, contains capacity and permitted frequency of lines
    :param path_to_lines: str, path to the directory containing JSON files with bus line data
    :return: tuple[BusLine, ...], a tuple containing the loaded BusLine objects
    """
    loaded_lines: list[BusLine] = []
    all_files_to_load = glob.glob(os.path.join(path_to_lines, "*.json"))
    for i, line_to_load in enumerate(tqdm(all_files_to_load, desc="importing lines", colour="blue")):
        with open(line_to_load, encoding="utf-8") as json_file:
            loaded_lines.append(line_factory.create_line_from_json(LineNr(i), json.load(json_file)))
    return tuple(loaded_lines)


def _equalise_travel_times_per_link(lines: Sequence[BusLine]) -> tuple[BusLine, ...]:
    """
    Equalize the travel times per link across different bus lines with the average travel time.
    :param lines: Sequence[BusLine], sequence of busline objects
    :return: tuple[BusLine, ...], a tuple of BusLine objects with equal travel time
    """
    average_travel_time_per_link = _calculate_average_travel_time_per_link(lines)
    return tuple(
        line._replace(
            direction_up=update_trip_times(average_travel_time_per_link, line.direction_up),
            direction_down=update_trip_times(average_travel_time_per_link, line.direction_down),
        )
        for line in lines
    )


def _calculate_average_travel_time_per_link(
    lines: Sequence[BusLine],
) -> dict[tuple[StationName, StationName], timedelta]:
    """
    Calculate the average travel time per link across all the directions of bus lines.
    :param lines: Sequence[BusLine], sequence of BusLine objects
    :return: dict[tuple[str, str], timedelta], a dict where key is source and target of the link,
        and value is the average travel time of the link
    """
    travel_times_per_link: dict[tuple[StationName, StationName], list[float]] = defaultdict(list)
    for direction in chain.from_iterable((line.direction_up, line.direction_down) for line in lines):
        for (source, target), time_delta in direction.trip_time_by_pair():
            travel_times_per_link[(source, target)].append(time_delta.total_seconds())
    return {k: timedelta(seconds=round(mean(v))) for k, v in travel_times_per_link.items()}
