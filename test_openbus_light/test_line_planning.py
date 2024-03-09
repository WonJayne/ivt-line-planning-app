import unittest
from copy import copy
from datetime import timedelta
from itertools import product
from math import ceil

from test_openbus_light.shared import cached_scenario, test_parameters

from openbus_light.model import (
    CHF,
    BusLine,
    Capacity,
    DemandMatrix,
    Direction,
    LineFrequency,
    LineName,
    LineNr,
    PlanningScenario,
    PointIn2D,
    Station,
    StationName,
    WalkableDistance,
)
from openbus_light.plan import (
    LinePlanningNetwork,
    LinePlanningParameters,
    LPPData,
    LPPResult,
    create_line_planning_problem,
)
from openbus_light.plan.network import Activity


def _create_non_walking_scenario() -> PlanningScenario:
    """
    Generate a simple non-walking scenario with fictional stations, bus lines and demand.
    :return: PlanningScenario
    """
    stations = (
        Station(StationName("A"), (PointIn2D(1, 1),), (LineNr(1), LineNr(2)), [], []),
        Station(StationName("B"), (PointIn2D(1, 1),), (LineNr(1),), [], []),
        Station(StationName("C"), (PointIn2D(1, 1),), (LineNr(1),), [], []),
        Station(StationName("D"), (PointIn2D(1, 1),), (LineNr(1), LineNr(2)), [], []),
    )
    bus_lines = (
        BusLine(
            LineNr(1),
            LineName("1"),
            Direction(
                "a", ("A", "B", "C", "D"), (timedelta(seconds=300), timedelta(seconds=300), timedelta(seconds=300))
            ),
            Direction(
                "b", ("D", "C", "B", "A"), (timedelta(seconds=300), timedelta(seconds=300), timedelta(seconds=300))
            ),
            capacity=Capacity(100),
            permitted_frequencies=(LineFrequency(1), LineFrequency(2)),
        ),
        BusLine(
            LineNr(2),
            LineName("2"),
            Direction("a", ("A", "D"), (timedelta(seconds=300),)),
            Direction("b", ("D", "A"), (timedelta(seconds=300),)),
            capacity=Capacity(100),
            permitted_frequencies=(LineFrequency(1), LineFrequency(2)),
        ),
    )
    demand = DemandMatrix(
        {
            StationName("A"): {StationName("B"): 100, StationName("C"): 50, StationName("D"): 100},
            StationName("D"): {StationName("A"): 100, StationName("B"): 50, StationName("C"): 100},
        }
    )
    return PlanningScenario(demand, bus_lines, tuple(), stations)


def _create_only_walking_scenario() -> PlanningScenario:
    """
    Generate a planning scenario where walking is the only available mode.
    :return: PlanningScenario
    """
    stations = (
        Station("A", (PointIn2D(1, 1),), (1,), [], []),
        Station("B", (PointIn2D(1, 1),), (1,), [], []),
        Station("C", (PointIn2D(1, 1),), (1,), [], []),
        Station("D", (PointIn2D(1, 1),), (1,), [], []),
    )
    bus_lines = (
        BusLine(
            0,
            "1",
            Direction(
                "a", ("A", "B", "C", "D"), (timedelta(seconds=300), timedelta(seconds=300), timedelta(seconds=300))
            ),
            Direction("b", ("D", "A"), (timedelta(seconds=300),)),
            capacity=100,
            permitted_frequencies=(1, 2),
        ),
    )
    demand = DemandMatrix({"A": {"D": 100}, "D": {"A": 100}})
    walking_distances = tuple(
        WalkableDistance(first_station, second_station, timedelta(seconds=300))
        for first_station, second_station in product(stations, stations)
        if first_station != second_station
    )
    return PlanningScenario(demand, bus_lines, walking_distances, stations)


def _solve_this_lpp(parameters: LinePlanningParameters, scenario: PlanningScenario) -> LPPResult:
    """
    Create line planning problem based on LPP Data, and solve the problem.
    :param parameters: LinePlanningParameters
    :param scenario: PlanningScenario
    :return: LPPResult, result of the LP Problem
    """
    planning_data = LPPData(
        parameters, scenario, LinePlanningNetwork.create_from_scenario(scenario, parameters.period_duration)
    )
    first_lpp = create_line_planning_problem(planning_data)
    first_lpp.solve()
    return first_lpp.get_result()


def _calculate_number_of_vehicles(scenario_with_frequency_1: PlanningScenario) -> int:
    """
    Calculate the number of vehicles needed to serve a planning scenario with frequency of 1.
    :param scenario_with_frequency_1: PlanningScenario, where frequency is 1
    :return: int, number of vehicles needed to serve in the scenario
    """
    return sum(
        ceil(
            (
                sum(dt.total_seconds() for dt in line.direction_a.trip_times)
                + sum(dt.total_seconds() for dt in line.direction_b.trip_times)
                + 2 * test_parameters().dwell_time_at_terminal.total_seconds()
            )
            / test_parameters().period_duration.total_seconds()
            * line.permitted_frequencies[0]
        )
        for line in scenario_with_frequency_1.bus_lines
    )


