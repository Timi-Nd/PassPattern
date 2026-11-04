from dataclasses import dataclass
from datetime import date
from itertools import product

import pytest

from passpattern import EvidenceKey, PassPatternEngine
from passpattern.contextual import (
    US_QWERTY,
    CalendarDateDetector,
    KeyboardLayout,
    KeyboardWalkDetector,
    YearDetector,
    default_contextual_detectors,
)


@dataclass(frozen=True)
class Prepared:
    processed_text: str


def matches(detector, text: str):
    return tuple(detector.detect(Prepared(text)))


def evidence(match) -> dict[EvidenceKey, int | float | bool]:
    return {item.key: item.value for item in match.evidence}


@pytest.mark.parametrize(
    ("text", "ambiguous", "order_code"),
    [
        ("2026-11-02", False, 1),
        ("2026/11/02", False, 1),
        ("02-11-2026", True, 0),
        ("02/11/2026", True, 0),
        ("11-02-2026", True, 0),
        ("11/02/2026", True, 0),
    ],
)
def test_calendar_detector_recognizes_supported_date_formats(
    text: str,
    ambiguous: bool,
    order_code: int,
) -> None:
    found = matches(CalendarDateDetector(), text)

    assert [(match.start_index, match.end_index) for match in found] == [(0, 10)]
    assert found[0].detector_id == "contextual.calendar_date"
    assert found[0].pattern_type == "calendar_date"
    assert evidence(found[0])[EvidenceKey.LENGTH] == 10
    assert evidence(found[0])[EvidenceKey.SEPARATOR_COUNT] == 2
    assert evidence(found[0])[EvidenceKey.AMBIGUOUS] is ambiguous
    assert evidence(found[0])[EvidenceKey.DATE_ORDER] == order_code


@pytest.mark.parametrize(
    ("text", "is_valid"),
    [
        ("2024-02-29", True),
        ("2025-02-29", False),
        ("2026-04-31", False),
        ("2026-11-02", True),
        ("2026-13-02", False),
        ("2026-00-12", False),
        ("31/04/2026", False),
        ("13/04/2026", True),
    ],
)
def test_calendar_detector_uses_gregorian_validation(text: str, is_valid: bool) -> None:
    assert bool(matches(CalendarDateDetector(), text)) is is_valid


def test_calendar_detector_ignores_empty_and_non_ascii_digits() -> None:
    detector = CalendarDateDetector()

    assert matches(detector, "") == ()
    assert matches(detector, "٢٠٢٦-١١-٠٢") == ()


def test_calendar_auto_preserves_ambiguity_without_duplicate_spans() -> None:
    found = matches(CalendarDateDetector(), "03/04/2026")

    assert len(found) == 1
    assert evidence(found[0])[EvidenceKey.AMBIGUOUS] is True


@pytest.mark.parametrize(
    ("date_order", "expected_ambiguous", "expected_code"),
    [("auto", True, 0), ("dmy", True, 2), ("mdy", True, 3)],
)
def test_calendar_date_order_preserves_ambiguity_metadata(
    date_order: str,
    expected_ambiguous: bool,
    expected_code: int,
) -> None:
    found = matches(CalendarDateDetector(date_order=date_order), "03/04/2026")

    assert len(found) == 1
    assert evidence(found[0])[EvidenceKey.AMBIGUOUS] is expected_ambiguous
    assert evidence(found[0])[EvidenceKey.DATE_ORDER] == expected_code


def test_calendar_ymd_mode_accepts_year_first_format_only() -> None:
    detector = CalendarDateDetector(date_order="ymd")

    assert len(matches(detector, "2026-11-02")) == 1
    assert matches(detector, "02-11-2026") == ()
    assert evidence(matches(detector, "2026-11-02")[0])[EvidenceKey.DATE_ORDER] == 1


