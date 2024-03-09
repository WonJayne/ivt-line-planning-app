import argparse
import os
import warnings
from collections import defaultdict
from datetime import timedelta
from typing import Mapping

from constants import (
    GPS_BOX,
    MEASUREMENTS,
    PATH_TO_DEMAND,
    PATH_TO_DEMAND_DISTRICT_POINTS,
    PATH_TO_LINE_DATA,
    PATH_TO_STATIONS,
    WINTERTHUR_IMAGE,
)

from openbus_light.manipulate import ScenarioPaths, load_scenario
from openbus_light.model import CHF, Capacity, LineFrequency, LineNr, Meter, MeterPerSecond, PlanningScenario
from openbus_light.plan import LinePlanningNetwork, LinePlanningParameters, LPPData, create_line_planning_problem
from openbus_light.plan.summary import create_summary
from openbus_light.plot import (
    PlotBackground,
    create_colormap,
    create_station_and_demand_plot,
    create_station_and_line_plot,
    plot_network_in_swiss_coordinate_grid,
    plot_network_usage_in_swiss_coordinates,
)
from openbus_light.plot.line import plot_lines_in_swiss_coordinates
from openbus_light.plot.line_usage import plot_available_vs_used_capacity_per_link, plot_usage_for_each_direction


def get_paths() -> ScenarioPaths:
    return ScenarioPaths(
        to_lines=PATH_TO_LINE_DATA,
        to_stations=PATH_TO_STATIONS,
        to_districts=PATH_TO_DEMAND_DISTRICT_POINTS,
        to_demand=PATH_TO_DEMAND,
        to_measurements=MEASUREMENTS,
    )


def configure_parameters() -> LinePlanningParameters:
    return LinePlanningParameters(
        egress_time_weight=0,
        period_duration=timedelta(hours=1),
        waiting_time_weight=10,
        in_vehicle_time_weight=10,
        walking_time_weight=10,
        dwell_time_at_terminal=timedelta(seconds=300),
        vehicle_cost_per_period=CHF(1000),
        permitted_frequencies=(LineFrequency(4), LineFrequency(6), LineFrequency(8)),
        demand_association_radius=Meter(500),
        walking_speed_between_stations=MeterPerSecond(0.6),
        maximal_walking_distance=Meter(500),
        demand_scaling=0.1,
        maximal_number_of_vehicles=None,
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
    scenario: PlanningScenario, new_capacities_by_line_nr: Mapping[LineNr, Capacity]
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


def do_the_line_planning(use_current_frequencies: bool) -> None:
    """
    Do the line planning. If an optimal solution is found, plot available v.s. used capacity
        for each line, and summary of the planning. Otherwise, raise warning.
    :return: None
    """
    paths = get_paths()
    parameters = configure_parameters()
    baseline_scenario = load_scenario(parameters, paths)

    updated_scenario = update_scenario(baseline_scenario, parameters, use_current_frequencies)

    updated_scenario.check_consistency()
    planning_data = LPPData(
        parameters,
        updated_scenario,
        LinePlanningNetwork.create_from_scenario(updated_scenario, parameters.period_duration),
    )

    plot_path = "plots"
    os.makedirs(plot_path, exist_ok=True)
    figure = create_station_and_demand_plot(
        stations=planning_data.scenario.stations, plot_background=PlotBackground(WINTERTHUR_IMAGE, GPS_BOX)
    )
    figure.savefig(os.path.join(plot_path, "stations_and_caugt_demand.jpg"), dpi=900)
    figure = plot_network_in_swiss_coordinate_grid(
        planning_data.network, create_colormap([line.number for line in planning_data.scenario.bus_lines])
    )
    figure.write_html(os.path.join(plot_path, "network_in_swiss_coordinates.html"))

    lpp = create_line_planning_problem(planning_data)
    print("Solving the line planning problem...")
    lpp.solve()
    print("Solving the line planning problem...done")
    result = lpp.get_result()

    if result.success:
        os.makedirs(plot_path, exist_ok=True)
        for line, passengers in result.solution.passengers_per_link.items():
            plot_usage_for_each_direction(line, passengers).write_html(
                os.path.join("plots", f"available_vs_used_capacity_for_line_{line.number}.html")
            )
        create_station_and_line_plot(
            stations=planning_data.scenario.stations,
            lines=planning_data.scenario.bus_lines,
            plot_background=PlotBackground(WINTERTHUR_IMAGE, GPS_BOX),
        ).savefig(os.path.join(plot_path, "network.jpg"), dpi=900)
        plot_lines_in_swiss_coordinates(
            stations=planning_data.scenario.stations, lines=planning_data.scenario.bus_lines
        ).write_html(os.path.join(plot_path, "lines_in_swiss_coordinates.html"))
        plot_network_usage_in_swiss_coordinates(
            planning_data.network, result.solution, scale_with_capacity=True
        ).write_html(os.path.join(plot_path, "scaled_network_with_passengers_per_link_in_swiss_coordinates.html"))
        plot_network_usage_in_swiss_coordinates(
            planning_data.network, result.solution, scale_with_capacity=False
        ).write_html(os.path.join(plot_path, "network_with_passengers_per_link_in_swiss_coordinates.html"))
        print(create_summary(planning_data, result))
        return
    warnings.warn(f"lpp is not optimal, adjust {planning_data.parameters}", UserWarning)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--use_current_frequencies", action="store_true", default=False)
    do_the_line_planning(parser.parse_args().use_current_frequencies)
