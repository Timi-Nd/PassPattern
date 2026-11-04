from dataclasses import dataclass

import pytest

from passpattern import (
    EngineConfig,
    EvidenceKey,
    NumericPatternMatch,
    NumericSequenceLimitError,
    PassPatternEngine,
    TooManyMatchesError,
)
from passpattern.structural import (
    AlphabeticSequenceDetector,
    NumericSequenceDetector,
    RepeatedCharacterDetector,
    RepeatedSubstringDetector,
    default_structural_detectors,
)


@dataclass(frozen=True)
class Prepared:
    processed_text: str


def detect(detector, text: str):
    return tuple(detector.detect(Prepared(text)))


def spans(matches):
    return [(match.start_index, match.end_index) for match in matches]


def evidence(match, key: EvidenceKey):
    return next(item.value for item in match.evidence if item.key is key)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("aaa", [(0, 3)]),
        ("1111", [(0, 4)]),
        ("!!!!", [(0, 4)]),
        ("\U0001f642\U0001f642\U0001f642", [(0, 3)]),
        ("\u732b\u732b\u732b", [(0, 3)]),
        ("aaabbb", [(0, 3), (3, 6)]),
        ("abc", []),
        ("aa", []),
        ("AaA", []),
    ],
)
def test_repeated_characters_detect_maximal_codepoint_runs(text: str, expected) -> None:
    matches = detect(RepeatedCharacterDetector(), text)

    assert spans(matches) == expected
    assert all(match.category == "structural" for match in matches)
    assert all(match.pattern_type == "repeated_character" for match in matches)


def test_repeated_character_threshold_and_count_evidence() -> None:
    detector = RepeatedCharacterDetector(min_repetitions=4)

    assert detect(detector, "aaa") == ()
    matches = detect(detector, "aaaaa")

    assert spans(matches) == [(0, 5)]
    assert evidence(matches[0], EvidenceKey.COUNT) == 5


def test_repeated_character_maximal_run_is_one_match() -> None:
    matches = detect(RepeatedCharacterDetector(), "a" * 1024)

    assert spans(matches) == [(0, 1024)]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RepeatedCharacterDetector(min_repetitions=1),
        lambda: RepeatedCharacterDetector(min_repetitions=0),
        lambda: RepeatedCharacterDetector(min_repetitions=True),
        lambda: RepeatedSubstringDetector(min_unit_length=1),
        lambda: RepeatedSubstringDetector(min_repetitions=0),
        lambda: NumericSequenceDetector(min_sequence_length=1),
        lambda: NumericSequenceDetector(max_digit_run=0),
        lambda: NumericSequenceDetector(max_digit_run=33),
        lambda: NumericSequenceDetector(max_term_digits=True),
        lambda: NumericSequenceDetector(max_term_value=1_000_000),
        lambda: NumericSequenceDetector(max_terms=17),
        lambda: NumericSequenceDetector(max_candidates=32_769),
        lambda: NumericSequenceDetector(max_work=100_001),
        lambda: NumericSequenceDetector(experimental_families=frozenset({"unknown"})),
        lambda: AlphabeticSequenceDetector(min_sequence_length=-1),
    ],
)
def test_detectors_reject_invalid_thresholds(factory) -> None:
    with pytest.raises(ValueError):
        factory()


def test_repeated_substrings_recognize_two_and_three_repetitions() -> None:
    detector = RepeatedSubstringDetector()

    two = detect(detector, "abab")
    three = detect(detector, "abcabcabc")

    assert (0, 4) in spans(two)
    assert any(evidence(match, EvidenceKey.COUNT) == 2 for match in two)
    assert (0, 9) in spans(three)
    assert any(
        spans((match,)) == [(0, 9)]
        and evidence(match, EvidenceKey.COUNT) == 3
        and evidence(match, EvidenceKey.LENGTH) == 3
        for match in three
    )


