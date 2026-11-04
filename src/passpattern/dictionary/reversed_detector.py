"""Detection of dictionary words written in reversed code-point order."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from passpattern.config import TextNormalization
from passpattern.dictionary.entries import DictionaryEntry
from passpattern.dictionary.lexicon import DictionaryLexicon
from passpattern.dictionary.transformations import (
    TransformationAutomaton,
    fold_ascii_character,
)
from passpattern.models import Evidence, EvidenceKey, PatternMatch
from passpattern.native import PreparedPassword


@dataclass(frozen=True, slots=True)
class ReversedWordDetector:
    """Find embedded reversed dictionary words, skipping case-insensitive palindromes."""

    lexicon: DictionaryLexicon
    min_word_length: int = 4
    _automaton: TransformationAutomaton = field(init=False, repr=False, compare=False)
    _exact_entries: Mapping[str, DictionaryEntry] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.lexicon, DictionaryLexicon):
            raise TypeError("lexicon must be a DictionaryLexicon.")
        if (
            isinstance(self.min_word_length, bool)
            or not isinstance(self.min_word_length, int)
            or self.min_word_length < 1
            or self.min_word_length > self.lexicon.max_word_length
        ):
            raise ValueError("min_word_length must be within the lexicon word-length limits.")

        items = []
        exact_entries = {}
        for entry in self.lexicon.entries:
            folded_word = "".join(fold_ascii_character(char) for char in entry.word)
            reversed_word = entry.word[::-1]
            folded_reversed = "".join(fold_ascii_character(char) for char in reversed_word)
            if len(entry.word) >= self.min_word_length and folded_word != folded_reversed:
                items.append((folded_reversed, entry))
                exact_entries[reversed_word] = entry
        object.__setattr__(self, "_automaton", TransformationAutomaton(items))
        object.__setattr__(self, "_exact_entries", MappingProxyType(exact_entries))

    @property
    def detector_id(self) -> str:
        return "dictionary.reversed_word"

    @property
    def required_normalization(self) -> TextNormalization:
        return self.lexicon.normalization

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        nodes = self._automaton.nodes
        state = 0
        for end_index, character in enumerate(text, start=1):
            folded = fold_ascii_character(character)
            while state and folded not in nodes[state].transitions:
                state = nodes[state].failure
            state = nodes[state].transitions.get(folded, 0)

            output_state = state
            while output_state >= 0:
                node = nodes[output_state]
                if node.entries and node.depth >= self.min_word_length:
                    start_index = end_index - node.depth
                    selected = self._exact_entries.get(text[start_index:end_index])
                    if selected is None:
                        selected = node.entries[0]
                    yield PatternMatch(
                        detector_id=self.detector_id,
                        category="dictionary",
                        pattern_type="reversed_word",
                        start_index=start_index,
                        end_index=end_index,
                        evidence=(
                            Evidence(EvidenceKey.LENGTH, node.depth),
                            Evidence(EvidenceKey.RANK, selected.rank),
                        ),
                    )
                output_state = node.output_link
