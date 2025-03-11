# encoding: utf-8

from pathlib import Path

_DATA_ROOT = Path("data")
SCENARIO_PATH = _DATA_ROOT / "scenario"
PATH_TO_DEMAND = SCENARIO_PATH / "Nachfrage.csv"
PATH_TO_DEMAND_DISTRICT_POINTS = SCENARIO_PATH / "Bezirkspunkte.csv"
PATH_TO_STATIONS = SCENARIO_PATH / "Haltestellen.zip"
MEASUREMENTS = SCENARIO_PATH / "Messungen.zip"
WINTERTHUR_IMAGE = SCENARIO_PATH / "Winterthur_Karte.png"
PATH_TO_LINE_DATA = _DATA_ROOT / "lines"
GPS_BOX = (8.61, 8.88, 47.35, 47.62)

RESULT_DIRECTORY = Path("results")
