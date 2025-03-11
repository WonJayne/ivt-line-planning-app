from pathlib import Path
from typing import NamedTuple


class ScenarioPaths(NamedTuple):
    to_demand: Path
    to_lines: Path
    to_stations: Path
    to_districts: Path
    to_measurements: Path
