"""Recognition of bounded physical walks on a US QWERTY keyboard."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from passpattern.contextual.keyboard_layout import US_QWERTY
from passpattern.models import Evidence, EvidenceKey, PatternMatch
from passpattern.native import PreparedPassword


@dataclass(frozen=True, slots=True)
class KeyboardWalkDetector:
    """Find maximal overlapping key paths with a bounded number of turns."""

    min_walk_length: int = 4
    max_turns: int = 1
    layout: str = "us_qwerty"

    def __post_init__(self) -> None:
        if (
            isinstance(self.min_walk_length, bool)
            or not isinstance(self.min_walk_length, int)
            or self.min_walk_length < 2
        ):
            raise ValueError("min_walk_length must be an integer of at least 2.")
        if (
            isinstance(self.max_turns, bool)
            or not isinstance(self.max_turns, int)
            or self.max_turns < 0
        ):
            raise ValueError("max_turns must be a non-negative integer.")
        if self.layout != "us_qwerty":
            raise ValueError("Only the 'us_qwerty' keyboard layout is supported.")

    @property
    def detector_id(self) -> str:
        return "contextual.keyboard_walk"

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        keys = tuple(_ascii_key(character) for character in text)
        edge_index = 0
        while edge_index < len(keys) - 1:
            direction = self._valid_edge(keys, edge_index)
            if direction is None:
                edge_index += 1
                continue

            run_start = edge_index
            directions: list[tuple[int, int]] = []
            while edge_index < len(keys) - 1:
                direction = self._valid_edge(keys, edge_index)
                if direction is None:
                    break
                if edge_index > run_start and keys[edge_index - 1] == keys[edge_index + 1]:
                    break
                directions.append(direction)
                edge_index += 1

            yield from self._emit_run(run_start, directions)

    @staticmethod
    def _valid_edge(
        keys: tuple[str | None, ...],
        index: int,
    ) -> tuple[int, int] | None:
        first = keys[index]
        second = keys[index + 1]
        if first is None or second is None or not US_QWERTY.are_neighbors(first, second):
            return None
        return US_QWERTY.direction(first, second)

    def _emit_run(
        self,
        run_start: int,
        directions: list[tuple[int, int]],
    ) -> Iterator[PatternMatch]:
        direction_groups: list[tuple[int, int]] = []
        for edge_offset, direction in enumerate(directions):
            if not direction_groups or directions[direction_groups[-1][0]] != direction:
                direction_groups.append((edge_offset, edge_offset + 1))
            else:
                first_edge, _ = direction_groups[-1]
                direction_groups[-1] = (first_edge, edge_offset + 1)

        max_groups = self.max_turns + 1
        group_count = len(direction_groups)
        window_size = min(max_groups, group_count)
        window_starts = range(group_count - window_size + 1)

        for first_group in window_starts:
            last_group = first_group + window_size - 1
            first_edge = direction_groups[first_group][0]
            last_edge_exclusive = direction_groups[last_group][1]
            start = run_start + first_edge
            end = run_start + last_edge_exclusive + 1
            if end - start < self.min_walk_length:
                continue
            turns = window_size - 1
            yield PatternMatch(
                detector_id=self.detector_id,
                category="contextual",
                pattern_type="keyboard_walk",
                start_index=start,
                end_index=end,
                evidence=(
                    Evidence(EvidenceKey.LENGTH, end - start),
                    Evidence(EvidenceKey.COUNT, turns),
                ),
            )


def _ascii_key(character: str) -> str | None:
    if "A" <= character <= "Z":
        return chr(ord(character) + 32)
    if ("a" <= character <= "z") or ("0" <= character <= "9"):
        return character
    return None
