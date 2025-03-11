import warnings
import zipfile
from collections import defaultdict
from collections.abc import KeysView
from dataclasses import replace
from enum import IntEnum
from itertools import chain
from pathlib import Path
from types import MappingProxyType
from typing import Any, Collection, Iterable, Mapping, NamedTuple, Optional, Sequence

import pandas as pd

from ..model import BusLine, Direction, DirectionName, LineName, RecordedTrip, StationName, TripNr
from ..utils import pairwise, skip_one_line_in_file


def enrich_lines_with_recorded_trips(path: Path, lines: Collection[BusLine]) -> tuple[BusLine, ...]:
    """
    Enrich lines by converting specified columns to datetime format, and adding recorded trips
        in the directions of bus lines.
    :param path: str, path to the file holding the recorded trips
    :param lines: Collection[BusLine], collection of bus lines
    :return: tuple[BusLine], a tuple of enriched BusLines
    """
    if path.suffix == ".zip":
        with zipfile.ZipFile(path, "r") as zip_file:
            with zip_file.open(zip_file.namelist()[0], "r") as file_handle:
                skip_one_line_in_file(file_handle)
                raw_measurements = pd.read_csv(file_handle, sep=";", encoding="utf-8", dtype=str)
    else:
        with open(path, encoding="utf-8", mode="r") as file_handle:
            skip_one_line_in_file(file_handle)
            raw_measurements = pd.read_csv(file_handle, sep=";", encoding="utf-8", dtype=str)

    enriched_lines = []
    lines_by_name = {line.name: line for line in lines}
    for line_id, grouped_measurements in raw_measurements.groupby("LINIEN_TEXT"):
        line_id = LineName(str(line_id))
        if line_id not in lines_by_name:
            continue
        first_conversion = _convert_these_columns_to_datetime(
            grouped_measurements, ("ANKUNFTSZEIT", "ABFAHRTSZEIT"), "%d.%m.%Y %H:%M"
        )
        second_conversion = _convert_these_columns_to_datetime(
            first_conversion, ("AN_PROGNOSE", "AB_PROGNOSE"), "%d.%m.%Y %H:%M:%S"
        )
        enriched_lines.append(_add_recorded_trips_to_line(lines_by_name[line_id], second_conversion))
    return tuple(enriched_lines)


def _convert_these_columns_to_datetime(
    data_frame: pd.DataFrame, columns: Iterable[str], datetime_format: Optional[str]
) -> pd.DataFrame:
    """
    Convert specified columns to datetime format. Parsing errors are set to NaT.
    :param data_frame: pd.DataFrame, dataframe of bus line information
    :param columns: Iterable[str], iterable of names of the column that need to be converted to datetime
    :param datetime_format: Optional[str], specified format of the datetime, that guides the conversion
    :return: pd.DataFrame, dataframe with specified columns converted to datetime
    """
    for column in columns:
        data_frame[column] = pd.to_datetime(data_frame[column], errors="coerce", format=datetime_format)
    return data_frame


def __is_the_start_of_a_run(row_as_tuple: tuple[Any, ...]) -> bool:
    """
    Check whether a row is the start of the run by checking whether the ''ANKUNFTSZEIT'' is null,
        because at the start of a run, the arrival time is usually not recorded.
    :param row_as_tuple: tuple[Any, ...], tuple that represents a row from a dataframe
    :return: bool, True indicates that the row is the start of the run
    """
    return pd.isnull(row_as_tuple.ANKUNFTSZEIT)  # type: ignore


def __is_the_end_of_a_run(row_as_tuple: tuple[Any, ...]) -> bool:
    """
    Check whether a row is the start of the run by checking whether the ''ABFAHRTSZEIT'' is null.
    :param row_as_tuple: tuple[Any, ...], tuple that represents a row from a dataframe
    :return: bool, True indicates that the row is the end of the run
    """
    return pd.isnull(row_as_tuple.ABFAHRTSZEIT)  # type: ignore


class _Event(IntEnum):
    START = 1
    END = -1


def _find_indices_of_start_and_end_pairs(measurements: pd.DataFrame) -> tuple[tuple[int, int], ...]:
    """
    Find the pair of indices of start and end of a run.
    :param measurements: pd.DataFrame, dataframe containing information of the run
    :return: tuple[tuple[int, int], ...], tuple of pairs of start and end index
    """

    first_departure_with_index = (
        (_Event.START, i) for i, row in enumerate(measurements.itertuples(index=False)) if __is_the_start_of_a_run(row)
    )
    last_arrival_with_index = (
        (_Event.END, i) for i, row in enumerate(measurements.itertuples(index=False)) if __is_the_end_of_a_run(row)
    )
    events_with_indexes = sorted(
        chain.from_iterable((first_departure_with_index, last_arrival_with_index)), key=lambda p: p[1]
    )
    return tuple(
        (first_index, second_index)
        for (first_event, first_index), (second_event, second_index) in pairwise(events_with_indexes)
        if first_event == _Event.START and second_event == _Event.END
    )