def test_repeated_substrings_use_primitive_units_and_deduplicate() -> None:
    matches = detect(RepeatedSubstringDetector(), "abcabcabc")

    assert not any(
        match.start_index == 0 and evidence(match, EvidenceKey.LENGTH) == 6 for match in matches
    )
    assert len(
        {
            (
                match.start_index,
                match.end_index,
                evidence(match, EvidenceKey.LENGTH),
            )
            for match in matches
        }
    ) == len(matches)


def test_repeated_substrings_keep_legitimate_overlapping_occurrences() -> None:
    matches = detect(RepeatedSubstringDetector(), "abababa")
    match_spans = spans(matches)

    assert (0, 6) in match_spans
    assert (1, 7) in match_spans


def test_repeated_substrings_support_long_and_unicode_units() -> None:
    long_unit = "abcdefghij"
    long_matches = detect(RepeatedSubstringDetector(), long_unit * 2)
    unicode_matches = detect(RepeatedSubstringDetector(), "\U0001f642\u732b" * 3)

    assert any(
        spans((match,)) == [(0, 20)] and evidence(match, EvidenceKey.LENGTH) == 10
        for match in long_matches
    )
    assert any(
        spans((match,)) == [(0, 6)] and evidence(match, EvidenceKey.LENGTH) == 2
        for match in unicode_matches
    )


def test_repeated_substrings_respect_configured_minimums() -> None:
    detector = RepeatedSubstringDetector(min_unit_length=3, min_repetitions=3)

    assert detect(detector, "abab") == ()
    matches = detect(detector, "abcabcabc")
    assert any(spans((match,)) == [(0, 9)] for match in matches)


def test_repeated_substring_pathological_inputs_remain_bounded_and_lazy() -> None:
    alternating = "ab" * 512
    matches = detect(RepeatedSubstringDetector(), alternating)
    unique = "".join(chr(0x1000 + index) for index in range(1024))

    assert len(matches) <= len(alternating)
    assert detect(RepeatedSubstringDetector(), "a" * 1024) == ()
    assert detect(RepeatedSubstringDetector(), unique) == ()


def test_empty_and_single_codepoint_inputs_produce_no_structural_matches() -> None:
    for detector in default_structural_detectors():
        assert detect(detector, "") == ()
        assert detect(detector, "x") == ()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1234", [(0, 4, 1)]),
        ("9876", [(0, 4, -1)]),
        ("012345", [(0, 6, 1)]),
        ("654321", [(0, 6, -1)]),
        ("13579", [(0, 5, 1)]),
        ("1111", []),
        ("8901", []),
        ("\uff11\uff12\uff13", []),
        ("\u0661\u0662\u0663", []),
    ],
)
def test_numeric_sequences_are_ascii_maximal_runs(text: str, expected) -> None:
    matches = detect(NumericSequenceDetector(), text)

    assert [
        (match.start_index, match.end_index, evidence(match, EvidenceKey.DIRECTION))
        for match in matches
    ] == expected


def test_numeric_sequences_support_thresholds_multiple_runs_and_overlaps() -> None:
    minimum = NumericSequenceDetector(min_sequence_length=4)
    assert detect(minimum, "123") == ()
    assert spans(detect(minimum, "1234")) == [(0, 4)]

    matches = detect(NumericSequenceDetector(), "12321 4567")
    assert [(match.start_index, match.end_index) for match in matches] == [
        (0, 3),
        (2, 5),
        (6, 10),
    ]