def test_calendar_compact_dates_are_opt_in_and_report_zero_separators() -> None:
    assert matches(CalendarDateDetector(), "20261102") == ()
    found = matches(CalendarDateDetector(allow_compact=True), "20261102")

    assert len(found) == 1
    assert evidence(found[0])[EvidenceKey.SEPARATOR_COUNT] == 0
    assert evidence(found[0])[EvidenceKey.AMBIGUOUS] is False


def test_calendar_respects_configured_year_bounds_and_matching_separators() -> None:
    detector = CalendarDateDetector(min_year=2000, max_year=2024)

    assert len(matches(detector, "2000-01-01")) == 1
    assert len(matches(detector, "2024-12-31")) == 1
    assert matches(detector, "1999-12-31") == ()
    assert matches(detector, "2025-01-01") == ()
    assert matches(CalendarDateDetector(), "2026-11/02") == ()


def test_calendar_dmy_and_mdy_preferences_expose_only_order_code() -> None:
    dmy = matches(CalendarDateDetector(date_order="dmy"), "13/04/2026")
    mdy_fallback = matches(CalendarDateDetector(date_order="mdy"), "13/04/2026")

    assert evidence(dmy[0])[EvidenceKey.DATE_ORDER] == 2
    assert evidence(mdy_fallback[0])[EvidenceKey.DATE_ORDER] == 2
    assert "13" not in repr(dmy)
    assert "2026" not in repr(dmy)


@pytest.mark.parametrize("text", ["12320261102", "202611029", "120261102"])
def test_calendar_does_not_match_dates_inside_longer_digit_runs(text: str) -> None:
    assert matches(CalendarDateDetector(allow_compact=True), text) == ()


def test_calendar_allows_letters_and_unicode_around_dates_with_codepoint_spans() -> None:
    text = "\U0001f642e\u0301date=2026-11-02!"
    found = matches(CalendarDateDetector(), text)

    start = text.index("2026")
    assert [(match.start_index, match.end_index) for match in found] == [(start, start + 10)]


def test_calendar_detects_multiple_dates_and_preserves_safe_metadata() -> None:
    text = "2024-02-29xx2025/03/01"
    found = matches(CalendarDateDetector(), text)

    assert [(match.start_index, match.end_index) for match in found] == [(0, 10), (12, 22)]
    assert "2024" not in repr(found)
    assert "29" not in repr(found)


def test_calendar_differentially_matches_standard_library_dates() -> None:
    for year in (1900, 2000, 2024, 2025):
        detector = CalendarDateDetector(min_year=year, max_year=year)
        for month, day in product(range(1, 13), range(1, 32)):
            text = f"{year:04d}-{month:02d}-{day:02d}"
            try:
                date(year, month, day)
            except ValueError:
                expected = ()
            else:
                expected = ((0, 10),)
            actual = tuple((item.start_index, item.end_index) for item in matches(detector, text))
            assert actual == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_year": 0},
        {"max_year": 10000},
        {"min_year": True},
        {"min_year": 2027, "max_year": 2026},
        {"date_order": "automatic"},
        {"date_order": []},
        {"allow_compact": 1},
    ],
)
def test_calendar_rejects_invalid_configuration(kwargs) -> None:
    with pytest.raises(ValueError):
        CalendarDateDetector(**kwargs)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Summer2026!", [(6, 10)]),
        ("1998Password", [(0, 4)]),
        ("Welcome2001", [(7, 11)]),
        ("abc1234", []),
        ("999999", []),
        ("2026", [(0, 4)]),
        ("x1900y2099!", [(1, 5), (6, 10)]),
    ],
)
def test_year_detector_recognizes_exact_bounded_ascii_runs(
    text: str,
    expected: list[tuple[int, int]],
) -> None:
    found = matches(YearDetector(), text)

    assert [(match.start_index, match.end_index) for match in found] == expected
    assert all(evidence(match)[EvidenceKey.LENGTH] == 4 for match in found)


def test_year_detector_ignores_empty_text() -> None:
    assert matches(YearDetector(), "") == ()


