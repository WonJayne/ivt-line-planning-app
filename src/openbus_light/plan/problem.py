from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from itertools import chain
from math import ceil
from types import MappingProxyType
from typing import Collection, NamedTuple

import numpy as np
import pulp as pl
from pulp import PULP_CBC_CMD, LpVariable
from tqdm import tqdm

from ..model import BusLine, Direction, LineFrequency, LineNr, PlanningScenario, StationName
from ..utils import pairwise
from .network import Activity, LinePlanningNetwork
from .parameters import LinePlanningParameters
from .result import LPPResult, LPPSolution, PassengersPerLink


class LPPData(NamedTuple):
    parameters: LinePlanningParameters
    scenario: PlanningScenario
    network: LinePlanningNetwork


class _LPPVariables(NamedTuple):
    line_configuration: dict[tuple[LineNr, LineFrequency], LpVariable]
    passenger_flow: dict[tuple[StationName, int], LpVariable]


@dataclass(frozen=True)
class LPP:
    _model: pl.LpProblem
    _variables: _LPPVariables
    _data: LPPData

    def solve(self) -> None:
        """
        Solve the mixed integer linear program.
        If it is infeasible, the model is written to a file.
        """
        self._model.solve(PULP_CBC_CMD(msg=True))
        if self._model.status == pl.LpStatusInfeasible:
            self._model.writeLP(f"{self.__class__.__name__}.lp")

    def get_result(self) -> LPPResult:
        """
        Get the result of the mixed integer linear program.
        If no optimal solution is available, error or failure is indicated.
        :return: LPPResult, the overall result or outcome of the problem
        """
        if self._model.status == pl.LpStatusOptimal:
            return LPPResult.from_success(self._get_solution())
        return LPPResult.from_error()

    def _get_solution(self) -> LPPSolution:
        """
        Get the solution of the mixed integer linear program.
        Extract the active bus lines in the scenario, and calculate the values
            of decision variables that optimize the result.
        :return: LPPSolution, the values of decision variables
        """
        active_lines = self._extract_active_lines()
        return LPPSolution(
            weighted_travel_time=self._calculate_weighted_travel_times(),
            active_lines=active_lines,
            used_vehicles=self._calculate_number_of_used_vehicles(active_lines),
            passengers_per_link=self._extract_passengers_per_link(active_lines),
        )

    def _calculate_weighted_travel_times(self) -> MappingProxyType[Activity, timedelta]:
        """
        Calculate the weighted travel time of different activities (i.e. access
            time, in-vehicle time, egress time etc.).
        :return: MappingProxyType[Activity, timedelta], an immutable mapping of
            activities and their travel times
        """
        cumulated_flows: dict[Activity, float] = defaultdict(float)
        weights = calculate_activity_weights(self._data.network, self._data.parameters)
        links = self._data.network.all_links
        accumulated_passenger_flows = self._accumulate_flows_per_edge_index(self._get_passenger_flow_values())
        for edge_index, (link, weight) in enumerate(zip(links, weights)):
            cumulated_flows[link.activity] += sum(accumulated_passenger_flows[edge_index]) * weight
        return MappingProxyType({key: timedelta(seconds=time) for key, time in cumulated_flows.items()})

    @staticmethod
    def _accumulate_flows_per_edge_index(
        passenger_flows: dict[tuple[StationName, int], float]
    ) -> defaultdict[int, list[float]]:
        """
        Accumulate the passenger flows by edge.
        :param passenger_flows: dict[tuple[str, int], float], a dictionary of
            edge and flows on that edge
        :return: default-dict[int, list[float]], a default-dict of edge index
            and the list of passenger flows on the edge
        """
        accumulated_passenger_flows = defaultdict(list)
        for (_, edge_index), flow in passenger_flows.items():
            accumulated_passenger_flows[edge_index].append(flow)
        return accumulated_passenger_flows

    def _extract_active_lines(self) -> tuple[BusLine, ...]:
        """
        Extract the active lines, which is determined by the value of ``is_selected``
            in ``selected_line_configurations``. If a line is selected, replace the
            value of attribute ``permitted_frequencies`` with a tuple.
        :return: tuple[BusLine, ...], a tuple of modified ``BusLine`` objects for lines
            that are extracted
        """
        line_lookup: dict[int, BusLine] = {line.number: line for line in self._data.scenario.bus_lines}
        selected_line_configurations = self._get_line_activation_values()
        return tuple(
            line_lookup[line_nr]._replace(permitted_frequencies=(frequency,))
            for (line_nr, frequency), is_selected in selected_line_configurations.items()
            if is_selected > 0.5
        )

    def _calculate_number_of_used_vehicles(self, active_lines: Collection[BusLine]) -> int:
        """
        Calculate the number of used vehicles for all active lines in the solution.
        :param active_lines: Collection[BusLine], the active lines in the solution
        :return: int, the number of used vehicles
        """
        parameters = self._data.parameters
        return sum(
            _calculate_number_of_required_vehicles(
                line.permitted_frequencies[0],
                _calculate_minimal_circulation_time(line, parameters.dwell_time_at_terminal),
                parameters.period_duration,
            )
            for line in active_lines
        )

    def _extract_passengers_per_link(
        self, active_lines: Collection[BusLine]
    ) -> MappingProxyType[BusLine, MappingProxyType[Direction, tuple[PassengersPerLink, ...]]]:
        """
        Calculate the passenger count per link for each direction of each bus line.
        :return: MappingProxyType[BusLine, MappingProxyType[Direction, tuple[PassengersPerLink, ...]]],
            a read-only nested dict which indexes the passenger count by bus lines and two directions.
        """
        create_line_node_name = self._data.network.create_line_node_name
        flows = self._get_passenger_flow_values()
        passengers_per_line: dict[BusLine, dict[Direction, tuple[PassengersPerLink, ...]]] = {}
        accumulated_passenger_flows = self._accumulate_flows_per_edge_index(flows)
        for line in active_lines:
            passengers_per_line[line] = {}
            for direction in (line.direction_a, line.direction_b):
                node_names = tuple(
                    create_line_node_name(station_name, line, direction) for station_name in direction.station_sequence
                )
                count = (
                    sum(accumulated_passenger_flows[self._get_network_link_index(first, second)])
                    for first, second in pairwise(node_names)
                )
                passengers_per_line[line][direction] = tuple(
                    PassengersPerLink(station_a, station_b, node_a, node_b, pax)
                    for (station_a, station_b), (node_a, node_b), pax in zip(
                        direction.station_names_as_pairs, pairwise(node_names), count
                    )
                )
        return MappingProxyType({key: MappingProxyType(value) for key, value in passengers_per_line.items()})

    def _get_network_link_index(self, source: str, target: str) -> int:
        """
        Get the index of a link in the network from the vertices of the link.
        :param source: the ID or name of the start vertex
        :param target: the ID or name of the end vertex
        :return: int, the link index
        """
        return self._data.network.get_link_index(source=source, target=target)

    def _get_line_activation_values(self) -> dict[tuple[LineNr, LineFrequency], float]:
        """
        Get the activation value of lines. If value > 0.5, it's an active line, otherwise not active.
        :return: dict[tuple[LineNr, LineFrequency], float], a dict of the line numbers and the values that determine
            if a line is active
        """
        return {key: var.varValue for key, var in self._variables.line_configuration.items()}  # type ignore

    def _get_passenger_flow_values(self) -> dict[tuple[StationName, int], float]:
        """
        Get passenger flows on each edge.
        :return: dict[tuple[StationName, int], float], a dict of edge index and passenger flows on it
        """
        return {key: var.varValue for key, var in self._variables.passenger_flow.items()}


