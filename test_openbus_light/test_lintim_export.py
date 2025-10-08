"""Tests for exporting planning scenarios to the LinTim format."""

from __future__ import annotations

import csv

from pathlib import Path

from openbus_light.export import (
    export_planning_scenario_to_lintim,
    export_planning_scenario_to_lintim_with_walk_lines,
)

from .shared import cached_scenario


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_export_creates_expected_files(tmp_path):
    scenario = cached_scenario()

    export_planning_scenario_to_lintim(scenario, tmp_path)

    stops_path = tmp_path / "stops.csv"
    edges_path = tmp_path / "edges.csv"
    line_concept_path = tmp_path / "line-concept.csv"
    line_stop_path = tmp_path / "line-stop.csv"
    od_path = tmp_path / "od.csv"
    footpaths_path = tmp_path / "footpaths.csv"

    for path in (stops_path, edges_path, line_concept_path, line_stop_path, od_path, footpaths_path):
        assert path.exists(), f"missing expected LinTim file: {path.name}"

    stops_rows = _read_csv(stops_path)
    station_names = {row["stop_name"] for row in stops_rows}
    assert station_names, "stops.csv must contain at least one station"
    assert str(scenario.stations[0].name) in station_names

    edges_rows = _read_csv(edges_path)
    assert edges_rows, "edges.csv must contain at least one edge"
    assert any(float(row["travel_time_seconds"]) > 0 for row in edges_rows)
    modes = {row["mode"] for row in edges_rows}
    assert "vehicle" in modes
    if scenario.walkable_distances:
        assert "walk" in modes

    line_concept_rows = _read_csv(line_concept_path)
    assert line_concept_rows, "line-concept.csv must list at least one line"
    assert any(row["direction_name"] for row in line_concept_rows)
    assert any(int(row["vehicle_capacity"]) > 0 for row in line_concept_rows if row["vehicle_capacity"])

    line_stop_rows = _read_csv(line_stop_path)
    assert line_stop_rows, "line-stop.csv must contain ordered stops"
    assert any(row["line_id"] == line_concept_rows[0]["line_id"] for row in line_stop_rows)

    od_rows = _read_csv(od_path)
    assert any(float(row["passengers"]) > 0 for row in od_rows)

    footpath_rows = _read_csv(footpaths_path)
    if scenario.walkable_distances:
        assert any(float(row["walking_time_seconds"]) > 0 for row in footpath_rows)


def test_walks_can_be_exported_as_lines(tmp_path):
    scenario = cached_scenario()

    export_planning_scenario_to_lintim_with_walk_lines(scenario, tmp_path)

    footpaths_path = tmp_path / "footpaths.csv"
    assert not footpaths_path.exists(), "footpaths.csv should not be created when exporting walks as lines"

    line_concept_rows = _read_csv(tmp_path / "line-concept.csv")
    walk_line_rows = [row for row in line_concept_rows if row["line_id"].startswith("WALK_")]
    assert walk_line_rows, "synthetic walk lines must be present"
