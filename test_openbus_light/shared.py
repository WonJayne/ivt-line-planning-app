from datetime import timedelta
from functools import lru_cache

from excercise_3 import load_paths

from openbus_light.line_planning import LinePlanningParameters
from openbus_light.manipulating import load_scenario
from openbus_light.modelling import PlanningScenario


def test_parameters() -> LinePlanningParameters:
    return LinePlanningParameters(
        egress_time_weight=0,
        period_duration=timedelta(hours=1),
        waiting_time_weight=2,
        in_vehicle_time_weight=1,
        walking_time_weight=2,
        dwell_time_at_terminal=timedelta(seconds=5 * 60),
        vehicle_cost_per_period=1000,
        vehicle_capacity=80,
        permitted_frequencies=(1, 2, 3, 4, 5, 6, 8, 10),
        demand_association_radius=500,
        walking_speed_between_stations=0.6,
        maximal_walking_distance=300,
        demand_scaling=0.1,
        maximal_number_of_vehicles=None,
    )


@lru_cache(maxsize=1)
def cached_scenario() -> PlanningScenario:
    return load_scenario(test_parameters(), load_paths())
