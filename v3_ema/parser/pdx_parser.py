from __future__ import annotations
from pathlib import Path
from typing import Any
from .pdx_tokenizer import tokenize, Token


class PdxParseError(Exception):
    pass


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.toks = tokens
        self.i = 0

    def peek(self, off: int = 0) -> Token:
        return self.toks[self.i + off]

    def eat(self) -> Token:
        t = self.toks[self.i]
        self.i += 1
        return t

    def parse_top(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        while self.peek().kind != "EOF":
            self._parse_assignment_or_value(out)
        return out

    def parse_block(self) -> Any:
        # we are positioned just after '{'
        # First, decide whether this is a list-of-scalars or an assignment block.
        if self.peek().kind == "RBRACE":
            self.eat()
            return {}
        # Probe: list if next is IDENT/STRING and the token after is NOT '='
        if self.peek().kind in ("IDENT", "STRING") and self.peek(1).kind != "EQ" and self.peek(1).kind != "LBRACE":
            # Pure list: scan scalars / nested blocks until '}'
            # In practice these are flat scalar lists (e.g. production_methods = { pm_a pm_b })
            items: list[Any] = []
            while self.peek().kind != "RBRACE" and self.peek().kind != "EOF":
                t = self.peek()
                if t.kind == "LBRACE":
                    self.eat()
                    items.append(self.parse_block())
                elif t.kind in ("IDENT", "STRING"):
                    items.append(self.eat().value)
                else:
                    raise PdxParseError(f"Unexpected token {t} in list at line {t.line}")
            if self.peek().kind == "RBRACE":
                self.eat()
            return items
        # Otherwise: assignment block (dict)
        out: dict[str, Any] = {}
        while self.peek().kind != "RBRACE" and self.peek().kind != "EOF":
            self._parse_assignment_or_value(out)
        if self.peek().kind == "RBRACE":
            self.eat()
        return out

    def _parse_assignment_or_value(self, out: dict[str, Any]) -> None:
        key_tok = self.eat()
        if key_tok.kind not in ("IDENT", "STRING"):
            raise PdxParseError(f"Expected key, got {key_tok} at line {key_tok.line}")
        key = key_tok.value
        op_tok = self.peek()
        if op_tok.kind != "EQ":
            # Bare value at top level (rare); treat as a flag-style "key" with empty value
            self._set_or_append(out, key, "")
            return
        self.eat()  # consume '=' or comparison
        val_tok = self.peek()
        if val_tok.kind == "LBRACE":
            self.eat()
            value: Any = self.parse_block()
        elif val_tok.kind in ("IDENT", "STRING"):
            value = self.eat().value
            # Tagged block syntax: `key = tag { ... }` (e.g. `color = hsv{ 0.5 0.3 0.8 }`).
            # The tag is discarded; the block becomes the value.
            if self.peek().kind == "LBRACE":
                self.eat()
                value = self.parse_block()
        else:
            raise PdxParseError(f"Expected value after '=', got {val_tok} at line {val_tok.line}")
        self._set_or_append(out, key, value)

    @staticmethod
    def _set_or_append(d: dict[str, Any], key: str, value: Any) -> None:
        if key in d:
            existing = d[key]
            if isinstance(existing, list) and (not existing or not isinstance(existing[0], (str, int, float))):
                # already a list of values from prior duplicates
                existing.append(value)
            elif isinstance(existing, list):
                # could be a parsed bare list; still append the new value
                existing.append(value)
            else:
                d[key] = [existing, value]
        else:
            d[key] = value


def parse(text: str) -> dict[str, Any]:
    toks = list(tokenize(text))
    return _Parser(toks).parse_top()


def parse_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return parse(text)


def load_dir(path: Path, glob: str = "*.txt") -> dict[str, Any]:
    """Parse every .txt in a directory (non-recursive) and merge top-level keys."""
    merged: dict[str, Any] = {}
    for p in sorted(path.glob(glob)):
        d = parse_file(p)
        for k, v in d.items():
            if k in merged:
                # later file wins (mod-style override)
                merged[k] = v
            else:
                merged[k] = v
    return merged
