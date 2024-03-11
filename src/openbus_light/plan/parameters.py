from datetime import timedelta
from typing import NamedTuple

from ..model import LineFrequency
from ..model.type import CHF, CHFPerHour, Meter, MeterPerSecond


class LinePlanningParameters(NamedTuple):
    egress_time_cost: CHFPerHour
    waiting_time_cost: CHFPerHour
    in_vehicle_time_cost: CHFPerHour
    walking_time_cost: CHFPerHour
    dwell_time_at_terminal: timedelta
    period_duration: timedelta
    vehicle_cost_per_period: CHF
    permitted_frequencies: tuple[LineFrequency, ...]
    demand_scaling: float
    demand_association_radius: Meter
    walking_speed_between_stations: MeterPerSecond
    maximal_walking_distance: Meter
    maximal_number_of_vehicles: None | int
