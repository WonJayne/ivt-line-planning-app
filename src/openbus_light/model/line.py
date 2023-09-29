from typing import NamedTuple

from .direction import Direction


class BusLine(NamedTuple):
    number: int
    line_name: str
    direction_a: Direction
    direction_b: Direction
    regular_capacity: int
    permitted_frequencies: tuple[int, ...]
