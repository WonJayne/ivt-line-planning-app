from typing import IO

from .iterators import pairwise


def skip_one_line_in_file(file_handle: IO) -> None:
    next(file_handle)
