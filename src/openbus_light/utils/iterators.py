from itertools import tee
from typing import Iterable, TypeVar

IterT = TypeVar("IterT")


def pairwise(iterable: Iterable[IterT]) -> Iterable[tuple[IterT, IterT]]:
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    first, second = tee(iterable)
    next(second, None)
    return zip(first, second)
