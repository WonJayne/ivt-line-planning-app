from collections import defaultdict
from typing import Collection, Literal, Mapping, Sequence

from matplotlib import pyplot as plt

from openbus_light.model import BusLine, Direction
from openbus_light.plan.result import PassengersPerLink


def plot_available_vs_used_capacity_per_link(
    passengers_per_link: Mapping[BusLine, Mapping[Direction, Sequence[PassengersPerLink]]],
    sort_criteria: Literal["pax"] | Literal["capacity"],
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

    _add_bar_plot_to_axis([sum(value[2] for value in values) for values in values_in_direction], left_axis)
    _add_bar_plot_to_axis([sum(value[1] for value in values) for values in values_in_direction], left_axis)
    _add_bar_plot_to_axis([sum(value[2] for value in values) for values in values_in_other_direction], right_axis)
    _add_bar_plot_to_axis([sum(value[1] for value in values) for values in values_in_other_direction], right_axis)
    left_axis.invert_xaxis()
    return figure


def _add_bar_plot_to_axis(values_to_add: Collection[float], left_axis: plt.Axes) -> None:
    left_axis.barh(tuple(range(len(values_to_add))), values_to_add)


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
