from dataclasses import dataclass

import pytest

from passpattern import (
    EngineConfig,
    EvidenceKey,
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
        ("13579", []),
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
