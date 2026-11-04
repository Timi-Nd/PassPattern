"""Detection of maximal contiguous repetitions of primitive substrings."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from passpattern.models import Evidence, EvidenceKey, PatternMatch
from passpattern.native import PreparedPassword
from passpattern.structural._validation import validate_minimum


@dataclass(frozen=True, slots=True)
class RepeatedSubstringDetector:
    """Find tandem repeats, retaining meaningful overlaps and primitive units only."""

    min_unit_length: int = 2
    min_repetitions: int = 2

    def __post_init__(self) -> None:
        validate_minimum(self.min_unit_length, "min_unit_length")
        validate_minimum(self.min_repetitions, "min_repetitions")

    @property
    def detector_id(self) -> str:
        return "structural.repeated_substring"

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        length = len(text)
        longest_common_prefix = [0] * length

        for start in range(length - 1, -1, -1):
            suffix_prefix = _prefix_function(text, start)
            maximum_period = length - start - 1

            for period in range(1, maximum_period + 1):
                if text[start] == text[start + period]:
                    longest_common_prefix[period] += 1
                else:
                    longest_common_prefix[period] = 0

            for period in range(self.min_unit_length, (length - start) // 2 + 1):
                common_length = longest_common_prefix[period]
                if common_length < period:
                    continue

                unit_prefix = suffix_prefix[period - 1]
                primitive_period = period - unit_prefix
                if primitive_period < period and period % primitive_period == 0:
                    continue

                repetition_count = 1 + common_length // period
                if repetition_count < self.min_repetitions:
                    continue

                yield PatternMatch(
                    detector_id=self.detector_id,
                    category="structural",
                    pattern_type="repeated_substring",
                    start_index=start,
                    end_index=start + repetition_count * period,
                    evidence=(
                        Evidence(EvidenceKey.COUNT, repetition_count),
                        Evidence(EvidenceKey.LENGTH, period),
                    ),
                )


def _prefix_function(text: str, offset: int) -> list[int]:
    """Compute KMP prefix lengths for a suffix without copying password text."""
    suffix_length = len(text) - offset
    prefix = [0] * suffix_length
    matched = 0

    for index in range(1, suffix_length):
        while matched and text[offset + index] != text[offset + matched]:
            matched = prefix[matched - 1]
        if text[offset + index] == text[offset + matched]:
            matched += 1
        prefix[index] = matched

    return prefix
