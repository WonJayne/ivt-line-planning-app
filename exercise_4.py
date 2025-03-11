import os
import pickle
import tempfile
from collections import defaultdict
from datetime import timedelta
from typing import AbstractSet

import pandas as pd
import plotly.graph_objects as go
from _constants import RESULT_DIRECTORY
from exercise_3 import get_paths
from pandas import DataFrame
from tqdm import tqdm

from openbus_light.manipulate import load_scenario
from openbus_light.manipulate.recorded_trip import enrich_lines_with_recorded_trips
from openbus_light.model import CHF, BusLine, CHFPerHour, LineFrequency, LineNr, Meter, MeterPerSecond, RecordedTrip
from openbus_light.plan import LinePlanningParameters
from openbus_light.utils import pairwise


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


def calculate_dwell_times(recorded: RecordedTrip) -> DataFrame:
    """
    Calculate the planned and observed dwell time at each stop in a recorded trip.
    :param recorded: RecordedTrip, contains trip information
    :return: DataFrame, contains two columns, each recording the planned and observed dwell time
    """
    dwell_time_planned = (
        departure - arrival
        for arrival, departure in zip(
            recorded.record["arrival_planned"][1:-1], recorded.record["departure_planned"][1:-1]
        )
    )
    dwell_time_observed = (
        departure - arrival
        for arrival, departure in zip(
            recorded.record["arrival_observed"][1:-1], recorded.record["departure_observed"][1:-1]
        )
    )
    return pd.DataFrame({"dwell_time_planned": dwell_time_planned, "dwell_time_observed": dwell_time_observed})


def load_bus_lines_with_measurements(selected: AbstractSet[LineNr]) -> tuple[BusLine, ...]:
    """
    Load the bus lines with recorded measurements, enrich lines with recorded trips, and cache the result.
    :param selected: frozenset[LineNr], numbers of the bus lines
    :return: tuple[BusLine, ...], enriched bus lines (with recorded trips)
    """
    cache_key = "$".join(map(str, sorted(selected)))
    cache_filename = os.path.join(tempfile.gettempdir(), ".open_bus_light_cache", f"{cache_key}.pickle")
    if os.path.exists(cache_filename):
        with open(cache_filename, "rb") as f:
            print(f"loaded bus lines from cache {cache_filename}")
            return pickle.load(f)
    paths = get_paths()
    parameters = configure_parameters()
    baseline_scenario = load_scenario(parameters, paths)
    baseline_scenario.check_consistency()
    selected_lines = {line for line in baseline_scenario.bus_lines if line.number in selected}
    lines_with_recordings = enrich_lines_with_recorded_trips(paths.to_measurements, selected_lines)
    os.makedirs(os.path.dirname(cache_filename), exist_ok=True)
    with open(cache_filename, "wb") as f:
        pickle.dump(lines_with_recordings, f)
    return lines_with_recordings


def analysis_template(selected_line_numbers: AbstractSet[LineNr]) -> None:
    """
    Calculate the trip times and dwell times of the bus lines and their trips.
    :param selected_line_numbers: AbstractSet[int], bus line numbers
    """
    for line in load_bus_lines_with_measurements(selected_line_numbers):
        for direction in (line.direction_up, line.direction_down):
            trip_times_by_station_pair = defaultdict(list)
            dwell_times_by_station = defaultdict(list)
            for trip in tqdm(direction.recorded_trips, desc=f"Analyzing {line.number} {direction.name}"):
                stations = trip.record["station_name"]
                observed_trip_times = calculate_trip_times(trip)["trip_time_observed"]
                for (a, b), trip_time in zip(pairwise(stations), observed_trip_times):
                    trip_times_by_station_pair[(a, b)].append(trip_time.total_seconds())
                observed_dwell_times = calculate_dwell_times(trip)["dwell_time_observed"]
                for dwell_time, station in zip(observed_dwell_times, stations):
                    dwell_times_by_station[station].append(dwell_time.total_seconds())

            # Now, let's create the violin plot for the trip times.
            fig = go.Figure()

            # Adding a violin plot for each station pair.
            for a, b in direction.station_names_as_pairs:
                observed_dwell_times = trip_times_by_station_pair[(a, b)]
                fig.add_trace(go.Violin(y=observed_dwell_times, name=f"{a} to {b} (n={len(observed_dwell_times)})"))

            fig.update_layout(
                title=f"Observed Trip Times for line {line.name}, direction {direction.name}",
                yaxis_title="Trip Time (seconds)",
                xaxis_title="Station Pair",
            )
            dump_path = os.path.join(f"{RESULT_DIRECTORY}", "Analysis", f"{line.name}")
            os.makedirs(dump_path, exist_ok=True)
            fig.write_html(os.path.join(dump_path, f"trip_times_violin_example_{direction.name}.html"))

            # Now, let's create the violin plot for the dwell times.
            fig = go.Figure()

            # Adding a violin plot for each station.
            for station in direction.station_sequence:
                observed_dwell_times = dwell_times_by_station[station]
                fig.add_trace(go.Violin(y=observed_dwell_times, name=f"{station} (n={len(observed_dwell_times)})"))

            fig.update_layout(
                title=f"Observed Dwell Times for line {line.name}, direction {direction.name}",
                yaxis_title="Dwell Time (seconds)",
                xaxis_title="Station",
            )
            fig.write_html(os.path.join(dump_path, f"dwell_times_violin_example_{direction.name}.html"))


if __name__ == "__main__":
    analysis_template(frozenset((LineNr(1), LineNr(0), LineNr(2), LineNr(3), LineNr(4), LineNr(5), LineNr(6))))
