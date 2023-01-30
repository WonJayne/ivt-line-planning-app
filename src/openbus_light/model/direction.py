from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property

from ..utils import pairwise


@dataclass(frozen=True)
class Direction:
    name: str
    station_names: tuple[str, ...]
    trip_times: tuple[timedelta, ...]

    def __post_init__(self) -> None:
        if not (
            len(self.station_names) - 1 == len(self.trip_times) or len(self.station_names) == len(self.trip_times) == 0
        ):
            raise RuntimeError(f"Invalid number of stops and trip times in {self}")

    @cached_property
    def station_count(self) -> int:
        return len(self.station_names)

    @property
    def stations_as_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(pairwise(self.station_names))

    def trip_time_per_stop_pair(self) -> tuple[tuple[tuple[str, str], timedelta], ...]:
        return tuple(((s, t), dt) for (s, t), dt in zip(self.stations_as_pairs, self.trip_times))
