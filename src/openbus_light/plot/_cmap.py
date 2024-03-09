from collections import defaultdict
from collections.abc import Collection
from typing import Generic, Hashable, TypeVar

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import plotly.express as px
from _plotly_utils.colors import sample_colorscale

T = TypeVar("T", bound=Hashable)


class ColorMap(dict[T, str], Generic[T]):
    pass


def create_colormap(elements: Collection[T], default_color: str | None = None) -> ColorMap[T]:
    """
    Create a colormap for the given elements.
    :param elements: Collection[T], collection of elements
    :param default_color: str | None, default color
    :return: ColorMap[T], colormap

    >>> create_colormap(['a', 'b', 'c'])
    {'a': '#63cb5f', 'b': '#65cb5e', 'c': '#69cd5b'}
    >>> create_colormap(['a', 'b', 'c'], default_color='red')
    {'a': '#63cb5f', 'b': '#65cb5e', 'c': '#69cd5b'}

    """
    count = len(elements)
    colors = sample_colorscale(px.colors.cyclical.Phase, samplepoints=[i / count for i in range(0, count)])
    if default_color is not None:
        return ColorMap[T]({element: colors[i] for i, element in enumerate(elements)})

    cmap = defaultdict(lambda: default_color)  # type: ignore
    cmap.update({element: colors[i] for i, element in enumerate(elements)})
    return ColorMap[T](cmap)


def create_continuous_colormap(
    low: float, high: float, cmap_name: str = "viridis"
) -> tuple[mcolors.Colormap, mcolors.Normalize]:
    """
    Create a continuous colormap for mapping values between low and high.

    :param low: The lower bound of the range of values.
    :param high: The upper bound of the range of values.
    :param cmap_name: The name of the matplotlib colormap to use.
    :return: tuple[mcolors.Colormap, mcolors.Normalize], colormap and normalization
    """
    # Normalize the colormap between the low and high values
    norm = mcolors.Normalize(vmin=low, vmax=high)

    # Get the colormap from matplotlib's available colormaps
    cmap = plt.cm.get_cmap(cmap_name)

    # You can now use `cmap(norm(value))` to get the color for any value in [low, high]
    return cmap, norm


def rgba_to_plotly_string(rgba: tuple[float, float, float, float]) -> str:
    return f"rgba({int(rgba[0] * 255)}, {int(rgba[1] * 255)}, {int(rgba[2] * 255)}, {rgba[3]})"
