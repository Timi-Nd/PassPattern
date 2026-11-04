"""Deterministic, bounded detection of mathematical ASCII digit sequences."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from passpattern.errors import NumericSequenceLimitError
from passpattern.models import (
    Evidence,
    EvidenceKey,
    NumericPatternMatch,
    NumericTerm,
    PatternMatch,
)
from passpattern.native import PreparedPassword
from passpattern.structural._sequences import detect_sequences
from passpattern.structural._validation import validate_minimum
from passpattern.structural.numeric_interpretation import is_ascii_digit, iter_digit_runs
from passpattern.structural.numeric_patterns import (
    NumericCandidate,
    find_numeric_candidates,
)

_EXPERIMENTAL_FAMILIES = frozenset({"geometric_progression", "fibonacci_like_progression"})


@dataclass(frozen=True, slots=True)
class NumericSequenceDetector:
    """Find legacy ±1 digit runs and bounded mathematical sequences."""

    min_sequence_length: int = 3
    max_digit_run: int = 32
    max_term_digits: int = 6
    max_term_value: int = 999_999
    max_terms: int = 8
    max_candidates: int = 8192
    max_work: int = 100_000
    experimental_families: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        validate_minimum(self.min_sequence_length, "min_sequence_length")
        _validate_limit(self.max_digit_run, "max_digit_run", 1, 32)
        _validate_limit(self.max_term_digits, "max_term_digits", 1, 6)
        _validate_limit(self.max_term_value, "max_term_value", 1, 999_999)
        _validate_limit(self.max_terms, "max_terms", 4, 16)
        _validate_limit(self.max_candidates, "max_candidates", 1, 32_768)
        _validate_limit(self.max_work, "max_work", 1, 100_000)
        families = frozenset(self.experimental_families)
        if not families.issubset(_EXPERIMENTAL_FAMILIES):
            raise ValueError("experimental_families contains an unsupported family.")
        object.__setattr__(self, "experimental_families", families)

    @property
    def detector_id(self) -> str:
        return "structural.numeric_sequence"

    def detect(self, prepared_password: PreparedPassword) -> Iterator[PatternMatch]:
        text = prepared_password.processed_text
        runs = tuple(iter_digit_runs(text))
        if any(run.end_index - run.start_index > self.max_digit_run for run in runs):
            raise NumericSequenceLimitError(
                "A numeric digit run exceeded the configured maximum length."
            )

        candidates = [
            _legacy_candidate(match, text)
            for match in detect_sequences(
                text,
                self.detector_id,
                "numeric_sequence",
                self.min_sequence_length,
                _ascii_digit_value,
            )
        ]
        candidates.extend(
            find_numeric_candidates(
                text,
                runs,
                max_term_digits=self.max_term_digits,
                max_term_value=self.max_term_value,
                max_terms=self.max_terms,
                max_candidates=self.max_candidates,
                max_work=self.max_work,
                experimental_families=self.experimental_families,
            )
        )
        yield from _matches_from_candidates(self.detector_id, candidates)


def _validate_limit(value: int, name: str, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} through {maximum}.")


def _legacy_candidate(match: PatternMatch, text: str) -> NumericCandidate:
    direction = next(item.value for item in match.evidence if item.key is EvidenceKey.DIRECTION)
    terms = tuple(
        NumericTerm(ord(text[index]) - ord("0"), index, index + 1)
        for index in range(match.start_index, match.end_index)
    )
    return NumericCandidate("numeric_sequence", terms, int(direction), 1, int(direction))


def _matches_from_candidates(
    detector_id: str,
    candidates: list[NumericCandidate],
) -> tuple[NumericPatternMatch, ...]:
    grouped: dict[
        tuple[str, int, int], dict[tuple[tuple[int, int, int], ...], NumericCandidate]
    ] = {}
    segmentations_by_span: dict[tuple[int, int], set[tuple[tuple[int, int, int], ...]]] = {}
    for candidate in candidates:
        key = (candidate.family, candidate.terms[0].start_index, candidate.terms[-1].end_index)
        segmentation = tuple(
            (term.start_index, term.end_index, term.value) for term in candidate.terms
        )
        grouped.setdefault(key, {})[segmentation] = candidate
        span = (candidate.terms[0].start_index, candidate.terms[-1].end_index)
        segmentations_by_span.setdefault(span, set()).add(segmentation)

    matches: list[NumericPatternMatch] = []
    for (family, start_index, end_index), interpretations in grouped.items():
        ambiguous = len(segmentations_by_span[(start_index, end_index)]) > 1
        candidate = min(
            interpretations.values(),
            key=lambda item: (
                -len(item.terms),
                tuple(term.start_index for term in item.terms),
                tuple(term.end_index for term in item.terms),
            ),
        )
        matches.append(
            NumericPatternMatch(
                detector_id=detector_id,
                category="structural",
                pattern_type=family,
                start_index=candidate.terms[0].start_index,
                end_index=candidate.terms[-1].end_index,
                evidence=(
                    Evidence(
                        EvidenceKey.LENGTH,
                        candidate.terms[-1].end_index - candidate.terms[0].start_index,
                    ),
                    Evidence(EvidenceKey.DIRECTION, candidate.direction),
                ),
                terms=candidate.terms,
                parameter_numerator=candidate.parameter_numerator,
                parameter_denominator=candidate.parameter_denominator,
                ambiguous=ambiguous,
            )
        )
    matches.sort(
        key=lambda match: (
            match.start_index,
            match.end_index,
            match.pattern_type,
            tuple((term.start_index, term.end_index, term.value) for term in match.terms),
        )
    )
    return tuple(matches)


def _ascii_digit_value(character: str) -> int | None:
    return ord(character) if is_ascii_digit(character) else None
