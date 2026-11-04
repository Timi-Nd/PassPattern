"""Dictionary word detector over native-prepared password text."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from passpattern.config import TextNormalization
from passpattern.dictionary.lexicon import DictionaryLexicon
from passpattern.dictionary.matcher import DictionaryMatcher
from passpattern.models import PatternMatch
from passpattern.native import PreparedPassword


@dataclass(frozen=True, slots=True)
class DictionaryWordDetector:
    """Find ranked dictionary words embedded in prepared text."""

    lexicon: DictionaryLexicon
    min_word_length: int = 3
    _matcher: DictionaryMatcher = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.lexicon, DictionaryLexicon):
            raise TypeError("lexicon must be a DictionaryLexicon.")
        if (
            isinstance(self.min_word_length, bool)
            or not isinstance(self.min_word_length, int)
            or self.min_word_length < 1
        ):
            raise ValueError("min_word_length must be a positive integer.")
        if self.min_word_length < self.lexicon.min_word_length:
            raise ValueError("min_word_length cannot be below the lexicon minimum.")
        if self.min_word_length > self.lexicon.max_word_length:
            raise ValueError("min_word_length cannot exceed the lexicon maximum.")
        object.__setattr__(self, "_matcher", DictionaryMatcher(self.lexicon))

    @property
    def detector_id(self) -> str:
        return "dictionary.word"

    @property
    def required_normalization(self) -> TextNormalization:
        return self.lexicon.normalization

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        yield from self._matcher.find_matches(
            prepared_password.processed_text,
            min_word_length=self.min_word_length,
        )
