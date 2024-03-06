from typing import NamedTuple

from .direction import Direction
from .type import Capacity, LineFrequency, LineName, LineNr


class BusLine(NamedTuple):
    number: LineNr
    line_name: LineName
    direction_a: Direction
    direction_b: Direction
    regular_capacity: Capacity
    permitted_frequencies: tuple[LineFrequency, ...]
