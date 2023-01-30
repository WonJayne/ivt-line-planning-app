from datetime import timedelta
from typing import NamedTuple

from .station import Station


class WalkableDistance(NamedTuple):
    starting_at: Station
    ending_at: Station
    walking_time: timedelta
