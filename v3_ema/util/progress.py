"""Tiny dependency-free progress bar to stderr (no tqdm).

Used by the map renderer for multi-image runs (`regions map --all`, the Excel
atlas). Prints a single carriage-return-updated line; falls back silently when
stderr isn't a TTY (e.g. piped to a file) by still printing periodic lines.
"""
from __future__ import annotations

import sys
from typing import Iterable, Sequence, TypeVar

T = TypeVar("T")


def track(items: Sequence[T], label: str = "", width: int = 24) -> Iterable[T]:
    """Yield each item while drawing a progress bar like:

        Rendering [###########-------------]  5/14  building_iron_mine
    """
    n = len(items)
    if n == 0:
        return
    stream = sys.stderr
    tty = getattr(stream, "isatty", lambda: False)()
    for i, item in enumerate(items, 1):
        yield item
        filled = round(width * i / n)
        bar = "#" * filled + "-" * (width - filled)
        name = str(item) if not label else f"{label}"
        line = f"\r  [{bar}] {i:>3}/{n}  {name[:40]:<40}"
        if tty:
            stream.write(line)
            stream.flush()
        elif i == n or i % max(1, n // 10) == 0:
            stream.write(line.lstrip("\r") + "\n")
            stream.flush()
    if tty:
        stream.write("\n")
        stream.flush()
