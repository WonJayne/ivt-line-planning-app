# LinTim export mapping

The exporter in `openbus_light.export.lintim` transforms a `PlanningScenario` into the LinTim input
collection described in the [LinTim documentation](https://www.lintim.net/doc/lintiminput.pdf).
This file records the conventions used so future extensions stay compatible with the official
specification.

## Station identifiers

* Every `Station.name` is mapped to a numeric identifier by sorting the names alphabetically and
  assigning consecutive numbers starting at 1. The resulting table is written to `stops.csv` with the
  columns `stop_id`, `stop_name`, `latitude`, and `longitude` using the values from
  `Station.center_position`.

## Network edges

* For each `Direction.trip_time_by_pair()` the exporter creates a directed record in `edges.csv` with
  the origin identifier, destination identifier, travel time in seconds, and a straight-line distance
  derived from the station coordinates. The `mode` column contains `vehicle` for bus movements and
  `walk` for walkable links. When multiple lines share the same connection, the fastest travel time is
  preserved.

## Line descriptions

* `line-concept.csv` contains one row per `(BusLine.number, Direction.name)` pair. The identifiers are
  deterministic strings of the form `LINE_<number>_<direction>` with non-alphanumeric characters
  replaced by underscores. Each row records the vehicle capacity and the permitted frequencies. The
  ordered stop sequence for every direction is stored in `line-stop.csv` with 1-based indices.

* Walking links can be exported as additional lines via the CLI flag `--walks-as-lines`. In that mode
  the exporter writes synthetic line identifiers `WALK_<originId>_<destinationId>` and stores the two
  involved stops in `line-stop.csv`.

## Demand and footpaths

* Passenger demand is serialised to `od.csv` by converting `DemandMatrix.all_od_pairs()` into origin
  and destination identifiers. Demand values are written without modification.

* When the default footpath representation is used, the exporter writes `footpaths.csv`. Each row
  contains the origin and destination identifiers, the walking time in seconds, and the straight-line
  distance calculated for the corresponding stations.

These mappings ensure the generated CSV files follow the LinTim expectations while staying faithful
to the structure of the `PlanningScenario`. If new LinTim tables need to be filled in the future,
extend the exporter with the same deterministic mapping patterns described above.
