from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from itertools import chain
from math import ceil
from types import MappingProxyType
from typing import Collection, NamedTuple

import gurobipy as grb
import numpy as np

from ..model import BusLine, PlanningScenario
from .network import Activity, LinePlanningNetwork
from .parameters import LinePlanningParameters
from .result import LPPResult, LPPSolution


class LPPData(NamedTuple):
    parameters: LinePlanningParameters
    scenario: PlanningScenario
    network: LinePlanningNetwork


class _LPPVariables(NamedTuple):
    line_configuration: grb.tupledict[tuple[int, int], grb.Var]
    passenger_flow: grb.tupledict[tuple[str, int], grb.Var]


@dataclass(frozen=True)
class LPP:
    _model: grb.Model
    _variables: _LPPVariables
    _data: LPPData

    def solve(self) -> None:
        self._model.optimize()
        if self._model.getAttr("status") == grb.GRB.INFEASIBLE:
            self._model.computeIIS()
            self._model.write(f"{self.__class__.__name__}.ilp")

    def get_result(self) -> LPPResult:
        if self._model.getAttr("status") == grb.GRB.OPTIMAL:
            return LPPResult.from_success(self._get_solution())
        return LPPResult.from_error()

    def _get_solution(self) -> LPPSolution:
        active_lines = self._extract_active_lines()
        return LPPSolution(
            weighted_travel_time=self.calculate_weighted_travel_times(),
            active_lines=active_lines,
            used_vehicles=self._calculate_number_of_used_vehicles(active_lines),
        )

    def calculate_weighted_travel_times(self) -> MappingProxyType[Activity, timedelta]:
        passenger_flows = self._get_passenger_flow_values()
        cumulated_flows: dict[Activity, float] = defaultdict(float)
        weights = calculate_activity_weights(self._data.network, self._data.parameters)
        links = self._data.network.all_links
        for i, (link, weight) in enumerate(zip(links, weights)):
            cumulated_flows[link.activity] += sum(passenger_flows.select("*", i)) * weight
        return MappingProxyType({key: timedelta(seconds=time) for key, time in cumulated_flows.items()})

    def _extract_active_lines(self) -> tuple[BusLine, ...]:
        line_lookup = {line.number: line for line in self._data.scenario.bus_lines}
        selected_line_configurations = self._get_line_activation_values()
        return tuple(
            line_lookup[line_nr]._replace(permitted_frequencies=(frequency,))
            for (line_nr, frequency), is_selected in selected_line_configurations.items()
            if is_selected > 0.5
        )

    def _calculate_number_of_used_vehicles(self, active_lines: Collection[BusLine]) -> int:
        parameters = self._data.parameters
        return sum(
            _calculate_number_of_required_vehicles(
                line.permitted_frequencies[0],
                _calculate_minimal_circulation_time(line, parameters.dwell_time_at_terminal),
                parameters.period_duration,
            )
            for line in active_lines
        )

    def _get_line_activation_values(self) -> grb.tupledict[tuple[int, int], float]:
        return self._model.getAttr("X", self._variables.line_configuration)  # noqa

    def _get_passenger_flow_values(self) -> grb.tupledict[tuple[str, int], float]:
        return self._model.getAttr("X", self._variables.passenger_flow)  # noqa


def create_line_planning_problem(lpp_data: LPPData) -> LPP:
    _add_constraints(lpp_data, lpp_model := grb.Model(), lpp_variables := _add_variables(lpp_model, lpp_data))
    return LPP(lpp_model, lpp_variables, lpp_data)


def _add_constraints(lpp_data: LPPData, lpp_model: grb.Model, lpp_variables: _LPPVariables) -> None:
    _add_flow_conservation_constraints(lpp_model, lpp_variables, lpp_data)
    _add_capacity_constraints(lpp_model, lpp_variables, lpp_data)
    _add_at_most_one_config_per_line_allowed(lpp_model, lpp_variables, lpp_data)
    if lpp_data.parameters.maximal_number_of_vehicles is not None:
        _restrict_the_number_of_vehicles(lpp_model, lpp_variables, lpp_data)


def _add_variables(lpp_model: grb.Model, lpp_data: LPPData) -> _LPPVariables:
    passenger_flow_variables = _add_passenger_flow_variables(lpp_data, lpp_model)
    line_configuration_variables = _add_line_configuration_variables(lpp_data, lpp_model)
    return _LPPVariables(line_configuration_variables, passenger_flow_variables)


def _add_line_configuration_variables(data: LPPData, model: grb.Model) -> grb.tupledict[tuple[int, int], grb.Var]:
    line_configuration_variables: grb.tupledict[tuple[int, int], grb.Var] = grb.tupledict()
    parameters = data.parameters
    for line in data.scenario.bus_lines:
        minimal_circulation_time = _calculate_minimal_circulation_time(line, parameters.dwell_time_at_terminal)
        for frequency in line.permitted_frequencies:
            required_circulations = _calculate_number_of_required_vehicles(
                frequency, minimal_circulation_time, parameters.period_duration
            )
            line_configuration_variables[line.number, frequency] = model.addVar(
                lb=0,
                ub=1,
                obj=required_circulations * parameters.vehicle_cost_per_period,
                vtype=grb.GRB.BINARY,
                name=f"line:{line.number}@{frequency}",
            )
    return line_configuration_variables


def _calculate_number_of_required_vehicles(
    frequency: int, minimal_circulation_time: timedelta, period_duration: timedelta
) -> int:
    return ceil(minimal_circulation_time.total_seconds() / period_duration.total_seconds() * frequency)


