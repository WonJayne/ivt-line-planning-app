import warnings
from collections import defaultdict
from dataclasses import replace
from enum import IntEnum
from itertools import chain
from typing import Any, Collection, Iterable, Mapping, Optional, Sequence

import pandas as pd

from ..model import BusLine, Direction, RecordedTrip
from ..utils import pairwise, skip_one_line_in_file


def enrich_lines_with_recorded_trips(path: str, lines: Collection[BusLine]) -> tuple[BusLine, ...]:
    with open(path, encoding="utf-8", mode="r") as file_handle:
        skip_one_line_in_file(file_handle)
        raw_measurements = pd.read_csv(file_handle, sep=";", encoding="utf-8", dtype=str)

    enriched_lines = []
    lines_by_number = {str(line.number): line for line in lines}
    for line_id, grouped_measurements in raw_measurements.groupby("LINIEN_TEXT"):
        if line_id not in lines_by_number:
            continue
        first_conversion = _convert_these_columns_to_datetime(
            grouped_measurements, ("ANKUNFTSZEIT", "ABFAHRTSZEIT"), "%d.%m.%Y %H:%M"
        )
        second_conversion = _convert_these_columns_to_datetime(
            first_conversion, ("AN_PROGNOSE", "AB_PROGNOSE"), "%d.%m.%Y %H:%M:%S"
        )
        enriched_lines.append(_add_recorded_trips_to_line(lines_by_number[line_id], second_conversion))
    return tuple(enriched_lines)


def _convert_these_columns_to_datetime(
    data_frame: pd.DataFrame, columns: Iterable[str], datetime_format: Optional[str]
) -> pd.DataFrame:
    for column in columns:
        data_frame[column] = pd.to_datetime(data_frame[column], errors="coerce", format=datetime_format)
    return data_frame


def __is_the_start_of_a_run(row_as_tuple: tuple[Any, ...]) -> bool:
    return pd.isnull(row_as_tuple.ANKUNFTSZEIT)  # type: ignore


def __is_the_end_of_a_run(row_as_tuple: tuple[Any, ...]) -> bool:
    return pd.isnull(row_as_tuple.ABFAHRTSZEIT)  # type: ignore


def _find_index_of_start_and_end_pairs(measurements: pd.DataFrame) -> tuple[tuple[int, int], ...]:
    class _Event(IntEnum):
        START = 1
        END = -1

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
    line_nr: int, measurements: pd.DataFrame, pairs: Collection[tuple[int, int]]
) -> dict[tuple[str, str], tuple[RecordedTrip, ...]]:
    recorded_trips_by_start_end = defaultdict(list)

    for begin, end in pairs:
        recorded_trip = RecordedTrip(
            number=line_nr,
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


def __get_stop_name_order(direction: Direction) -> dict[str, int]:
    count = 0
    return {name: (count := count + 1) for name in direction.station_names}


def _assign_recorded_trips_to_directions(
    line: BusLine, recorded_trips: Mapping[tuple[str, str], Sequence[RecordedTrip]]
) -> tuple[tuple[RecordedTrip, ...], tuple[RecordedTrip, ...], tuple[RecordedTrip, ...]]:
    stops_order_direction_a = __get_stop_name_order(line.direction_a)
    stop_order_direction_b = __get_stop_name_order(line.direction_b)

    recorded_trips_in_direction_a: list[RecordedTrip] = []
    recorded_trips_in_direction_b: list[RecordedTrip] = []
    missed_trips: list[RecordedTrip] = []

    for (start, end), trips in recorded_trips.items():
        are_in_direction_a = (
            start in stops_order_direction_a
            and end in stops_order_direction_a
            and stops_order_direction_a[start] < stops_order_direction_a[end]
        )
        if are_in_direction_a:
            recorded_trips_in_direction_a.extend(trips)
            continue
        are_in_direction_b = (
            start in stop_order_direction_b
            and end in stop_order_direction_b
            and stop_order_direction_b[start] < stop_order_direction_b[end]
        )
        if are_in_direction_b:
            recorded_trips_in_direction_b.extend(trips)
            continue
        missed_trips.extend(trips)

    return tuple(recorded_trips_in_direction_a), tuple(recorded_trips_in_direction_b), tuple(missed_trips)


def _add_recorded_trips_to_line(line: BusLine, raw_recordings: pd.DataFrame) -> BusLine:
    index_pairs = _find_index_of_start_and_end_pairs(raw_recordings)
    recorded_trips = _extract_recorded_trips(line.number, raw_recordings, index_pairs)
    in_direction_a, in_direction_b, no_direction = _assign_recorded_trips_to_directions(line, recorded_trips)
    if len(no_direction) > 0:
        warnings.warn(
            f"There are some measurements ({len(no_direction)}) in {line.number} "
            f"that cannot be assigned a direction "
        )
    updated_direction_a = replace(line.direction_a, recorded_trips=in_direction_a)
    updated_direction_b = replace(line.direction_b, recorded_trips=in_direction_b)
    return line._replace(direction_a=updated_direction_a, direction_b=updated_direction_b)
