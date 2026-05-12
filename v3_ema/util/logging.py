from __future__ import annotations
import logging

_FMT = "%(asctime)s %(levelname).1s %(name)s | %(message)s"


def get_logger(name: str = "v3_ema", level: int = logging.INFO) -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(_FMT, "%H:%M:%S"))
        log.addHandler(h)
        log.setLevel(level)
        log.propagate = False
    return log
