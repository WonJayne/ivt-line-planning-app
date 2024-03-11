from datetime import timedelta
from typing import TypedDict

from openbus_light.model.type import CHF, Hour, LineFrequency, LineNr, Meter, MeterPerSecond, Second, VehicleCapacity

from .problem import LPPData
from .result import LPPResult


# Ignore duplication as it is on purpose (we want to have the same structure for the summary, but as a TypedDict)
# pylint: disable=duplicate-code
class ParameterDict(TypedDict):
    egress_time_cost: float
    waiting_time_cost: float
    in_vehicle_time_cost: float
    walking_time_cost: float
    dwell_time_at_terminal: Second
    period_duration: Second
    vehicle_cost_per_period: CHF
    permitted_frequencies: tuple[LineFrequency, ...]
    demand_scaling: float
    demand_association_radius: Meter
    walking_speed_between_stations: MeterPerSecond
    maximal_walking_distance: Meter
    maximal_number_of_vehicles: None | int


class LineDict(TypedDict):
    number: LineNr
    frequency: LineFrequency
    capacity: VehicleCapacity


class Summary(TypedDict):
    used_parameters: ParameterDict
    total_passengers_transported: float
    weighted_time_per_activity: dict[str, Hour]
    number_of_demand_relations: int
    active_lines: list[LineDict]
    used_vehicles: int


def create_summary(planning_data: LPPData, result: LPPResult) -> Summary:
    demand_matrix = planning_data.scenario.demand_matrix
    total_demand = sum(demand_matrix.starting_from(origins) for origins in demand_matrix.all_origins())
    number_of_demand_relations = sum(
        sum(demand > 0 for demand in demand_matrix.matrix[origins].values()) for origins in demand_matrix.all_origins()
    )

    solution = result.solution

    return {
        "used_parameters": (
            {
                key: (value if not isinstance(value, timedelta) else value.total_seconds())  # type: ignore
                for key, value in sorted(planning_data.parameters._asdict().items())  # type: ignore
            }
        ),
        "total_passengers_transported": total_demand,
        "number_of_demand_relations": number_of_demand_relations,
        "weighted_cost_per_activity": {
            activity.name: cost for activity, cost in solution.generalised_travel_time.items()
        },
        "active_lines": [
            {"number": line.number, "frequency": line.permitted_frequencies[0], "capacity": line.capacity}
            for line in sorted(solution.active_lines, key=lambda x: x.number)
        ],
        "used_vehicles": round(solution.used_vehicles),
    }
