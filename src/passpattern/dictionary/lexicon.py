"""Immutable, bounded lexicons built from explicitly supplied entries."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from passpattern.config import TextNormalization
from passpattern.dictionary.entries import DictionaryEntry

NormalizationMode = TextNormalization


@dataclass(frozen=True, slots=True, init=False)
class DictionaryLexicon:
    """A deterministic tuple of entries with explicit size and normalization limits.

    Exact duplicate spellings are resolved by keeping the lowest rank, then the
    lexicographically smallest source identifier, with an absent identifier ordered
    before a supplied identifier. Case variants remain separate so exact-case
    preference can be applied when a password is scanned.
    """

    entries: tuple[DictionaryEntry, ...]
    min_word_length: int
    max_word_length: int
    max_entries: int
    max_total_codepoints: int
    normalization: NormalizationMode
    unicode_data_version: str

    def __init__(
        self,
        entries: Iterable[DictionaryEntry],
        *,
        min_word_length: int = 1,
        max_word_length: int = 128,
        max_entries: int = 100_000,
        max_total_codepoints: int = 2_000_000,
        normalization: NormalizationMode = "none",
    ) -> None:
        _positive_integer(min_word_length, "min_word_length")
        _positive_integer(max_word_length, "max_word_length")
        _positive_integer(max_entries, "max_entries")
        _positive_integer(max_total_codepoints, "max_total_codepoints")
        if min_word_length > max_word_length:
            raise ValueError("min_word_length cannot exceed max_word_length.")
        if normalization not in ("none", "nfc"):
            raise ValueError("normalization must be 'none' or 'nfc'.")

        selected: dict[str, DictionaryEntry] = {}
        supplied_count = 0
        supplied_codepoints = 0
        for entry in entries:
            supplied_count += 1
            if supplied_count > max_entries:
                raise ValueError("Dictionary exceeds max_entries.")
            if not isinstance(entry, DictionaryEntry):
                raise TypeError("entries must contain only DictionaryEntry values.")
            if normalization == "nfc" and unicodedata.normalize("NFC", entry.word) != entry.word:
                raise ValueError("Dictionary entries must already be NFC-normalized.")
            word_length = len(entry.word)
            if word_length < min_word_length:
                raise ValueError("Dictionary word is shorter than min_word_length.")
            if word_length > max_word_length:
                raise ValueError("Dictionary word exceeds max_word_length.")
            supplied_codepoints += word_length
            if supplied_codepoints > max_total_codepoints:
                raise ValueError("Dictionary exceeds max_total_codepoints.")

            existing = selected.get(entry.word)
            if existing is None or _entry_order(entry) < _entry_order(existing):
                selected[entry.word] = entry

        ordered_entries = tuple(
            sorted(selected.values(), key=lambda entry: (ascii_fold(entry.word), entry.word))
        )
        total_codepoints = sum(len(entry.word) for entry in ordered_entries)
        if total_codepoints > max_total_codepoints:
            raise ValueError("Compiled dictionary exceeds max_total_codepoints.")

        object.__setattr__(self, "entries", ordered_entries)
        object.__setattr__(self, "min_word_length", min_word_length)
        object.__setattr__(self, "max_word_length", max_word_length)
        object.__setattr__(self, "max_entries", max_entries)
        object.__setattr__(self, "max_total_codepoints", max_total_codepoints)
        object.__setattr__(self, "normalization", normalization)
        object.__setattr__(self, "unicode_data_version", unicodedata.unidata_version)


def ascii_fold(text: str) -> str:
    """Lowercase only ASCII A-Z, preserving Unicode code-point count."""
    return "".join(
        chr(ord(character) + 32) if "A" <= character <= "Z" else character for character in text
    )


def _entry_order(entry: DictionaryEntry) -> tuple[int, str]:
    return entry.rank, entry.source_id or ""


def _positive_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
