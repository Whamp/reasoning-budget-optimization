from __future__ import annotations

import re
from dataclasses import dataclass

_BOXED_RE = re.compile(r"\\boxed\{([^{}]+)\}")
_INT_RE = re.compile(r"(?<![-\d])(\d{1,6})(?![\d])")


@dataclass(frozen=True)
class Score:
    correct: bool
    parsed_answer: str | None
    target: str


def parse_aime_answer(text: str) -> str | None:
    boxed = _BOXED_RE.findall(text)
    if boxed:
        return _normalize_int(boxed[-1])
    ints = _INT_RE.findall(text)
    if ints:
        return _normalize_int(ints[-1])
    return None


def score_aime_answer(output: str, target: str) -> Score:
    parsed = parse_aime_answer(output)
    normalized_target = _normalize_int(target)
    return Score(correct=parsed == normalized_target, parsed_answer=parsed, target=normalized_target)


def _normalize_int(value: str) -> str:
    stripped = value.strip()
    if stripped.isdigit():
        return str(int(stripped))
    return stripped
