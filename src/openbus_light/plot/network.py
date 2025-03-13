from collections import defaultdict
from itertools import chain
from typing import NamedTuple

import numpy as np
import plotly.graph_objs as go

from openbus_light.model import LineNr
from openbus_light.plan import LinePlanningNetwork, LPNLink
from openbus_light.plan.network import Activity, NodeName
from openbus_light.plan.result import LPPSolution, PassengersPerLink
from openbus_light.plot._cmap import ColorMap, create_continuous_colormap, rgba_to_plotly_string
from openbus_light.plot._convert import shift_line_perpendicular, wgs84_to_lv03


class _Data(NamedTuple):
    """
    A named tuple for the data of the plot.
    Attributes:
        x (list[float | None]): The x-coordinates of the plot.
        y (list[float | None]): The y-coordinates of the plot.
        text (list[str | None]): The text of the plot.
        color (list[str | None]): The color of the plot.
    """

    x: list[float | None]
    y: list[float | None]
    text: list[str | None]
    color: list[str | None]


def plot_network_in_swiss_coordinate_grid(
    network: LinePlanningNetwork, cmap: None | ColorMap[LineNr] = None
) -> go.Figure:
    """
    Plot the network in Swiss coordinates.
    :param network: The network to be plotted.
    :param cmap: ColorMap[LineNr], a colormap for the lines.
    :return: go.Figure, the plotly figure.
    """
    projected_coordinates = tuple(_project_and_shift_network_nodes(network).values())

    if cmap is None:
        color = ["black"] * len(network.all_nodes)
    else:
        color = [cmap[node.line_nr] if node.line_nr is not None else "black" for node in network.all_nodes]
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[x for x, _ in projected_coordinates],
            y=[y for _, y in projected_coordinates],
            mode="markers",
            marker={"size": 10, "color": color},
            name="Stations",
            text=[
                (
                    f"{node.name}"
                    if node.line_nr is None
                    else f"{node.name},<br>L:{node.line_nr},<br>D:{node.direction_name}"
                )
                for node in network.all_nodes
            ],
            hoverinfo="text",
        )
    )

    by_name: dict[str, _Data] = defaultdict(lambda: _Data([], [], [], []))
    for (s, t), link in zip((es.tuple for es in network.graph.es), network.all_links):
        link: LPNLink  # type: ignore
        name = link.activity.name if link.line_nr is None else f"L:{link.line_nr}"
        start_point, end_point = projected_coordinates[s], projected_coordinates[t]
        if link.activity == Activity.IN_VEHICLE:
            by_name[name].x.extend((start_point[0], 0.5 * (start_point[0] + end_point[0]), end_point[0], None))
            by_name[name].y.extend((start_point[1], 0.5 * (start_point[1] + end_point[1]), end_point[1], None))
        else:
            offset = np.sqrt((start_point[0] - end_point[0]) ** 2 + (start_point[1] - end_point[1]) ** 2) * 0.1
            shifted_line = shift_line_perpendicular(start_point[0], start_point[1], end_point[0], end_point[1], offset)
            by_name[name].x.extend((start_point[0], (shifted_line[0] + shifted_line[2]) * 0.5, end_point[0], None))
            by_name[name].y.extend((start_point[1], (shifted_line[1] + shifted_line[3]) * 0.5, end_point[1], None))
        if link.line_nr is None:
            by_name[name].text.extend((f"{link.activity.name} <br>dt: {link.duration.total_seconds()} sec<br>",) * 4)
        else:
            by_name[name].text.extend(
                (f"{link.activity.name} <br>dt: {link.duration.total_seconds()} sec<br>L: {link.line_nr}",) * 4
            )
        by_name[name].color.extend(
            (cmap[link.line_nr] if cmap is not None and link.line_nr is not None else "black",) * 4
        )

    for name, data in by_name.items():
        figure.add_trace(
            go.Scatter(
                x=data.x,
                y=data.y,
                mode="lines",
                line={
                    "width": 1,
                    "color": data.color[0],
                    "shape": "spline",
                    "dash": "dot" if name == Activity.WALKING.name else "solid",
                },
                name=name,
                text=data.text,
                hoverinfo="text",
                legendgroup=name,
                showlegend=True,
            )
        )
    return figure


def _project_and_shift_network_nodes(network: LinePlanningNetwork) -> dict[NodeName, tuple[float, float]]:
    """
    Project the network nodes to Swiss coordinates and shift them to avoid overlap.
    :param network: The network to be plotted.
    :return: dict, a mapping of node names to Swiss coordinates.
    """
    line_direction_tuples = sorted(
        {(node.direction_name, node.line_nr) for node in network.all_nodes if node.line_nr is not None}
    )
    # create circular offsets for each line
    x_offsets = np.cos(np.linspace(0, 2 * np.pi, len(line_direction_tuples) + 1)[:-1])
    y_offsets = np.sin(np.linspace(0, 2 * np.pi, len(line_direction_tuples) + 1)[:-1])
    x_offset_by_line: dict[tuple[None | str, None | LineNr], float] = {
        key: x_offsets[i] * 10 for i, key in enumerate(line_direction_tuples)
    }
    y_offset_by_line: dict[tuple[None | str, None | LineNr], float] = {
        key: y_offsets[i] * 10 for i, key in enumerate(line_direction_tuples)
    }
    x_offset_by_line[None, None] = y_offset_by_line[None, None] = 0
    generator = (wgs84_to_lv03(node.coordinates.lat, node.coordinates.long) for node in network.all_nodes)
    return {
        node.name: (
            x + x_offset_by_line[node.direction_name, node.line_nr],
            y + y_offset_by_line[node.direction_name, node.line_nr],
        )
        for (x, y), node in zip(generator, network.all_nodes)
    }


