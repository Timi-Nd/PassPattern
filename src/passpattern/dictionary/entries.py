"""Validated immutable dictionary entries."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SOURCE_IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}\Z")


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    """A word and dataset-supplied positive frequency rank."""

    word: str
    rank: int
    source_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.word, str) or not self.word:
            raise ValueError("Dictionary words must be non-empty strings.")
        if any(0xD800 <= ord(character) <= 0xDFFF for character in self.word):
            raise ValueError("Dictionary words must contain valid Unicode scalar values.")
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank < 1:
            raise ValueError("Dictionary rank must be a positive integer.")
        if self.source_id is not None and (
            not isinstance(self.source_id, str) or not _SOURCE_IDENTIFIER.fullmatch(self.source_id)
        ):
            raise ValueError("source_id must be a short ASCII identifier.")
