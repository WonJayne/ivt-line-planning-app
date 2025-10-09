from types import SimpleNamespace
from typing import Any, NamedTuple

try:  # pragma: no cover - optional dependency
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - executed when pandas is unavailable
    pd = SimpleNamespace(DataFrame=Any)  # type: ignore[assignment]

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
