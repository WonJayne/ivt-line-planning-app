"""Tests for exporting planning scenarios to the LinTim format."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Mapping

from openbus_light.export import (
    export_planning_scenario_to_lintim,
    export_planning_scenario_to_lintim_with_walk_lines,
)

from .shared import cached_scenario


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def _station_ids(scenario) -> Mapping[str, int]:
    return {
        str(station.name): index
        for index, station in enumerate(sorted(scenario.stations, key=lambda item: str(item.name)), start=1)
    }


def test_export_creates_expected_files(tmp_path):
    scenario = cached_scenario()

    export_planning_scenario_to_lintim(scenario, tmp_path)

    stops_path = tmp_path / "stops.csv"
    edges_path = tmp_path / "edges.csv"
    lines_path = tmp_path / "lines.csv"
    od_path = tmp_path / "od.csv"
    walking_path = tmp_path / "walking_distances.csv"

    for path in (stops_path, edges_path, lines_path, od_path, walking_path):
        assert path.exists(), f"missing expected LinTim file: {path.name}"

    stops_rows = _read_csv(stops_path)
    station_names = {row["stop-name"] for row in stops_rows}
    assert station_names, "stops.csv must contain at least one station"
    assert str(scenario.stations[0].name) in station_names
    assert all("x" in row and "y" in row for row in stops_rows)

    edges_rows = _read_csv(edges_path)
    assert edges_rows, "edges.csv must contain at least one edge"
    assert any(float(row["length"]) > 0 for row in edges_rows)

    line_rows = _read_csv(lines_path)
    assert line_rows, "lines.csv must list at least one line"
    assert all(row["property"] == "line" for row in line_rows)
    assert any(
        len([stop_id for stop_id in row["sequence"].split(",") if stop_id]) >= 2 for row in line_rows
    )

    od_rows = _read_csv(od_path)
    assert any(float(row["passengers"]) > 0 for row in od_rows)

    walking_rows = _read_csv(walking_path)
    if scenario.walkable_distances:
        assert any(float(row["length"]) > 0 for row in walking_rows)


def test_walks_can_be_exported_as_lines(tmp_path):
    scenario = cached_scenario()

    export_planning_scenario_to_lintim_with_walk_lines(scenario, tmp_path)

    walking_path = tmp_path / "walking_distances.csv"
    assert walking_path.exists(), "walking_distances.csv must always be created"

    line_rows = _read_csv(tmp_path / "lines.csv")

    if scenario.walkable_distances:
        station_ids = _station_ids(scenario)
        expected_sequences = {
            f"{station_ids[str(walk.starting_at.name)]},{station_ids[str(walk.ending_at.name)]}"
            for walk in scenario.walkable_distances
        }
        assert expected_sequences & {row["sequence"] for row in line_rows}, "synthetic walk lines must be present"
