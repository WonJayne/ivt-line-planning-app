from typing import NewType

StationName = NewType("StationName", str)
DirectionName = NewType("DirectionName", str)
DistrictName = NewType("DistrictName", str)
DistrictPointId = NewType("DistrictPointId", str)
LineNr = NewType("LineNr", int)
LineName = NewType("LineName", str)
LineFrequency = NewType("LineFrequency", int)  # in number per period, e.g. 4 per hour
Capacity = NewType("Capacity", int)  # in number of passengers per bus
TripNr = NewType("TripNr", int)
CirculationId = NewType("CirculationId", int)
Meter = NewType("Meter", float)
MeterPerSecond = NewType("MeterPerSecond", float)
CHF = NewType("CHF", int)