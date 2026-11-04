"""Detection of dictionary words followed by bounded ASCII suffixes."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field

from passpattern.config import TextNormalization
from passpattern.dictionary.lexicon import DictionaryLexicon
from passpattern.dictionary.matcher import DictionaryMatcher
from passpattern.models import Evidence, EvidenceKey, PatternMatch
from passpattern.native import PreparedPassword

_MAX_SUFFIX_LENGTH = 128


@dataclass(frozen=True, slots=True)
class DictionaryCompoundDetector:
    """Find dictionary words followed by bounded ASCII digits or punctuation."""

    lexicon: DictionaryLexicon
    min_word_length: int = 3
    max_suffix_length: int = 16
    _matcher: DictionaryMatcher = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.lexicon, DictionaryLexicon):
            raise TypeError("lexicon must be a DictionaryLexicon.")
        if (
            isinstance(self.min_word_length, bool)
            or not isinstance(self.min_word_length, int)
            or self.min_word_length < self.lexicon.min_word_length
            or self.min_word_length > self.lexicon.max_word_length
        ):
            raise ValueError("min_word_length must be within the lexicon word-length limits.")
        if (
            isinstance(self.max_suffix_length, bool)
            or not isinstance(self.max_suffix_length, int)
            or not 1 <= self.max_suffix_length <= _MAX_SUFFIX_LENGTH
        ):
            raise ValueError(f"max_suffix_length must be between 1 and {_MAX_SUFFIX_LENGTH}.")
        object.__setattr__(self, "_matcher", DictionaryMatcher(self.lexicon))

    @property
    def detector_id(self) -> str:
        return "dictionary.compound"

    @property
    def required_normalization(self) -> TextNormalization:
        return self.lexicon.normalization

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        for word_match in self._matcher.find_matches(
            text,
            min_word_length=self.min_word_length,
        ):
            word_start = word_match.start_index
            word_end = word_match.end_index
            if word_start and _is_word_character(text[word_start - 1]):
                continue

            suffix_end = word_end
            while (
                suffix_end < len(text)
                and suffix_end - word_end < self.max_suffix_length
                and _is_suffix_character(text[suffix_end])
            ):
                suffix_end += 1
            suffix_length = suffix_end - word_end
            if suffix_length == 0:
                continue
            if suffix_end < len(text) and _is_suffix_character(text[suffix_end]):
                continue
            if suffix_end < len(text) and _is_word_character(text[suffix_end]):
                continue

            word_evidence = {item.key: item.value for item in word_match.evidence}
            yield PatternMatch(
                detector_id=self.detector_id,
                category="dictionary",
                pattern_type="dictionary_compound",
                start_index=word_start,
                end_index=suffix_end,
                evidence=(
                    Evidence(EvidenceKey.LENGTH, suffix_end - word_start),
                    Evidence(EvidenceKey.RANK, word_evidence[EvidenceKey.RANK]),
                    Evidence(EvidenceKey.CASE_EXACT, word_evidence[EvidenceKey.CASE_EXACT]),
                    Evidence(EvidenceKey.COUNT, suffix_length),
                ),
            )


def _is_suffix_character(character: str) -> bool:
    return ("0" <= character <= "9") or (
        "!" <= character <= "/"
        or ":" <= character <= "@"
        or "[" <= character <= "`"
        or "{" <= character <= "~"
    )


def _is_word_character(character: str) -> bool:
    return character.isalnum() or unicodedata.category(character).startswith("M")
