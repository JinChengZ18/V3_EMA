from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TRACKED_EXACT_KEYS = {
    "state_birth_rate_mult",
    "state_mortality_mult",
    "state_mortality_wealth_mult",
    "state_mortality_turmoil_mult",
    "state_pollution_generation_add",
    "state_pollution_reduction_health_mult",
    "state_standard_of_living_add",
    "state_working_adult_ratio_add",
    "state_food_security_add",
}

NUMERIC_ASSIGNMENT_RE = re.compile(r"\b([A-Za-z0-9_]+)\s*=\s*([-+]?\d+(?:\.\d+)?)\b")
BLOCK_START_RE = re.compile(r"\b([A-Za-z0-9_:.+-]+)\s*=\s*\{")


@dataclass(frozen=True)
class ModifierSource:
    key: str
    value: float
    file: str
    line_number: int
    scope: str
    line: str


def is_tracked_modifier_key(key: str) -> bool:
    if key in TRACKED_EXACT_KEYS:
        return True
    if key.endswith("_mortality_mult"):
        return True
    if key.endswith("_birth_rate_mult"):
        return True
    return False


def scan_modifier_sources(game_root: Path) -> list[ModifierSource]:
    common = game_root / "game" / "common"
    out: list[ModifierSource] = []
    for path in sorted(common.rglob("*.txt")):
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        stack: list[str] = []
        for line_number, raw in enumerate(lines, 1):
            clean = raw.split("#", 1)[0]
            for match in NUMERIC_ASSIGNMENT_RE.finditer(clean):
                key = match.group(1)
                if not is_tracked_modifier_key(key):
                    continue
                out.append(
                    ModifierSource(
                        key=key,
                        value=float(match.group(2)),
                        file=str(path.relative_to(game_root)),
                        line_number=line_number,
                        scope=" > ".join(stack[-5:]),
                        line=raw.strip(),
                    )
                )
            for match in BLOCK_START_RE.finditer(clean):
                key = match.group(1)
                rest = clean[match.end() - 1 :]
                if "{" in rest:
                    stack.append(key)
            for _ in range(clean.count("}")):
                if stack:
                    stack.pop()
    return out


def summarize_sources(sources: Iterable[ModifierSource]) -> list[dict[str, str | float | int]]:
    groups: dict[str, list[ModifierSource]] = {}
    for source in sources:
        groups.setdefault(source.key, []).append(source)
    rows: list[dict[str, str | float | int]] = []
    for key, values in sorted(groups.items()):
        nums = [v.value for v in values]
        files = {v.file for v in values}
        rows.append(
            {
                "key": key,
                "count": len(values),
                "file_count": len(files),
                "min": min(nums),
                "max": max(nums),
                "sum": sum(nums),
            }
        )
    rows.sort(key=lambda r: (-int(r["count"]), str(r["key"])))
    return rows