@pytest.mark.parametrize(
    ("text", "family", "values", "parameter", "direction"),
    [
        ("1234", "numeric_sequence", (1, 2, 3, 4), (1, 1), 1),
        ("2468", "arithmetic_progression", (2, 4, 6, 8), (2, 1), 1),
        ("13579", "arithmetic_progression", (1, 3, 5, 7, 9), (2, 1), 1),
        ("8642", "arithmetic_progression", (8, 6, 4, 2), (-2, 1), -1),
        ("97531", "arithmetic_progression", (9, 7, 5, 3, 1), (-2, 1), -1),
        ("10121416", "arithmetic_progression", (10, 12, 14, 16), (2, 1), 1),
        ("20304050", "arithmetic_progression", (20, 30, 40, 50), (10, 1), 1),
        (
            "235711",
            "consecutive_prime_sequence",
            (2, 3, 5, 7, 11),
            None,
            1,
        ),
        (
            "11131719",
            "consecutive_prime_sequence",
            (11, 13, 17, 19),
            None,
            1,
        ),
    ],
)
def test_numeric_sequence_families_report_terms_and_relationship(
    text: str,
    family: str,
    values: tuple[int, ...],
    parameter: tuple[int, int] | None,
    direction: int,
) -> None:
    matches = detect(NumericSequenceDetector(), text)
    match = next(match for match in matches if match.pattern_type == family)

    assert isinstance(match, NumericPatternMatch)
    assert tuple(term.value for term in match.terms) == values
    assert tuple((term.start_index, term.end_index) for term in match.terms) == tuple(
        (
            sum(len(str(value)) for value in values[:index]),
            sum(len(str(value)) for value in values[: index + 1]),
        )
        for index in range(len(values))
    )
    assert (match.parameter_numerator, match.parameter_denominator) == (
        parameter if parameter is not None else (None, None)
    )
    assert evidence(match, EvidenceKey.DIRECTION) == direction
    assert not match.ambiguous


@pytest.mark.parametrize("text", ["2469", "235", "2359", "23513", "2235", "102030", "9999"])
def test_numeric_sequences_reject_non_sequences_and_short_prime_runs(text: str) -> None:
    assert detect(NumericSequenceDetector(), text) == ()


def test_numeric_sequences_preserve_legacy_subsequences() -> None:
    matches = detect(NumericSequenceDetector(), "1235")

    assert [(match.start_index, match.end_index) for match in matches] == [(0, 3)]


def test_experimental_numeric_families_are_separately_opt_in() -> None:
    assert detect(NumericSequenceDetector(), "24816") == ()
    assert not any(
        match.pattern_type == "fibonacci_like_progression"
        for match in detect(NumericSequenceDetector(), "11235813")
    )

    geometric = NumericSequenceDetector(experimental_families=frozenset({"geometric_progression"}))
    assert not any(
        match.pattern_type == "geometric_progression" for match in detect(geometric, "248")
    )
    geometric_match = next(
        match
        for match in detect(geometric, "24816")
        if match.pattern_type == "geometric_progression"
    )
    assert tuple(term.value for term in geometric_match.terms) == (2, 4, 8, 16)
    assert (geometric_match.parameter_numerator, geometric_match.parameter_denominator) == (2, 1)
    descending_geometric = next(
        match
        for match in detect(geometric, "16842")
        if match.pattern_type == "geometric_progression"
    )
    assert tuple(term.value for term in descending_geometric.terms) == (16, 8, 4, 2)
    assert (
        descending_geometric.parameter_numerator,
        descending_geometric.parameter_denominator,
    ) == (1, 2)
    assert evidence(descending_geometric, EvidenceKey.DIRECTION) == -1

    fibonacci = NumericSequenceDetector(
        experimental_families=frozenset({"fibonacci_like_progression"})
    )
    assert not any(
        match.pattern_type == "fibonacci_like_progression" for match in detect(fibonacci, "11235")
    )
    fibonacci_match = next(
        match
        for match in detect(fibonacci, "11235813")
        if match.pattern_type == "fibonacci_like_progression"
    )
    assert tuple(term.value for term in fibonacci_match.terms) == (1, 1, 2, 3, 5, 8, 13)


def test_numeric_sequences_define_leading_zero_and_ascii_behavior() -> None:
    assert detect(NumericSequenceDetector(), "0123")[0].pattern_type == "numeric_sequence"
    assert detect(NumericSequenceDetector(), "010203") == ()
    text = "01020304"
    match = next(
        match
        for match in detect(NumericSequenceDetector(), text)
        if match.pattern_type == "arithmetic_progression"
    )
    assert tuple(term.value for term in match.terms) == (0, 10, 20, 30)
    assert all(text[term.start_index : term.end_index] == str(term.value) for term in match.terms)
    assert detect(NumericSequenceDetector(), "\u0662\u0664\u0668") == ()


