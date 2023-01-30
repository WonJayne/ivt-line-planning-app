from __future__ import annotations

import uuid
from collections import Counter
from itertools import chain, product
from typing import Collection, Sequence

import numpy as np
import pandas as pd

from ..line_planning import LinePlanningParameters
from ..modelling import DemandMatrix, DistrictPoints, PointIn2D, Station
from ..utils import skip_one_line_in_file
from .paths import ScenarioPaths
from .point import calculate_distance_in_m


def _load_all_district_points(path_to_demand_district_points: str) -> tuple[DistrictPoints, ...]:
    with open(path_to_demand_district_points, encoding="utf-8") as file:
        skip_one_line_in_file(file)
        raw_demand_points = pd.read_csv(file, sep=",", encoding="utf-8", dtype=str)

    return tuple(
        DistrictPoints(
            district_name=row.BEZIRKE,
            position=PointIn2D(lat=float(row.YCOORD), long=float(row.XCOORD)),
            id=str(uuid.uuid4()),
        )
        for row in raw_demand_points.itertuples(index=False)
        if not pd.isnull(row.BEZIRKE)
    )


def load_demand_matrix(
    stations: Sequence[Station], parameters: LinePlanningParameters, paths: ScenarioPaths
) -> DemandMatrix:
    all_district_points = _load_all_district_points(paths.to_districts)
    demanded_relations = _load_all_demanded_relations(paths.to_demand)

    _map_district_to_nearest_station(all_district_points, stations, parameters.demand_association_radius)

    covered_district_points = tuple(chain.from_iterable(station.district_points for station in stations))
    stations_per_district = Counter(station.district_name for station in covered_district_points)
    demand_between_district_points = _distribute_demand_between_districts(
        covered_district_points, parameters.demand_scaling, demanded_relations, stations_per_district
    )
    from_station_to_other_stations = _map_demand_from_districts_to_stations(demand_between_district_points, stations)

    return DemandMatrix(matrix=_sort_from_station_to_other_stations(from_station_to_other_stations))


def _map_district_to_nearest_station(
    all_district_points: Collection[DistrictPoints], stations: Sequence[Station], association_radius: int
) -> None:
    for district_point in all_district_points:
        distances = tuple(
            min(calculate_distance_in_m(district_point.position, point) for point in station.points)
            for station in stations
        )
        nearest_station_index: int = np.argmin(distances)  # type:ignore
        if distances[nearest_station_index] < association_radius:
            nearest_stop = stations[nearest_station_index]
            nearest_stop.district_points.append(district_point)


def _map_demand_from_districts_to_stations(
    demand_between_district_points: dict[str, dict[str, float]], stations: Collection[Station]
) -> dict[str, dict[str, float]]:
    return {
        origin.name: {
            destination.name: sum(
                demand_between_district_points[origin_district.id][destination_district.id]
                for origin_district, destination_district in product(
                    origin.district_points, destination.district_points
                )
            )
            for destination in stations
        }
        for origin in stations
    }


def _sort_from_station_to_other_stations(
    from_station_to_other_stations: dict[str, dict[str, float]]
) -> dict[str, dict[str, float]]:
    return {
        origin_key: dict(sorted(demand.items(), key=lambda x: x[0]))
        for origin_key, demand in sorted(from_station_to_other_stations.items(), key=lambda x: x[0])
    }


def _distribute_demand_between_districts(
    covered_district_points: Collection[DistrictPoints],
    demand_scale: float,
    demanded_relations: dict[tuple[str, str], float],
    stations_per_district: dict[str, int],
) -> dict[str, dict[str, float]]:
    return {
        origin_district.id: {
            target_district.id: demanded_relations[origin_district.district_name, target_district.district_name]
            * (1 / stations_per_district[origin_district.district_name])
            * (1 / stations_per_district[target_district.district_name])
            * demand_scale
            for target_district in covered_district_points
        }
        for origin_district in covered_district_points
    }


def _load_all_demanded_relations(path_to_demand: str) -> dict[tuple[str, str], float]:
    with open(path_to_demand, encoding="utf-8") as file:
        skip_one_line_in_file(file)
        raw_demand = pd.read_csv(file, sep=",", encoding="utf-8", dtype=str)
        return {
            (relation.FROM, relation.TO): round(float(relation.DEMAND), 4)
            for relation in raw_demand.itertuples(index=False)
        }
