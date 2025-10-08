"""Export :class:`~openbus_light.model.scenario.PlanningScenario` data to LinTim files."""

from __future__ import annotations

import csv
from math import atan2, cos, radians, sin, sqrt
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, Iterable, Mapping, Sequence

from ..model.direction import Direction
from ..model.line import BusLine
from ..model.scenario import PlanningScenario
from ..model.station import Station
from ..model.walkable_distance import WalkableDistance

try:  # pragma: no cover - optional dependency
    from ..plot._convert import wgs84_to_lv03 as _convert_to_lv03
except ModuleNotFoundError:  # pragma: no cover - fallback when numba is missing
    _convert_to_lv03 = None


class WalkRepresentation(Enum):
    """Possible representations of walking links in the LinTim export."""

    FOOTPATHS = "footpaths"
    SYNTHETIC_LINES = "synthetic_lines"


def export_planning_scenario_to_lintim(scenario: PlanningScenario, output_dir: Path) -> None:
    """Export ``scenario`` to LinTim CSV files in ``output_dir`` using footpaths."""

    _export_planning_scenario_to_lintim(scenario, output_dir, WalkRepresentation.FOOTPATHS)


def export_planning_scenario_to_lintim_with_walk_lines(
    scenario: PlanningScenario, output_dir: Path
) -> None:
    """Export ``scenario`` to LinTim CSV files representing walks as additional lines."""

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

    line_rows = _collect_line_rows(scenario, station_id_by_name, walk_representation)
    _write_lines(output_dir / "lines.csv", line_rows)

    demand_rows = _collect_demand_rows(scenario, station_id_by_name)
    _write_demand(output_dir / "od.csv", demand_rows)

    walking_rows = _collect_walking_rows(scenario.walkable_distances, station_id_by_name)
    _write_walking_distances(output_dir / "walking_distances.csv", walking_rows)


def _create_station_id_mapping(stations: Sequence[Station]) -> Mapping[str, int]:
    sorted_stations = sorted(stations, key=lambda station: str(station.name))
    return {str(station.name): index for index, station in enumerate(sorted_stations, start=1)}


def _write_stops(
    path: Path, stations_by_name: Mapping[str, Station], station_id_by_name: Mapping[str, int]
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["stop-id", "stop-name", "x", "y"],
            delimiter=";",
        )
        writer.writeheader()
        for station_name, station_id in sorted(station_id_by_name.items(), key=lambda item: item[1]):
            station = stations_by_name[station_name]
            x_coord, y_coord = _to_swiss_coordinates(station.center_position.lat, station.center_position.long)
            writer.writerow(
                {
                    "stop-id": station_id,
                    "stop-name": station_name,
                    "x": round(x_coord, 3),
                    "y": round(y_coord, 3),
                }
            )


def _collect_edge_rows(
    scenario: PlanningScenario,
    station_id_by_name: Mapping[str, int],
    station_by_name: Mapping[str, Station],
) -> list[tuple[int, int, float, float]]:
    edges: Dict[tuple[int, int], tuple[float, float]] = {}

    def register_edge(origin_name: str, destination_name: str, travel_time_seconds: float) -> None:
        origin_id = station_id_by_name[origin_name]
        destination_id = station_id_by_name[destination_name]
        distance = _distance_between(station_by_name[origin_name], station_by_name[destination_name])
        key = (origin_id, destination_id)
        current = edges.get(key)
        if current is None or travel_time_seconds < current[0]:
            edges[key] = (travel_time_seconds, distance)

    for line in scenario.bus_lines:
        _register_direction_edges(line.direction_up, register_edge)
        _register_direction_edges(line.direction_down, register_edge)

    ordered = sorted(edges.items(), key=lambda item: item[0])
    return [
        (index, origin, destination, travel_time, distance)
        for index, ((origin, destination), (travel_time, distance)) in enumerate(ordered, start=1)
    ]


def _register_direction_edges(
    direction: Direction, register_edge: Callable[[str, str, float], None]
) -> None:
    for (origin, destination), trip_time in direction.trip_time_by_pair():
        register_edge(str(origin), str(destination), trip_time.total_seconds())


