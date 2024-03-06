from datetime import timedelta
from typing import NamedTuple

from ..model import Capacity, LineFrequency
from ..model.type import CHF, Meter, MeterPerSecond


class LinePlanningParameters(NamedTuple):
    egress_time_weight: float
    waiting_time_weight: float
    in_vehicle_time_weight: float
    walking_time_weight: float
    dwell_time_at_terminal: timedelta
    period_duration: timedelta
    vehicle_cost_per_period: CHF
    vehicle_capacity: Capacity
    permitted_frequencies: tuple[LineFrequency, ...]
    demand_scaling: float
    demand_association_radius: Meter
    walking_speed_between_stations: MeterPerSecond
    maximal_walking_distance: Meter
    maximal_number_of_vehicles: None | int
