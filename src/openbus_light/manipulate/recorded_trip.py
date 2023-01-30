from collections import defaultdict
from dataclasses import replace
from datetime import timedelta
from typing import Collection, Tuple

import pandas as pd

from ..model import BusLine, RecordedTrip
from ..utils import skip_one_line_in_file


def _load_all_measurements() -> None:
    pass


def load_lines_from_measurements(path: str, lines: Collection[BusLine]) -> tuple[BusLine, ...]:
    with open(path, encoding="utf-8", mode="r") as file_handle:
        skip_one_line_in_file(file_handle)
        raw_measurements = pd.read_csv(file_handle, sep=";", encoding="utf-8", dtype=str)

    enriched_lines = []
    for line in lines:
        measurement_for_this_line = raw_measurements[raw_measurements["LINIEN_TEXT"] == str(line.number)]
        enriched_lines.append(_add_measurements_to_lines(line, measurement_for_this_line))
    return tuple(enriched_lines)


if __name__ == "__main__":
    load_lines_from_measurements("data\\scenario\\Messungen.csv", [])


def _find_all_start_end_pairs_in_measurements(measurements: pd.DataFrame) -> tuple[tuple[int, int], ...]:
    departure_event_with_index = tuple(
        (0, i) for i, row in enumerate(measurements.itertuples(index=False)) if pd.isnull(row.ANKUNFTSZEIT)
    )
    arrival_event_with_index = tuple(
        (1, i) for i, row in enumerate(measurements.itertuples(index=False)) if pd.isnull(row.ABFAHRTSZEIT)
    )
    events_with_indexes = sorted(departure_event_with_index + arrival_event_with_index, key=lambda p: p[1])
    return tuple(
        (index_event_pair[1], events_with_indexes[_idx + 1][1])
        for _idx, index_event_pair in enumerate(events_with_indexes)
        if index_event_pair[0] == 0 and _idx + 1 < len(events_with_indexes) and events_with_indexes[_idx + 1][0] == 1
    )


def _extract_measurement_pairs(
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
                [
                    dict(
                        station_name=row.HALTESTELLEN_NAME,
                        arrival_planned=row.ANKUNFTSZEIT,
                        arrival_observed=row.AN_PROGNOSE,
                        departure_planned=row.ABFAHRTSZEIT,
                        departure_observed=row.AB_PROGNOSE,
                    )
                    for row in measurements[begin : end + 1].itertuples(index=False)
                ]
            ),
        )
        recorded_trips_by_start_end[(recorded_trip.start, recorded_trip.end)].append(recorded_trip)

    return {key: tuple(value) for key, value in recorded_trips_by_start_end.items()}


def _add_measurements_to_lines(line: BusLine, measurements: pd.DataFrame) -> BusLine:
    pairs = _find_all_start_end_pairs_in_measurements(measurements)

    line_with_measurements = replace(line, recorded_trips=_extract_measurement_pairs(line, measurements, pairs))
    base_pair = max(measurements_binned.keys(), key=lambda k: len(measurements_binned[k]))
    base_m = measurements_binned[base_pair][0]

    try:
        opp_pair = max(
            (
                k
                for k in measurements_binned.keys()
                if k[0] == base_m.end and k[1] == base_m.start and k[0] != base_m.start and k[1] != base_m.end
            ),
            key=lambda k: len(measurements_binned[k]),
        )
        opp_m = measurements_binned[opp_pair][0]
    except:
        opp_m = None

    line.stops_in_direction_a = list(measurements["haltestelle"])
    line.trip_time_in_direction_a = [
        (
            datetime.strptime(d2["ankunft_soll"], "%d.%m.%Y %H:%M")
            - datetime.strptime(d1["abfahrt_soll"], "%d.%m.%Y %H:%M")
        )
        for (_, d1), (_, d2) in zip(measurements[:-1].iterrows(), measurements[1:].iterrows())
    ]

    line.trip_time_in_direction_a = [
        dt if dt.total_seconds() > 0 else timedelta(seconds=5) for dt in line.trip_time_in_direction_a
    ]
    line.stops_a = len(line.stops_in_direction_a)

    print(type(measurements.iloc[0]["ankunft_soll"]))
    print(type(line.trip_time_in_direction_a[0]))

    if opp_m:
        line.stops_in_direction_b = list(opp_m.daten["haltestelle"])
        line.trip_time_b = [
            (
                datetime.strptime(d2["ankunft_soll"], "%d.%m.%Y %H:%M")
                - datetime.strptime(d1["abfahrt_soll"], "%d.%m.%Y %H:%M")
            )
            for (_, d1), (_, d2) in zip(opp_m.daten[:-1].iterrows(), opp_m.daten[1:].iterrows())
        ]
        line.trip_time_b = [dt if dt.total_seconds() > 0 else timedelta(seconds=30) for dt in line.trip_time_b]
        line.stops_b = len(line.stops_in_direction_b)
        print(opp_m)

    print(f"Bearbeitung Linie {line.number} beendet.")