def create_line_planning_problem(lpp_data: LPPData) -> LPP:
    """
    Create the line planning problem, i.e. the mixed integer linear program.
    :param lpp_data: LPPData, the data for the line planning problem
    :return: LPP (Line Planning Problem), the mixed integer linear program
    """
    lpp_model = pl.LpProblem()
    lpp_variables = _add_variables(lpp_data)
    _add_constraints(lpp_data, lpp_model, lpp_variables)
    _add_objective(lpp_data, lpp_model, lpp_variables)
    return LPP(lpp_model, lpp_variables, lpp_data)


def _add_constraints(lpp_data: LPPData, lpp_model: pl.LpProblem, lpp_variables: _LPPVariables) -> None:
    """
    Add all constraints to the mixed integer linear program.
    :param lpp_data: LPPData, the data for the line planning problem
    :param lpp_model: LpProblem (pulp) the model to which the constraints are added
    :param lpp_variables: _LPPVariables, the variables of the line planning problem
    """
    _add_flow_conservation_constraints(lpp_model, lpp_variables, lpp_data)
    _add_capacity_constraints(lpp_model, lpp_variables, lpp_data)
    _add_at_most_one_config_per_line_allowed(lpp_model, lpp_variables, lpp_data)
    if lpp_data.parameters.maximal_number_of_vehicles is not None:
        _restrict_the_number_of_vehicles(lpp_model, lpp_variables, lpp_data)


def _add_variables(lpp_data: LPPData) -> _LPPVariables:
    """
    Add line configuration variables and passenger flow variables.
    :param lpp_data: LPPData, data of the line planning problem
    :return: _LPPVariables, a class that that encapsulates line configuration variables and
        passenger flow variables
    """
    passenger_flow_variables = _add_passenger_flow_variables(lpp_data)
    line_configuration_variables = _add_line_configuration_variables(lpp_data)
    return _LPPVariables(line_configuration_variables, passenger_flow_variables)


