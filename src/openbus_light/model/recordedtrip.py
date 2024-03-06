from typing import NamedTuple

import pandas as pd

from openbus_light.model.type import CirculationId, StationName, TripNr


class RecordedTrip(NamedTuple):
    number: TripNr
    circulation_id: CirculationId
    start: StationName
    end: StationName
    stop_count: int
    record: pd.DataFrame
