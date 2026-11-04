"""Reusable trie and Aho-Corasick primitives for dictionary transformations."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from passpattern.dictionary.entries import DictionaryEntry


@dataclass(slots=True)
class _MutableNode:
    transitions: dict[str, int]
    entries: list[DictionaryEntry]
    depth: int


@dataclass(frozen=True, slots=True)
class TransformationNode:
    """Immutable compiled trie node."""

    transitions: Mapping[str, int]
    entries: tuple[DictionaryEntry, ...]
    failure: int
    output_link: int
    depth: int


@dataclass(frozen=True, slots=True)
class TransformationAutomaton:
    """Immutable trie with failure and output links for compiled dictionary keys."""

    nodes: tuple[TransformationNode, ...]

    def __init__(self, items: Iterable[tuple[str, DictionaryEntry]]) -> None:
        mutable_nodes = [_MutableNode({}, [], 0)]
        for key, entry in items:
            if not key:
                continue
            state = 0
            for character in key:
                child = mutable_nodes[state].transitions.get(character)
                if child is None:
                    child = len(mutable_nodes)
                    mutable_nodes[state].transitions[character] = child
                    mutable_nodes.append(_MutableNode({}, [], mutable_nodes[state].depth + 1))
                state = child
            mutable_nodes[state].entries.append(entry)

        failures = [0] * len(mutable_nodes)
        output_links = [-1] * len(mutable_nodes)
        queue: deque[int] = deque(mutable_nodes[0].transitions.values())
        while queue:
            state = queue.popleft()
            for character, child in mutable_nodes[state].transitions.items():
                queue.append(child)
                failure = failures[state]
                while failure and character not in mutable_nodes[failure].transitions:
                    failure = failures[failure]
                failures[child] = mutable_nodes[failure].transitions.get(character, 0)
                failure_state = failures[child]
                output_links[child] = (
                    failure_state
                    if mutable_nodes[failure_state].entries
                    else output_links[failure_state]
                )

        object.__setattr__(
            self,
            "nodes",
            tuple(
                TransformationNode(
                    transitions=MappingProxyType(dict(node.transitions)),
                    entries=tuple(sorted(node.entries, key=_entry_order)),
                    failure=failures[index],
                    output_link=output_links[index],
                    depth=node.depth,
                )
                for index, node in enumerate(mutable_nodes)
            ),
        )


def fold_ascii_character(character: str) -> str:
    if "A" <= character <= "Z":
        return chr(ord(character) + 32)
    return character


def entry_order(entry: DictionaryEntry) -> tuple[int, str, str]:
    return entry.rank, entry.word, entry.source_id or ""


def _entry_order(entry: DictionaryEntry) -> tuple[int, str, str]:
    return entry_order(entry)
