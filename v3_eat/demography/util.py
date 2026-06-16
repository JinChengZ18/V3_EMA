from __future__ import annotations

import math
import re


def clamp(value: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, value))


def number_after(text: str, pattern: str, default: float) -> float:
    match = re.search(pattern + r"\s*([-+]?\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else default


def pct(value: float, digits: int = 2) -> str:
    if abs(value) < 0.5 * 10 ** (-digits) / 100.0:
        value = 0.0
    return f"{value * 100:.{digits}f}%"


def symlog(value: float, linthresh: float = 0.01) -> float:
    if value == 0.0:
        return 0.0
    return math.copysign(math.log10(1.0 + abs(value) / linthresh), value)


def display_units(text: str) -> int:
    return sum(2 if ord(ch) > 127 else 1 for ch in text)


def integer_percent_ticks(values: list[float]) -> list[float]:
    low = math.floor(min(values) * 100.0)
    high = math.ceil(max(values) * 100.0)
    if low == high:
        low -= 1
        high += 1
    span = high - low
    if span <= 12:
        step = 1
    elif span <= 28:
        step = 2
    elif span <= 70:
        step = 5
    else:
        step = 10
    start = math.floor(low / step) * step
    end = math.ceil(high / step) * step
    ticks = [i / 100.0 for i in range(start, end + step, step)]
    if low <= 0 <= high and 0.0 not in ticks:
        ticks.append(0.0)
        ticks.sort()
    return ticks
