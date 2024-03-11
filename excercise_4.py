import os
import pickle
import tempfile
from datetime import timedelta

import pandas as pd
from excercise_3 import get_paths
from pandas import DataFrame

from openbus_light.manipulate import load_scenario
from openbus_light.manipulate.recorded_trip import enrich_lines_with_recorded_trips
from openbus_light.model import CHF, BusLine, CHFPerHour, LineFrequency, LineNr, Meter, MeterPerSecond, RecordedTrip
from openbus_light.plan import LinePlanningParameters


def configure_parameters() -> LinePlanningParameters:
    return LinePlanningParameters(
        period_duration=timedelta(hours=1),
        egress_time_cost=CHFPerHour(20),
        waiting_time_cost=CHFPerHour(40),
        in_vehicle_time_cost=CHFPerHour(20),
        walking_time_cost=CHFPerHour(30),
        dwell_time_at_terminal=timedelta(seconds=300),
        vehicle_cost_per_period=CHF(500),
        permitted_frequencies=(LineFrequency(4), LineFrequency(6), LineFrequency(8)),
        demand_association_radius=Meter(150),
        walking_speed_between_stations=MeterPerSecond(0.6),
        maximal_walking_distance=Meter(500),
        demand_scaling=0.1,
        maximal_number_of_vehicles=None,
    )


def calculate_trip_times(recorded_trip: RecordedTrip) -> pd.DataFrame:
    """
    Calculate the planned and observed trip times between consecutive stops in a recorded trip.
    :param recorded_trip: RecordedTrip, contains trip information
    :return: pd.DataFrame, contains two columns, each recording the planned and observed trip time
    """
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
    """
    Calculate the planned and observed dwell time at each stop in a recorded trip.
    :param recorded_trip: RecordedTrip, contains trip information
    :return: DataFrame, contains two columns, each recording the planned and observed dwell time
    """
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


def load_bus_lines_with_measurements(selected_line_numbers: frozenset[LineNr]) -> tuple[BusLine, ...]:
    """
    Load the bus lines with recorded measurements, enrich lines with recorded trips, and cache the result.
    :param selected_line_numbers: frozenset[int], numbers of the bus lines
    :return: tuple[BusLine, ...], enriched bus lines
    """
    cache_key = "$".join(map(str, sorted(selected_line_numbers)))
    cache_filename = os.path.join(tempfile.gettempdir(), ".open_bus_light_cache", f"{cache_key}.pickle")
    if os.path.exists(cache_filename):
        with open(cache_filename, "rb") as f:
            print(f"loaded bus lines from cache {cache_filename}")
            return pickle.load(f)
    paths = get_paths()
    parameters = configure_parameters()
    baseline_scenario = load_scenario(parameters, paths)
    baseline_scenario.check_consistency()
    selected_lines = {line for line in baseline_scenario.bus_lines if line.number in selected_line_numbers}
    lines_with_recordings = enrich_lines_with_recorded_trips(paths.to_measurements, selected_lines)
    os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
    with open(cache_filename, "wb") as f:
        pickle.dump(lines_with_recordings, f)
    return lines_with_recordings


def analysis(selected_line_numbers: frozenset[LineNr]) -> None:
    """
    Calculate the trip times and dwell times of the bus lines and their trips.
    :param selected_line_numbers: frozenset[int], bus line numbers
    """
    lines_with_recordings = load_bus_lines_with_measurements(selected_line_numbers)
    for line in lines_with_recordings:
        for direction in (line.direction_a, line.direction_b):
            for record in direction.recorded_trips:
                trip_times = calculate_trip_times(record)
                dwell_times = calculate_dwell_times(record)
                raise ValueError("Not implemented yet")


if __name__ == "__main__":
    analysis(frozenset(LineNr(i) for i in range((5))))