def test_numeric_sequences_preserve_embedded_unicode_codepoint_offsets() -> None:
    text = "\U0001f512x2468y"
    match = next(
        match
        for match in detect(NumericSequenceDetector(), text)
        if match.pattern_type == "arithmetic_progression"
    )

    assert (match.start_index, match.end_index) == (2, 6)
    assert [(term.start_index, term.end_index) for term in match.terms] == [
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
    ]


def test_numeric_sequence_limits_are_explicit_and_bounded() -> None:
    NumericSequenceDetector(
        max_digit_run=32,
        max_term_digits=6,
        max_term_value=999_999,
        max_terms=16,
        max_candidates=32_768,
        max_work=100_000,
    )
    NumericSequenceDetector(
        max_digit_run=1,
        max_term_digits=1,
        max_term_value=1,
        max_terms=4,
        max_candidates=1,
        max_work=1,
    )
    assert detect(NumericSequenceDetector(max_digit_run=4), "2468")
    with pytest.raises(NumericSequenceLimitError):
        detect(NumericSequenceDetector(max_digit_run=4), "24680")
    with pytest.raises(NumericSequenceLimitError):
        detect(NumericSequenceDetector(max_work=1), "2468")
    assert detect(NumericSequenceDetector(max_term_value=8), "2468")
    one_digit_terms = detect(NumericSequenceDetector(max_term_digits=1), "24681012")
    assert tuple(
        term.value
        for match in one_digit_terms
        if match.pattern_type == "arithmetic_progression"
        for term in match.terms
    ) == (2, 4, 6, 8)
    bounded_terms = detect(NumericSequenceDetector(max_term_value=8), "108642")
    assert any(
        match.pattern_type == "arithmetic_progression"
        and (match.start_index, match.end_index) == (2, 6)
        for match in bounded_terms
    )
    assert not any(
        match.pattern_type == "arithmetic_progression"
        for match in detect(NumericSequenceDetector(max_term_value=9), "10121416")
    )
    with pytest.raises(NumericSequenceLimitError):
        detect(NumericSequenceDetector(max_terms=4), "24681012")
    with pytest.raises(NumericSequenceLimitError):
        detect(NumericSequenceDetector(max_candidates=1), "2468-13579")
    assert detect(NumericSequenceDetector(), "1" * 32) == ()


def test_engine_propagates_numeric_sequence_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    engine = PassPatternEngine((NumericSequenceDetector(max_digit_run=3),))

    with pytest.raises(NumericSequenceLimitError):
        engine.analyze("1234")


def test_numeric_sequence_output_is_deterministic_and_deduplicated() -> None:
    detector = NumericSequenceDetector()
    first = detect(detector, "x2468y")
    second = detect(detector, "x2468y")

    assert first == second
    assert sum(match.pattern_type == "arithmetic_progression" for match in first) == 1


def test_numeric_sequence_segmentation_ambiguity_is_reported() -> None:
    matches = detect(NumericSequenceDetector(), "12345678")
    ambiguous_matches = [match for match in matches if match.end_index == 8]

    assert {match.pattern_type for match in ambiguous_matches} == {
        "arithmetic_progression",
        "numeric_sequence",
    }
    assert all(match.ambiguous for match in ambiguous_matches)
    assert tuple(
        term.value
        for match in ambiguous_matches
        if match.pattern_type == "arithmetic_progression"
        for term in match.terms
    ) == (12, 34, 56, 78)


