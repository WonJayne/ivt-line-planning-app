import unittest
from copy import copy
from datetime import timedelta

from test_openbus_light.shared import cached_scenario

from openbus_light.modelling import Station, WalkableDistance


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._baseline_scenario = cached_scenario()

    def test_consistency_ok(self) -> None:
        self.assertIsNone(self._baseline_scenario.check_consistency())

    def test_non_served_stop_fails(self) -> None:
        valid_scenario = self._baseline_scenario
        scenario_with_only_one_line = valid_scenario._replace(bus_lines=(valid_scenario.bus_lines[0],))

        with self.assertRaises(ValueError):
            scenario_with_only_one_line.check_consistency()

    def test_non_served_demand_fails(self) -> None:
        invalid_scenario = copy(self._baseline_scenario)
        invalid_scenario.demand_matrix.matrix[invalid_scenario.demand_matrix.all_origins()[0]]["DUMMY$$"] = 123

        with self.assertRaises(ValueError):
            invalid_scenario.check_consistency()

    def test_non_served_walk_fails(self) -> None:
        valid_scenario = self._baseline_scenario
        dummy_station = Station("S", tuple(), tuple(), [], [])
        dummy_distances = WalkableDistance(dummy_station, dummy_station, timedelta(seconds=0))
        scenario_with_only_one_line = valid_scenario._replace(walkable_distances=(dummy_distances,))

        with self.assertRaises(ValueError):
            scenario_with_only_one_line.check_consistency()


if __name__ == "__main__":
    unittest.main()
