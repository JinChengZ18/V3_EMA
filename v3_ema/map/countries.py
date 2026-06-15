"""Parse 1836 start ownership (game/common/history/states) → province color → country.

Used to draw national borders on the choropleth. We map each owned province's
hex color to its owning country tag at game start, so border pixels can be found
where adjacent provinces belong to different (significant) countries.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..util.logging import get_logger

log = get_logger()

_CREATE = re.compile(r"create_state\s*=\s*\{")
_COUNTRY = re.compile(r"country\s*=\s*c:(\w+)")
_OWNED = re.compile(r"owned_provinces\s*=\s*\{([^}]*)\}", re.S)
_HEX = re.compile(r"\"?x([0-9A-Fa-f]{6})\"?")


def _brace_block(txt: str, start: int) -> str:
    """Return the {...} block starting at the '{' index `start` (inclusive)."""
    depth = 0
    for j in range(start, len(txt)):
        c = txt[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return txt[start:j + 1]
    return txt[start:]


def load_start_ownership(game_root: Path) -> dict[int, str]:
    """Map province color (0xRRGGBB int) -> owning country tag at the 1836 start."""
    sdir = game_root / "game" / "common" / "history" / "states"
    out: dict[int, str] = {}
    if not sdir.exists():
        return out
    for f in sorted(sdir.glob("*.txt")):
        txt = f.read_text(encoding="utf-8-sig", errors="replace")
        for m in _CREATE.finditer(txt):
            block = _brace_block(txt, m.end() - 1)
            cm = _COUNTRY.search(block)
            om = _OWNED.search(block)
            if not cm or not om:
                continue
            tag = cm.group(1)
            for hm in _HEX.finditer(om.group(1)):
                out[int(hm.group(1), 16)] = tag
    log.info("Start ownership: %d provinces across %d countries",
             len(out), len(set(out.values())))
    return out


_TYPE = re.compile(r"country_type\s*=\s*(\w+)")
_DEF_TAG = re.compile(r"^\s*([A-Z][A-Z0-9_]{2,})\s*=\s*\{", re.M)


def load_country_types(game_root: Path) -> dict[str, str]:
    """tag -> country_type (recognized / unrecognized / colonial / decentralized / company)."""
    cdir = game_root / "game" / "common" / "country_definitions"
    out: dict[str, str] = {}
    if not cdir.exists():
        return out
    for f in sorted(cdir.glob("*.txt")):
        txt = f.read_text(encoding="utf-8-sig", errors="replace")
        for m in _DEF_TAG.finditer(txt):
            tag = m.group(1)
            tm = _TYPE.search(txt, m.end(), m.end() + 400)
            if tm and tag not in out:
                out[tag] = tm.group(1)
    return out


def country_sizes(ownership: dict[int, str]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for tag in ownership.values():
        sizes[tag] = sizes.get(tag, 0) + 1
    return sizes


# Which country_types each filter mode keeps. "civilized" drops only the
# decentralized tribal/clan polities (the "无关紧要的小国家"); "recognized" keeps
# only great-power-recognized states (drops China/Japan/Persia etc.).
FILTER_MODES = {
    "all": None,
    "civilized": {"recognized", "unrecognized", "colonial", "company"},
    "recognized": {"recognized"},
}


def significant_countries(
    ownership: dict[int, str],
    min_provinces: int,
    *,
    types: dict[str, str] | None = None,
    mode: str = "civilized",
) -> set[str]:
    """Tags worth outlining: own >= min_provinces AND pass the type filter."""
    allowed = FILTER_MODES.get(mode, FILTER_MODES["civilized"])
    sizes = country_sizes(ownership)
    out: set[str] = set()
    for t, n in sizes.items():
        if n < min_provinces:
            continue
        if allowed is not None and (types or {}).get(t, "unrecognized") not in allowed:
            continue
        out.add(t)
    return out
