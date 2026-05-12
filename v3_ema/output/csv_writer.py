from __future__ import annotations
import csv
from pathlib import Path
from typing import Iterable

from ..analysis.rows import Row, make_columns
from ..i18n import UI, get_ui


def write_csv(rows: Iterable[Row], path: Path, *, ui: UI | None = None) -> int:
    if ui is None:
        ui = get_ui("simp_chinese")
    columns = make_columns(ui)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow([label for _, label in columns])
        for r in rows:
            w.writerow(tuple(getattr(r, k) for k, _ in columns))
            n += 1
    return n
