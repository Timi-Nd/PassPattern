"""Four-digit year recognition with fixed inclusive bounds."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from passpattern.models import Evidence, EvidenceKey, PatternMatch
from passpattern.native import PreparedPassword


@dataclass(frozen=True, slots=True)
class YearDetector:
    """Find maximal four-ASCII-digit runs within a configured year range."""

    min_year: int = 1900
    max_year: int = 2099

    def __post_init__(self) -> None:
        _validate_year(self.min_year, "min_year")
        _validate_year(self.max_year, "max_year")
        if self.min_year > self.max_year:
            raise ValueError("min_year cannot exceed max_year.")

    @property
    def detector_id(self) -> str:
        return "contextual.year"

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        index = 0
        while index < len(text):
            if not _is_ascii_digit(text[index]):
                index += 1
                continue
            start = index
            while index < len(text) and _is_ascii_digit(text[index]):
                index += 1
            if index - start != 4:
                continue
            year = int(text[start:index])
            if self.min_year <= year <= self.max_year:
                yield PatternMatch(
                    detector_id=self.detector_id,
                    category="contextual",
                    pattern_type="four_digit_year",
                    start_index=start,
                    end_index=index,
                    evidence=(Evidence(EvidenceKey.LENGTH, 4),),
                )


def _validate_year(year: int, name: str) -> None:
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
        raise ValueError(f"{name} must be an integer from 1 through 9999.")


def _is_ascii_digit(character: str) -> bool:
    return "0" <= character <= "9"
