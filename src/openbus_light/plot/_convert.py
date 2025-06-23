"""Coordinate conversion helpers used by the plotting routines."""

import math

from numba import njit

BERN_LAT_DEG = 46.9524055556  # 169028.66 / 3600
BERN_LON_DEG = 7.4395833333  # 26782.5 / 3600

LV03_EAST_A0 = 600072.37
LV03_EAST_A1 = 211455.93
LV03_EAST_A2 = -10938.51
LV03_EAST_A3 = -0.36
LV03_EAST_A4 = -44.54

LV03_NORTH_B0 = 200147.07
LV03_NORTH_B1 = 308807.95
LV03_NORTH_B2 = 3745.25
LV03_NORTH_B3 = 76.63
LV03_NORTH_B4 = -194.56
LV03_NORTH_B5 = 119.79


def wgs84_to_lv03(lat: float, lon: float) -> tuple[float, float]:
    """
    Convert WGS84 coordinates (latitude, longitude) to Swiss coordinate system LV03 (CH1903).

    Args:
        lat (float): Latitude in decimal degrees.
        lon (float): Longitude in decimal degrees.

    Returns:
        tuple: A tuple containing the converted coordinates (east, north) in the Swiss coordinate system LV03.
    """

    # Convert degrees to seconds (arc)
    # Source: swisstopo CH1903 transformation formula
    lat_sec = (lat - BERN_LAT_DEG) * 3600
    lon_sec = (lon - BERN_LON_DEG) * 3600

    # Auxiliary values (% Bern)
    lat_aux = lat_sec / 10000.0
    lon_aux = lon_sec / 10000.0

    # Calculate easting (y)
    east = (
        LV03_EAST_A0
        + LV03_EAST_A1 * lon_aux
        + LV03_EAST_A2 * lon_aux * lat_aux
        + LV03_EAST_A3 * lon_aux * lat_aux**2
        + LV03_EAST_A4 * lon_aux**3
    )

    # Calculate northing (x)
    north = (
        LV03_NORTH_B0
        + LV03_NORTH_B1 * lat_aux
        + LV03_NORTH_B2 * lon_aux**2
        + LV03_NORTH_B3 * lat_aux**2
        + LV03_NORTH_B4 * lon_aux**2 * lat_aux
        + LV03_NORTH_B5 * lat_aux**3
    )

    return east, north


@njit
def shift_line_perpendicular(
    x_1: float, y_1: float, x_2: float, y_2: float, shift_distance: float
) -> tuple[float, float, float, float]:
    dx = x_1 - x_2
    dy = y_1 - y_2
    rotation_angle = math.atan2(dy, dx) - math.pi / 2
    x_s1 = x_1 + math.cos(rotation_angle) * shift_distance
    x_s2 = x_2 + math.cos(rotation_angle) * shift_distance
    y_s1 = y_1 + math.sin(rotation_angle) * shift_distance
    y_s2 = y_2 + math.sin(rotation_angle) * shift_distance
    return x_s1, y_s1, x_s2, y_s2
