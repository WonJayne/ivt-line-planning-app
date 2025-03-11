from typing import Mapping, NamedTuple, Sequence

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.container import BarContainer
from plotly.graph_objs import graph_objs as go
from plotly.subplots import make_subplots

from openbus_light.model import BusLine, Direction, StationName
from openbus_light.plan.result import PassengersPerLink


class _StationPair(NamedTuple):
    departing: StationName
    arriving: StationName

    def to_plot_str(self) -> str:
        return f"{self.departing.strip('Winterthur, ')} -> {self.arriving.strip('Winterthur, ')}"

    def to_reverse_plot_str(self) -> str:
        return f"{self.arriving.strip('Winterthur, ')} -> {self.departing.strip('Winterthur, ')}"


def _create_alignment_of_stop_sequences(
    bus_line: BusLine,
) -> tuple[tuple[_StationPair | None, ...], tuple[_StationPair | None, ...]]:
    aligned_a: list[_StationPair | None] = []
    aligned_b: list[_StationPair | None] = []
    pairs_a = [_StationPair(*pair) for pair in bus_line.direction_up.station_names_as_pairs]
    pairs_b = [_StationPair(b, a) for a, b in bus_line.direction_down.station_names_as_pairs]
    pairs_b.reverse()
    i, j = 0, 0
    while i < len(pairs_a) or j < len(pairs_b):
        if i < len(pairs_a) and pairs_a[i] in pairs_b:
            index_b = pairs_b.index(pairs_a[i])
            if j < index_b:
                aligned_a.extend([None] * (index_b - j))
                aligned_b.extend(_StationPair(*pair) for pair in pairs_b[j:index_b])
                j = index_b
            aligned_a.append(_StationPair(*pairs_a[i]))
            aligned_b.append(_StationPair(*pairs_b[j]))
            i += 1
            j += 1
        elif i < len(pairs_a):
            aligned_a.append(_StationPair(*pairs_a[i]))
            aligned_b.append(None)
            i += 1
        elif j < len(pairs_b):
            aligned_a.append(None)
            aligned_b.append(_StationPair(*pairs_b[j]))
            j += 1

    return tuple(aligned_a), (tuple(None if pair is None else _StationPair(pair[1], pair[0]) for pair in aligned_b))


def _map_passenger_count_to_station_pairs(
    aligned_station_pairs: Sequence[_StationPair | None], passengers_in_direction_a: Sequence[PassengersPerLink]
) -> tuple[float, ...]:
    pax_lookup = {
        _StationPair(section.start_station, section.end_station): section.pax for section in passengers_in_direction_a
    }
    return tuple(pax_lookup.pop(section) if section in pax_lookup else np.nan for section in aligned_station_pairs)


def _add_bar_plot_to_axis(values_to_add: Sequence[float], left_axis: plt.Axes, label: str) -> BarContainer:
    return left_axis.barh(tuple(range(len(values_to_add))), values_to_add, label=label)


def plot_usage_for_each_direction(
    line: BusLine, pax_by_link_and_direction: Mapping[Direction, Sequence[PassengersPerLink]]
) -> go.Figure:
    aligned_a, aligned_b = _create_alignment_of_stop_sequences(line)
    count_in_direction_a = _map_passenger_count_to_station_pairs(
        aligned_a, pax_by_link_and_direction[line.direction_up]
    )
    count_in_direction_b = _map_passenger_count_to_station_pairs(
        aligned_b, pax_by_link_and_direction[line.direction_down]
    )

    available_capacity = line.capacity * line.permitted_frequencies[0]

    capacity_a = [available_capacity for _ in count_in_direction_a]
    capacity_b = [available_capacity for _ in count_in_direction_b]

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True)

    fig.add_trace(
        go.Bar(
            x=capacity_a,
            y=[pair.to_plot_str() if pair is not None else None for pair in aligned_a],
            name="Available Capacity A",
            orientation="h",
            marker={"color": "lightblue"},
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=count_in_direction_a,
            y=[pair.to_plot_str() if pair is not None else None for pair in aligned_a],
            name="Used Capacity A",
            orientation="h",
            marker={"color": "blue"},
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=capacity_b,
            y=[pair.to_reverse_plot_str() if pair is not None else None for pair in aligned_b],
            name="Available Capacity B",
            orientation="h",
            marker={"color": "lightcoral"},
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            x=count_in_direction_b,
            y=[pair.to_reverse_plot_str() if pair is not None else None for pair in aligned_b],
            name="Used Capacity B",
            orientation="h",
            marker={"color": "red"},
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        barmode="overlay",
        title_text="Available vs Used Capacity for Each Direction",
        xaxis_title="Pax [n]",
        xaxis2_title="Pax [n]",
        yaxis_title="Line Segment",
    )
    fig.update_yaxes(autorange="reversed")

    return fig
