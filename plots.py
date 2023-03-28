from collections import defaultdict
from typing import Collection, Literal, Mapping, NamedTuple, Sequence

import numpy as np
from matplotlib import pyplot as plt

from openbus_light.model import BusLine, Direction
from openbus_light.plan.result import PassengersPerLink


class StationPair(NamedTuple):
    departing: str
    arriving: str


def _create_alignment_of_stop_sequences(
    bus_line: BusLine,
) -> tuple[tuple[StationPair | None, ...], tuple[StationPair | None, ...]]:
    aligned_a = []
    aligned_b = []
    pairs_a = [StationPair(*pair) for pair in bus_line.direction_a.stations_as_pairs]
    pairs_b = [StationPair(b, a) for a, b in bus_line.direction_b.stations_as_pairs]
    pairs_b.reverse()
    i, j = 0, 0
    while i < len(pairs_a) or j < len(pairs_b):
        if i < len(pairs_a) and pairs_a[i] in pairs_b:
            index_b = pairs_b.index(pairs_a[i])
            if j < index_b:
                aligned_a.extend([None] * (index_b - j))
                aligned_b.extend(StationPair(*pair) for pair in pairs_b[j:index_b])
                j = index_b
            aligned_a.append(StationPair(*pairs_a[i]))
            aligned_b.append(StationPair(*pairs_b[j]))
            i += 1
            j += 1
        elif i < len(pairs_a):
            aligned_a.append(StationPair(*pairs_a[i]))
            aligned_b.append(None)
            i += 1
        elif j < len(pairs_b):
            aligned_a.append(None)
            aligned_b.append(StationPair(*pairs_b[j]))
            j += 1

    return tuple(aligned_a), (tuple(None if pair is None else StationPair(pair[1], pair[0]) for pair in aligned_b))


def __to_str(station_pair: StationPair) -> str:
    return f"{station_pair.departing.strip('Winterthur, ')} -> {station_pair.arriving.strip('Winterthur, ')}"


def plot_available_vs_used_capacity_for_each_direction(
    line: BusLine, passengers_by_link_and_direction: Mapping[Direction, Sequence[PassengersPerLink]]
) -> plt.Figure:
    aligned_a, aligned_b = _create_alignment_of_stop_sequences(line)
    count_in_direction_a = map_passenger_count_to_station_pairs(
        aligned_a, passengers_by_link_and_direction[line.direction_a]
    )
    count_in_direction_b = map_passenger_count_to_station_pairs(
        aligned_b, passengers_by_link_and_direction[line.direction_b]
    )
    figure, (left_axis, right_axis) = plt.subplots(nrows=1, ncols=2, sharey=True)
    available_capacity = line.regular_capacity * line.permitted_frequencies[0]
    bar_container_a = _add_bar_plot_to_axis(
        [np.NAN if np.isnan(count) else available_capacity for count in count_in_direction_a], left_axis, "capacity"
    )
    bar_container_b = _add_bar_plot_to_axis(
        [np.NAN if np.isnan(count) else available_capacity for count in count_in_direction_b], right_axis, "capacity"
    )
    _add_bar_plot_to_axis(count_in_direction_a, left_axis, "pax")
    _add_bar_plot_to_axis(count_in_direction_b, right_axis, "pax")
    left_axis.invert_xaxis()
    left_axis.set_ylabel("Line Segment (Direction A->B)")
    right_y_axis = right_axis.twinx()
    right_y_axis.set_ylabel("Line Segment (Direction B->A)")
    left_axis.set_xlabel("Pax [n]")
    right_axis.set_xlabel("Pax [n]")
    left_axis.set_yticklabels([])
    right_axis.set_yticklabels([])
    right_y_axis.set_yticklabels([])
    left_axis.legend()
    label_offset = 5  # Adjust this value to position the labels correctly
    for bar, station_pair in zip(bar_container_a, aligned_a):
        if station_pair is not None:
            left_axis.text(
                label_offset + bar.get_width(), bar.get_y(), __to_str(station_pair), va="center", ha="right", fontsize=8
            )

    for bar, station_pair in zip(bar_container_b, aligned_b):
        if station_pair is not None:
            right_axis.text(
                bar.get_width() + label_offset, bar.get_y(), __to_str(station_pair), va="center", ha="left", fontsize=8
            )
    return figure


