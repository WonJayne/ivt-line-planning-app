"""Convenience imports for the plotting helpers used in the exercises.

The functions exposed here allow you to visualise demand matrices, bus lines and
line-planning networks. They are primarily used in ``exercise_3.py`` and
``exercise_4.py`` to analyse the provided scenario for the city of Winterthur.
"""

from ._background import PlotBackground
from ._cmap import ColorMap, create_colormap
from .demand import create_od_plot, create_station_and_demand_plot
from .line import create_station_and_line_plot, plot_lines_in_swiss_coordinates
from .line_usage import plot_usage_for_each_direction
from .network import (
    plot_network_in_swiss_coordinate_grid,
    plot_network_usage_in_swiss_coordinates,
)