def _add_line_configuration_variables(data: LPPData) -> dict[tuple[LineNr, LineFrequency], LpVariable]:
    """
    Add binary configuration variables.
    :param data: LPPData, data of the line planning problem
    :return: dict[tuple[int, int], LpVariable], a dict whose key is line number and frequency, while
        value is a binary variable
    """
    line_configuration_variables: dict[tuple[LineNr, LineFrequency], LpVariable] = {}
    for line in data.scenario.bus_lines:
        for frequency in line.permitted_frequencies:
            line_configuration_variables[line.number, frequency] = LpVariable(
                cat=pl.const.LpBinary, name=f"line:{line.number}-{frequency}"
            )
    return line_configuration_variables


def _calculate_number_of_required_vehicles(
    frequency: int, minimal_circulation_time: timedelta, period_duration: timedelta
) -> int:
    """
    Calculate the number of vehicles required under the given condition.
    :param frequency: int, the number of services (i.e. circulations) within the given period.
    :param minimal_circulation_time: timedelta, the minimum time required for a single circulation of a vehicle
    :param period_duration: timedelta, the entire period of the calculation.
    :return: int, the number of vehicles that meets the frequency requirement and time constraints
    """
    return ceil(minimal_circulation_time.total_seconds() / period_duration.total_seconds() * frequency)


def _calculate_minimal_circulation_time(line: BusLine, dwell_time_at_terminal: timedelta) -> timedelta:
    """
    Calculate the minimal circulation time of a bus line
    :param line: BusLine, a class of bus line
    :param dwell_time_at_terminal: timedelta, time that the bus spends at each of the two terminals
    :return: timedelta, circulation time, which is the sum of travel time and dwell time
    """
    in_seconds = dwell_time_at_terminal.total_seconds() * 2 + sum(
        dt.total_seconds() for dt in chain.from_iterable((line.direction_a.trip_times, line.direction_b.trip_times))
    )
    return timedelta(seconds=in_seconds)


def _add_passenger_flow_variables(line_planning_data: LPPData) -> dict[tuple[StationName, int], LpVariable]:
    """
    Add passenger flow variables.
    :param line_planning_data: LPPData, data of the line planning problem
    :return: dict[tuple[str, str], LpVariable], a dict whose key is origin and link index, while value
        is non-negative continuous variable
    """
    passenger_flow_variables: dict[tuple[StationName, int], LpVariable] = {}
    all_origins = line_planning_data.scenario.demand_matrix.all_origins()
    link_weights = calculate_activity_weights(line_planning_data.network, line_planning_data.parameters)
    for origin in all_origins:
        for link_index in range(len(link_weights)):
            passenger_flow_variables[origin, link_index] = LpVariable(
                lowBound=0, upBound=None, e=None, cat=pl.const.LpContinuous, name=f"{origin}-{link_index}"
            )
    return passenger_flow_variables


def _add_objective(data: LPPData, model: pl.LpProblem, variables: _LPPVariables) -> None:
    """
    Add an objective to the line planning problem.
    :param data: LPPData, data of the LP problem
    :param model: pl.LpProblem, the LP model
    :param variables: _LPPVariables, a class that that encapsulates line configuration variables and
        passenger flow variables
    :return: objective function of the LP problem, which is the combination of weighted sum of
        passenger flows and the cost of operating vehicles
    """
    weights = calculate_activity_weights(data.network, data.parameters)
    passenger_part_in_hours = pl.lpSum(
        weights[i] * variable / 3600 for (_, i), variable in variables.passenger_flow.items()
    )
    vehicle_part = 0
    for (line_index, line_freq), variable in tqdm(variables.line_configuration.items(), desc="adding objective"):
        circulation_time = _calculate_minimal_circulation_time(
            data.scenario.bus_lines[line_index - 1], data.parameters.dwell_time_at_terminal
        )
        vehicle_part += (
            _calculate_number_of_required_vehicles(line_freq, circulation_time, data.parameters.period_duration)
            * data.parameters.vehicle_cost_per_period
            * variable
        )
    model.objective = passenger_part_in_hours + vehicle_part


def calculate_activity_weights(
    line_planning_network: LinePlanningNetwork, parameters: LinePlanningParameters
) -> tuple[float, ...]:
    """
    Calculate activity weights by multiplying time spent on the activity and the parameter.
    :param line_planning_network: LinePlanningNetwork, the network of the line planning problem
    :param parameters: LinePlanningParameters, a class which contains parameters for the lpp
    :return: tuple[float, ...], a tuple which contains the weights of different activities
    """
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


