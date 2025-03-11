from __future__ import annotations

import uuid
from collections import Counter
from itertools import chain, product
from pathlib import Path
from typing import Collection, Sequence

import numpy as np
import pandas as pd

from ..model import DemandMatrix, DistrictPoint, PointIn2D, Station
from ..model.type import DistrictName, DistrictPointId, Meter, StationName
from ..plan import LinePlanningParameters
from ..utils import skip_one_line_in_file
from .paths import ScenarioPaths
from .point import calculate_distance_in_m


def _load_all_district_points(path_to_demand_district_points: Path) -> tuple[DistrictPoint, ...]:
    """
    Load all district points. From file convert to DistrictPoints.
    :param path_to_demand_district_points: str, path and name of the file
    :return: tuple[DistrictPoints, ...], tuple of all the district points
    """
    with open(path_to_demand_district_points, encoding="utf-8") as file:
        skip_one_line_in_file(file)
        raw_demand_points = pd.read_csv(file, sep=",", encoding="utf-8", dtype=str)

    return tuple(
        DistrictPoint(
            district_name=row.BEZIRKE,
            position=PointIn2D(lat=float(row.YCOORD), long=float(row.XCOORD)),
            id=DistrictPointId(str(uuid.uuid4())),
        )
        for row in raw_demand_points.itertuples(index=False)
        if not pd.isnull(row.BEZIRKE)
    )


def load_demand_matrix(
    stations: Sequence[Station], parameters: LinePlanningParameters, paths: ScenarioPaths
) -> DemandMatrix:
    """
    Load demand matrix.
    :param stations: Sequence[Station], sequence of bus stations
    :param parameters: LinePlanningParameters, parameters for the line planning problem
    :param paths: ScenarioPaths, paths in the scenario
    :return: DemandMatrix, an alphabetically sorted demand matrix, with origin stations,
        destination stations, and demand between them
    """
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
    all_district_points: Collection[DistrictPoint], stations: Sequence[Station], association_radius: Meter
) -> None:
    """
    Associate each district point with the nearest station. if the distance between
        district point and station is within the radius, assign the district to the station.
    :param all_district_points: Collection[DistrictPoints], the collection of all district points
    :param stations: Sequence[Station], sequence of all the stations
    :param association_radius: int, specified radius around stations
    """
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
    demand_between_district_points: dict[DistrictPointId, dict[DistrictPointId, float]], stations: Collection[Station]
) -> dict[StationName, dict[StationName, float]]:
    """
    Mao the demand between districts to demand between stations.
    :param demand_between_district_points: dict[str, dict[str, float]], a dict where the key
        is the origin district, the value is a nested dict of destined district and demand
        between them
    :param stations: Collection[Station], collection of stations
    :return: dict[str, dict[str, float]], a dict where the key is the origin station, the
        value is a nested dict of the destined station and demand between two stations
    """
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
    from_station_to_other_stations: dict[StationName, dict[StationName, float]],
) -> dict[StationName, dict[StationName, float]]:
    """
    Sort the dictionary alphabetically based on origin names and destination names.
    :param from_station_to_other_stations: dict[str, dict[str, float]], original dict
    :return: dict[str, dict[str, float]], sorted dict
    """
    return {
        origin_key: dict(sorted(demand.items(), key=lambda x: x[0]))
        for origin_key, demand in sorted(from_station_to_other_stations.items(), key=lambda x: x[0])
    }


def _distribute_demand_between_districts(
    covered_district_points: Collection[DistrictPoint],
    demand_scale: float,
    demanded_relations: dict[tuple[DistrictName, DistrictName], float],
    stations_per_district: dict[DistrictName, int],
) -> dict[DistrictPointId, dict[DistrictPointId, float]]:
    """
    Distribute the demand between districts.
    :param covered_district_points: Collection[DistrictPoints], collection of the district points
    :param demand_scale: float, a scaling factor
    :param demanded_relations: dict[tuple[str, str], float], the original demand between districts
    :param stations_per_district: dict[str, int], number of stations in each district
    :return: dict[str, dict[str, float]], demand between original and destination districts
    """
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


def _load_all_demanded_relations(path_to_demand: Path) -> dict[tuple[DistrictName, DistrictName], float]:
    """
    Load all the origins and destinations with the demand between them.
    :param path_to_demand: str, path and name of the file
    :return: dict[tuple[str, str], float], a dict where that key is origin and destination,
        and value is the demand between them
    """
    with open(path_to_demand, encoding="utf-8") as file:
        skip_one_line_in_file(file)
        raw_demand = pd.read_csv(file, sep=",", encoding="utf-8", dtype=str)
        return {
            (DistrictName(relation.FROM), DistrictName(relation.TO)): round(float(relation.DEMAND) * 1.87, 4)
            for relation in raw_demand.itertuples(index=False)
        }
