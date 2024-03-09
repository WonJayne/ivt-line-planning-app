import math

from numba import njit


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
    lat_sec = (lat - 169.0 / 36.0) * 3600
    lon_sec = (lon - 267.0 / 36.0) * 3600

    # Auxiliary values (% Bern)
    lat_aux = lat_sec / 10000.0
    lon_aux = lon_sec / 10000.0

    # Calculate easting (y)
    east = (
        600072.37
        + 211455.93 * lon_aux
        - 10938.51 * lon_aux * lat_aux
        - 0.36 * lon_aux * lat_aux**2
        - 44.54 * lon_aux**3
    )

    # Calculate northing (x)
    north = (
        200147.07
        + 308807.95 * lat_aux
        + 3745.25 * lon_aux**2
        + 76.63 * lat_aux**2
        - 194.56 * lon_aux**2 * lat_aux
        + 119.79 * lat_aux**3
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