def map_passenger_count_to_station_pairs(
    aligned_station_pairs: Sequence[StationPair], passengers_in_direction_a: Sequence[PassengersPerLink]
) -> tuple[int, ...]:
    pax_lookup = {StationPair(section.start, section.end): section.pax for section in passengers_in_direction_a}
    return tuple(pax_lookup.pop(section) if section in pax_lookup else np.NAN for section in aligned_station_pairs)


def plot_available_vs_used_capacity_per_link(
    passengers_per_link: Mapping[BusLine, Mapping[Direction, Sequence[PassengersPerLink]]],
    sort_criteria: Literal["pax", "capacity"],
) -> plt.Figure:
    data_in_sorted_direction, data_in_other_direction = _get_data_sorted_by_direction(passengers_per_link)
    sorted_count = _create_sorted_total_count(
        data_in_sorted_direction, data_in_other_direction, sort_criteria=sort_criteria
    )

    figure, (left_axis, right_axis) = plt.subplots(nrows=1, ncols=2, sharey=True)

    values_in_direction = tuple(
        data_in_sorted_direction[key] if key in data_in_sorted_direction else tuple() for key, _ in sorted_count
    )
    values_in_other_direction = tuple(
        data_in_other_direction[key] if key in data_in_other_direction else tuple() for key, _ in sorted_count
    )

    _add_bar_plot_to_axis([sum(value[2] for value in values) for values in values_in_direction], left_axis, "capacity")
    _add_bar_plot_to_axis([sum(value[1] for value in values) for values in values_in_direction], left_axis, "pax")
    _add_bar_plot_to_axis(
        [sum(value[2] for value in values) for values in values_in_other_direction], right_axis, "capacity"
    )
    _add_bar_plot_to_axis(
        [sum(value[1] for value in values) for values in values_in_other_direction], right_axis, "pax"
    )
    left_axis.invert_xaxis()
    left_axis.set_ylabel("Line Segment (Direction A->B)")
    right_y_axis = right_axis.twinx()
    right_y_axis.set_ylabel("Line Segment (Direction B->A)")
    left_axis.set_xlabel("Pax [n]")
    right_axis.set_xlabel("Pax [n]")
    left_axis.legend()
    return figure


def _add_bar_plot_to_axis(values_to_add: Collection[float], left_axis: plt.Axes, label: str) -> plt.Axes:
    return left_axis.barh(tuple(range(len(values_to_add))), values_to_add, label=label)


def _create_sorted_total_count(
    data_in_sorted_direction: Mapping[tuple[str, str], list[tuple[str, float, int]]],
    data_in_other_direction: Mapping[tuple[str, str], list[tuple[str, float, int]]],
    sort_criteria: Literal["count"] | Literal["capacity"],
) -> list[tuple[tuple[str, str], int]]:
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
) -> tuple[dict[tuple[str, str], list[tuple[str, float, int]]], dict[tuple[str, str], list[tuple[str, float, int]]]]:
    passengers_in_sorted_direction, passengers_in_other_direction = defaultdict(list), defaultdict(list)
    for line, passengers_per_direction in passengers_per_line.items():
        capacity = line.regular_capacity * line.permitted_frequencies[0]
        for direction, passengers_per_link in passengers_per_direction.items():
            line_and_direction = f"{line.number}->{direction.name}"
            for link in passengers_per_link:
                data = (line_and_direction, link.pax, capacity)
                is_in_sorted_order = link.start == sorted((link.start, link.end))[0]
                if is_in_sorted_order:
                    passengers_in_sorted_direction[link.start, link.end].append(data)
                    continue
                passengers_in_other_direction[link.end, link.start].append(data)
    return dict(passengers_in_sorted_direction), dict(passengers_in_other_direction)
