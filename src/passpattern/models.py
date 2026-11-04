"""Immutable, password-safe result models."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,79}\Z")


class EvidenceKey(str, Enum):
    """Supported non-secret evidence fields."""

    COUNT = "count"
    CASE_EXACT = "case_exact"
    DATE_ORDER = "date_order"
    DIRECTION = "direction"
    LENGTH = "length"
    OFFSET = "offset"
    RANK = "rank"
    AMBIGUOUS = "ambiguous"
    SEPARATOR_COUNT = "separator_count"
    SUBSTITUTION_COUNT = "substitution_count"


@dataclass(frozen=True, slots=True)
class Evidence:
    """A typed numeric or boolean fact; arbitrary text is intentionally unsupported."""

    key: EvidenceKey
    value: int | float | bool

    def __post_init__(self) -> None:
        if not isinstance(self.key, EvidenceKey):
            raise TypeError("Evidence key must be an EvidenceKey.")
        if isinstance(self.value, bool):
            return
        if isinstance(self.value, int):
            return
        if isinstance(self.value, float) and math.isfinite(self.value):
            return
        raise TypeError("Evidence values must be finite numbers or booleans.")


@dataclass(frozen=True, slots=True)
class PatternMatch:
    """A password-free pattern span, indexed in Unicode code points."""

    detector_id: str
    category: str
    pattern_type: str
    start_index: int
    end_index: int
    evidence: tuple[Evidence, ...] = ()

    def __post_init__(self) -> None:
        for field_name, value in (
            ("detector_id", self.detector_id),
            ("category", self.category),
            ("pattern_type", self.pattern_type),
        ):
            if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
                raise ValueError(f"{field_name} must be a lowercase ASCII identifier.")

        if isinstance(self.start_index, bool) or not isinstance(self.start_index, int):
            raise TypeError("start_index must be an integer.")
        if isinstance(self.end_index, bool) or not isinstance(self.end_index, int):
            raise TypeError("end_index must be an integer.")
        if self.start_index < 0 or self.end_index <= self.start_index:
            raise ValueError("Match spans must be non-empty, non-negative half-open ranges.")

        evidence = tuple(self.evidence)
        if any(not isinstance(item, Evidence) for item in evidence):
            raise TypeError("evidence must contain only Evidence values.")
        if len({item.key for item in evidence}) != len(evidence):
            raise ValueError("Evidence keys must be unique within a match.")
        object.__setattr__(self, "evidence", evidence)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Deterministically ordered matches, with no password-bearing data."""

    matches: tuple[PatternMatch, ...] = ()

    def __post_init__(self) -> None:
        matches = tuple(self.matches)
        if any(not isinstance(match, PatternMatch) for match in matches):
            raise TypeError("matches must contain only PatternMatch values.")
        object.__setattr__(self, "matches", matches)
