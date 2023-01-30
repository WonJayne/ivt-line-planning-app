from __future__ import annotations

from itertools import chain
from typing import Collection, NamedTuple

from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from ..model import Station


class PlotBackground(NamedTuple):
    path_to_image: str
    bounding_box: tuple[float, float, float, float]


def create_plot(stations: Collection[Station], plot_background: PlotBackground) -> Figure:
    district_points = tuple(chain.from_iterable(station.district_points for station in stations))
    figure, axis = plt.subplots(figsize=(8, 8))
    axis.set_title("Default Title, if we see this in your report, it's not so good")
    axis.set_xlim(plot_background.bounding_box[0], plot_background.bounding_box[1])
    axis.set_ylim(plot_background.bounding_box[2], plot_background.bounding_box[3])
    background_image = plt.imread(plot_background.path_to_image)
    axis.imshow(background_image, zorder=0, extent=plot_background.bounding_box)
    axis.scatter(
        [point.position.long for point in district_points],
        [point.position.lat for point in district_points],
        zorder=1,
        alpha=0.51,
        c="b",
        s=5,
    )
    axis.scatter(
        [station.center_position.long for station in stations],
        [station.center_position.lat for station in stations],
        zorder=2,
        alpha=0.5,
        c="r",
        s=10,
    )
    axis.scatter(
        [station.center_position.long for station in stations],
        [station.center_position.lat for station in stations],
        zorder=4,
        alpha=1,
        c="r",
        s=5,
    )
    axis.lines.extend(
        (
            Line2D(
                [station.center_position.long, point.position.long],
                [station.center_position.lat, point.position.lat],
                linewidth=0.75,
                # linestyle="--",
                color=[0, 0, 1],
                alpha=0.5,
                zorder=3,
            )
            for station in stations
            for point in station.district_points
        )
    )
    return figure
