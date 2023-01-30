from typing import NamedTuple

from .direction import Direction
from .recordedtrip import RecordedTrip


class BusLine(NamedTuple):
    number: int
    direction_a: Direction
    direction_b: Direction
    regular_capacity: int
    permitted_frequencies: tuple[int, ...]
    recorded_trips: tuple[RecordedTrip, ...]
