import pandas as pd
from excercise_3 import configure_parameters, load_paths
from pandas import DataFrame

from openbus_light.manipulate import load_scenario
from openbus_light.manipulate.recorded_trip import enrich_lines_with_recorded_trips
from openbus_light.model import RecordedTrip


def calculate_trip_times(recorded_trip: RecordedTrip) -> pd.DataFrame:
    trip_time_planned = (
        arrival - departure
        for departure, arrival in zip(
            recorded_trip.record["departure_planned"][:-1], recorded_trip.record["arrival_planned"][1:]
        )
    )
    trip_time_observed = (
        arrival - departure
        for departure, arrival in zip(
            recorded_trip.record["departure_observed"][:-1], recorded_trip.record["arrival_observed"][1:]
        )
    )
    return pd.DataFrame({"trip_time_planned": trip_time_planned, "trip_time_observed": trip_time_observed})


def calculate_dwell_times(recorded_trip: RecordedTrip) -> DataFrame:
    dwell_time_planned = (
        departure - arrival
        for arrival, departure in zip(
            recorded_trip.record["arrival_planned"][1:-1], recorded_trip.record["departure_planned"][1:-1]
        )
    )
    dwell_time_observed = (
        departure - arrival
        for arrival, departure in zip(
            recorded_trip.record["arrival_observed"][1:-1], recorded_trip.record["departure_observed"][1:-1]
        )
    )
    return pd.DataFrame({"dwell_time_planned": dwell_time_planned, "dwell_time_observed": dwell_time_observed})


def main() -> None:
    paths = load_paths()
    parameters = configure_parameters()
    baseline_scenario = load_scenario(parameters, paths)
    baseline_scenario.check_consistency()
    lines_with_recordings = enrich_lines_with_recorded_trips(paths.to_measurements, baseline_scenario.bus_lines)

    for line in lines_with_recordings:
        for direction in (line.direction_a, line.direction_b):
            for record in direction.recorded_trips:
                trip_times = calculate_trip_times(record)
                dwell_times = calculate_dwell_times(record)


if __name__ == "__main__":
    main()
