from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Token:
    kind: str   # LBRACE | RBRACE | EQ | IDENT | STRING | EOF
    value: str
    line: int


def tokenize(text: str) -> Iterator[Token]:
    if text.startswith("﻿"):
        text = text[1:]
    n = len(text)
    i = 0
    line = 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if c.isspace():
            i += 1
            continue
        if c == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if c == "{":
            yield Token("LBRACE", "{", line); i += 1; continue
        if c == "}":
            yield Token("RBRACE", "}", line); i += 1; continue
        if c == "=":
            yield Token("EQ", "=", line); i += 1; continue
        if c in "<>":
            j = i + 1
            if j < n and text[j] == "=":
                j += 1
            yield Token("EQ", text[i:j], line)
            i = j
            continue
        if c in "?!" and i + 1 < n and text[i + 1] == "=":
            yield Token("EQ", text[i:i + 2], line)
            i += 2
            continue
        if c == '"':
            j = i + 1
            buf = []
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    buf.append(text[j + 1])
                    j += 2
                    continue
                if text[j] == "\n":
                    line += 1
                buf.append(text[j])
                j += 1
            yield Token("STRING", "".join(buf), line)
            i = j + 1 if j < n else j
            continue
        # IDENT: numbers, identifiers, dotted paths, signed numbers
        j = i
        if c == "-" and j + 1 < n and (text[j + 1].isdigit() or text[j + 1] == "."):
            j += 1
        while j < n and not text[j].isspace() and text[j] not in "{}=#\"":
            j += 1
        if j == i:
            i += 1
            continue
        yield Token("IDENT", text[i:j], line)
        i = j
    yield Token("EOF", "", line)