@pytest.mark.parametrize("text", ["1232026123", "12026", "20260", "１２３４"])
def test_year_detector_rejects_longer_runs_and_non_ascii_digits(text: str) -> None:
    assert matches(YearDetector(), text) == ()


def test_year_detector_supports_unicode_prefix_and_suffix() -> None:
    text = "\U0001f642\u65e5\u672c\u8a9e2026e\u0301"
    found = matches(YearDetector(), text)

    assert [(match.start_index, match.end_index) for match in found] == [
        (text.index("2026"), text.index("2026") + 4)
    ]


def test_year_detector_keeps_year_overlap_with_calendar_date() -> None:
    text = "2026-11-02"
    direct = matches(YearDetector(), text)

    assert [(match.start_index, match.end_index) for match in direct] == [(0, 4)]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_year": 0},
        {"max_year": 10000},
        {"min_year": True},
        {"min_year": 2027, "max_year": 2026},
    ],
)
def test_year_detector_rejects_invalid_configuration(kwargs) -> None:
    with pytest.raises(ValueError):
        YearDetector(**kwargs)


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("1", "2", True),
        ("q", "w", True),
        ("a", "s", True),
        ("z", "x", True),
        ("1", "q", True),
        ("q", "a", True),
        ("a", "z", True),
        ("3", "q", False),
        ("1", "w", False),
        ("q", "p", False),
        ("q", "q", False),
        ("Q", "w", False),
        ("é", "q", False),
    ],
)
def test_us_qwerty_physical_neighbor_table(first: str, second: str, expected: bool) -> None:
    assert US_QWERTY.are_neighbors(first, second) is expected


def test_keyboard_layout_copies_and_freezes_positions() -> None:
    supplied = {"q": (2, 1), "w": (6, 1)}
    layout = KeyboardLayout("test", supplied)
    supplied["q"] = (100, 100)

    assert layout.are_neighbors("q", "w")
    with pytest.raises(TypeError):
        layout.positions["q"] = (100, 100)  # type: ignore[index]


@pytest.mark.parametrize(
    "text",
    ["qwerty", "QWERTY", "asdf", "zxcv", "poiuy", "lkjh", "12345", "1qaz", "2wsx"],
)
def test_keyboard_detector_recognizes_common_physical_paths(text: str) -> None:
    found = matches(KeyboardWalkDetector(), text)

    assert any((match.start_index, match.end_index) == (0, len(text)) for match in found)
    assert all(match.pattern_type == "keyboard_walk" for match in found)
    assert all(EvidenceKey.LENGTH in evidence(match) for match in found)


def test_keyboard_detector_recognizes_turns_and_preserves_overlapping_walks() -> None:
    found = matches(KeyboardWalkDetector(), "qwerfdsa")

    assert {(match.start_index, match.end_index) for match in found} == {(0, 5), (3, 8)}
    assert all(evidence(match)[EvidenceKey.COUNT] == 1 for match in found)


def test_keyboard_detector_limits_turns_and_rejects_false_connections() -> None:
    strict = KeyboardWalkDetector(max_turns=0)

    strict_spans = {(match.start_index, match.end_index) for match in matches(strict, "qwerfdsa")}
    assert strict_spans == {(0, 4), (4, 8)}
    assert (0, 5) not in strict_spans
    assert matches(KeyboardWalkDetector(), "123qwe") == ()


def test_keyboard_detector_blocks_backtracking_and_repeated_key_presses() -> None:
    assert matches(KeyboardWalkDetector(), "qwew") == ()
    assert (1, 5) in {
        (match.start_index, match.end_index) for match in matches(KeyboardWalkDetector(), "qaqwe")
    }
    found = matches(KeyboardWalkDetector(), "qwwert")

    assert all(not (match.start_index == 0 and match.end_index == 6) for match in found)
    assert any((match.start_index, match.end_index) == (2, 6) for match in found)


