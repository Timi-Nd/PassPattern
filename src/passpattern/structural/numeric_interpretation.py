"""Bounded ASCII digit-run and canonical integer-term interpretation."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from passpattern.models import NumericTerm


@dataclass(frozen=True, slots=True)
class DigitRun:
    start_index: int
    end_index: int


def is_ascii_digit(character: str) -> bool:
    return "0" <= character <= "9"


def iter_digit_runs(text: str) -> Iterator[DigitRun]:
    index = 0
    while index < len(text):
        if not is_ascii_digit(text[index]):
            index += 1
            continue
        start = index
        while index < len(text) and is_ascii_digit(text[index]):
            index += 1
        yield DigitRun(start, index)


def iter_terms_at(
    text: str,
    start_index: int,
    run_end: int,
    max_digits: int,
    max_value: int,
) -> Iterator[NumericTerm]:
    """Yield canonical terms beginning at one run position, shortest first."""
    for end_index in range(start_index + 1, min(run_end, start_index + max_digits) + 1):
        if end_index > start_index + 1 and text[start_index] == "0":
            return
        value = int(text[start_index:end_index])
        if value > max_value:
            return
        yield NumericTerm(value, start_index, end_index)


def term_matches_at(text: str, start_index: int, run_end: int, value: int) -> NumericTerm | None:
    if value < 0:
        return None
    token = str(value)
    end_index = start_index + len(token)
    if end_index <= run_end and text[start_index:end_index] == token:
        return NumericTerm(value, start_index, end_index)
    return None


def can_extend_left(
    text: str,
    first_term: NumericTerm,
    expected_previous: int,
    run_start: int,
    max_digits: int,
    max_value: int,
) -> bool:
    if expected_previous < 0 or expected_previous > max_value:
        return False
    token = str(expected_previous)
    if len(token) > max_digits:
        return False
    start_index = first_term.start_index - len(token)
    return start_index >= run_start and text[start_index : first_term.start_index] == token
