import unittest
from copy import copy
from datetime import timedelta

from test_openbus_light.shared import cached_scenario

from unittest.mock import patch

from openbus_light.model import PlanningScenario, PointIn2D, Station, StationName, WalkableDistance, Direction


class MyTestCase(unittest.TestCase):
    _baseline_scenario: PlanningScenario

    def setUp(self) -> None:
        """
        Set up a baseline scenario.
        """
        self._baseline_scenario = cached_scenario()

    def test_consistency_ok(self) -> None:
        """
        Check the consistency of the scenario.
        """
        self.assertIsNone(self._baseline_scenario.check_consistency())

    def test_non_served_stop_fails(self) -> None:
        """
        Test that a non-served stop in this scenario raises Error.
        """
        valid_scenario = self._baseline_scenario
        scenario_with_only_one_line = valid_scenario._replace(bus_lines=(valid_scenario.bus_lines[0],))

        with self.assertRaises(ValueError):
            scenario_with_only_one_line.check_consistency()

    def test_non_served_demand_fails(self) -> None:
        """
        Test that demand for a non-served stop raises Error.
        """
        invalid_scenario = copy(self._baseline_scenario)
        invalid_scenario.demand_matrix.matrix[invalid_scenario.demand_matrix.all_origins()[0]][
            StationName("DUMMY$$")
        ] = 123

        with self.assertRaises(ValueError):
            invalid_scenario.check_consistency()

    def test_non_served_walk_fails(self) -> None:
        """
        Test that if a walkable distance starts or ends at a non-served stop, Error is raised.
        """
        valid_scenario = self._baseline_scenario
        dummy_station = Station(StationName("S"), (PointIn2D(1, 1),), tuple(), [], [])
        dummy_distances = WalkableDistance(dummy_station, dummy_station, timedelta(seconds=0))
        scenario_with_only_one_line = valid_scenario._replace(walkable_distances=(dummy_distances,))

        with self.assertRaises(ValueError):
            scenario_with_only_one_line.check_consistency()

    def test_line_with_unknown_station_fails(self) -> None:
        """Bus lines referencing stations not defined in the scenario should fail."""
        line = self._baseline_scenario.bus_lines[0]
        new_station = StationName("UNKNOWN$$")
        new_direction = Direction(
            line.direction_up.name,
            line.direction_up.station_sequence + (new_station,),
            line.direction_up.trip_times + (timedelta(seconds=60),),
            line.direction_up.recorded_trips,
        )
        modified_line = line._replace(direction_up=new_direction)
        invalid_scenario = self._baseline_scenario._replace(
            bus_lines=(modified_line,) + self._baseline_scenario.bus_lines[1:]
        )
        with self.assertRaises(ValueError):
            invalid_scenario.check_consistency()

    def test_nonexistent_origin_demand_fails(self) -> None:
        """Demand matrix containing unknown origins should fail."""
        invalid_scenario = copy(self._baseline_scenario)
        invalid_scenario.demand_matrix.matrix[StationName("ORIGIN$$")] = {invalid_scenario.stations[0].name: 42.0}
        with self.assertRaises(ValueError):
            invalid_scenario.check_consistency()

    def test_walk_distance_with_unknown_start_fails(self) -> None:
        """Walkable distances using undefined stations should fail."""
        valid_station = self._baseline_scenario.stations[0]
        dummy_station = Station(StationName("X"), (PointIn2D(0, 0),), tuple(), [], [])
        walk = WalkableDistance(dummy_station, valid_station, timedelta(seconds=0))
        invalid_scenario = self._baseline_scenario._replace(walkable_distances=(walk,))
        with self.assertRaises(ValueError):
            invalid_scenario.check_consistency()

    def test_load_scenario_invokes_check(self) -> None:
        """Ensure ``load_scenario`` calls ``PlanningScenario.check_consistency``."""
        from exercise_3 import get_paths
        from openbus_light.manipulate.scenario import load_scenario
        from test_openbus_light.shared import test_parameters

        with patch(
            "openbus_light.model.scenario.PlanningScenario.check_consistency", side_effect=RuntimeError
        ) as mocked:
            with self.assertRaises(RuntimeError):
                load_scenario(test_parameters(), get_paths())
            mocked.assert_called_once()


if __name__ == "__main__":
    unittest.main()
