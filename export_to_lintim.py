"""Export the baseline planning scenario to the LinTim data format."""

from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

from _constants import (
    MEASUREMENTS,
    PATH_TO_DEMAND,
    PATH_TO_DEMAND_DISTRICT_POINTS,
    PATH_TO_LINE_DATA,
    PATH_TO_STATIONS,
)

from openbus_light.export import (
    export_planning_scenario_to_lintim,
    export_planning_scenario_to_lintim_with_walk_lines,
)
from openbus_light.manipulate import ScenarioPaths, load_scenario
from openbus_light.model import CHF, CHFPerHour, LineFrequency, Meter, MeterPerSecond
from openbus_light.plan import LinePlanningParameters


def get_paths() -> ScenarioPaths:
    """Return the baseline data paths required for the scenario export."""

    return ScenarioPaths(
        to_lines=PATH_TO_LINE_DATA,
        to_stations=PATH_TO_STATIONS,
        to_districts=PATH_TO_DEMAND_DISTRICT_POINTS,
        to_demand=PATH_TO_DEMAND,
        to_measurements=MEASUREMENTS,
    )


def _default_parameters() -> LinePlanningParameters:
    """Create a set of parameters that matches the default exercise configuration."""

    return LinePlanningParameters(
        period_duration=timedelta(hours=1),
        egress_time_cost=CHFPerHour(20),
        waiting_time_cost=CHFPerHour(40),
        in_vehicle_time_cost=CHFPerHour(20),
        walking_time_cost=CHFPerHour(30),
        dwell_time_at_terminal=timedelta(minutes=5),
        vehicle_cost_per_period=CHF(500),
        permitted_frequencies=(
            LineFrequency(1),
            LineFrequency(2),
            LineFrequency(4),
            LineFrequency(6),
            LineFrequency(8),
            LineFrequency(10),
        ),
        demand_association_radius=Meter(450),
        walking_speed_between_stations=MeterPerSecond(0.6),
        maximal_walking_distance=Meter(300),
        demand_scaling=1.0,
        maximal_number_of_vehicles=None,
        solver="cbc",
    )


def main() -> None:
    """CLI entry point that writes LinTim CSV files for the baseline scenario."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="Directory that will receive the LinTim CSV files.")
    parser.add_argument(
        "--walks-as-lines",
        action="store_true",
        help="Represent walking connections as synthetic lines instead of footpaths.csv.",
    )
    args = parser.parse_args()

    scenario = load_scenario(_default_parameters(), get_paths())

    if args.walks_as_lines:
        export_planning_scenario_to_lintim_with_walk_lines(scenario, args.output_dir)
    else:
        export_planning_scenario_to_lintim(scenario, args.output_dir)


if __name__ == "__main__":
    main()