def _calculate_minimal_circulation_time(line: BusLine, dwell_time_at_terminal: timedelta) -> timedelta:
    in_seconds = dwell_time_at_terminal.total_seconds() * 2 + sum(
        dt.total_seconds() for dt in chain.from_iterable((line.direction_a.trip_times, line.direction_b.trip_times))
    )
    return timedelta(seconds=in_seconds)


def _add_passenger_flow_variables(
    line_planning_data: LPPData, model: grb.Model
) -> grb.tupledict[tuple[str, int], grb.Var]:
    passenger_flow_variables: grb.tupledict[tuple[str, int], grb.Var] = grb.tupledict()
    all_origins = line_planning_data.scenario.demand_matrix.all_origins()
    link_weights = calculate_activity_weights(line_planning_data.network, line_planning_data.parameters)
    for origin in all_origins:
        for link_index, weight in enumerate(link_weights):
            passenger_flow_variables[origin, link_index] = model.addVar(
                lb=0, ub=float("inf"), obj=weight, vtype=grb.GRB.CONTINUOUS, name=f"{origin}-{link_index}"
            )
    return passenger_flow_variables


def calculate_activity_weights(
    line_planning_network: LinePlanningNetwork, parameters: LinePlanningParameters
) -> tuple[float, ...]:
    weights = []
    for link in line_planning_network.all_links:
        total_seconds = link.duration.total_seconds()
        if link.activity == Activity.ACCESS_LINE:
            weights.append(total_seconds * parameters.waiting_time_weight)
            continue
        if link.activity == Activity.IN_VEHICLE:
            weights.append(total_seconds * parameters.in_vehicle_time_weight)
            continue
        if link.activity == Activity.WALKING:
            weights.append(total_seconds * parameters.walking_time_weight)
            continue
        if link.activity == Activity.EGRESS_LINE:
            weights.append(total_seconds * parameters.egress_time_weight)
            continue
        raise NotImplementedError(f"{link.activity} is not associated with a weighting factory")
    return tuple(weights)


def _add_capacity_constraints(model: grb.Model, variables: _LPPVariables, data: LPPData) -> None:
    line_lookup = {line.number: line for line in data.scenario.bus_lines}
    for i, link in enumerate(data.network.all_links):
        if link.activity == Activity.IN_VEHICLE and link.line_id is not None:
            line = line_lookup[link.line_id]
            all_flows_over_this_link = grb.quicksum(variables.passenger_flow.select("*", i))
            all_capacities_for_this_link = grb.quicksum(
                variables.line_configuration[line.number, frequency] * line.regular_capacity * frequency
                for frequency in line.permitted_frequencies
            )
            model.addConstr(all_flows_over_this_link <= all_capacities_for_this_link, name=f"cap{line.number}@{i}")
            continue

        if link.activity == Activity.ACCESS_LINE and link.line_id is not None:
            line = line_lookup[link.line_id]
            frequency = link.frequency
            all_flows_over_this_link = grb.quicksum(variables.passenger_flow.select("*", i))
            capacity_for_this_link = (
                variables.line_configuration[line.number, frequency] * line.regular_capacity * frequency
            )
            model.addConstr(all_flows_over_this_link <= capacity_for_this_link, name=f"cap{line.number}@{i}")
            continue


def _add_flow_conservation_constraints(model: grb.Model, variables: _LPPVariables, data: LPPData) -> None:
    lpp_network = data.network
    lpp_graph = data.network.graph
    node_incidences = [
        (lpp_graph.incident(i, mode="in"), lpp_graph.incident(i, mode="out")) for i in lpp_graph.vs.indices
    ]
    flow_balance_at_nodes = np.zeros((lpp_graph.vcount(), 1))
    for origin in data.scenario.demand_matrix.all_origins():
        flow_balance_at_nodes *= 0
        for station_name, outflow in data.scenario.demand_matrix.matrix[origin].items():
            node_index = lpp_graph.vs.find(name=lpp_network.egress_node_name_from_station_name(station_name)).index
            flow_balance_at_nodes[node_index] = round(-outflow, 2)
        origin_index = lpp_graph.vs.find(name=lpp_network.access_node_name_from_station_name(origin)).index
        flow_balance_at_nodes[origin_index] = -sum(flow_balance_at_nodes)
        for flow_balance, (incoming_indices, outgoing_indices) in zip(flow_balance_at_nodes, node_incidences):
            model.addConstr(
                grb.quicksum(variables.passenger_flow[origin, i] for i in incoming_indices)
                - grb.quicksum(variables.passenger_flow[origin, i] for i in outgoing_indices)
                == -flow_balance,
                name="flow_balance",
            )


def _add_at_most_one_config_per_line_allowed(model: grb.Model, variables: _LPPVariables, data: LPPData) -> None:
    for line in data.scenario.bus_lines:
        model.addConstr(grb.quicksum(variables.line_configuration.select(line.number, "*")) <= 1)


def _restrict_the_number_of_vehicles(model: grb.Model, variables: _LPPVariables, data: LPPData) -> None:
    line_configuration_variables = variables.line_configuration
    parameters = data.parameters
    required_vehicles_when_selected = []
    for line in data.scenario.bus_lines:
        minimal_circulation_time = _calculate_minimal_circulation_time(line, parameters.dwell_time_at_terminal)
        for frequency in line.permitted_frequencies:
            required_circulations = _calculate_number_of_required_vehicles(
                frequency, minimal_circulation_time, parameters.period_duration
            )
            required_vehicles_when_selected.append(
                line_configuration_variables[line.number, frequency] * required_circulations
            )
    model.addConstr(grb.quicksum(required_vehicles_when_selected) <= parameters.maximal_number_of_vehicles)
