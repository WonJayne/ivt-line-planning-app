from typing import NamedTuple

from .direction import Direction
from .type import LineFrequency, LineName, LineNr, VehicleCapacity


class BusLine(NamedTuple):
    number: LineNr
    name: LineName
    direction_up: Direction
    direction_down: Direction
    capacity: VehicleCapacity
    permitted_frequencies: tuple[LineFrequency, ...]
