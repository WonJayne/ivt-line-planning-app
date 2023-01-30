from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import constants
import pandas as pd

from src.openbus_light.model import BusLine
from src.openbus_light.model.recordedtrip import RecordedTrip


def build_line_from_measurements(line: BusLine, measurements: pd.DataFrame) -> None:
    print(f"Bearbeitung der Linie {line.number}")

    starts = [(0, idx) for idx, (_, row) in enumerate(measurements.iterrows()) if pd.isnull(row["ANKUNFTSZEIT"])]
    ends = [(1, idx) for idx, (_, row) in enumerate(measurements.iterrows()) if pd.isnull(row["ABFAHRTSZEIT"])]

    idxs = starts + ends
    idxs.sort(key=lambda p: p[1])
    pairs = [
        (p[1], idxs[_idx + 1][1])
        for _idx, p in enumerate(idxs)
        if p[0] == 0 and _idx + 1 < len(idxs) and idxs[_idx + 1][0] == 1
    ]

    line.recorded_trips = [
        RecordedTrip(
            number=line.number,
            circulation_id=measurements.iloc[p[0]]["UMLAUF_ID"],
            start=measurements.iloc[p[0]]["HALTESTELLEN_NAME"],
            end=measurements.iloc[p[1]]["HALTESTELLEN_NAME"],
            stop_count=p[1] - p[0] + 1,
            data=pd.DataFrame(
                [
                    dict(
                        haltestelle=r["HALTESTELLEN_NAME"],
                        ankunft_soll=r["ANKUNFTSZEIT"],
                        ankunft_ist=r["AN_PROGNOSE"],
                        abfahrt_soll=r["ABFAHRTSZEIT"],
                        abfahrt_ist=r["AB_PROGNOSE"],
                    )
                    for _, r in measurements[p[0] : p[1] + 1].iterrows()
                ]
            ),
        )
        for p in pairs
    ]

    measurements_binned = defaultdict(list)
    for m in line.recorded_trips:
        measurements_binned[(m.start, m.end)].append(m)

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

    line.stops_in_direction_a = list(constants.SCENARIO_PATH["haltestelle"])
    line.trip_time_in_direction_a = [
        (
            datetime.strptime(d2["ankunft_soll"], "%d.%m.%Y %H:%M")
            - datetime.strptime(d1["abfahrt_soll"], "%d.%m.%Y %H:%M")
        )
        for (_, d1), (_, d2) in zip(constants.SCENARIO_PATH[:-1].iterrows(), constants.SCENARIO_PATH[1:].iterrows())
    ]
    line.trip_time_in_direction_a = [
        dt if dt.total_seconds() > 0 else timedelta(seconds=5) for dt in line.trip_time_in_direction_a
    ]
    line.stops_a = len(line.stops_in_direction_a)

    print(type(constants.SCENARIO_PATH.iloc[0]["ankunft_soll"]))
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


def load_exercise_4(nur_linie: int = None) -> tuple[list[BusLine], list[Station]]:
    empty_stops = load_served_stations()
    lines, stops = generate_network(empty_stops, export=False, load=True, load_data=True, line_only=nur_linie)
    return lines, stops