# pylint: disable=too-many-locals
def plot_network_usage_in_swiss_coordinates(
    network: LinePlanningNetwork, solution: LPPSolution, scale_with_capacity: bool
) -> go.Figure:
    """
    Plot the network usage in Swiss coordinates.
    :param network: The network to be plotted.
    :param solution: The solution to be plotted.
    :param scale_with_capacity: If True, the passenger count is scaled by the capacity of the line.
    :return: go.Figure, the plotly figure.
    """
    reduced = network.shallow_copy()
    del network
    active_lines = {line.number for line in solution.active_lines}
    reduced.graph.delete_edges([i for i, link in enumerate(reduced.all_links) if link.line_nr not in active_lines])

    all_passenger_per_link: tuple[PassengersPerLink, ...] = tuple(
        chain.from_iterable(ppl for group in solution.passengers_per_link.values() for ppl in group.values())
    )
    cmap_name = "hot"
    if scale_with_capacity:
        capacity_by_line = {
            LineNr(line.number): line.capacity * line.permitted_frequencies[0] for line in solution.active_lines
        }
        continuous_scale, normaliser = create_continuous_colormap(0, 1, cmap_name)
        max_pax = 1.0
    else:
        max_pax = max(all_passenger_per_link, key=lambda ppl: ppl.pax).pax if len(all_passenger_per_link) > 0 else 100
        continuous_scale, normaliser = create_continuous_colormap(0, max_pax, cmap_name)
        capacity_by_line = {}  # should raise a key error if used, deliberately not used
    passengers_by_end_nodes = {(rel.start_node, rel.end_node): rel.pax for rel in all_passenger_per_link}
    node_names = reduced.all_node_names
    figure = go.Figure()
    projected_coordinates = _project_and_shift_network_nodes(reduced)
    already_seen_names = set()
    for (s, t), link in zip((es.tuple for es in reduced.graph.es), reduced.all_links):
        link: LPNLink  # type: ignore
        use_a_straight_line = link.activity == Activity.IN_VEHICLE
        start_name, end_name = node_names[s], node_names[t]
        if use_a_straight_line:
            count = passengers_by_end_nodes[(start_name, end_name)]
            if scale_with_capacity:
                assert link.line_nr is not None
                count = count / capacity_by_line[link.line_nr]
        else:
            count = 0
        start, end = projected_coordinates[start_name], projected_coordinates[end_name]
        if use_a_straight_line:
            x = [start[0], 0.5 * (start[0] + end[0]), end[0], None]
            y = [start[1], 0.5 * (start[1] + end[1]), end[1], None]
            text = [f"{count:.2f}" for _ in range(4)]
        else:
            offset = np.sqrt((start[0] - end[0]) ** 2 + (start[1] - end[1]) ** 2) * 0.2
            shifted_line = shift_line_perpendicular(start[0], start[1], end[0], end[1], offset)
            x = [start[0], (shifted_line[0] + shifted_line[2]) * 0.5, end[0], None]
            y = [start[1], (shifted_line[1] + shifted_line[3]) * 0.5, end[1], None]
            text = [f"{count:.2f}" for _ in range(4)]
        name = link.activity.name if link.line_nr is None else f"L:{link.line_nr}"
        color = rgba_to_plotly_string(continuous_scale(normaliser(count)))
        figure.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                line={"width": 2, "color": color, "shape": "spline"},
                name=name,
                text=text,
                hoverinfo="text",
                legendgroup=name,
                showlegend=name not in already_seen_names,
            )
        )
        already_seen_names.add(name)

    # Create dummy scatter trace for the color bar
    figure.add_trace(_create_color_bar(cmap_name, 0, max_pax))
    figure.update_layout(coloraxis_colorbar_x=-0.15)
    return figure


def _create_color_bar(cmap_name: str, _min: float, _max: float) -> go.Scatter:
    """
    Create a dummy scatter trace for the color bar.
    :param cmap_name: The name of the colormap.
    :param _min: The minimum value for the color bar.
    :param _max: The maximum value for the color bar.
    :return: go.Scatter, the scatter trace for the color bar.
    """
    assert _min <= _max
    return go.Scatter(
        x=[None],
        y=[None],
        mode="markers",
        marker={
            "size": 1,
            "color": [_min, _max],
            "colorscale": cmap_name,
            "colorbar": {
                "title": "Passengers",
                "tickvals": [_min, _max / 2, _max],
                "ticktext": [f"{_min:.2f}", f"{(_max / 2):.2f}", f"{_max:.2f}"],
                "x": -0.1,
            },
            "showscale": True,
        },
        showlegend=False,
        hoverinfo="none",
    )
