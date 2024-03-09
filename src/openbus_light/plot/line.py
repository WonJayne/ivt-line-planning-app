from collections.abc import Collection
from itertools import chain

import matplotlib.pyplot as plt
import numpy as np
from plotly.graph_objs import graph_objs as go

from openbus_light.model import BusLine, Direction, Station
from openbus_light.plot._background import PlotBackground
from openbus_light.plot._cmap import ColorMap
from openbus_light.plot._convert import wgs84_to_lv03


def create_station_and_line_plot(
    stations: Collection[Station], lines: Collection[BusLine], plot_background: PlotBackground
) -> plt.Figure:
    """
    Create a plot showing the public transport network with stations and lines.

    Args:
        stations (list): A list of Station objects with center_position attributes.
        lines (list): A list of BusLine objects with direction_a and direction_b attributes.
        plot_background (PlotBackground): An object with path_to_image and bounding_box attributes for background image.

    Returns:
        matplotlib.figure.Figure: The figure object containing the network plot.
    """
    figure, axis = plt.subplots(figsize=(10, 10))
    axis.imshow(plt.imread(plot_background.path_to_image), zorder=0, extent=plot_background.bounding_box)

    # Plot stations
    center_lookup = {station.name: station.center_position for station in stations}
    for station in stations:
        axis.scatter(
            station.center_position.long, station.center_position.lat, zorder=1, alpha=1, c="k", s=20, label="Stations"
        )

    for direction in chain.from_iterable((line.direction_a, line.direction_b) for line in lines):
        axis.plot(
            [center_lookup[s_name].long for s_name in direction.station_sequence],
            [center_lookup[s_name].lat for s_name in direction.station_sequence],
            zorder=2,
            alpha=0.5,
            c="b",
        )
    # Optional: Customize the plot
    axis.set_title("Public Transport Network")
    axis.set_xlabel("Longitude")
    axis.set_ylabel("Latitude")

    return figure


def plot_lines_in_swiss_coordinates(
    stations: Collection[Station], lines: Collection[BusLine], cmap: None | ColorMap = None
) -> go.Figure:
    """
    Create a plot showing the public transport network with stations and lines in Swiss coordinates.

    Args:
        stations (list): A list of Station objects with center_position attributes.
        lines (list): A list of BusLine objects with direction_a and direction_b attributes.
        cmap (ColorMap): An object with color attributes for the lines.

    Returns:
        plotly.graph_objs.graph_objs.Figure: The figure object containing the network plot.

    """
    figure = go.Figure()

    center_lookup = {}
    for station in stations:
        center_lookup[station.name] = wgs84_to_lv03(station.center_position.lat, station.center_position.long)

    figure.add_trace(
        go.Scatter(
            x=[x_ for x_, _ in center_lookup.values()],
            y=[y_ for _, y_ in center_lookup.values()],
            mode="markers",
            marker={"size": 10, "color": "black"},
            name="Stations",
            text=[station.name for station in stations],
            hoverinfo="text",
        )
    )

    line_direction_pairs = tuple(
        chain.from_iterable(((line, line.direction_a), (line, line.direction_b)) for line in lines)
    )

    # Generate offsets to distinguish between lines/line_direction_pairs
    offsets: list[float] = np.linspace(-10, 10, len(line_direction_pairs)).tolist()

    # Plot lines with offsets for visibility
    for (_line, _direction), offset in zip(line_direction_pairs, offsets):
        _line: BusLine  # type: ignore
        _direction: Direction  # type: ignore
        figure.add_trace(
            go.Scatter(
                x=[center_lookup[a][0] + offset for a in _direction.station_sequence],
                y=[center_lookup[a][1] + offset for a in _direction.station_sequence],
                mode="lines",
                line={"color": ColorMap[_line.name] if cmap is not None else "blue", "width": 2},  # type: ignore
                name=f"Line {_line.number} {_direction.name}<br> At {_line.permitted_frequencies}",
                text=[
                    f"{a} to {b}, Line {_line.number} {_direction.name}" for a, b in _direction.station_names_as_pairs
                ],
                hoverinfo="text",
                legendgroup=f"Line {_line.number} {_direction.name}",
            )
        )

    # Optional: Customize the plot
    figure.update_layout(
        title="Public Transport Network, Swiss Coordinates",
        xaxis_title="Easting",
        yaxis_title="Northing",
        showlegend=True,
    )
    return figure
