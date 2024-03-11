import os

_DATA_ROOT = "data"
SCENARIO_PATH = os.path.join(_DATA_ROOT, "scenario")
PATH_TO_DEMAND = os.path.join(SCENARIO_PATH, "Nachfrage.csv")
PATH_TO_DEMAND_DISTRICT_POINTS = os.path.join(SCENARIO_PATH, "Bezirkspunkte.csv")
PATH_TO_STATIONS = os.path.join(SCENARIO_PATH, "Haltestellen.zip")
MEASUREMENTS = os.path.join(SCENARIO_PATH, "Messungen.zip")
WINTERTHUR_IMAGE = os.path.join(SCENARIO_PATH, "Winterthur_Karte.png")
PATH_TO_LINE_DATA = os.path.join(_DATA_ROOT, "lines")
GPS_BOX = (8.61, 8.88, 47.35, 47.62)

RESULT_DIRNAME = "results"
