from typing import NamedTuple

import pandas as pd


class RecordedTrip(NamedTuple):
    number: int
    circulation_id: int
    start: str
    end: str
    stop_count: int
    record: pd.DataFrame