def _write_edges(path: Path, edges: Sequence[tuple[int, int, int, float, float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["edge-id", "left-stop-id", "right-stop-id", "length", "lower-bound", "upper-bound"],
            delimiter=";",
        )
        writer.writeheader()
        for edge_id, origin_id, destination_id, travel_time_seconds, distance_meters in edges:
            writer.writerow(
                {
                    "edge-id": edge_id,
                    "left-stop-id": origin_id,
                    "right-stop-id": destination_id,
                    "length": round(distance_meters / 1000.0, 6),
                    "lower-bound": 0,
                    "upper-bound": 999,
                }
            )


def _collect_line_rows(
    scenario: PlanningScenario,
    station_id_by_name: Mapping[str, int],
    walk_representation: WalkRepresentation,
) -> list[tuple[int, list[int]]]:
    sequences: list[list[int]] = []

    for line in sorted(scenario.bus_lines, key=lambda candidate: (int(candidate.number), str(candidate.name))):
        sequences.extend(_direction_station_ids(line.direction_up, station_id_by_name))
        sequences.extend(_direction_station_ids(line.direction_down, station_id_by_name))

    if walk_representation is WalkRepresentation.SYNTHETIC_LINES:
        for walk in sorted(
            scenario.walkable_distances,
            key=lambda candidate: (str(candidate.starting_at.name), str(candidate.ending_at.name)),
        ):
            origin = station_id_by_name[str(walk.starting_at.name)]
            destination = station_id_by_name[str(walk.ending_at.name)]
            sequences.append([origin, destination])

    return [(index, sequence) for index, sequence in enumerate(sequences, start=1)]


def _direction_station_ids(direction: Direction, station_id_by_name: Mapping[str, int]) -> list[list[int]]:
    station_ids = [station_id_by_name[str(station_name)] for station_name in direction.station_sequence]
    return [station_ids] if station_ids else []


def _write_lines(path: Path, line_rows: Sequence[tuple[int, Sequence[int]]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["property", "line_group", "sequence"], delimiter=";")
        writer.writeheader()
        for line_group, sequence in line_rows:
            writer.writerow(
                {
                    "property": "line",
                    "line_group": line_group,
                    "sequence": ",".join(str(stop_id) for stop_id in sequence),
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
        writer = csv.DictWriter(
            handle,
            fieldnames=["origin-stop-id", "destination-stop-id", "passengers"],
            delimiter=";",
        )
        writer.writeheader()
        for origin_id, destination_id, passengers in demand_rows:
            writer.writerow(
                {
                    "origin-stop-id": origin_id,
                    "destination-stop-id": destination_id,
                    "passengers": passengers,
                }
            )


def _collect_walking_rows(
    walkable_distances: Iterable[WalkableDistance], station_id_by_name: Mapping[str, int]
) -> list[tuple[int, int, int, float]]:
    rows: list[tuple[int, int, int, float]] = []
    for index, walk in enumerate(
        sorted(
            walkable_distances,
            key=lambda candidate: (str(candidate.starting_at.name), str(candidate.ending_at.name)),
        ),
        start=1,
    ):
        origin_name = str(walk.starting_at.name)
        destination_name = str(walk.ending_at.name)
        rows.append(
            (
                index,
                station_id_by_name[origin_name],
                station_id_by_name[destination_name],
                walk.walking_time.total_seconds(),
            )
        )
    return rows


def _write_walking_distances(path: Path, rows: Sequence[tuple[int, int, int, float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["edge-id", "left-stop-id", "right-stop-id", "length", "is-directed"],
            delimiter=";",
        )
        writer.writeheader()
        for edge_id, origin_id, destination_id, walking_seconds in rows:
            writer.writerow(
                {
                    "edge-id": edge_id,
                    "left-stop-id": origin_id,
                    "right-stop-id": destination_id,
                    "length": round(walking_seconds, 3),
                    "is-directed": 1,
                }
            )


def _distance_between(origin: Station, destination: Station) -> float:
    origin_position = origin.center_position
    destination_position = destination.center_position

    delta_lon = radians(destination_position.long) - radians(origin_position.long)
    delta_lat = radians(destination_position.lat) - radians(origin_position.lat)

    value_a = (
        sin(delta_lat / 2) ** 2
        + cos(radians(origin_position.lat))
        * cos(radians(destination_position.lat))
        * sin(delta_lon / 2) ** 2
    )
    value_c = 2 * atan2(sqrt(value_a), sqrt(1 - value_a))
    earth_radius = 6_373_000.0
    return earth_radius * value_c


def _to_swiss_coordinates(lat: float, lon: float) -> tuple[float, float]:
    if _convert_to_lv03 is not None:  # pragma: no cover - dependent on optional numba import
        return _convert_to_lv03(lat, lon)

    # Fallback conversion based on swisstopo CH1903 transformation formula
    bern_lat_deg = 46.9524055556
    bern_lon_deg = 7.4395833333

    lv03_east_a0 = 600072.37
    lv03_east_a1 = 211455.93
    lv03_east_a2 = -10938.51
    lv03_east_a3 = -0.36
    lv03_east_a4 = -44.54

    lv03_north_b0 = 200147.07
    lv03_north_b1 = 308807.95
    lv03_north_b2 = 3745.25
    lv03_north_b3 = 76.63
    lv03_north_b4 = -194.56
    lv03_north_b5 = 119.79

    lat_sec = (lat - bern_lat_deg) * 3600
    lon_sec = (lon - bern_lon_deg) * 3600

    lat_aux = lat_sec / 10000.0
    lon_aux = lon_sec / 10000.0

    east = (
        lv03_east_a0
        + lv03_east_a1 * lon_aux
        + lv03_east_a2 * lon_aux * lat_aux
        + lv03_east_a3 * lon_aux * lat_aux**2
        + lv03_east_a4 * lon_aux**3
    )

    north = (
        lv03_north_b0
        + lv03_north_b1 * lat_aux
        + lv03_north_b2 * lon_aux**2
        + lv03_north_b3 * lat_aux**2
        + lv03_north_b4 * lon_aux**2 * lat_aux
        + lv03_north_b5 * lat_aux**3
    )

    return east, north
