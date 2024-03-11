import argparse
import json
import os
import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Mapping

from _constants import (
    GPS_BOX,
    MEASUREMENTS,
    PATH_TO_DEMAND,
    PATH_TO_DEMAND_DISTRICT_POINTS,
    PATH_TO_LINE_DATA,
    PATH_TO_STATIONS,
    RESULT_DIRNAME,
    WINTERTHUR_IMAGE,
)

from openbus_light.manipulate import ScenarioPaths, load_scenario
from openbus_light.model import (
    CHF,
    CHFPerHour,
    LineFrequency,
    LineNr,
    Meter,
    MeterPerSecond,
    PlanningScenario,
    Second,
    VehicleCapacity,
)
from openbus_light.plan import (
    LinePlanningNetwork,
    LinePlanningParameters,
    LPPData,
    create_line_planning_problem,
    create_summary,
)
from openbus_light.plot import (
    PlotBackground,
    create_colormap,
    create_station_and_demand_plot,
    create_station_and_line_plot,
    plot_lines_in_swiss_coordinates,
    plot_network_in_swiss_coordinate_grid,
    plot_network_usage_in_swiss_coordinates,
    plot_usage_for_each_direction,
)
from openbus_light.plot.demand import create_od_plot


def get_paths() -> ScenarioPaths:
    return ScenarioPaths(
        to_lines=PATH_TO_LINE_DATA,
        to_stations=PATH_TO_STATIONS,
        to_districts=PATH_TO_DEMAND_DISTRICT_POINTS,
        to_demand=PATH_TO_DEMAND,
        to_measurements=MEASUREMENTS,
    )


def update_frequencies(
    scenario: PlanningScenario, new_frequencies_by_line_nr: Mapping[LineNr, tuple[LineFrequency, ...]]
) -> PlanningScenario:
    """
    Update the permitted frequencies of bus lines.
    :param scenario: PlanningScenario
    :param new_frequencies_by_line_nr: Mapping[int, tuple[int, ...]], a mapping of line
        numbers to new permitted frequencies
    :return: PlanningScenario, updated scenario
    """
    updated_lines = []
    for line in scenario.bus_lines:
        updated_lines.append(line._replace(permitted_frequencies=new_frequencies_by_line_nr[line.number]))
    return scenario._replace(bus_lines=tuple(updated_lines))


def update_capacities(
    scenario: PlanningScenario, new_capacities_by_line_nr: Mapping[LineNr, VehicleCapacity]
) -> PlanningScenario:
    """
    Update the capacities of bus lines.
    :param scenario: PlanningScenario
    :param new_capacities_by_line_nr: Mapping[int, int], a mapping of lines numbers to new capacities
    :return: PlanningScenario, updated scenario
    """
    updated_lines = []
    for line in scenario.bus_lines:
        updated_lines.append(line._replace(capacity=new_capacities_by_line_nr[line.number]))
    return scenario._replace(bus_lines=tuple(updated_lines))


def update_scenario(
    baseline_scenario: PlanningScenario, parameters: LinePlanningParameters, use_current_frequencies: bool
) -> PlanningScenario:
    """
    Update the scenario with new permitted frequencies and capacities.
    :param baseline_scenario: PlanningScenario
    :param parameters: LinePlanningParameters
    :param use_current_frequencies: bool, whether to use the current frequencies of the lines
    :return: PlanningScenario, updated scenario
    """

    if use_current_frequencies:
        new_frequencies_by_line_id = {
            LineNr(0): (LineFrequency(6),),
            LineNr(1): (LineFrequency(6),),
            LineNr(2): (LineFrequency(6),),
            LineNr(3): (LineFrequency(6),),
            LineNr(4): (LineFrequency(6),),
            LineNr(5): (LineFrequency(5),),
            LineNr(6): (LineFrequency(8),),
            LineNr(7): (LineFrequency(6),),
        }
    else:
        new_frequencies_by_line_id = defaultdict(lambda: parameters.permitted_frequencies)
    capacities_by_line_id = {0: 100, 1: 100, 2: 65, 3: 65, 4: 65, 5: 65, 6: 40, 7: 40}
    updated_scenario = update_capacities(baseline_scenario, capacities_by_line_id)
    return update_frequencies(updated_scenario, new_frequencies_by_line_id)


