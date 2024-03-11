from __future__ import annotations

from itertools import chain
from typing import Collection

import numpy as np
import plotly.graph_objects as go
from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from ..model import DemandMatrix, Station
from ._background import PlotBackground
from ._convert import shift_line_perpendicular, wgs84_to_lv03


def create_station_and_demand_plot(stations: Collection[Station], plot_background: PlotBackground) -> Figure:
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


# pylint: disable=too-many-locals
def create_od_plot(od_matrix: DemandMatrix, stations: Collection[Station]) -> go.Figure:
    """
    Create a plot of the origin-destination matrix with a slider for dynamically adjusting the minimum demand threshold.
    :param od_matrix: DemandMatrix, the origin-destination matrix
    :param stations: Collection[Station], the collection of stations
    :return: go.Figure, the plotly figure
    """
    station_coordinates = {
        station.name: wgs84_to_lv03(station.center_position.lat, station.center_position.long) for station in stations
    }

    # Pre-calculate min and max pax for slider range and normalization
    min_pax = min(chain.from_iterable(v.values() for v in od_matrix.matrix.values()))
    delta_pax = max(chain.from_iterable(v.values() for v in od_matrix.matrix.values())) - min_pax

    pax_counts = []
    figure = go.Figure()
    for origin, destination, pax in od_matrix.all_od_pairs():
        o_coordinates, d_coordinates = station_coordinates[origin], station_coordinates[destination]
        shifted_line = shift_line_perpendicular(
            o_coordinates[0],
            o_coordinates[1],
            d_coordinates[0],
            d_coordinates[1],
            np.sqrt((o_coordinates[0] - d_coordinates[0]) ** 2 + (o_coordinates[1] - d_coordinates[1]) ** 2) * 0.05,
        )
        shifted_midpoint = ((shifted_line[0] + shifted_line[2]) * 0.5, (shifted_line[1] + shifted_line[3]) * 0.5)
        figure.add_trace(
            go.Scatter(
                x=[o_coordinates[0], shifted_midpoint[0], d_coordinates[0]],
                y=[o_coordinates[1], shifted_midpoint[1], d_coordinates[1]],
                mode="lines",
                line={"width": (3 + 17 * (pax - min_pax) / delta_pax), "color": "limegreen", "shape": "spline"},
                opacity=0.27,
                showlegend=False,
                visible=True,
                hovertext=f"{origin} to {destination}: {pax:.2f} pax",
            )
        )
        pax_counts.append(pax)

    # Add station markers (always visible)
    figure.add_trace(
        go.Scatter(
            x=[x for x, _ in station_coordinates.values()],
            y=[y for _, y in station_coordinates.values()],
            mode="markers",
            marker={"color": "black", "size": 10},
            name="Stations",
            text=list(station_coordinates.keys()),
            hoverinfo="text",
            visible=True,
        )
    )

    # Define steps for the slider
    pax_counts.sort()
    # sample 10 thresholds from the sorted list of passenger counts
    steps = []
    for threshold in pax_counts[:: len(pax_counts) // 11][:10]:
        visible_traces = [passengers >= threshold for _, _, passengers in od_matrix.all_od_pairs()] + [True]
        steps.append({"method": "update", "args": [{"visible": visible_traces}], "label": f"{threshold:.2f}"})

    figure.update_layout(
        sliders=[{"active": 0, "currentvalue": {"prefix": "Minimum pax: "}, "pad": {"t": 50}, "steps": steps}],
        title="Origin-Destination Plot with Demand Slider",
        showlegend=False,
        xaxis_title="Easting [m]",
        yaxis_title="Northing [m]",
        hovermode="closest",
        paper_bgcolor="lightgrey",
        plot_bgcolor="lightgrey",
    )
    return figure
