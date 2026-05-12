from __future__ import annotations
import re
from pathlib import Path
from typing import Iterable

_LINE_RE = re.compile(r'^\s+([A-Za-z0-9_\.\-]+)\s*:\s*\d*\s*"((?:[^"\\]|\\.)*)"\s*(?:#.*)?$')
_REF_RE = re.compile(r'\$([A-Za-z0-9_\.\|]+)\$')
_ICON_RE = re.compile(r'£[A-Za-z0-9_\.]+(?:\|[^£]*)?£')
_AT_ICON_RE = re.compile(r'@[A-Za-z0-9_]+!')           # newer @key! icon syntax
_FORMAT_RE = re.compile(r'#[A-Za-z!]+|#!')
_TAG_RE = re.compile(r'(?:\[[^\]]*\])')
# Resolve [Concept('foo', 'fallback')] → translated foo (fallback if not found)
_CONCEPT_FULL_RE = re.compile(r"\[Concept\('([^']+)'(?:,\s*'([^']*)')?\)\]")
# Resolve [concept_xxx] inline references
_CONCEPT_RE = re.compile(r'\[(concept_[A-Za-z0-9_]+)(?:\|[^\]]*)?\]')


class LocStore:
    def __init__(self) -> None:
        self.raw: dict[str, str] = {}

    def add(self, key: str, value: str) -> None:
        # Last write wins (later mod overrides etc.)
        self.raw[key] = value

    def get(self, key: str, default: str | None = None) -> str:
        if key not in self.raw:
            return default if default is not None else key
        return self._resolve(key, set())

    def get_clean(self, key: str, default: str | None = None) -> str:
        """Resolved value with format codes / icon codes stripped + concepts
        resolved, suitable for plain text."""
        s = self.get(key, default)
        s = _ICON_RE.sub("", s)
        s = _AT_ICON_RE.sub("", s)

        # Resolve [Concept('concept_x', 'fallback')] → loc(concept_x) or fallback
        def _full(m: re.Match) -> str:
            ref = m.group(1)
            fallback = m.group(2) or ""
            resolved = self._resolve(ref, set()) if ref in self.raw else ""
            # Strip nested tags from the resolved value before returning
            r = _ICON_RE.sub("", resolved)
            r = _AT_ICON_RE.sub("", r)
            r = _TAG_RE.sub("", r).strip()
            return r or fallback
        s = _CONCEPT_FULL_RE.sub(_full, s)

        # Resolve [concept_xxx] → loc(concept_xxx) — strip if not found
        def _short(m: re.Match) -> str:
            ref = m.group(1)
            resolved = self._resolve(ref, set()) if ref in self.raw else ""
            r = _ICON_RE.sub("", resolved)
            r = _AT_ICON_RE.sub("", r)
            r = _TAG_RE.sub("", r).strip()
            return r
        s = _CONCEPT_RE.sub(_short, s)

        s = _FORMAT_RE.sub("", s)
        s = _TAG_RE.sub("", s)
        return s.strip()

    def _resolve(self, key: str, seen: set[str], depth: int = 0) -> str:
        if depth > 8 or key in seen:
            return self.raw.get(key, key)
        if key not in self.raw:
            return key
        seen = seen | {key}
        v = self.raw[key]

        def repl(m: re.Match) -> str:
            inner = m.group(1).split("|", 1)[0]
            return self._resolve(inner, seen, depth + 1)

        return _REF_RE.sub(repl, v)


def _iter_yml_lines(path: Path) -> Iterable[str]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for line in text.splitlines():
        yield line


def load_localization(game_root: Path, lang: str = "simp_chinese") -> LocStore:
    store = LocStore()
    loc_dir = game_root / "game" / "localization" / lang
    if not loc_dir.is_dir():
        return store
    # rglob picks up subdirs like map/, modifiers/, etc. that hold state names,
    # state traits, strategic regions, and so on.
    for p in sorted(loc_dir.rglob("*.yml")):
        for line in _iter_yml_lines(p):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("l_") and stripped.endswith(":"):
                continue
            m = _LINE_RE.match(line)
            if m:
                store.add(m.group(1), m.group(2))
    return store
