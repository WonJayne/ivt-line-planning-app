"""Simple container for background map information."""

from typing import NamedTuple


class PlotBackground(NamedTuple):
    """Location of the background image and its coordinates."""

    path_to_image: str
    bounding_box: tuple[float, float, float, float]
