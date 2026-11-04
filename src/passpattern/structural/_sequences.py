"""Shared linear-time logic for fixed-step ASCII sequence detectors."""

from __future__ import annotations

from collections.abc import Callable, Iterator

from passpattern.models import Evidence, EvidenceKey, PatternMatch


def detect_sequences(
    text: str,
    detector_id: str,
    pattern_type: str,
    minimum_length: int,
    value_for: Callable[[str], int | None],
) -> Iterator[PatternMatch]:
    start = 0
    direction = 0

    for index in range(len(text) - 1):
        left = value_for(text[index])
        right = value_for(text[index + 1])
        step = 0 if left is None or right is None else right - left
        if step not in (-1, 1):
            match = _sequence_match(
                detector_id, pattern_type, start, index + 1, direction, minimum_length
            )
            if match is not None:
                yield match
            direction = 0
            continue

        if direction == 0:
            start = index
            direction = step
        elif step != direction:
            match = _sequence_match(
                detector_id, pattern_type, start, index + 1, direction, minimum_length
            )
            if match is not None:
                yield match
            start = index
            direction = step

    match = _sequence_match(detector_id, pattern_type, start, len(text), direction, minimum_length)
    if match is not None:
        yield match


def _sequence_match(
    detector_id: str,
    pattern_type: str,
    start: int,
    end: int,
    direction: int,
    minimum_length: int,
) -> PatternMatch | None:
    if direction == 0 or end - start < minimum_length:
        return None
    return PatternMatch(
        detector_id=detector_id,
        category="structural",
        pattern_type=pattern_type,
        start_index=start,
        end_index=end,
        evidence=(
            Evidence(EvidenceKey.LENGTH, end - start),
            Evidence(EvidenceKey.DIRECTION, direction),
        ),
    )
