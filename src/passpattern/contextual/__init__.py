"""Deterministic detectors for calendar, year, and US QWERTY patterns."""

from passpattern.contextual.calendar_date import CalendarDateDetector
from passpattern.contextual.keyboard_layout import US_QWERTY, KeyboardLayout
from passpattern.contextual.keyboard_walk import KeyboardWalkDetector
from passpattern.contextual.year import YearDetector


def default_contextual_detectors() -> tuple[
    CalendarDateDetector,
    YearDetector,
    KeyboardWalkDetector,
]:
    """Return fresh contextual detectors configured with conservative defaults."""
    return CalendarDateDetector(), YearDetector(), KeyboardWalkDetector()


__all__ = [
    "CalendarDateDetector",
    "KeyboardLayout",
    "KeyboardWalkDetector",
    "US_QWERTY",
    "YearDetector",
    "default_contextual_detectors",
]