def _extract_recorded_trips(
    line_id: LineName, measurements: pd.DataFrame, pairs: Collection[tuple[int, int]]
) -> dict[tuple[StationName, StationName], Sequence[RecordedTrip]]:
    """
    Extract recorded trips from the measurements.
    :param line_id: LineName, name of the bus line
    :param measurements: pd.DataFrame, dataframe containing information of the run
    :param pairs: Collection[tuple[int, int]], pairs of start and end index
    :return: dict[tuple[StationName, StationName], Sequence[RecordedTrip]],
    start station and end station with recorded trips
    """

    recorded_trips_by_start_end = defaultdict(list)
    for i, (begin, end) in enumerate(pairs):
        recorded_trip = RecordedTrip(
            line=line_id,
            direction=DirectionName("UNDEFINED"),
            trip_nr=TripNr(i),
            circulation_id=measurements.iloc[begin].UMLAUF_ID,
            start=measurements.iloc[begin].HALTESTELLEN_NAME,
            end=measurements.iloc[end].HALTESTELLEN_NAME,
            stop_count=end - begin + 1,
            record=pd.DataFrame(
                {
                    "station_name": row.HALTESTELLEN_NAME,
                    "arrival_planned": row.ANKUNFTSZEIT,
                    "arrival_observed": row.AN_PROGNOSE,
                    "departure_planned": row.ABFAHRTSZEIT,
                    "departure_observed": row.AB_PROGNOSE,
                }
                for row in measurements[begin : end + 1].itertuples(index=False)
            ),
        )
        recorded_trips_by_start_end[(recorded_trip.start, recorded_trip.end)].append(recorded_trip)

    return {key: tuple(value) for key, value in recorded_trips_by_start_end.items()}


class StationOrdering(NamedTuple):
    first_occurrence: MappingProxyType[StationName, int]
    last_occurrence: MappingProxyType[StationName, int]

    @classmethod
    def from_direction(cls, direction: Direction) -> "StationOrdering":
        """
        Create a StationOrdering from a Direction.
        :param direction: Direction, the direction
        :return: StationOrdering, the station ordering
        """
        return cls(
            MappingProxyType({name: i for i, name in (reversed(tuple(enumerate(direction.station_sequence))))}),
            MappingProxyType({name: i for i, name in enumerate(direction.station_sequence)}),
        )

    @property
    def keys(self) -> KeysView[StationName]:
        return self.first_occurrence.keys()

    def contains(self, station: StationName) -> bool:
        return station in self.first_occurrence and station in self.last_occurrence


def _assign_recorded_trips_to_directions(
    line: BusLine, recorded_trips: Mapping[tuple[StationName, StationName], Sequence[RecordedTrip]]
) -> tuple[tuple[RecordedTrip, ...], tuple[RecordedTrip, ...], tuple[RecordedTrip, ...]]:
    """
    Assign recorded trips to directions, if the order of start station is smaller than
        the order of end station in direction a, the trip is assigned to direction a.
        Likewise for direction b.
    :param line: BusLine
    :param recorded_trips: Mapping[tuple[str, str], Sequence[RecordedTrip]], start station
        and end station with recorded trips between the stations
    :return: tuple[tuple[RecordedTrip, ...], tuple[RecordedTrip, ...], tuple[RecordedTrip, ...]],
        contains a tuple for recorded trips in direction a, a tuple for direction b, and a tuple
        for missed trips
    """
    order_direction_a = StationOrdering.from_direction(line.direction_up)
    order_direction_b = StationOrdering.from_direction(line.direction_down)

    recorded_trips_in_direction_a: list[RecordedTrip] = []
    recorded_trips_in_direction_b: list[RecordedTrip] = []
    missed_trips: list[RecordedTrip] = []

    for (start, end), trips in recorded_trips.items():
        are_in_direction_a = (
            order_direction_a.contains(start)
            and order_direction_a.contains(end)
            and order_direction_a.first_occurrence[start] < order_direction_a.last_occurrence[end]
        )
        if are_in_direction_a:
            recorded_trips_in_direction_a.extend(t._replace(direction=line.direction_up.name) for t in trips)
            continue
        are_in_direction_b = (
            order_direction_b.contains(start)
            and order_direction_b.contains(end)
            and order_direction_b.first_occurrence[start] < order_direction_b.last_occurrence[end]
        )
        if are_in_direction_b:
            recorded_trips_in_direction_b.extend(t._replace(direction=line.direction_down.name) for t in trips)
            continue
        missed_trips.extend(trips)

    return tuple(recorded_trips_in_direction_a), tuple(recorded_trips_in_direction_b), tuple(missed_trips)


def _add_recorded_trips_to_line(line: BusLine, raw_recordings: pd.DataFrame) -> BusLine:
    """
    Add recorded trips to the corresponding direction of the bus line.
    :param line: BusLine
    :param raw_recordings: pd.DataFrame, dataframe containing trips information
    :return: BusLine, bus line with recorded trips added in the directions
    """
    index_pairs = _find_indices_of_start_and_end_pairs(raw_recordings)
    recorded_trips = _extract_recorded_trips(line.name, raw_recordings, index_pairs)
    in_direction_a, in_direction_b, no_direction = _assign_recorded_trips_to_directions(line, recorded_trips)
    if len(no_direction) > 0:
        warnings.warn(
            f"There are some measurements ({len(no_direction)}) in {line.number=}, {line.name=}\n"
            f"that cannot be assigned a direction \n"
            f"while {len(in_direction_a)} and {len(in_direction_b)} are assigned to the directions.",
            RuntimeWarning,
        )
    return line._replace(
        direction_up=replace(line.direction_up, recorded_trips=in_direction_a),
        direction_down=replace(line.direction_down, recorded_trips=in_direction_b),
    )
