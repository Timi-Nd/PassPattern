"""Calendar-date recognition using bounded ASCII scans and Gregorian validation."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Literal

from passpattern.models import Evidence, EvidenceKey, PatternMatch
from passpattern.native import PreparedPassword

DateOrder = Literal["auto", "dmy", "mdy", "ymd"]
_DATE_ORDERS = frozenset(("auto", "dmy", "mdy", "ymd"))
_DATE_ORDER_CODES = {"auto": 0, "ymd": 1, "dmy": 2, "mdy": 3}


@dataclass(frozen=True, slots=True)
class CalendarDateDetector:
    """Find valid, bounded Gregorian dates using ASCII digits only."""

    min_year: int = 1900
    max_year: int = 2099
    date_order: DateOrder = "auto"
    allow_compact: bool = False

    def __post_init__(self) -> None:
        _validate_year(self.min_year, "min_year")
        _validate_year(self.max_year, "max_year")
        if self.min_year > self.max_year:
            raise ValueError("min_year cannot exceed max_year.")
        if not isinstance(self.date_order, str) or self.date_order not in _DATE_ORDERS:
            raise ValueError("date_order must be 'auto', 'dmy', 'mdy', or 'ymd'.")
        if not isinstance(self.allow_compact, bool):
            raise ValueError("allow_compact must be a boolean.")

    @property
    def detector_id(self) -> str:
        return "contextual.calendar_date"

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        for start in range(len(text)):
            if not _is_ascii_digit(text[start]):
                continue
            if start and _is_ascii_digit(text[start - 1]):
                continue

            parsed = self._parse_at(text, start)
            if parsed is None:
                continue
            end, separator_count, ambiguous, order_code = parsed
            if end < len(text) and _is_ascii_digit(text[end]):
                continue
            yield PatternMatch(
                detector_id=self.detector_id,
                category="contextual",
                pattern_type="calendar_date",
                start_index=start,
                end_index=end,
                evidence=(
                    Evidence(EvidenceKey.LENGTH, end - start),
                    Evidence(EvidenceKey.SEPARATOR_COUNT, separator_count),
                    Evidence(EvidenceKey.AMBIGUOUS, ambiguous),
                    Evidence(EvidenceKey.DATE_ORDER, order_code),
                ),
            )

    def _parse_at(self, text: str, start: int) -> tuple[int, int, bool, int] | None:
        if start + 10 <= len(text):
            token = text[start : start + 10]
            if (
                _is_ascii_digits(token[:4])
                and token[4] in "-/"
                and token[7] == token[4]
                and _is_ascii_digits(token[5:7])
                and _is_ascii_digits(token[8:10])
            ):
                year = int(token[:4])
                month = int(token[5:7])
                day = int(token[8:10])
                if self._valid_date(year, month, day):
                    return start + 10, 2, False, _DATE_ORDER_CODES["ymd"]

            if (
                _is_ascii_digits(token[:2])
                and token[2] in "-/"
                and token[5] == token[2]
                and _is_ascii_digits(token[3:5])
                and _is_ascii_digits(token[6:10])
                and self.date_order != "ymd"
            ):
                first = int(token[:2])
                second = int(token[3:5])
                year = int(token[6:10])
                dmy_valid = self._valid_date(year, second, first)
                mdy_valid = self._valid_date(year, first, second)
                if dmy_valid or mdy_valid:
                    ambiguous = dmy_valid and mdy_valid
                    if dmy_valid and mdy_valid:
                        selected_order = self.date_order
                    elif dmy_valid:
                        selected_order = "dmy"
                    else:
                        selected_order = "mdy"
                    order_code = _DATE_ORDER_CODES.get(selected_order, 0)
                    return start + 10, 2, ambiguous, order_code

        if self.allow_compact and self.date_order in ("auto", "ymd") and start + 8 <= len(text):
            token = text[start : start + 8]
            if _is_ascii_digits(token):
                year = int(token[:4])
                month = int(token[4:6])
                day = int(token[6:8])
                if self._valid_date(year, month, day):
                    return start + 8, 0, False, _DATE_ORDER_CODES["ymd"]
        return None

    def _valid_date(self, year: int, month: int, day: int) -> bool:
        if not self.min_year <= year <= self.max_year:
            return False
        try:
            date(year, month, day)
        except ValueError:
            return False
        return True


def _validate_year(year: int, name: str) -> None:
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999:
        raise ValueError(f"{name} must be an integer from 1 through 9999.")


def _is_ascii_digit(character: str) -> bool:
    return "0" <= character <= "9"


def _is_ascii_digits(text: str) -> bool:
    return bool(text) and all(_is_ascii_digit(character) for character in text)