def test_keyboard_detector_handles_unicode_boundaries_and_multiple_walks() -> None:
    text = "\U0001f642qwerty--e\u0301asdf"
    found = matches(KeyboardWalkDetector(), text)

    assert [(match.start_index, match.end_index) for match in found] == [(1, 7), (11, 15)]


def test_keyboard_detector_ignores_non_ascii_and_empty_text() -> None:
    detector = KeyboardWalkDetector()

    assert matches(detector, "") == ()
    assert matches(detector, "qwe\u00e9r") == ()
    assert matches(detector, "\u03b1\u03b2\u03b3\u03b4") == ()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_walk_length": 1},
        {"min_walk_length": True},
        {"max_turns": -1},
        {"max_turns": True},
        {"layout": "dvorak"},
        {"layout": None},
    ],
)
def test_keyboard_detector_rejects_invalid_configuration(kwargs) -> None:
    with pytest.raises(ValueError):
        KeyboardWalkDetector(**kwargs)


def test_keyboard_adversarial_maximum_length_is_bounded_and_deterministic() -> None:
    detector = KeyboardWalkDetector()
    text = "qwerfdsa" * 128

    first = matches(detector, text)
    second = matches(detector, text)

    assert first == second
    assert len(first) <= len(text)


def test_keyboard_detector_matches_exhaustive_small_reference() -> None:
    alphabet = ("q", "w", "e", "a", "s", "1", "2")
    detector = KeyboardWalkDetector()

    def valid_walk(text: str) -> bool:
        directions = []
        for index in range(len(text) - 1):
            first = text[index]
            second = text[index + 1]
            if not US_QWERTY.are_neighbors(first, second):
                return False
            if index and text[index - 1] == second:
                return False
            directions.append(US_QWERTY.direction(first, second))
        turns = sum(
            first != second for first, second in zip(directions, directions[1:], strict=False)
        )
        return turns <= 1

    for length in range(6):
        for characters in product(alphabet, repeat=length):
            text = "".join(characters)
            expected = set()
            for start in range(len(text)):
                for end in range(start + 4, len(text) + 1):
                    if not valid_walk(text[start:end]):
                        continue
                    can_extend_left = start > 0 and valid_walk(text[start - 1 : end])
                    can_extend_right = end < len(text) and valid_walk(text[start : end + 1])
                    if not can_extend_left and not can_extend_right:
                        expected.add((start, end))
            actual = {(match.start_index, match.end_index) for match in matches(detector, text)}
            assert actual == expected, text


def test_default_contextual_factory_returns_fresh_configured_detectors() -> None:
    first = default_contextual_detectors()
    second = default_contextual_detectors()

    assert tuple(detector.detector_id for detector in first) == (
        "contextual.calendar_date",
        "contextual.year",
        "contextual.keyboard_walk",
    )
    assert all(left is not right for left, right in zip(first, second, strict=True))


def test_contextual_detectors_use_safe_evidence_and_preserve_overlaps() -> None:
    password = "2026-11-02qwerty"

    calendar_matches = matches(CalendarDateDetector(), password)
    year_matches = matches(YearDetector(), password)
    keyboard_matches = matches(KeyboardWalkDetector(), password)
    all_matches = calendar_matches + year_matches + keyboard_matches

    assert {(match.start_index, match.end_index) for match in all_matches} >= {
        (0, 10),
        (0, 4),
        (9, 16),
    }
    assert "2026" not in repr(all_matches)
    assert "qwerty" not in repr(all_matches)


def test_contextual_detectors_are_opt_in_and_engine_sorts_overlaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    engine = PassPatternEngine(default_contextual_detectors())

    result = engine.analyze("2026-11-02qwerty")

    assert [
        (match.start_index, match.end_index, match.detector_id) for match in result.matches
    ] == [
        (0, 4, "contextual.year"),
        (0, 10, "contextual.calendar_date"),
        (9, 16, "contextual.keyboard_walk"),
    ]