def do_the_line_planning(experiment_id: str, use_current_frequencies: bool, parameters: LinePlanningParameters) -> None:
    """
    Do the line planning. If an optimal solution is found, plot available v.s. used capacity
        for each line, and summary of the planning. Otherwise, raise warning.
    :return: None
    """
    paths = get_paths()
    baseline_scenario = load_scenario(parameters, paths)

    updated_scenario = update_scenario(baseline_scenario, parameters, use_current_frequencies)

    updated_scenario.check_consistency()
    planning_data = LPPData(
        parameters,
        updated_scenario,
        LinePlanningNetwork.create_from_scenario(updated_scenario, parameters.period_duration),
    )

    os.makedirs((dump_path := os.path.join(RESULT_DIRNAME, experiment_id)), exist_ok=True)
    figure = create_station_and_demand_plot(
        stations=planning_data.scenario.stations, plot_background=PlotBackground(WINTERTHUR_IMAGE, GPS_BOX)
    )
    figure.savefig(os.path.join(dump_path, "stations_and_caught_demand.jpg"), dpi=900)
    figure = create_od_plot(planning_data.scenario.demand_matrix, planning_data.scenario.stations)
    figure.write_html(os.path.join(dump_path, "origin_destination_matrix.html"))
    figure = plot_network_in_swiss_coordinate_grid(
        planning_data.network, create_colormap([line.number for line in planning_data.scenario.bus_lines])
    )
    figure.write_html(os.path.join(dump_path, "network_in_swiss_coordinates.html"))

    lpp = create_line_planning_problem(planning_data)
    print("Solving the line planning problem...")
    lpp.solve()
    result = lpp.get_result()
    print(f"Solving the line planning problem...done, {result.success=}")

    if not result.success:
        raise UserWarning("No optimal solution found, please check the parameters.")

    os.makedirs(dump_path, exist_ok=True)
    for line, passengers in result.solution.passengers_per_link.items():
        plot_usage_for_each_direction(line, passengers).write_html(
            os.path.join(dump_path, f"available_vs_used_capacity_for_line_{line.number}.html")
        )
    create_station_and_line_plot(
        stations=planning_data.scenario.stations,
        lines=planning_data.scenario.bus_lines,
        plot_background=PlotBackground(WINTERTHUR_IMAGE, GPS_BOX),
    ).savefig(os.path.join(dump_path, "network.jpg"), dpi=900)
    plot_lines_in_swiss_coordinates(
        stations=planning_data.scenario.stations, lines=planning_data.scenario.bus_lines
    ).write_html(os.path.join(dump_path, "lines_in_swiss_coordinates.html"))
    plot_network_usage_in_swiss_coordinates(
        planning_data.network, result.solution, scale_with_capacity=True
    ).write_html(os.path.join(dump_path, "scaled_network_with_passengers_per_link_in_swiss_coordinates.html"))
    plot_network_usage_in_swiss_coordinates(
        planning_data.network, result.solution, scale_with_capacity=False
    ).write_html(os.path.join(dump_path, "network_with_passengers_per_link_in_swiss_coordinates.html"))
    with open(os.path.join(dump_path, f"{experiment_id}.Summary.json"), "w") as f:
        json.dump(create_summary(planning_data, result), f, indent=4)


