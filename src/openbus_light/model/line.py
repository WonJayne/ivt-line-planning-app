from typing import NamedTuple

from .direction import Direction
from .type import LineFrequency, LineName, LineNr, VehicleCapacity


class BusLine(NamedTuple):
    number: LineNr
    name: LineName
    direction_a: Direction
    direction_b: Direction
    capacity: VehicleCapacity
    permitted_frequencies: tuple[LineFrequency, ...]
