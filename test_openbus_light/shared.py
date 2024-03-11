from datetime import timedelta
from functools import lru_cache

from exercise_3 import get_paths

from openbus_light.manipulate import load_scenario
from openbus_light.model import LineFrequency, MeterPerSecond, PlanningScenario
from openbus_light.plan import LinePlanningParameters


def test_parameters() -> LinePlanningParameters:
    return LinePlanningParameters(
        egress_time_cost=0,
        period_duration=timedelta(hours=1),
        waiting_time_cost=2,
        in_vehicle_time_cost=1,
        walking_time_cost=2,
        dwell_time_at_terminal=timedelta(seconds=5 * 60),
        vehicle_cost_per_period=1000,
        permitted_frequencies=(
            LineFrequency(1),
            LineFrequency(2),
            LineFrequency(3),
            LineFrequency(4),
            LineFrequency(5),
            LineFrequency(6),
        ),
        demand_association_radius=500,
        walking_speed_between_stations=MeterPerSecond(0.6),
        maximal_walking_distance=300,
        demand_scaling=0.1,
        maximal_number_of_vehicles=None,
    )


@lru_cache(maxsize=1)
def cached_scenario() -> PlanningScenario:
    return load_scenario(test_parameters(), get_paths())
