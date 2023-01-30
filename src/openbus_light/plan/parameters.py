from datetime import timedelta
from typing import NamedTuple, Optional


class LinePlanningParameters(NamedTuple):
    egress_time_weight: float
    waiting_time_weight: float
    in_vehicle_time_weight: float
    walking_time_weight: float
    dwell_time_at_terminal: timedelta
    period_duration: timedelta
    vehicle_cost_per_period: int
    vehicle_capacity: int
    permitted_frequencies: tuple[int, ...]
    demand_scaling: float
    demand_association_radius: int
    walking_speed_between_stations: float
    maximal_walking_distance: int
    maximal_number_of_vehicles: Optional[int]
