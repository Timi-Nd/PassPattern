"""Detection of maximal runs of identical Unicode code points."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from passpattern.models import Evidence, EvidenceKey, PatternMatch
from passpattern.native import PreparedPassword
from passpattern.structural._validation import validate_minimum


@dataclass(frozen=True, slots=True)
class RepeatedCharacterDetector:
    """Find maximal consecutive runs of the same code point."""

    min_repetitions: int = 3

    def __post_init__(self) -> None:
        validate_minimum(self.min_repetitions, "min_repetitions")

    @property
    def detector_id(self) -> str:
        return "structural.repeated_character"

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        run_start = 0

        for index in range(1, len(text) + 1):
            if index < len(text) and text[index] == text[run_start]:
                continue

            run_length = index - run_start
            if run_length >= self.min_repetitions:
                yield PatternMatch(
                    detector_id=self.detector_id,
                    category="structural",
                    pattern_type="repeated_character",
                    start_index=run_start,
                    end_index=index,
                    evidence=(Evidence(EvidenceKey.COUNT, run_length),),
                )
            run_start = index
