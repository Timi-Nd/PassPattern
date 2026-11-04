"""Detection of maximal ascending or descending ASCII digit sequences."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from passpattern.models import PatternMatch
from passpattern.native import PreparedPassword
from passpattern.structural._sequences import detect_sequences
from passpattern.structural._validation import validate_minimum


@dataclass(frozen=True, slots=True)
class NumericSequenceDetector:
    """Find maximal ASCII digit runs with a constant step of +1 or -1."""

    min_sequence_length: int = 3

    def __post_init__(self) -> None:
        validate_minimum(self.min_sequence_length, "min_sequence_length")

    @property
    def detector_id(self) -> str:
        return "structural.numeric_sequence"

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        yield from detect_sequences(
            prepared_password.processed_text,
            self.detector_id,
            "numeric_sequence",
            self.min_sequence_length,
            _ascii_digit_value,
        )


def _ascii_digit_value(character: str) -> int | None:
    codepoint = ord(character)
    if ord("0") <= codepoint <= ord("9"):
        return codepoint
    return None
