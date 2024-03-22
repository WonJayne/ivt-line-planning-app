from typing import NamedTuple

import pandas as pd

from openbus_light.model.type import CirculationId, DirectionName, LineName, StationName, TripNr


class RecordedTrip(NamedTuple):
    line: LineName
    direction: DirectionName
    trip_nr: TripNr
    circulation_id: CirculationId
    start: StationName
    end: StationName
    stop_count: int
    record: pd.DataFrame
