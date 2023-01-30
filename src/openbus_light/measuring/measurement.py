from dataclasses import dataclass

import pandas as pd


@dataclass()
class Measurement:
    number: int
    circulation_id: int
    start: str
    end: str
    stop_count: int
    data: pd.DataFrame
