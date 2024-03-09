from collections import defaultdict
from typing import Collection, Literal, Mapping, NamedTuple, Sequence

import numpy as np
from matplotlib import pyplot as plt
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
    pairs_a = [_StationPair(*pair) for pair in bus_line.direction_a.station_names_as_pairs]
    pairs_b = [_StationPair(b, a) for a, b in bus_line.direction_b.station_names_as_pairs]
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


def plot_usage_for_each_direction(
    line: BusLine, pax_by_link_and_direction: Mapping[Direction, Sequence[PassengersPerLink]]
) -> go.Figure:
    aligned_a, aligned_b = _create_alignment_of_stop_sequences(line)
    count_in_direction_a = map_passenger_count_to_station_pairs(aligned_a, pax_by_link_and_direction[line.direction_a])
    count_in_direction_b = map_passenger_count_to_station_pairs(aligned_b, pax_by_link_and_direction[line.direction_b])

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
            marker_color="lightblue",
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
            marker_color="blue",
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
            marker_color="pink",
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
            marker_color="red",
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


def map_passenger_count_to_station_pairs(
    aligned_station_pairs: Sequence[_StationPair | None], passengers_in_direction_a: Sequence[PassengersPerLink]
) -> tuple[float, ...]:
    pax_lookup = {
        _StationPair(section.start_station, section.end_station): section.pax for section in passengers_in_direction_a
    }
    return tuple(pax_lookup.pop(section) if section in pax_lookup else np.NAN for section in aligned_station_pairs)


def plot_available_vs_used_capacity_per_link(
    passengers_per_link: Mapping[BusLine, Mapping[Direction, Sequence[PassengersPerLink]]],
    sort_criteria: Literal["pax", "capacity"],
) -> go.Figure:
    data_in_sorted_direction, data_in_other_direction = _get_data_sorted_by_direction(passengers_per_link)
    sorted_count = _create_sorted_total_count(
        data_in_sorted_direction, data_in_other_direction, sort_criteria=sort_criteria
    )

    # Preparing data for plotting
    values_in_direction_a = tuple(
        data_in_sorted_direction[key] if key in data_in_sorted_direction else tuple() for key, _ in sorted_count
    )
    values_in_direction_b = tuple(
        data_in_other_direction[key] if key in data_in_other_direction else tuple() for key, _ in sorted_count
    )

    # Create subplot figure with 1 row and 2 columns
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=("Direction A->B", "Direction B->A"))

    # Capacity and pax for direction A->B
    fig.add_trace(
        go.Bar(
            x=[sum(value[2] for value in values) for values in values_in_direction_a],
            y=[key for key, _ in sorted_count],
            name="Capacity A->B",
            orientation="h",
            marker_color="rgba(100, 200, 255, 0.6)",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=[sum(value[1] for value in values) for values in values_in_direction_a],
            y=[key for key, _ in sorted_count],
            name="Pax A->B",
            orientation="h",
            marker_color="rgba(50, 100, 255, 0.9)",
        ),
        row=1,
        col=1,
    )

    # Capacity and pax for direction B->A
    fig.add_trace(
        go.Bar(
            x=[sum(value[1] for value in values) for values in values_in_direction_b],
            y=[key for key, _ in sorted_count],
            name="Pax B->A",
            orientation="h",
            marker_color="rgba(255, 50, 50, 0.9)",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            x=[sum(value[2] for value in values) for values in values_in_direction_b],
            y=[key for key, _ in sorted_count],
            name="Capacity B->A",
            orientation="h",
            marker_color="rgba(255, 150, 150, 0.6)",
        ),
        row=1,
        col=2,
    )

    # Update layout for a consistent look and shared y-axis
    fig.update_layout(
        barmode="overlay",  # Overlay bars to show capacity vs pax
        title_text="Available vs Used Capacity Per Link",
        xaxis_title="Pax/Capacity [n]",
        xaxis2_title="Pax/Capacity [n]",
        yaxis_title="Line Segments",
    )

    return fig


def _add_bar_plot_to_axis(values_to_add: Collection[float], left_axis: plt.Axes, label: str) -> plt.Axes:
    return left_axis.barh(tuple(range(len(values_to_add))), values_to_add, label=label)


def _create_sorted_total_count(
    data_in_sorted_direction: Mapping[tuple[StationName, StationName], list[tuple[str, float, int]]],
    data_in_other_direction: Mapping[tuple[StationName, StationName], list[tuple[str, float, int]]],
    sort_criteria: Literal["pax"] | Literal["capacity"],
) -> list[tuple[tuple[StationName, StationName], int]]:
    total_count = {}
    if sort_criteria.casefold() == "pax":
        sort_index = 1
    elif sort_criteria.casefold() == "capacity":
        sort_index = 2
    else:
        raise NotImplementedError(f"{sort_criteria=} not available")

    for key, values in data_in_sorted_direction.items():
        total_count[key] = sum(data[sort_index] for data in values)  # type: ignore
        if key in data_in_other_direction:
            total_count[key] += sum(data[sort_index] for data in data_in_other_direction[key])  # type: ignore
    for key, values in data_in_other_direction.items():
        if key in data_in_sorted_direction:
            continue
        total_count[key] = sum(data[sort_index] for data in values)  # type: ignore
    return sorted(total_count.items(), key=lambda x: x[1])  # type: ignore


def _get_data_sorted_by_direction(
    passengers_per_line: Mapping[BusLine, Mapping[Direction, Sequence[PassengersPerLink]]]
) -> tuple[
    dict[tuple[StationName, StationName], list[tuple[str, float, int]]],
    dict[tuple[StationName, StationName], list[tuple[str, float, int]]],
]:
    passengers_in_sorted_direction, passengers_in_other_direction = defaultdict(list), defaultdict(list)
    for line, passengers_per_direction in passengers_per_line.items():
        capacity = line.capacity * line.permitted_frequencies[0]
        for direction, passengers_per_link in passengers_per_direction.items():
            line_and_direction = f"{line.number}->{direction.name}"
            for link in passengers_per_link:
                data = (line_and_direction, link.pax, capacity)
                is_in_sorted_order = link.start_station == sorted((link.start_station, link.start_station))[0]
                if is_in_sorted_order:
                    passengers_in_sorted_direction[link.start_station, link.end_station].append(data)
                    continue
                passengers_in_other_direction[link.end_station, link.start_station].append(data)
    return dict(passengers_in_sorted_direction), dict(passengers_in_other_direction)
