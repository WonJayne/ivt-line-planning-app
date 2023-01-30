import glob
import json
import os
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import timedelta
from itertools import chain
from statistics import mean
from typing import Any, Sequence

from tqdm import tqdm

from ..modelling import BusLine, Direction
from .direction import update_trip_times


def _convert_seconds_to_timedelta(seconds: float) -> timedelta:
    return timedelta(seconds=seconds)


@dataclass(frozen=True)
class LineFactory:
    regular_capacity: int
    permitted_frequencies: tuple[int, ...]

    def create_line_from_json(self, json_data: dict[Any, Any]) -> BusLine:
        number = int(json_data["nummer"])

        direction_a = Direction(
            station_names=tuple(map(str, json_data["linie_a"])),
            trip_times=tuple(map(_convert_seconds_to_timedelta, json_data["fahrzeiten_a"])),
            name="a",
        )

        direction_b = Direction(
            station_names=tuple(map(str, json_data["linie_b"])),
            trip_times=tuple(map(_convert_seconds_to_timedelta, json_data["fahrzeiten_b"])),
            name="b",
        )

        if not direction_a.station_count == json_data["stops_a"]:
            raise RuntimeError("Import failed due to inconsistent number of stops")
        if not direction_b.station_count == json_data["stops_b"]:
            raise RuntimeError("Import failed due to inconsistent number of stops")

        return BusLine(number, direction_a, direction_b, self.regular_capacity, self.permitted_frequencies)


def load_lines_from_json(line_factory: LineFactory, path_to_lines: str) -> tuple[BusLine, ...]:
    loaded_lines: list[BusLine] = []
    all_files_to_load = glob.glob(os.path.join(path_to_lines, "*.json"))
    for line_to_load in tqdm(all_files_to_load, desc="importing lines", colour="green"):
        with open(line_to_load, encoding="utf-8") as json_file:
            loaded_lines.append(line_factory.create_line_from_json(json.load(json_file)))
    return tuple(loaded_lines)


def equalise_travel_times_per_link(lines: Sequence[BusLine]) -> tuple[BusLine, ...]:
    average_travel_time_per_link = _calculate_average_travel_time_per_link(lines)
    return tuple(
        replace(
            line,
            direction_a=update_trip_times(average_travel_time_per_link, line.direction_a),
            direction_b=update_trip_times(average_travel_time_per_link, line.direction_b),
        )
        for line in lines
    )


def _calculate_average_travel_time_per_link(lines: Sequence[BusLine]) -> dict[tuple[str, str], timedelta]:
    travel_times_per_link: dict[tuple[str, str], list[float]] = defaultdict(list)
    for direction in chain.from_iterable((line.direction_a, line.direction_b) for line in lines):
        for (source, target), time_delta in direction.trip_time_per_stop_pair():
            travel_times_per_link[(source, target)].append(time_delta.total_seconds())
    return {k: timedelta(seconds=round(mean(v))) for k, v in travel_times_per_link.items()}
