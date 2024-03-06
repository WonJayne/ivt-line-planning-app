from itertools import tee
from typing import IO, Iterable, TypeVar


def skip_one_line_in_file(file_handle: IO) -> None:
    next(file_handle)


IterT = TypeVar("IterT")


def pairwise(iterable: Iterable[IterT]) -> Iterable[tuple[IterT, IterT]]:
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    first, second = tee(iterable)
    next(second, None)
    return zip(first, second)
