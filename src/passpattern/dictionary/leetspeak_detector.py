"""Bounded dictionary matching with directional leetspeak substitutions."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from passpattern.config import TextNormalization
from passpattern.dictionary.lexicon import DictionaryLexicon
from passpattern.dictionary.transformations import (
    TransformationAutomaton,
    entry_order,
    fold_ascii_character,
)
from passpattern.errors import DictionarySearchLimitError
from passpattern.models import Evidence, EvidenceKey, PatternMatch
from passpattern.native import PreparedPassword

DEFAULT_SUBSTITUTIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "@": ("a",),
        "4": ("a",),
        "0": ("o",),
        "3": ("e",),
        "5": ("s",),
        "$": ("s",),
        "7": ("t",),
        "1": ("i", "l"),
        "!": ("i",),
    }
)
_MAX_SUBSTITUTION_SOURCES = 64
_MAX_SUBSTITUTION_TARGETS = 8


@dataclass(frozen=True, slots=True)
class LeetspeakDetector:
    """Recognize bounded, length-preserving substitutions in dictionary words."""

    lexicon: DictionaryLexicon
    max_substitutions: int = 3
    min_word_length: int = 4
    substitutions: Mapping[str, tuple[str, ...]] = field(
        default_factory=lambda: DEFAULT_SUBSTITUTIONS
    )
    max_active_states: int = 4096
    max_work: int = 1_000_000
    _automaton: TransformationAutomaton = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.lexicon, DictionaryLexicon):
            raise TypeError("lexicon must be a DictionaryLexicon.")
        _positive_integer(self.max_substitutions, "max_substitutions")
        _positive_integer(self.min_word_length, "min_word_length")
        _positive_integer(self.max_active_states, "max_active_states")
        _positive_integer(self.max_work, "max_work")
        if self.min_word_length > self.lexicon.max_word_length:
            raise ValueError("min_word_length cannot exceed the lexicon maximum.")

        substitutions = _validate_substitutions(self.substitutions)
        object.__setattr__(self, "substitutions", MappingProxyType(substitutions))
        object.__setattr__(
            self,
            "_automaton",
            TransformationAutomaton(
                (ascii_fold_word(entry.word), entry)
                for entry in self.lexicon.entries
                if len(entry.word) >= self.min_word_length
            ),
        )

    @property
    def detector_id(self) -> str:
        return "dictionary.leetspeak"

    @property
    def required_normalization(self) -> TextNormalization:
        return self.lexicon.normalization

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        nodes = self._automaton.nodes
        work = 0
        for start_index in range(len(text)):
            active: dict[tuple[int, int], None] = {(0, 0): None}
            match_by_span: dict[tuple[int, int], tuple[int, int, str, str]] = {}
            max_end = min(len(text), start_index + self.lexicon.max_word_length)

            for end_index in range(start_index, max_end):
                interpretations = self._interpretations(text[end_index])
                next_active: dict[tuple[int, int], None] = {}
                for state, substitutions_used in active:
                    node = nodes[state]
                    for character, is_substitution in interpretations:
                        work += 1
                        if work > self.max_work:
                            raise DictionarySearchLimitError(
                                "Leetspeak matching exceeded its configured work limit."
                            )
                        transition = node.transitions.get(character)
                        if transition is None:
                            continue
                        next_count = substitutions_used + int(is_substitution)
                        if next_count > self.max_substitutions:
                            continue
                        key = (transition, next_count)
                        next_active[key] = None
                        if len(next_active) > self.max_active_states:
                            raise DictionarySearchLimitError(
                                "Leetspeak matching exceeded its configured active-state limit."
                            )

                        terminal = nodes[transition]
                        if next_count and terminal.entries:
                            end = end_index + 1
                            candidate = min(terminal.entries, key=entry_order)
                            span = (start_index, end)
                            candidate_tuple = (
                                next_count,
                                *entry_order(candidate),
                            )
                            current = match_by_span.get(span)
                            if current is None or candidate_tuple < current:
                                match_by_span[span] = candidate_tuple

                active = next_active
                if not active:
                    break

            for (match_start, end_index), (substitution_count, rank, _, _) in match_by_span.items():
                yield PatternMatch(
                    detector_id=self.detector_id,
                    category="dictionary",
                    pattern_type="leetspeak_word",
                    start_index=match_start,
                    end_index=end_index,
                    evidence=(
                        Evidence(EvidenceKey.LENGTH, end_index - match_start),
                        Evidence(EvidenceKey.RANK, rank),
                        Evidence(EvidenceKey.SUBSTITUTION_COUNT, substitution_count),
                    ),
                )

    def _interpretations(self, character: str) -> tuple[tuple[str, bool], ...]:
        folded = fold_ascii_character(character)
        interpretations = [(folded, False)]
        for replacement in self.substitutions.get(character, ()):
            if replacement != folded:
                interpretations.append((replacement, True))
        return tuple(interpretations)


def ascii_fold_word(word: str) -> str:
    return "".join(fold_ascii_character(character) for character in word)


def _validate_substitutions(
    substitutions: Mapping[str, object],
) -> dict[str, tuple[str, ...]]:
    if not isinstance(substitutions, Mapping):
        raise ValueError("substitutions must be a mapping.")
    if len(substitutions) > _MAX_SUBSTITUTION_SOURCES:
        raise ValueError("substitutions exceeds the supported number of source characters.")
    validated: dict[str, tuple[str, ...]] = {}
    for source, targets in substitutions.items():
        if (
            not isinstance(source, str)
            or len(source) != 1
            or "a" <= source <= "z"
            or "A" <= source <= "Z"
        ):
            raise ValueError("Each substitution source must be one non-letter code point.")
        if not isinstance(targets, (tuple, list)):
            raise ValueError("Each substitution target must be a collection of ASCII letters.")
        if len(targets) > _MAX_SUBSTITUTION_TARGETS:
            raise ValueError("Each source character exceeds the supported number of targets.")
        target_tuple: tuple[object, ...] = tuple(targets)
        if not target_tuple:
            raise ValueError("Each substitution target must be an ASCII letter.")
        validated_targets: list[str] = []
        for target in target_tuple:
            if (
                not isinstance(target, str)
                or len(target) != 1
                or not ("a" <= target <= "z" or "A" <= target <= "Z")
            ):
                raise ValueError("Each substitution target must be an ASCII letter.")
            validated_targets.append(target.lower())
        validated[source] = tuple(sorted(set(validated_targets)))
    return validated


def _positive_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