def test_numeric_sequence_preserves_two_term_legacy_threshold() -> None:
    matches = detect(NumericSequenceDetector(min_sequence_length=2), "12")

    assert len(matches) == 1
    assert tuple(term.value for term in matches[0].terms) == (1, 2)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("abcd", [(0, 4, 1)]),
        ("zyxw", [(0, 4, -1)]),
        ("ABCDEF", [(0, 6, 1)]),
        ("aBcD", [(0, 4, 1)]),
        ("mnop", [(0, 4, 1)]),
        ("qwerty", []),
        ("yza", []),
        ("\u00e9\u00ea\u00eb", []),
        ("\u0430\u0431\u0432", []),
    ],
)
def test_alphabetic_sequences_are_ascii_case_insensitive_runs(text: str, expected) -> None:
    matches = detect(AlphabeticSequenceDetector(), text)

    assert [
        (match.start_index, match.end_index, evidence(match, EvidenceKey.DIRECTION))
        for match in matches
    ] == expected


def test_alphabetic_sequences_support_thresholds_and_direction_changes() -> None:
    minimum = AlphabeticSequenceDetector(min_sequence_length=4)
    assert detect(minimum, "abc") == ()
    assert spans(detect(minimum, "abcd")) == [(0, 4)]

    matches = detect(AlphabeticSequenceDetector(), "abcba")
    assert spans(matches) == [(0, 3), (2, 5)]


def test_default_detector_factory_returns_independent_detector_instances() -> None:
    first = default_structural_detectors()
    second = default_structural_detectors()

    assert [detector.detector_id for detector in first] == [
        "structural.repeated_character",
        "structural.repeated_substring",
        "structural.numeric_sequence",
        "structural.alphabetic_sequence",
    ]
    assert all(left is not right for left, right in zip(first, second, strict=True))


def test_all_structural_detectors_integrate_through_engine_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def prepare(password: str, config: EngineConfig) -> Prepared:
        calls.append(password)
        return Prepared(password)

    monkeypatch.setattr("passpattern.engine.prepare_password", prepare)
    engine = PassPatternEngine(default_structural_detectors())
    result = engine.analyze("aaa1212121234AbCd\U0001f642\U0001f642\U0001f642")

    assert calls == ["aaa1212121234AbCd\U0001f642\U0001f642\U0001f642"]
    assert {
        "structural.repeated_character",
        "structural.repeated_substring",
        "structural.numeric_sequence",
        "structural.alphabetic_sequence",
    } == {match.detector_id for match in result.matches}
    assert any(
        match.detector_id == "structural.repeated_substring"
        and match.start_index == 3
        and match.end_index == 11
        for match in result.matches
    )
    assert any(
        match.detector_id == "structural.numeric_sequence"
        and match.start_index == 9
        and match.end_index == 13
        for match in result.matches
    )
    processed_text = "aaa1212121234AbCd\U0001f642\U0001f642\U0001f642"
    assert all(match.end_index <= len(processed_text) for match in result.matches)
    assert tuple(result.matches) == tuple(
        sorted(
            result.matches,
            key=lambda match: (
                match.start_index,
                match.end_index,
                match.detector_id,
                match.category,
                match.pattern_type,
                tuple((item.key.value, item.value) for item in match.evidence),
            ),
        )
    )


def test_structural_engine_preserves_overlaps_and_honors_match_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    engine = PassPatternEngine(
        default_structural_detectors(),
        EngineConfig(max_matches=1),
    )

    with pytest.raises(TooManyMatchesError, match="match limit"):
        engine.analyze("abab1234")


def test_engine_match_limit_stops_large_lazy_repeated_substring_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    engine = PassPatternEngine((RepeatedSubstringDetector(),))

    with pytest.raises(TooManyMatchesError):
        engine.analyze("ab" * 512)


def test_structural_detectors_can_be_selected_through_engine_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    engine = PassPatternEngine(
        default_structural_detectors(),
        EngineConfig(detector_ids=frozenset({"structural.numeric_sequence"})),
    )

    result = engine.analyze("aaa1234")

    assert {match.detector_id for match in result.matches} == {"structural.numeric_sequence"}


def test_structural_matches_contain_only_safe_typed_evidence() -> None:
    matches = detect(RepeatedCharacterDetector(), "🙂🙂🙂")

    assert matches[0].evidence[0].key is EvidenceKey.COUNT
    assert matches[0].evidence[0].value == 3
    assert "🙂" not in repr(matches[0])
