"""Immutable engine configuration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, TypeAlias

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,79}\Z")
TextNormalization: TypeAlias = Literal["none", "nfc"]


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Native text-processing settings and per-analysis resource limits."""

    max_codepoints: int = 1024
    max_utf8_bytes: int = 4096
    normalization: TextNormalization = "none"
    max_matches: int = 1000
    detector_ids: frozenset[str] | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_codepoints, bool)
            or not isinstance(self.max_codepoints, int)
            or self.max_codepoints < 1
        ):
            raise ValueError("max_codepoints must be a positive integer.")
        if (
            isinstance(self.max_utf8_bytes, bool)
            or not isinstance(self.max_utf8_bytes, int)
            or self.max_utf8_bytes < 1
        ):
            raise ValueError("max_utf8_bytes must be a positive integer.")
        if self.normalization not in ("none", "nfc"):
            raise ValueError("normalization must be 'none' or 'nfc'.")
        if (
            isinstance(self.max_matches, bool)
            or not isinstance(self.max_matches, int)
            or self.max_matches < 1
        ):
            raise ValueError("max_matches must be a positive integer.")

        if self.detector_ids is not None:
            detector_ids = frozenset(self.detector_ids)
            if any(
                not isinstance(item, str) or not _IDENTIFIER.fullmatch(item)
                for item in detector_ids
            ):
                raise ValueError("Detector identifiers must be lowercase ASCII identifiers.")
            object.__setattr__(self, "detector_ids", detector_ids)
