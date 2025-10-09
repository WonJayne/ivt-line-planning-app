from datetime import timedelta
from functools import lru_cache

from _constants import (
    MEASUREMENTS,
    PATH_TO_DEMAND,
    PATH_TO_DEMAND_DISTRICT_POINTS,
    PATH_TO_LINE_DATA,
    PATH_TO_STATIONS,
)

from openbus_light.manipulate import ScenarioPaths, load_scenario
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
        solver="cbc",
    )


@lru_cache(maxsize=1)
def cached_scenario() -> PlanningScenario:
    return load_scenario(test_parameters(), get_paths())
def get_paths() -> ScenarioPaths:
    return ScenarioPaths(
        to_lines=PATH_TO_LINE_DATA,
        to_stations=PATH_TO_STATIONS,
        to_districts=PATH_TO_DEMAND_DISTRICT_POINTS,
        to_demand=PATH_TO_DEMAND,
        to_measurements=MEASUREMENTS,
    )


