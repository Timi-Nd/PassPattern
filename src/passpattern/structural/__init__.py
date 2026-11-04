"""Deterministic detectors for basic structural password patterns."""

from passpattern.detector import Detector
from passpattern.structural.alphabetic_sequence import AlphabeticSequenceDetector
from passpattern.structural.numeric_sequence import NumericSequenceDetector
from passpattern.structural.repeat_char import RepeatedCharacterDetector
from passpattern.structural.repeat_substring import RepeatedSubstringDetector


def default_structural_detectors() -> tuple[Detector, ...]:
    """Return fresh detectors configured with the documented default thresholds."""
    return (
        RepeatedCharacterDetector(),
        RepeatedSubstringDetector(),
        NumericSequenceDetector(),
        AlphabeticSequenceDetector(),
    )


__all__ = [
    "AlphabeticSequenceDetector",
    "NumericSequenceDetector",
    "RepeatedCharacterDetector",
    "RepeatedSubstringDetector",
    "default_structural_detectors",
]