def _add_capacity_constraints(model: pl.LpProblem, variables: _LPPVariables, data: LPPData) -> None:
    """
    Add capacity constraints to the LP problem, passenger flows should not exceed the constraints.
    :param model: pl.LpProblem, the LP model
    :param variables: _LPPVariables, a class that that encapsulates line configuration variables and
        passenger flow variables
    :param data: LPPData, data of the LP problem
    """
    line_lookup = {line.number: line for line in data.scenario.bus_lines}
    pax_lookup = defaultdict(list)
    for (_, edge_index), variable in variables.passenger_flow.items():
        pax_lookup[edge_index].append(variable)
    for i, link in tqdm(tuple(enumerate(data.network.all_links)), desc="adding capacity constraints"):
        if link.activity == Activity.IN_VEHICLE and link.line_nr is not None:
            line = line_lookup[link.line_nr]
            all_flows_over_this_link = pl.lpSum(pax_lookup[i])
            all_capacities_for_this_link = pl.lpSum(
                variables.line_configuration[line.number, frequency] * line.capacity * frequency
                for frequency in line.permitted_frequencies
            )
            model.addConstraint(all_flows_over_this_link <= all_capacities_for_this_link, name=f"cap{line.number}@{i}")
            continue

        if link.activity == Activity.ACCESS_LINE and link.line_nr is not None:
            line = line_lookup[link.line_nr]
            frequency = link.frequency
            if frequency is None:
                raise ValueError(f"f{link} does not have a frequency {link.frequency}")
            all_flows_over_this_link = pl.lpSum(pax_lookup[i])
            capacity_for_this_link = variables.line_configuration[line.number, frequency] * line.capacity * frequency
            model.addConstraint(all_flows_over_this_link <= capacity_for_this_link, name=f"cap{line.number}@{i}")
            continue


def _add_flow_conservation_constraints(model: pl.LpProblem, variables: _LPPVariables, data: LPPData) -> None:
    """
    Add flow conservation constraints, which ensure that for each node, the inflow equals the outflow.
    :param model: pl.LpProblem, the LP model
    :param variables: _LPPVariables, a class that that encapsulates line configuration variables and
        passenger flow variables
    :param data: LPPData, data of the LP problem
    """
    lpp_network = data.network
    lpp_graph = data.network.graph
    node_incidences = [
        (lpp_graph.incident(i, mode="in"), lpp_graph.incident(i, mode="out")) for i in lpp_graph.vs.indices
    ]
    flow_balance_at_nodes = np.zeros((lpp_graph.vcount(), 1))
    for origin in tqdm(data.scenario.demand_matrix.all_origins(), desc="adding flow conservation constraints"):
        flow_balance_at_nodes *= 0
        for station_name, outflow in data.scenario.demand_matrix.matrix[origin].items():
            node_index = lpp_graph.vs.find(name=lpp_network.egress_node_name_from_station_name(station_name)).index
            flow_balance_at_nodes[node_index] = round(-outflow, 2)
        origin_index = lpp_graph.vs.find(name=lpp_network.access_node_name_from_station_name(origin)).index
        flow_balance_at_nodes[origin_index] = -sum(flow_balance_at_nodes)
        for flow_balance, (incoming_indices, outgoing_indices) in zip(flow_balance_at_nodes, node_incidences):
            model.addConstraint(
                pl.lpSum(variables.passenger_flow[origin, i] for i in incoming_indices)
                - pl.lpSum(variables.passenger_flow[origin, i] for i in outgoing_indices)
                == -flow_balance
            )


def _add_at_most_one_config_per_line_allowed(model: pl.LpProblem, variables: _LPPVariables, data: LPPData) -> None:
    """
    Add configuration constraint, which ensures no more than one configuration is added to each line.
    :param model: pl.LpProblem, the LP model
    :param variables: _LPPVariables, a class that that encapsulates line configuration variables and
        passenger flow variables
    :param data: LPPData, data of the LP problem
    """
    configurations_by_line = defaultdict(list)
    for (line_id, _), variable in variables.line_configuration.items():
        configurations_by_line[line_id].append(variable)
    for line in data.scenario.bus_lines:
        model.addConstraint(pl.lpSum(configurations_by_line[line.number]) <= 1)


def _restrict_the_number_of_vehicles(model: pl.LpProblem, variables: _LPPVariables, data: LPPData) -> None:
    """
    Add constraints of the number of vehicles, ensuring that it does not exceed the maximal number.
    :param model: pl.LpProblem, the LP model
    :param variables: _LPPVariables, a class that that encapsulates line configuration variables and
        passenger flow variables
    :param data: LPPData, data of the LP problem
    """
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
    model.addConstraint(pl.lpSum(required_vehicles_when_selected) <= parameters.maximal_number_of_vehicles)
