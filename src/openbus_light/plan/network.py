from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum, unique
from typing import Collection, NamedTuple, Optional

import igraph

from ..model import BusLine, Direction, PlanningScenario, WalkableDistance
from ..utils import pairwise


@unique
class Activity(IntEnum):
    IN_VEHICLE = 1
    WALKING = 2
    ACCESS_LINE = 3
    EGRESS_LINE = 4
    TRANSFER = 5


class LPNLink(NamedTuple):
    activity: Activity
    duration: timedelta
    line_id: Optional[int]
    frequency: Optional[int]


class LPNNode(NamedTuple):
    name: str
    line_id: Optional[int]
    direction: Optional[str]


@dataclass(frozen=True)
class LinePlanningNetwork:
    graph: igraph.Graph

    def __post_init__(self) -> None:
        """
        Check whether the graph is directed. If not, raise an error.
        :return: None
        """
        if not self.graph.is_directed():
            raise RuntimeError(f"graph of {self} must be directed")

    def shallow_copy(self) -> LinePlanningNetwork:
        """
        Create a shallow copy of LinePlanningNetwork.
        :return: LinePlanningNetwork, a copy of the instance
        """
        return LinePlanningNetwork(self.graph.copy())

    @property
    def all_links(self) -> list[LPNLink]:
        """
        Access all the links from the network graph.
        :return: list[LPNLink], a list of LPNLink
        """
        return self.graph.es[self._link_key()]

    @property
    def all_nodes(self) -> list[LPNNode]:
        """
        Access all the nodes from the network graph.
        :return: list[LPNNode], a list of LPNNode
        """
        return self.graph.vs[self._node_key()]

    @property
    def all_node_names(self) -> tuple[str]:
        """
        Get the names of all the nodes.
        :return: tuple[str]
        """
        return self.graph.vs["name"]

    def get_link_index(self, source: str, target: str) -> int:
        """
        Get the index of an edge between two vertices.
        :param source: str, the ID or name of the start vertex
        :param target: str, the ID or name of the end vertex
        :return: int, index of the link
        """
        return self.graph.get_eid(source, target)

    @classmethod
    def _node_key(cls) -> str:
        """
        Get the name of the node.
        :return: str, name of the node
        """
        return LPNNode.__name__

    @classmethod
    def _link_key(cls) -> str:
        """
        Get the name of the link.
        :return: str, name of the link
        """
        return LPNLink.__name__

    @classmethod
    def create_from_scenario(cls, scenario: PlanningScenario, period_duration: timedelta) -> LinePlanningNetwork:
        """
        Create line planning network with given scenario.
        :param scenario: PlanningScenario
        :param period_duration: timedelta, total duration of the planning problem
        :return: LinePlanningNetwork, network consisting of nodes and links
        """
        nodes_to_add = set()
        links_to_add: list[tuple[tuple[str, str], LPNLink]] = []
        lines_with_directions = (
            (line, direction) for line in scenario.bus_lines for direction in (line.direction_a, line.direction_b)
        )
        for line, direction in lines_with_directions:
            new_nodes, new_links = cls._create_nodes_and_links_for_segment(line, direction, period_duration)
            links_to_add.extend(new_links)
            nodes_to_add.update(new_nodes)

        for walkable_distance in scenario.walkable_distances:
            links_to_add.extend(cls._create_links_for_walkable_distances(walkable_distance))

        return cls(cls._create_underlying_digraph(nodes_to_add, links_to_add))

    @classmethod
    def _create_links_for_walkable_distances(
        cls, walkable_distance: WalkableDistance
    ) -> tuple[tuple[tuple[str, str], LPNLink], tuple[tuple[str, str], LPNLink]]:
        """
        Create links for walkable distances in the line planning network.
        :param walkable_distance: WalkableDistance, a class which contains the starting point,
            ending point and walking time
        :return: tuple[tuple[tuple[str, str], LPNLink], tuple[tuple[str, str], LPNLink]],
            a tuple of the source and target nodes along with the LPNLink object in both directions
        """
        source = cls.transfer_node_name_from_station_name(walkable_distance.starting_at.name)
        target = cls.transfer_node_name_from_station_name(walkable_distance.ending_at.name)
        walking_link = LPNLink(Activity.WALKING, walkable_distance.walking_time, None, None)
        return ((source, target), walking_link), ((target, source), walking_link)

    @classmethod
    def _create_nodes_and_links_for_segment(
        cls, line: BusLine, direction: Direction, period_duration: timedelta
    ) -> tuple[set[LPNNode], tuple[tuple[tuple[str, str], LPNLink], ...]]:
        """
        Create nodes and links for the bus line segment in a specific direction.
        :param line: BusLine
        :param direction: Direction
        :param period_duration: timedelta, total duration of the planning problem
        :return: tuple[set[LPNNode], tuple[tuple[tuple[str, str], LPNLink], ...]],
            a set of all nodes and a tuple of tuples representing the links to be added to the graph
        """
        access_nodes, egress_nodes, service_nodes, transfer_nodes = cls._create_nodes_for_direction(direction, line)
        links_to_add: list[tuple[tuple[str, str], LPNLink]] = []
        for frequency in line.permitted_frequencies:
            average_waiting_time = period_duration / frequency * 0.5
            access_link = LPNLink(Activity.ACCESS_LINE, average_waiting_time, line.number, frequency)
            links_to_add.extend(
                ((access.name, service.name), access_link) for access, service in zip(access_nodes, service_nodes)
            )
            links_to_add.extend(
                ((transfer.name, service.name), access_link) for transfer, service in zip(transfer_nodes, service_nodes)
            )
        egress_link = LPNLink(Activity.EGRESS_LINE, timedelta(seconds=60), line.number, None)
        links_to_add.extend(
            ((service.name, egress.name), egress_link) for service, egress in zip(service_nodes, egress_nodes)
        )
        links_to_add.extend(
            ((service.name, transfer.name), egress_link) for service, transfer in zip(service_nodes, transfer_nodes)
        )
        service_links = (LPNLink(Activity.IN_VEHICLE, dt, line.number, None) for dt in direction.trip_times)
        links_to_add.extend(
            ((first.name, second.name), link) for (first, second), link in zip(pairwise(service_nodes), service_links)
        )
        return set(access_nodes + egress_nodes + service_nodes + transfer_nodes), tuple(links_to_add)  # noqa

    @classmethod
    def _create_nodes_for_direction(
        cls, direction: Direction, line: BusLine
    ) -> tuple[tuple[LPNNode, ...], tuple[LPNNode, ...], tuple[LPNNode, ...], tuple[LPNNode, ...]]:
        """
        Generate nodes of different purposes for specific busline and direction.
        :param direction: Direction
        :param line: BusLine
        :return: tuple[tuple[LPNNode, ...], tuple[LPNNode, ...], tuple[LPNNode, ...], tuple[LPNNode, ...]],
            a tuple which contains tuples of 4 types of nodes
        """
        station_names = direction.station_names
        access_nodes = tuple(
            LPNNode(node_name, None, None) for node_name in map(cls.access_node_name_from_station_name, station_names)
        )
        egress_nodes = tuple(
            LPNNode(node_name, None, None) for node_name in map(cls.egress_node_name_from_station_name, station_names)
        )
        transfer_nodes = tuple(
            LPNNode(node_name, None, None) for node_name in map(cls.transfer_node_name_from_station_name, station_names)
        )
        service_nodes = tuple(
            LPNNode(node_name, line.number, direction.name)
            for node_name in map(lambda x: cls.create_line_node_name(x, line, direction), station_names)
        )

        return access_nodes, egress_nodes, service_nodes, transfer_nodes

    @classmethod
    def _create_underlying_digraph(
        cls, nodes: Collection[LPNNode], links_with_s_t: Collection[tuple[tuple[str, str], LPNLink]]
    ) -> igraph.Graph:
        """
        Create a directed graph based on the nodes and links.
        :param nodes: Collection[LPNNode]
        :param links_with_s_t: Collection[tuple[tuple[str, str], LPNLink]]
        :return: igraph.Graph, the underlying digraph
        """
        network = igraph.Graph(directed=True)
        network.add_vertices(
            len(nodes), attributes={"name": [node.name for node in nodes], f"{cls._node_key()}": list(nodes)}
        )
        network.add_edges((s, t) for (s, t), _ in links_with_s_t)
        for edge_index, (_, link) in enumerate(links_with_s_t):
            network.es[edge_index][cls._link_key()] = link
        return network

    @staticmethod
    def access_node_name_from_station_name(station_name: str) -> str:
        """
        Generate the names of access nodes.
        :param station_name: str, station name
        :return: str, name of the node
        """
        return f"{Activity.ACCESS_LINE.value}${station_name}"

    @staticmethod
    def egress_node_name_from_station_name(station_name: str) -> str:
        """
        Generate the names of egress nodes.
        :param station_name: str, station name
        :return: str, name of the node
        """
        return f"{Activity.EGRESS_LINE.value}${station_name}"

    @staticmethod
    def transfer_node_name_from_station_name(station_name: str) -> str:
        """
        Generate the names of transfer nodes.
        :param station_name: str, station name
        :return: str, name of the node
        """
        return f"{Activity.TRANSFER.value}${station_name}"

    @staticmethod
    def create_line_node_name(station_name: str, line: BusLine, direction: Direction) -> str:
        """
        Generate the node name associated with the bus line.
        :param station_name: str, station name
        :param line: BusLine
        :param direction: Direction
        :return: str, name of the node
        """
        return f"{line.number}-{direction.name}-{station_name}"
