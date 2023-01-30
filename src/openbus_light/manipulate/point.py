from math import atan2, cos, radians, sin, sqrt

from numba import njit

from ..model import PointIn2D

R = 6373000.0


@njit(cache=True)
def calculate_distance_in_m(point_1: PointIn2D, point_2: PointIn2D) -> float:
    d_lon = radians(point_2.long) - radians(point_1.long)  # lon2 - lon1
    d_lat = radians(point_2.lat) - radians(point_1.lat)  # lat2 - lat1

    value_a = sin(d_lat / 2) ** 2 + cos(point_1.lat) * cos(point_2.lat) * sin(d_lon / 2) ** 2
    value_c = 2 * atan2(sqrt(value_a), sqrt(1 - value_a))

    return R * value_c
