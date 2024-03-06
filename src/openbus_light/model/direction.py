from dataclasses import dataclass
from datetime import timedelta
from functools import cached_property

from ..utils import pairwise
from .recordedtrip import RecordedTrip
from .type import DirectionName, StationName


@dataclass(frozen=True)
class Direction:
    name: DirectionName
    station_names: tuple[StationName, ...]
    trip_times: tuple[timedelta, ...]
    recorded_trips: tuple[RecordedTrip, ...] = tuple()

    def __post_init__(self) -> None:
        """
        Check the validity of the number of stations and number of trips.
        """
        if not (
            len(self.station_names) - 1 == len(self.trip_times) or len(self.station_names) == len(self.trip_times) == 0
        ):
            raise RuntimeError(f"Invalid number of stops and trip times in {self}")

    @cached_property
    def station_count(self) -> int:
        """
        Count the number of stations.
        :return: int
        """
        return len(self.station_names)

    @property
    def stations_as_pairs(self) -> tuple[tuple[StationName, StationName], ...]:
        """
        Transform each consecutive 2 stations into pairs.
        :return: tuple[tuple[StationName, StationName], ...], pair of stations
        """
        return tuple(pairwise(self.station_names))

    def trip_time_by_pair(self) -> tuple[tuple[tuple[StationName, StationName], timedelta], ...]:
        """
        Get the trip time between each pair of consecutive stations.
        :return: tuple[tuple[tuple[str, str], timedelta], ...], name of the stations in pair
            and trip time between them
        """
        return tuple(((s, t), dt) for (s, t), dt in zip(self.stations_as_pairs, self.trip_times))
