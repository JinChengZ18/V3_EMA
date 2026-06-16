"""Parse named modifier blocks out of game/common files.

This is the structured counterpart to ``modifier_scan`` (which produces a flat
audit list with source-line info). ``parse_modifier_block`` lets calling code
read e.g. ``law_public_health`` and pull its ``state_mortality_mult`` value
directly, without depending on hand-synced constants.

Implementation uses ``v3_eat.parser.pdx_parser`` to correctly handle nested
syntax and comments. Scenario construction can opt in to this lookup; the
default scenarios in ``scenarios.py`` still ship hardcoded values so the
report's baseline output is reproducible without a game install.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from v3_eat.parser.pdx_parser import parse_file


_NUMERIC_KEY_HINTS = (
    "_mult",
    "_add",
)


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _flatten_numeric(prefix: str, node: Any, out: dict[str, float]) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            number = _coerce_number(v)
            if number is not None and any(k.endswith(h) for h in _NUMERIC_KEY_HINTS):
                out[k] = number
            elif isinstance(v, (dict, list)):
                _flatten_numeric(f"{prefix}.{k}" if prefix else k, v, out)
    elif isinstance(node, list):
        for item in node:
            _flatten_numeric(prefix, item, out)


def parse_modifier_block(path: Path, block_name: str) -> dict[str, float] | None:
    """Return the numeric assignments inside a top-level ``block_name = { ... }``.

    Returns ``None`` if the block is not found in the file. Nested sub-blocks
    (``modifier = { ... }``, ``institution_modifier = { ... }``, etc.) are
    flattened — every ``*_mult`` / ``*_add`` numeric assignment is included.
    """
    parsed = parse_file(path)
    block = parsed.get(block_name)
    if block is None:
        return None
    out: dict[str, float] = {}
    _flatten_numeric("", block, out)
    return out


def find_modifier_block(directory: Path, block_name: str, glob: str = "*.txt") -> dict[str, float] | None:
    """Search every file in ``directory`` (non-recursive) for a top-level
    ``block_name`` block. Returns the first match's numeric assignments.
    """
    for path in sorted(directory.glob(glob)):
        result = parse_modifier_block(path, block_name)
        if result is not None:
            return result
    return None
