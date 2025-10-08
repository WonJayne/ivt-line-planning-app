"""Export :class:`~openbus_light.model.scenario.PlanningScenario` data to LinTim files."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Iterator, Mapping, Sequence

from ..model.direction import Direction
from ..model.line import BusLine
from ..model.scenario import PlanningScenario
from ..model.station import Station
from ..model.walkable_distance import WalkableDistance


class WalkRepresentation(Enum):
    """Possible representations of walking links in the LinTim export."""

    FOOTPATHS = "footpaths"
    SYNTHETIC_LINES = "synthetic_lines"


@dataclass(frozen=True)
class _EdgeRow:
    """Representation of a LinTim edge."""

    from_stop_id: int
    to_stop_id: int
    travel_time_seconds: float
    distance: float
    mode: str


@dataclass(frozen=True)
class _LineConceptRow:
    """Representation of a LinTim line concept entry."""

    line_id: str
    line_number: int | None
    direction_name: str
    vehicle_capacity: int
    permitted_frequencies: str


@dataclass(frozen=True)
class _LineStopRow:
    """Representation of a LinTim ordered stop entry for a line."""

    line_id: str
    sequence: int
    stop_id: int


@dataclass(frozen=True)
class _FootpathRow:
    """Representation of a LinTim footpath."""

    from_stop_id: int
    to_stop_id: int
    walking_time_seconds: float
    distance: float


def export_planning_scenario_to_lintim(scenario: PlanningScenario, output_dir: Path) -> None:
    """Export ``scenario`` to LinTim CSV files in ``output_dir`` using footpaths."""

    _export_planning_scenario_to_lintim(scenario, output_dir, WalkRepresentation.FOOTPATHS)


def export_planning_scenario_to_lintim_with_walk_lines(
    scenario: PlanningScenario, output_dir: Path
) -> None:
    """Export ``scenario`` to LinTim CSV files representing walks as synthetic lines."""

    _export_planning_scenario_to_lintim(scenario, output_dir, WalkRepresentation.SYNTHETIC_LINES)


def _export_planning_scenario_to_lintim(
    scenario: PlanningScenario, output_dir: Path, walk_representation: WalkRepresentation
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    station_id_by_name = _create_station_id_mapping(scenario.stations)
    station_by_name = {str(station.name): station for station in scenario.stations}

    _write_stops(output_dir / "stops.csv", station_by_name, station_id_by_name)

    edge_rows = _collect_edge_rows(scenario, station_id_by_name, station_by_name)
    _write_edges(output_dir / "edges.csv", edge_rows)

    line_concept_rows, line_stop_rows = _collect_line_rows(
        scenario, station_id_by_name, walk_representation
    )
    _write_line_concept(output_dir / "line-concept.csv", line_concept_rows)
    _write_line_stop(output_dir / "line-stop.csv", line_stop_rows)

    demand_rows = _collect_demand_rows(scenario, station_id_by_name)
    _write_demand(output_dir / "od.csv", demand_rows)

    if walk_representation is WalkRepresentation.FOOTPATHS:
        footpath_rows = _collect_footpath_rows(scenario.walkable_distances, station_id_by_name, station_by_name)
        _write_footpaths(output_dir / "footpaths.csv", footpath_rows)


def _create_station_id_mapping(stations: Sequence[Station]) -> Mapping[str, int]:
    sorted_stations = sorted(stations, key=lambda station: str(station.name))
    return {str(station.name): index for index, station in enumerate(sorted_stations, start=1)}


def _write_stops(
    path: Path, stations_by_name: Mapping[str, Station], station_id_by_name: Mapping[str, int]
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stop_id", "stop_name", "latitude", "longitude"])
        writer.writeheader()
        for station_name, station_id in sorted(station_id_by_name.items(), key=lambda item: item[1]):
            station = stations_by_name[station_name]
            writer.writerow(
                {
                    "stop_id": station_id,
                    "stop_name": station_name,
                    "latitude": station.center_position.lat,
                    "longitude": station.center_position.long,
                }
            )


def _collect_edge_rows(
    scenario: PlanningScenario,
    station_id_by_name: Mapping[str, int],
    station_by_name: Mapping[str, Station],
) -> list[_EdgeRow]:
    edges: Dict[tuple[int, int, str], _EdgeRow] = {}

    def register_edge(
        origin_name: str, destination_name: str, travel_time_seconds: float, mode: str
    ) -> None:
        origin_id = station_id_by_name[origin_name]
        destination_id = station_id_by_name[destination_name]
        distance = _distance_between(station_by_name[origin_name], station_by_name[destination_name])
        key = (origin_id, destination_id, mode)
        current = edges.get(key)
        if current is None or travel_time_seconds < current.travel_time_seconds:
            edges[key] = _EdgeRow(
                from_stop_id=origin_id,
                to_stop_id=destination_id,
                travel_time_seconds=travel_time_seconds,
                distance=distance,
                mode=mode,
            )

    for line in scenario.bus_lines:
        _register_direction_edges(line.direction_up, register_edge)
        _register_direction_edges(line.direction_down, register_edge)

    for walk in scenario.walkable_distances:
        register_edge(str(walk.starting_at.name), str(walk.ending_at.name), walk.walking_time.total_seconds(), "walk")

    return sorted(edges.values(), key=lambda row: (row.from_stop_id, row.to_stop_id, row.mode))


def _register_direction_edges(
    direction: Direction, register_edge: Callable[[str, str, float, str], None]
) -> None:
    for (origin, destination), trip_time in direction.trip_time_by_pair():
        register_edge(str(origin), str(destination), trip_time.total_seconds(), "vehicle")


def _write_edges(path: Path, edges: Sequence[_EdgeRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["from_stop_id", "to_stop_id", "travel_time_seconds", "distance", "mode"]
        )
        writer.writeheader()
        for edge in edges:
            writer.writerow(
                {
                    "from_stop_id": edge.from_stop_id,
                    "to_stop_id": edge.to_stop_id,
                    "travel_time_seconds": edge.travel_time_seconds,
                    "distance": edge.distance,
                    "mode": edge.mode,
                }
            )


def _collect_line_rows(
    scenario: PlanningScenario,
    station_id_by_name: Mapping[str, int],
    walk_representation: WalkRepresentation,
) -> tuple[list[_LineConceptRow], list[_LineStopRow]]:
    line_concept_rows: list[_LineConceptRow] = []
    line_stop_rows: list[_LineStopRow] = []

    bus_line_rows = list(_iter_bus_line_rows(scenario.bus_lines, station_id_by_name))
    line_concept_rows.extend(row for row, _ in bus_line_rows)
    for _, stop_rows in bus_line_rows:
        line_stop_rows.extend(stop_rows)

    if walk_representation is WalkRepresentation.SYNTHETIC_LINES:
        walk_rows = _iter_walk_line_rows(scenario.walkable_distances, station_id_by_name)
        for concept_row, stop_rows in walk_rows:
            line_concept_rows.append(concept_row)
            line_stop_rows.extend(stop_rows)

    return line_concept_rows, line_stop_rows


def _iter_bus_line_rows(
    bus_lines: Sequence[BusLine], station_id_by_name: Mapping[str, int]
) -> Iterator[tuple[_LineConceptRow, list[_LineStopRow]]]:
    for line in sorted(bus_lines, key=lambda candidate: (int(candidate.number), str(candidate.name))):
        yield from _iter_direction_rows(line, station_id_by_name)


def _iter_direction_rows(
    line: BusLine, station_id_by_name: Mapping[str, int]
) -> Iterator[tuple[_LineConceptRow, list[_LineStopRow]]]:
    for direction in (line.direction_up, line.direction_down):
        line_id = _line_identifier(int(line.number), str(direction.name))
        permitted = "" if not line.permitted_frequencies else ";".join(
            str(int(freq)) for freq in sorted(line.permitted_frequencies)
        )
        concept_row = _LineConceptRow(
            line_id=line_id,
            line_number=int(line.number),
            direction_name=str(direction.name),
            vehicle_capacity=int(line.capacity),
            permitted_frequencies=permitted,
        )
        stop_rows = [
            _LineStopRow(line_id=line_id, sequence=index, stop_id=station_id_by_name[str(station_name)])
            for index, station_name in enumerate(direction.station_sequence, start=1)
        ]
        yield concept_row, stop_rows


def _iter_walk_line_rows(
    walkable_distances: Sequence[WalkableDistance], station_id_by_name: Mapping[str, int]
) -> Iterator[tuple[_LineConceptRow, list[_LineStopRow]]]:
    for walk in sorted(
        walkable_distances, key=lambda candidate: (str(candidate.starting_at.name), str(candidate.ending_at.name))
    ):
        origin_name = str(walk.starting_at.name)
        destination_name = str(walk.ending_at.name)
        line_id = f"WALK_{station_id_by_name[origin_name]}_{station_id_by_name[destination_name]}"
        concept_row = _LineConceptRow(
            line_id=line_id,
            line_number=None,
            direction_name=f"WALK from {origin_name} to {destination_name}",
            vehicle_capacity=0,
            permitted_frequencies="",
        )
        stop_rows = [
            _LineStopRow(line_id=line_id, sequence=1, stop_id=station_id_by_name[origin_name]),
            _LineStopRow(line_id=line_id, sequence=2, stop_id=station_id_by_name[destination_name]),
        ]
        yield concept_row, stop_rows


def _line_identifier(line_number: int, direction_name: str) -> str:
    sanitized_direction = "".join(character if character.isalnum() else "_" for character in direction_name)
    sanitized_direction = "_".join(part for part in sanitized_direction.split("_") if part)
    return f"LINE_{line_number}_{sanitized_direction or 'DIR'}"


def _write_line_concept(path: Path, rows: Sequence[_LineConceptRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "line_id",
                "line_number",
                "direction_name",
                "vehicle_capacity",
                "permitted_frequencies",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "line_id": row.line_id,
                    "line_number": "" if row.line_number is None else row.line_number,
                    "direction_name": row.direction_name,
                    "vehicle_capacity": row.vehicle_capacity,
                    "permitted_frequencies": row.permitted_frequencies,
                }
            )


def _write_line_stop(path: Path, rows: Sequence[_LineStopRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["line_id", "sequence", "stop_id"])
        writer.writeheader()
        for row in sorted(rows, key=lambda candidate: (candidate.line_id, candidate.sequence)):
            writer.writerow(
                {
                    "line_id": row.line_id,
                    "sequence": row.sequence,
                    "stop_id": row.stop_id,
                }
            )


def _collect_demand_rows(
    scenario: PlanningScenario, station_id_by_name: Mapping[str, int]
) -> list[tuple[int, int, float]]:
    rows: list[tuple[int, int, float]] = []
    for origin_name, destination_name, demand in scenario.demand_matrix.all_od_pairs():
        rows.append(
            (
                station_id_by_name[str(origin_name)],
                station_id_by_name[str(destination_name)],
                demand,
            )
        )
    return rows


def _write_demand(path: Path, demand_rows: Sequence[tuple[int, int, float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["origin_stop_id", "destination_stop_id", "passengers"])
        writer.writeheader()
        for origin_id, destination_id, passengers in demand_rows:
            writer.writerow(
                {
                    "origin_stop_id": origin_id,
                    "destination_stop_id": destination_id,
                    "passengers": passengers,
                }
            )


def _collect_footpath_rows(
    walkable_distances: Sequence[WalkableDistance],
    station_id_by_name: Mapping[str, int],
    station_by_name: Mapping[str, Station],
) -> list[_FootpathRow]:
    rows: list[_FootpathRow] = []
    for walk in walkable_distances:
        origin_name = str(walk.starting_at.name)
        destination_name = str(walk.ending_at.name)
        rows.append(
            _FootpathRow(
                from_stop_id=station_id_by_name[origin_name],
                to_stop_id=station_id_by_name[destination_name],
                walking_time_seconds=walk.walking_time.total_seconds(),
                distance=_distance_between(station_by_name[origin_name], station_by_name[destination_name]),
            )
        )
    return sorted(rows, key=lambda row: (row.from_stop_id, row.to_stop_id))


def _write_footpaths(path: Path, rows: Sequence[_FootpathRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["from_stop_id", "to_stop_id", "walking_time_seconds", "distance"]
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "from_stop_id": row.from_stop_id,
                    "to_stop_id": row.to_stop_id,
                    "walking_time_seconds": row.walking_time_seconds,
                    "distance": row.distance,
                }
            )


def _distance_between(origin: Station, destination: Station) -> float:
    origin_position = origin.center_position
    destination_position = destination.center_position
    delta_lat = destination_position.lat - origin_position.lat
    delta_long = destination_position.long - origin_position.long
    return math.hypot(delta_lat, delta_long)
