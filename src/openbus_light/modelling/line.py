from dataclasses import dataclass

from .direction import Direction


@dataclass(frozen=True)
class BusLine:
    number: int
    direction_a: Direction
    direction_b: Direction
    regular_capacity: int
    permitted_frequencies: tuple[int, ...]
