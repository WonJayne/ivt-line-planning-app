import warnings
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
from plots import plot_available_vs_used_capacity_for_each_direction, plot_available_vs_used_capacity_per_link

from openbus_light.manipulate import ScenarioPaths, load_scenario
from openbus_light.model import PlanningScenario
from openbus_light.plan import LinePlanningNetwork, LinePlanningParameters, LPPData, create_line_planning_problem
from openbus_light.plot.demand import PlotBackground, create_plot
from openbus_light.utils.summary import create_summary


def load_paths() -> ScenarioPaths:
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
        dwell_time_at_terminal=timedelta(seconds=5 * 60),
        vehicle_cost_per_period=0,
        vehicle_capacity=60,
        permitted_frequencies=(4, 10),
        demand_association_radius=500,
        walking_speed_between_stations=0.6,
        maximal_walking_distance=300,
        demand_scaling=0.1,
        maximal_number_of_vehicles=None,
    )


def update_frequencies(
    scenario: PlanningScenario, new_frequencies_by_line_nr: Mapping[int, tuple[int, ...]]
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


def update_capacities(scenario: PlanningScenario, new_capacities_by_line_nr: Mapping[int, int]) -> PlanningScenario:
    """
    Update the capacities of bus lines.
    :param scenario: PlanningScenario
    :param new_capacities_by_line_nr: Mapping[int, int], a mapping of lines numbers to new capacities
    :return: PlanningScenario, updated scenario
    """
    updated_lines = []
    for line in scenario.bus_lines:
        updated_lines.append(line._replace(regular_capacity=new_capacities_by_line_nr[line.number]))
    return scenario._replace(bus_lines=tuple(updated_lines))


def update_scenario(baseline_scenario: PlanningScenario) -> PlanningScenario:
    """
    Update the scenario with new permitted frequencies and capacities.
    :param baseline_scenario: PlanningScenario
    :return: PlanningScenario, updated scenario
    """
    new_frequencies_by_line_id = {0: (6,), 1: (6,), 2: (6,), 3: (6,), 4: (6,), 5: (5,), 6: (8,), 7: (6,)}
    new_capacities_by_line_id = {0: 100, 1: 100, 2: 65, 3: 65, 4: 65, 5: 65, 6: 40, 7: 40}
    updated_scenario = update_capacities(baseline_scenario, new_capacities_by_line_id)
    return update_frequencies(updated_scenario, new_frequencies_by_line_id)


def do_the_line_planning(do_plot: bool) -> None:
    """
    Do the line planning. If an optimal solution is found, plot available v.s. used capacity
        for each line, and summary of the planning. Otherwise, raise warning.
    :param do_plot: bool, indicate whether to generate plots
    :return:
    """
    paths = load_paths()
    parameters = configure_parameters()
    baseline_scenario = load_scenario(parameters, paths)

    updated_scenario = update_scenario(baseline_scenario)

    updated_scenario.check_consistency()
    planning_data = LPPData(
        parameters,
        updated_scenario,
        LinePlanningNetwork.create_from_scenario(updated_scenario, parameters.period_duration),
    )

    if do_plot:
        figure = create_plot(
            stations=planning_data.scenario.stations, plot_background=PlotBackground(WINTERTHUR_IMAGE, GPS_BOX)
        )
        figure.savefig("stations_and_caught_demand.jpg", dpi=900)

    lpp = create_line_planning_problem(planning_data)
    lpp.solve()
    result = lpp.get_result()

    if result.success:
        for line, passengers in result.solution.passengers_per_link.items():
            plot_available_vs_used_capacity_for_each_direction(line, passengers).savefig(
                f"available_vs_used_capacity_for_line_{line.number}.jpg", dpi=900
            )
        plot_available_vs_used_capacity_per_link(result.solution.passengers_per_link, sort_criteria="pax").savefig(
            "available_vs_used_capacity_sorted_by_pax.jpg", dpi=900
        )
        plot_available_vs_used_capacity_per_link(result.solution.passengers_per_link, sort_criteria="capacity").savefig(
            "available_vs_used_capacity_sorted_by_capacity.jpg", dpi=900
        )
        print(create_summary(planning_data, result))
        return
    warnings.warn(f"lpp is not optimal, adjust {planning_data.parameters}")


if __name__ == "__main__":
    do_the_line_planning(do_plot=False)
