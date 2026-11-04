"""Common detector interface."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from passpattern.config import TextNormalization
from passpattern.models import PatternMatch
from passpattern.native import PreparedPassword


class Detector(Protocol):
    """A deterministic, side-effect-free detector over a prepared password."""

    @property
    def detector_id(self) -> str:
        """Return this detector's stable lowercase identifier."""

    def detect(self, prepared_password: PreparedPassword) -> Iterable[PatternMatch]:
        """Return matches without retaining or exposing password text."""


@runtime_checkable
class NormalizationAwareDetector(Protocol):
    """Optional detector capability for required prepared-text normalization."""

    @property
    def required_normalization(self) -> TextNormalization:
        """Return the normalization mode required by this detector's data."""
