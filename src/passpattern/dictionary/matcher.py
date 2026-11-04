"""Reusable Aho-Corasick matcher for dictionary substring detection."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from passpattern.dictionary.entries import DictionaryEntry
from passpattern.dictionary.lexicon import DictionaryLexicon, ascii_fold
from passpattern.models import Evidence, EvidenceKey, PatternMatch

_DETECTOR_ID = "dictionary.word"


@dataclass(slots=True)
class _MutableNode:
    transitions: dict[str, int]
    entries: list[DictionaryEntry]
    depth: int


@dataclass(frozen=True, slots=True)
class _Node:
    transitions: Mapping[str, int]
    entries: tuple[DictionaryEntry, ...]
    failure: int
    output_link: int
    depth: int


@dataclass(frozen=True, slots=True)
class DictionaryMatcher:
    """An immutable automaton reusable across password analyses."""

    lexicon: DictionaryLexicon
    _nodes: tuple[_Node, ...]
    _exact_entries: Mapping[str, DictionaryEntry]

    def __init__(self, lexicon: DictionaryLexicon) -> None:
        if not isinstance(lexicon, DictionaryLexicon):
            raise TypeError("lexicon must be a DictionaryLexicon.")
        mutable_nodes = [_MutableNode({}, [], 0)]
        exact_entries = {entry.word: entry for entry in lexicon.entries}
        for entry in lexicon.entries:
            state = 0
            for character in ascii_fold(entry.word):
                next_state = mutable_nodes[state].transitions.get(character)
                if next_state is None:
                    next_state = len(mutable_nodes)
                    mutable_nodes[state].transitions[character] = next_state
                    mutable_nodes.append(_MutableNode({}, [], mutable_nodes[state].depth + 1))
                state = next_state
            mutable_nodes[state].entries.append(entry)

        failures = [0] * len(mutable_nodes)
        output_links = [-1] * len(mutable_nodes)
        queue: deque[int] = deque()
        for child in mutable_nodes[0].transitions.values():
            queue.append(child)

        while queue:
            state = queue.popleft()
            for character, child in mutable_nodes[state].transitions.items():
                queue.append(child)
                failure = failures[state]
                while failure and character not in mutable_nodes[failure].transitions:
                    failure = failures[failure]
                failures[child] = mutable_nodes[failure].transitions.get(character, 0)
                failure_state = failures[child]
                if mutable_nodes[failure_state].entries:
                    output_links[child] = failure_state
                else:
                    output_links[child] = output_links[failure_state]

        nodes = tuple(
            _Node(
                transitions=MappingProxyType(dict(node.transitions)),
                entries=tuple(sorted(node.entries, key=_candidate_order)),
                failure=failures[index],
                output_link=output_links[index],
                depth=node.depth,
            )
            for index, node in enumerate(mutable_nodes)
        )
        object.__setattr__(self, "lexicon", lexicon)
        object.__setattr__(self, "_nodes", nodes)
        object.__setattr__(self, "_exact_entries", MappingProxyType(exact_entries))

    def find_matches(
        self,
        processed_text: str,
        *,
        min_word_length: int = 1,
    ) -> Iterator[PatternMatch]:
        """Yield each matching span once, retaining overlapping dictionary words."""
        if not isinstance(processed_text, str):
            raise TypeError("processed_text must be a string.")
        if isinstance(min_word_length, bool) or not isinstance(min_word_length, int):
            raise ValueError("min_word_length must be a positive integer.")
        if min_word_length < 1:
            raise ValueError("min_word_length must be a positive integer.")

        state = 0
        for end_index, original_character in enumerate(processed_text, start=1):
            character = _fold_ascii_character(original_character)
            while state and character not in self._nodes[state].transitions:
                state = self._nodes[state].failure
            state = self._nodes[state].transitions.get(character, 0)

            output_state = state
            while output_state >= 0:
                node = self._nodes[output_state]
                if node.entries:
                    word_length = node.depth
                    if word_length >= min_word_length:
                        start_index = end_index - word_length
                        entry, exact_case = self._best_entry(
                            node.entries,
                            processed_text,
                            start_index,
                            end_index,
                            self._exact_entries,
                        )
                        yield PatternMatch(
                            detector_id=_DETECTOR_ID,
                            category="dictionary",
                            pattern_type="dictionary_word",
                            start_index=start_index,
                            end_index=end_index,
                            evidence=(
                                Evidence(EvidenceKey.LENGTH, word_length),
                                Evidence(EvidenceKey.RANK, entry.rank),
                                Evidence(EvidenceKey.CASE_EXACT, exact_case),
                            ),
                        )
                output_state = node.output_link

    @staticmethod
    def _best_entry(
        entries: tuple[DictionaryEntry, ...],
        processed_text: str,
        start_index: int,
        end_index: int,
        exact_entries: Mapping[str, DictionaryEntry],
    ) -> tuple[DictionaryEntry, bool]:
        exact_entry = exact_entries.get(processed_text[start_index:end_index])
        if exact_entry is not None:
            return exact_entry, True
        return entries[0], False


def _fold_ascii_character(character: str) -> str:
    if "A" <= character <= "Z":
        return chr(ord(character) + 32)
    return character


def _candidate_order(entry: DictionaryEntry) -> tuple[int, str, str]:
    return entry.rank, entry.word, entry.source_id or ""
