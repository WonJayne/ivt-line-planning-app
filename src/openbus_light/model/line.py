from typing import NamedTuple

from .direction import Direction
from .type import Capacity, LineFrequency, LineName, LineNr


class BusLine(NamedTuple):
    number: LineNr
    name: LineName
    direction_a: Direction
    direction_b: Direction
    capacity: Capacity
    permitted_frequencies: tuple[LineFrequency, ...]