def _calculate_total_passenger_count(non_walking_scenario: PlanningScenario) -> float:
    """
    Calculate the total number of passengers (i.e. demand values) in a non-walking scenario.
    :param non_walking_scenario: PlanningScenario
    :return: float, the total passenger demand
    """
    return sum(sum(from_here.values()) for from_here in non_walking_scenario.demand_matrix.matrix.values())


class LinePlanningTestCase(unittest.TestCase):
    def test_with_walking(self) -> None:
        """
        Compare the results of two different scenarios either favoring vehicles or walking.
        Check in line-favored solution, whether the weighted travel time for walking is 0, and vice versa.
        """
        parameters_favoring_vehicle = test_parameters()._replace(
            waiting_time_weight=0, in_vehicle_time_weight=1 / 300, walking_time_weight=1, vehicle_cost_per_period=CHF(0)
        )
        parameters_favoring_walking = test_parameters()._replace(
            waiting_time_weight=0, in_vehicle_time_weight=1, walking_time_weight=1 / 300, vehicle_cost_per_period=CHF(0)
        )
        scenario_with_walking = _create_only_walking_scenario()
        result_using_line = _solve_this_lpp(parameters_favoring_vehicle, scenario_with_walking)
        result_using_walking = _solve_this_lpp(parameters_favoring_walking, scenario_with_walking)

        self.assertEqual(result_using_line.solution.weighted_travel_time[Activity.WALKING].total_seconds(), 0)
        self.assertEqual(
            result_using_line.solution.weighted_travel_time[Activity.IN_VEHICLE].total_seconds(),
            _calculate_total_passenger_count(scenario_with_walking) * 2,
        )

        self.assertEqual(result_using_walking.solution.weighted_travel_time[Activity.ACCESS_LINE].total_seconds(), 0)

        self.assertEqual(
            result_using_walking.solution.weighted_travel_time[Activity.WALKING].total_seconds(),
            _calculate_total_passenger_count(scenario_with_walking),
        )

    def test_with_walking_and_no_vehicles(self) -> None:
        """
        Test scenarios where there are no vehicles or vehicles with zero capacity. Assert that under
            these scenarios, optimization should not succeed.
        """
        scenario = _create_non_walking_scenario()
        zero_capacity_scenario = scenario._replace(
            bus_lines=tuple(line._replace(capacity=Capacity(0)) for line in scenario.bus_lines)
        )
        parameters_with_no_vehicles = test_parameters()._replace(maximal_number_of_vehicles=0)

        zero_capacity_result = _solve_this_lpp(test_parameters(), zero_capacity_scenario)
        zero_vehicles_result = _solve_this_lpp(parameters_with_no_vehicles, scenario)

        self.assertFalse(zero_capacity_result.success)
        self.assertFalse(zero_vehicles_result.success)

    def test_zero_frequency_case(self) -> None:
        """
        Test scenario where the permitted frequency is 0, and assert that under such scenario,
            ´´ZeroDivisionError´´ is raised.
        """
        non_walking_scenario = _create_non_walking_scenario()
        zero_frequency_scenario = non_walking_scenario._replace(
            bus_lines=tuple(
                line._replace(permitted_frequencies=(LineFrequency(0),)) for line in non_walking_scenario.bus_lines
            )
        )

        with self.assertRaises(ZeroDivisionError):
            _solve_this_lpp(test_parameters(), zero_frequency_scenario)

    def test_with_simple_plan(self) -> None:
        """
        Test the parameters favoring walking in a non-walking scenario. Assert that KeyError is
            raised when attempting to access the weighted travel time for walking.
        """
        parameters_favoring_walking = test_parameters()._replace(
            waiting_time_weight=1 / 900,
            in_vehicle_time_weight=1 / 300,
            walking_time_weight=0,
            vehicle_cost_per_period=CHF(0),
            egress_time_weight=1 / 60,
        )
        non_walking_scenario = _create_non_walking_scenario()
        only_walking_weighted_result = _solve_this_lpp(parameters_favoring_walking, non_walking_scenario)

        with self.assertRaises(KeyError):
            self.assertEqual(only_walking_weighted_result.solution.weighted_travel_time[Activity.WALKING], 0)
        self.assertEqual(
            only_walking_weighted_result.solution.weighted_travel_time[Activity.EGRESS_LINE].total_seconds(),
            _calculate_total_passenger_count(non_walking_scenario),
        )
        self.assertEqual(
            only_walking_weighted_result.solution.weighted_travel_time[Activity.IN_VEHICLE].total_seconds(),
            _calculate_total_passenger_count(non_walking_scenario) + 100,
        )
        self.assertEqual(
            only_walking_weighted_result.solution.weighted_travel_time[Activity.ACCESS_LINE].total_seconds(),
            _calculate_total_passenger_count(non_walking_scenario),
        )


