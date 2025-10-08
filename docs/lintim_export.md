# LinTim export mapping

The exporter in `openbus_light.export.lintim` transforms a `PlanningScenario` into the LinTim input
collection described in the [LinTim documentation](https://www.lintim.net/doc/lintiminput.pdf).
This file records the conventions used so future extensions stay compatible with the official
specification.

## Station identifiers

* Every `Station.name` is mapped to a numeric identifier by sorting the names alphabetically and
  assigning consecutive numbers starting at 1. The resulting table is written to `stops.csv` with the
  columns `stop-id`, `stop-name`, `x`, and `y`. Coordinates are converted from WGS84 to the Swiss LV03
  system using the same transformation as the network plotting helpers to match the LinTim
  expectation of working in Swiss coordinates.

## Network edges

* For each `Direction.trip_time_by_pair()` the exporter creates a directed record in `edges.csv` with
  the origin identifier, destination identifier, and the straight-line distance derived from the
  station coordinates (in kilometres). The `lower-bound` and `upper-bound` columns are left open (0
  and 999) so downstream experiments can apply their own capacity constraints. When multiple lines
  share the same connection, the fastest travel time is used to derive the recorded distance.

## Line descriptions

* `lines.csv` contains one row per line direction (property `line`). The `line_group` column is a
  sequential identifier and `sequence` stores the ordered stop identifiers as a comma-separated list.

* Walking links can be exported as additional line entries via the CLI flag `--walks-as-lines`. In
  that mode the exporter appends each walk as a two-stop sequence using the same deterministic stop
  identifiers as the rest of the files.

## Demand and footpaths

* Passenger demand is serialised to `od.csv` by converting `DemandMatrix.all_od_pairs()` into origin
  and destination identifiers. Demand values are written without modification.

* Walking links are always written to `walking_distances.csv`. The file stores the origin and
  destination identifiers, the walking time in seconds, and flags every row as directed. These values
  align with the "Edge Walking" specification in the LinTim input documentation (see Section 8.3.9 of
  the official manual).

These mappings ensure the generated CSV files follow the LinTim expectations while staying faithful
to the structure of the `PlanningScenario`. If new LinTim tables need to be filled in the future,
extend the exporter with the same deterministic mapping patterns described above.
