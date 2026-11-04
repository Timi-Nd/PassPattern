"""Bounded mathematical relation detection over interpreted numeric terms."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from math import gcd, isqrt

from passpattern.errors import NumericSequenceLimitError
from passpattern.models import NumericTerm
from passpattern.structural.numeric_interpretation import (
    DigitRun,
    can_extend_left,
    iter_terms_at,
    term_matches_at,
)


@dataclass(frozen=True, slots=True)
class NumericCandidate:
    family: str
    terms: tuple[NumericTerm, ...]
    parameter_numerator: int | None
    parameter_denominator: int | None
    direction: int


class _WorkBudget:
    def __init__(self, max_candidates: int, max_work: int) -> None:
        self.max_candidates = max_candidates
        self.max_work = max_work
        self.candidate_count = 0
        self.work = 0

    def tick(self) -> None:
        self.work += 1
        if self.work > self.max_work:
            raise NumericSequenceLimitError("Numeric sequence analysis exceeded its work limit.")

    def add_candidate(self) -> None:
        self.candidate_count += 1
        if self.candidate_count > self.max_candidates:
            raise NumericSequenceLimitError(
                "Numeric sequence analysis exceeded its candidate limit."
            )


def find_numeric_candidates(
    text: str,
    runs: Iterable[DigitRun],
    *,
    max_term_digits: int,
    max_term_value: int,
    max_terms: int,
    max_candidates: int,
    max_work: int,
    experimental_families: frozenset[str],
) -> tuple[NumericCandidate, ...]:
    budget = _WorkBudget(max_candidates, max_work)
    candidates: list[NumericCandidate] = []
    seen: set[tuple[str, tuple[tuple[int, int, int], ...]]] = set()

    for run in runs:
        _find_arithmetic_candidates(
            text, run, budget, candidates, seen, max_term_digits, max_term_value, max_terms
        )
        _find_prime_candidates(
            text, run, budget, candidates, seen, max_term_digits, max_term_value, max_terms
        )
        if "geometric_progression" in experimental_families:
            _find_geometric_candidates(
                text, run, budget, candidates, seen, max_term_digits, max_term_value, max_terms
            )
        if "fibonacci_like_progression" in experimental_families:
            _find_fibonacci_candidates(
                text, run, budget, candidates, seen, max_term_digits, max_term_value, max_terms
            )
    return tuple(candidates)


def _find_arithmetic_candidates(
    text: str,
    run: DigitRun,
    budget: _WorkBudget,
    candidates: list[NumericCandidate],
    seen: set[tuple[str, tuple[tuple[int, int, int], ...]]],
    max_term_digits: int,
    max_term_value: int,
    max_terms: int,
) -> None:
    for start_index in range(run.start_index, run.end_index):
        for first in iter_terms_at(
            text, start_index, run.end_index, max_term_digits, max_term_value
        ):
            budget.tick()
            for second in iter_terms_at(
                text, first.end_index, run.end_index, max_term_digits, max_term_value
            ):
                budget.tick()
                difference = second.value - first.value
                if difference in (-1, 0, 1):
                    continue

                def next_arithmetic(values: list[int], step: int = difference) -> int:
                    return values[-1] + step

                terms = _extend_terms(
                    text,
                    run.end_index,
                    (first, second),
                    next_arithmetic,
                    max_terms,
                    max_term_digits,
                    max_term_value,
                    budget,
                )
                if len(terms) >= 4 and not can_extend_left(
                    text,
                    first,
                    first.value - difference,
                    run.start_index,
                    max_term_digits,
                    max_term_value,
                ):
                    _add_candidate(
                        NumericCandidate(
                            "arithmetic_progression",
                            terms,
                            difference,
                            1,
                            1 if difference > 0 else -1,
                        ),
                        candidates,
                        seen,
                        budget,
                    )


def _find_prime_candidates(
    text: str,
    run: DigitRun,
    budget: _WorkBudget,
    candidates: list[NumericCandidate],
    seen: set[tuple[str, tuple[tuple[int, int, int], ...]]],
    max_term_digits: int,
    max_term_value: int,
    max_terms: int,
) -> None:
    for start_index in range(run.start_index, run.end_index):
        for first in iter_terms_at(
            text, start_index, run.end_index, max_term_digits, max_term_value
        ):
            budget.tick()
            if not _is_prime(first.value, budget):
                continue
            second_value = _adjacent_prime(first.value, 1, max_term_value, budget)
            if second_value is None:
                continue
            second = term_matches_at(text, first.end_index, run.end_index, second_value)
            if second is None:
                continue

            def next_prime(_values: list[int]) -> int | None:
                return _adjacent_prime(_values[-1], 1, max_term_value, budget)

            terms = _extend_terms(
                text,
                run.end_index,
                (first, second),
                next_prime,
                max_terms,
                max_term_digits,
                max_term_value,
                budget,
            )
            if len(terms) >= 4 and not can_extend_left(
                text,
                first,
                _adjacent_prime(first.value, -1, max_term_value, budget) or -1,
                run.start_index,
                max_term_digits,
                max_term_value,
            ):
                _add_candidate(
                    NumericCandidate("consecutive_prime_sequence", terms, None, None, 1),
                    candidates,
                    seen,
                    budget,
                )


def _find_geometric_candidates(
    text: str,
    run: DigitRun,
    budget: _WorkBudget,
    candidates: list[NumericCandidate],
    seen: set[tuple[str, tuple[tuple[int, int, int], ...]]],
    max_term_digits: int,
    max_term_value: int,
    max_terms: int,
) -> None:
    for start_index in range(run.start_index, run.end_index):
        for first in iter_terms_at(
            text, start_index, run.end_index, max_term_digits, max_term_value
        ):
            budget.tick()
            if first.value == 0:
                continue
            for second in iter_terms_at(
                text, first.end_index, run.end_index, max_term_digits, max_term_value
            ):
                budget.tick()
                if second.value == 0 or first.value == second.value:
                    continue
                divisor = gcd(first.value, second.value)
                numerator = second.value // divisor
                denominator = first.value // divisor

                def next_geometric(
                    values: list[int],
                    ratio_numerator: int = numerator,
                    ratio_denominator: int = denominator,
                ) -> int | None:
                    product = values[-1] * ratio_numerator
                    if product % ratio_denominator:
                        return None
                    return product // ratio_denominator

                terms = _extend_terms(
                    text,
                    run.end_index,
                    (first, second),
                    next_geometric,
                    max_terms,
                    max_term_digits,
                    max_term_value,
                    budget,
                )
                if len(terms) >= 4:
                    previous_product = first.value * denominator
                    if previous_product % numerator:
                        continue
                    previous = previous_product // numerator
                    if can_extend_left(
                        text,
                        first,
                        previous,
                        run.start_index,
                        max_term_digits,
                        max_term_value,
                    ):
                        continue
                    _add_candidate(
                        NumericCandidate(
                            "geometric_progression",
                            terms,
                            numerator,
                            denominator,
                            1 if numerator > denominator else -1,
                        ),
                        candidates,
                        seen,
                        budget,
                    )


def _find_fibonacci_candidates(
    text: str,
    run: DigitRun,
    budget: _WorkBudget,
    candidates: list[NumericCandidate],
    seen: set[tuple[str, tuple[tuple[int, int, int], ...]]],
    max_term_digits: int,
    max_term_value: int,
    max_terms: int,
) -> None:
    for start_index in range(run.start_index, run.end_index):
        for first in iter_terms_at(
            text, start_index, run.end_index, max_term_digits, max_term_value
        ):
            budget.tick()
            for second in iter_terms_at(
                text, first.end_index, run.end_index, max_term_digits, max_term_value
            ):
                budget.tick()
                if second.value < first.value or first.value + second.value == 0:
                    continue
                terms = _extend_terms(
                    text,
                    run.end_index,
                    (first, second),
                    lambda values: values[-1] + values[-2],
                    max_terms,
                    max_term_digits,
                    max_term_value,
                    budget,
                )
                if len(terms) >= 6 and not can_extend_left(
                    text,
                    first,
                    second.value - first.value,
                    run.start_index,
                    max_term_digits,
                    max_term_value,
                ):
                    _add_candidate(
                        NumericCandidate(
                            "fibonacci_like_progression",
                            terms,
                            None,
                            None,
                            1,
                        ),
                        candidates,
                        seen,
                        budget,
                    )


def _extend_terms(
    text: str,
    run_end: int,
    initial_terms: tuple[NumericTerm, NumericTerm],
    next_value: Callable[[list[int]], int | None],
    max_terms: int,
    max_term_digits: int,
    max_term_value: int,
    budget: _WorkBudget,
) -> tuple[NumericTerm, ...]:
    terms = list(initial_terms)
    while len(terms) < max_terms:
        budget.tick()
        value = next_value([term.value for term in terms])
        if value is None or value > max_term_value or len(str(value)) > max_term_digits:
            return tuple(terms)
        next_term = term_matches_at(text, terms[-1].end_index, run_end, value)
        if next_term is None:
            return tuple(terms)
        terms.append(next_term)
    budget.tick()
    value = next_value([term.value for term in terms])
    if value is not None and value <= max_term_value and len(str(value)) <= max_term_digits:
        if term_matches_at(text, terms[-1].end_index, run_end, value) is not None:
            raise NumericSequenceLimitError(
                "A numeric sequence exceeded the configured maximum term count."
            )
    return tuple(terms)


def _add_candidate(
    candidate: NumericCandidate,
    candidates: list[NumericCandidate],
    seen: set[tuple[str, tuple[tuple[int, int, int], ...]]],
    budget: _WorkBudget,
) -> None:
    key = (
        candidate.family,
        tuple((term.start_index, term.end_index, term.value) for term in candidate.terms),
    )
    if key in seen:
        return
    budget.add_candidate()
    seen.add(key)
    candidates.append(candidate)


def _is_prime(value: int, budget: _WorkBudget) -> bool:
    if value < 2:
        return False
    for divisor in range(2, isqrt(value) + 1):
        budget.tick()
        if value % divisor == 0:
            return False
    return True


def _adjacent_prime(
    value: int,
    direction: int,
    max_value: int,
    budget: _WorkBudget,
) -> int | None:
    candidate = value + direction
    if direction > 0:
        if candidate <= 2:
            return 2
        if candidate % 2 == 0:
            candidate += 1
        while candidate <= max_value:
            if _is_prime(candidate, budget):
                return candidate
            candidate += 2
        return None

    while candidate >= 2:
        if candidate == 2 or candidate % 2 == 1:
            if _is_prime(candidate, budget):
                return candidate
        candidate -= 1
    return None
