from typing import NamedTuple


class PlotBackground(NamedTuple):
    path_to_image: str
    bounding_box: tuple[float, float, float, float]