class LinePlanningIntegrationTestCase(unittest.TestCase):
    _baseline_scenario: PlanningScenario

    def setUp(self) -> None:
        """
        Remove the demand matrix for origins starting from the 11th position onward.
        """
        self._baseline_scenario = copy(cached_scenario())
        for origin in sorted(self._baseline_scenario.demand_matrix.all_origins())[10:]:
            self._baseline_scenario.demand_matrix.matrix.pop(origin)

    def test_frequency_dependence(self) -> None:
        """
        Test the changing of frequency has an impact on waiting time.
        """
        scenario_with_frequency_2 = self._baseline_scenario._replace(
            bus_lines=tuple(
                line._replace(permitted_frequencies=(LineFrequency(20),)) for line in self._baseline_scenario.bus_lines
            )
        )

        scenario_with_frequency_1 = self._baseline_scenario._replace(
            bus_lines=tuple(
                line._replace(permitted_frequencies=(LineFrequency(10),)) for line in self._baseline_scenario.bus_lines
            )
        )

        parameters_only_transfer_weight = test_parameters()._replace(
            waiting_time_weight=1,
            in_vehicle_time_weight=0,
            walking_time_weight=0,
            vehicle_cost_per_period=CHF(0),
            egress_time_weight=0,
        )

        result_with_2 = _solve_this_lpp(parameters_only_transfer_weight, scenario_with_frequency_2)
        result_with_1 = _solve_this_lpp(parameters_only_transfer_weight, scenario_with_frequency_1)

        self.assertTrue(result_with_2.success)
        self.assertTrue(result_with_1.success)
        self.assertNotEqual(
            result_with_2.solution.weighted_travel_time[Activity.ACCESS_LINE],
            result_with_1.solution.weighted_travel_time[Activity.ACCESS_LINE],
        )
        self.assertEqual(result_with_1.solution.weighted_travel_time[Activity.IN_VEHICLE].total_seconds(), 0)
        self.assertEqual(result_with_2.solution.weighted_travel_time[Activity.IN_VEHICLE].total_seconds(), 0)

        self.assertAlmostEqual(
            result_with_2.solution.weighted_travel_time[Activity.ACCESS_LINE].total_seconds() * 2,
            result_with_1.solution.weighted_travel_time[Activity.ACCESS_LINE].total_seconds(),
            4,
        )

        self.assertNotEqual(result_with_2.solution.used_vehicles, result_with_1.solution.used_vehicles)
        self.assertEqual(result_with_1.solution.used_vehicles, _calculate_number_of_vehicles(scenario_with_frequency_1))
        self.assertEqual(result_with_2.solution.used_vehicles, _calculate_number_of_vehicles(scenario_with_frequency_2))

    def test_frequency_independence(self) -> None:
        """
        Test that the changing of frequency does not have an impact on in-vehicle time and walking time.
        """
        scenario_with_frequency_2 = self._baseline_scenario._replace(
            bus_lines=tuple(
                line._replace(permitted_frequencies=(LineFrequency(20),)) for line in self._baseline_scenario.bus_lines
            )
        )

        scenario_with_frequency_1 = self._baseline_scenario._replace(
            bus_lines=tuple(
                line._replace(permitted_frequencies=(LineFrequency(10),)) for line in self._baseline_scenario.bus_lines
            )
        )

        parameters_only_transfer_weight = test_parameters()._replace(
            waiting_time_weight=0, in_vehicle_time_weight=1, walking_time_weight=1, vehicle_cost_per_period=CHF(0)
        )

        result_with_2 = _solve_this_lpp(parameters_only_transfer_weight, scenario_with_frequency_2)
        result_with_1 = _solve_this_lpp(parameters_only_transfer_weight, scenario_with_frequency_1)

        self.assertTrue(result_with_2.success)
        self.assertTrue(result_with_1.success)
        self.assertEqual(
            result_with_2.solution.weighted_travel_time[Activity.ACCESS_LINE],
            result_with_1.solution.weighted_travel_time[Activity.ACCESS_LINE],
        )
        self.assertEqual(result_with_1.solution.weighted_travel_time[Activity.ACCESS_LINE].total_seconds(), 0)
        self.assertEqual(result_with_2.solution.weighted_travel_time[Activity.ACCESS_LINE].total_seconds(), 0)

        self.assertAlmostEqual(
            result_with_2.solution.weighted_travel_time[Activity.WALKING].total_seconds(),
            result_with_1.solution.weighted_travel_time[Activity.WALKING].total_seconds(),
            100,
        )
        self.assertAlmostEqual(
            result_with_2.solution.weighted_travel_time[Activity.IN_VEHICLE].total_seconds(),
            result_with_1.solution.weighted_travel_time[Activity.IN_VEHICLE].total_seconds(),
            100,
        )


if __name__ == "__main__":
    unittest.main()