def _convert_args_to_parameters(args: argparse.Namespace) -> LinePlanningParameters:
    """
     Convert the arguments to LinePlanningParameters.
    :param args: argparse.Namespace
    :return: LinePlanningParameters
    """
    return LinePlanningParameters(
        period_duration=timedelta(seconds=args.period_duration),
        egress_time_cost=CHFPerHour(args.egress_time_cost),
        waiting_time_cost=CHFPerHour(args.waiting_time_cost),
        in_vehicle_time_cost=CHFPerHour(args.in_vehicle_time_cost),
        walking_time_cost=CHFPerHour(args.walking_time_cost),
        dwell_time_at_terminal=timedelta(seconds=args.dwell_time_at_terminal),
        vehicle_cost_per_period=CHF(args.vehicle_cost_per_period),
        permitted_frequencies=tuple(LineFrequency(frequency) for frequency in args.permitted_frequencies),
        demand_association_radius=Meter(args.demand_association_radius),
        walking_speed_between_stations=MeterPerSecond(args.walking_speed_between_stations),
        maximal_walking_distance=Meter(args.maximal_walking_distance),
        demand_scaling=args.demand_scaling,
        maximal_number_of_vehicles=args.maximal_number_of_vehicles,
    )


def main() -> None:
    """
    Main function. Parse the arguments and do the line planning. All the results will be saved in the folder "plots".
    :return: None
    """

    parser = argparse.ArgumentParser()

    parser.add_argument("--period_duration", type=int, default=3600, help=f"Duration of the period, in {Second}.")
    parser.add_argument("--egress_time_cost", type=float, default=20, help=f"Weight of egress time, in {CHFPerHour}.")
    parser.add_argument("--waiting_time_cost", type=float, default=40, help=f"Weight of waiting time, in {CHFPerHour}.")
    parser.add_argument(
        "--in_vehicle_time_cost", type=float, default=20, help=f"Weight of in vehicle time, in {CHFPerHour}."
    )
    parser.add_argument("--walking_time_cost", type=float, default=30, help=f"Weight of walking time, in {CHFPerHour}.")
    parser.add_argument("--dwell_time_at_terminal", type=int, default=300, help=f"Dwell time at terminal, in {Second}.")
    parser.add_argument(
        "--vehicle_cost_per_period", type=int, default=500, help=f"Cost of a vehicle per period, in {CHF}."
    )
    parser.add_argument(
        "--permitted_frequencies",
        type=int,
        nargs="+",
        default=[4, 6, 8],
        help="In 1/Period, Permitted frequencies for the lines in the line planning problem.",
    )
    parser.add_argument(
        "--demand_association_radius",
        type=int,
        default=300,
        help="In meter. Radius of the demand association from a demand point to a station, distance is as crow flies.",
    )
    parser.add_argument(
        "--walking_speed_between_stations",
        type=float,
        default=0.6,
        help="In meter per second. Speed of walking between stations, distance is as crow flies.",
    )
    parser.add_argument(
        "--maximal_walking_distance",
        type=int,
        default=300,
        help="In meter. Maximal walking distance between a demand point and a station, distance is as crow flies.",
    )
    parser.add_argument(
        "--demand_scaling",
        type=float,
        default=0.1,
        help="Scaling factor for the demand. The demand is multiplied by this factor. "
        "0.0 means no demand, 1.0 means the entire daily demand.",
    )
    parser.add_argument(
        "--maximal_number_of_vehicles",
        type=int,
        default=None,
        help="Maximal number of vehicles to be used in the line planning problem, None means no limit.",
    )

    parser.add_argument(
        "--experiment_id",
        type=str,
        default=None,
        help="ID of the experiment, if not provided, a new ID will be generated.",
    )
    parser.add_argument(
        "--use_current_frequencies",
        action="store_true",
        default=False,
        help="Use the current frequencies of the lines in the line planning problem.",
    )
    args = parser.parse_args()

    experiment_id = args.experiment_id if args.experiment_id is not None else str(uuid.uuid4())
    do_the_line_planning(experiment_id, args.use_current_frequencies, _convert_args_to_parameters(args))


if __name__ == "__main__":
    main()
