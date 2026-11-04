import json
import unicodedata
from dataclasses import FrozenInstanceError, dataclass
from itertools import product
from pathlib import Path

import pytest

from passpattern import EngineConfig, EvidenceKey, PassPatternEngine, TooManyMatchesError
from passpattern.dictionary import (
    DictionaryCompoundDetector,
    DictionaryEntry,
    DictionaryLexicon,
    DictionaryMatcher,
    DictionaryWordDetector,
)


@dataclass(frozen=True)
class Prepared:
    processed_text: str


def build_lexicon(*words: tuple[str, int]) -> DictionaryLexicon:
    return DictionaryLexicon(DictionaryEntry(word, rank) for word, rank in words)


def detect(lexicon: DictionaryLexicon, text: str, *, min_word_length: int = 3):
    detector = DictionaryWordDetector(lexicon, min_word_length=min_word_length)
    return tuple(detector.detect(Prepared(text)))


def detect_compounds(
    lexicon: DictionaryLexicon,
    text: str,
    *,
    min_word_length: int = 3,
    max_suffix_length: int = 16,
):
    detector = DictionaryCompoundDetector(
        lexicon,
        min_word_length=min_word_length,
        max_suffix_length=max_suffix_length,
    )
    return tuple(detector.detect(Prepared(text)))


def metadata(match) -> dict[EvidenceKey, int | bool]:
    return {item.key: item.value for item in match.evidence}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("sunshine", [(0, 8)]),
        ("xxsunshine42", [(2, 10)]),
        ("Sunshine2026!", [(0, 8)]),
        ("SUNSHINE", [(0, 8)]),
        ("SuNsHiNe", [(0, 8)]),
        ("none-here", []),
        ("", []),
    ],
)
def test_dictionary_finds_exact_embedded_and_ascii_case_insensitive_words(
    text: str,
    expected: list[tuple[int, int]],
) -> None:
    lexicon = build_lexicon(("sunshine", 1))

    matches = detect(lexicon, text)

    assert [(match.start_index, match.end_index) for match in matches] == expected


def test_dictionary_default_minimum_word_length_and_configurable_threshold() -> None:
    lexicon = build_lexicon(("an", 3), ("sun", 2), ("sunshine", 1))

    assert [
        (match.start_index, match.end_index)
        for match in DictionaryWordDetector(lexicon).detect(Prepared("sunshine"))
    ] == [(0, 3), (0, 8)]
    assert detect(lexicon, "an") == ()
    assert [
        (match.start_index, match.end_index)
        for match in DictionaryWordDetector(lexicon, min_word_length=8).detect(Prepared("sunshine"))
    ] == [(0, 8)]


def test_dictionary_matches_multiple_overlapping_and_adjacent_entries() -> None:
    lexicon = build_lexicon(("sun", 10), ("sunflower", 2), ("flower", 3))

    matches = detect(lexicon, "sunflower")

    assert {(match.start_index, match.end_index) for match in matches} == {
        (0, 3),
        (0, 9),
        (3, 9),
    }


def test_dictionary_finds_repeated_occurrences_without_duplicate_spans() -> None:
    lexicon = build_lexicon(("dragon", 1), ("DRAGON", 9), ("dragon", 3))

    matches = detect(lexicon, "dragon-dragon")

    assert [(match.start_index, match.end_index) for match in matches] == [
        (0, 6),
        (7, 13),
    ]


def test_duplicate_resolution_prefers_exact_case_then_rank_then_stable_word() -> None:
    lexicon = DictionaryLexicon(
        [
            DictionaryEntry("sunshine", 20, "later"),
            DictionaryEntry("sunshine", 10, "earlier"),
            DictionaryEntry("SUNSHINE", 1, "best-rank"),
            DictionaryEntry("Sunshine", 30, "exact"),
        ]
    )

    exact = detect(lexicon, "Sunshine")[0]
    insensitive = detect(lexicon, "sUnShInE")[0]

    assert metadata(exact)[EvidenceKey.RANK] == 30
    assert metadata(exact)[EvidenceKey.CASE_EXACT] is True
    assert metadata(insensitive)[EvidenceKey.RANK] == 1
    assert metadata(insensitive)[EvidenceKey.CASE_EXACT] is False


def test_exact_duplicate_entries_keep_lowest_rank_deterministically() -> None:
    first = DictionaryLexicon(
        [
            DictionaryEntry("dragon", 9, "z-source"),
            DictionaryEntry("dragon", 2, "z-source"),
            DictionaryEntry("dragon", 2, "a-source"),
        ]
    )
    second = DictionaryLexicon(reversed(first.entries))

    assert first.entries == second.entries
    assert len(first.entries) == 1
    assert first.entries[0].rank == 2
    assert first.entries[0].source_id == "a-source"


@pytest.mark.parametrize(
    ("word", "rank", "source_id"),
    [
        ("", 1, None),
        ("word", 0, None),
        ("word", -1, None),
        ("word", True, None),
        ("bad\ud800", 1, None),
        ("word", 1, "contains spaces"),
    ],
)
def test_dictionary_entry_rejects_invalid_values(
    word: str,
    rank: int,
    source_id: str | None,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        DictionaryLexicon([DictionaryEntry(word, rank, source_id)])


def test_dictionary_lexicon_is_immutable_and_does_not_mutate_input() -> None:
    supplied = [DictionaryEntry("dragon", 3)]
    lexicon = DictionaryLexicon(supplied)
    supplied.append(DictionaryEntry("sunshine", 1))

    assert len(lexicon.entries) == 1
    with pytest.raises(FrozenInstanceError):
        lexicon.entries = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        lexicon.entries[0].rank = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_word_length": 0},
        {"max_word_length": 0},
        {"max_entries": 0},
        {"max_total_codepoints": 0},
        {"min_word_length": 4, "max_word_length": 3},
        {"normalization": "nfd"},
        {"normalization": None},
        {"normalization": "NFC"},
        {"max_word_length": 2},
    ],
)
def test_dictionary_lexicon_rejects_invalid_limits(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        DictionaryLexicon([DictionaryEntry("word", 1)], **kwargs)  # type: ignore[arg-type]


def test_dictionary_lexicon_enforces_entry_count_and_total_size_limits() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        DictionaryLexicon(
            [DictionaryEntry("one", 1), DictionaryEntry("two", 2)],
            max_entries=1,
        )
    with pytest.raises(ValueError, match="max_total_codepoints"):
        DictionaryLexicon([DictionaryEntry("word", 1)], max_total_codepoints=3)
    with pytest.raises(ValueError, match="max_word_length"):
        DictionaryLexicon([DictionaryEntry("word", 1)], max_word_length=3)


def test_lexicon_minimum_word_length_is_validated() -> None:
    with pytest.raises(ValueError, match="min_word_length"):
        DictionaryLexicon([DictionaryEntry("a", 1)], min_word_length=2)


def test_nfc_lexicon_accepts_composed_entries_and_rejects_decomposed_entries() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("caf\u00e9", 1)],
        normalization="nfc",
    )

    assert lexicon.entries[0].word == "caf\u00e9"
    assert lexicon.normalization == "nfc"
    assert lexicon.unicode_data_version == unicodedata.unidata_version
    with pytest.raises(ValueError, match="NFC-normalized") as error:
        DictionaryLexicon(
            [DictionaryEntry("cafe\u0301", 1)],
            normalization="nfc",
        )
    assert "cafe" not in str(error.value)


def test_none_lexicon_preserves_decomposed_unicode_exactly() -> None:
    decomposed = "cafe\u0301"
    lexicon = DictionaryLexicon(
        [DictionaryEntry(decomposed, 1)],
        normalization="none",
    )

    assert lexicon.entries[0].word == decomposed
    assert [
        (match.start_index, match.end_index)
        for match in detect(
            lexicon,
            f"xx{decomposed}!",
            min_word_length=1,
        )
    ] == [(2, 7)]
    assert detect(lexicon, "caf\u00e9", min_word_length=1) == ()


def test_dictionary_detector_declares_lexicon_normalization_requirement() -> None:
    nfc_detector = DictionaryWordDetector(
        DictionaryLexicon([DictionaryEntry("caf\u00e9", 1)], normalization="nfc")
    )
    none_detector = DictionaryWordDetector(
        DictionaryLexicon([DictionaryEntry("cafe\u0301", 1)], normalization="none")
    )

    assert nfc_detector.required_normalization == "nfc"
    assert none_detector.required_normalization == "none"


def test_unicode_exact_matching_uses_codepoint_indices_without_case_expansion() -> None:
    lexicon = build_lexicon(("\u732b\u72ac", 4), ("stra\u00dfe", 5), ("\u0130", 6))

    matches = detect(lexicon, "\U0001f642\u732b\u72acStra\u00dfe", min_word_length=1)

    assert [(match.start_index, match.end_index) for match in matches] == [
        (1, 3),
        (3, 9),
    ]
    assert detect(lexicon, "STRASSE", min_word_length=1) == ()
    assert detect(lexicon, "i\u0307", min_word_length=1) == ()
    assert [
        (match.start_index, match.end_index)
        for match in detect(lexicon, "\u0130", min_word_length=1)
    ] == [(0, 1)]


def test_combining_characters_are_matched_exactly_only() -> None:
    lexicon = build_lexicon(("e\u0301", 2), ("\u00e9", 1))

    assert {
        (match.start_index, match.end_index)
        for match in detect(lexicon, "e\u0301", min_word_length=1)
    } == {(0, 2)}
    assert {
        (match.start_index, match.end_index)
        for match in detect(lexicon, "\u00e9", min_word_length=1)
    } == {(0, 1)}


def test_lexicon_and_matcher_are_reused_without_retaining_password_text() -> None:
    lexicon = build_lexicon(("sunshine", 1))
    detector = DictionaryWordDetector(lexicon)
    matcher = detector._matcher
    prepared = "sunshine-SyntheticSentinel"

    first = tuple(detector.detect(Prepared(prepared)))
    second = tuple(detector.detect(Prepared(prepared)))

    assert detector._matcher is matcher
    assert matcher.lexicon is lexicon
    assert first == second
    assert "SyntheticSentinel" not in repr(matcher)
    assert "SyntheticSentinel" not in repr(first)


def test_dictionary_evidence_contains_only_safe_metadata() -> None:
    result = detect(build_lexicon(("password", 7)), "password")[0]

    assert result.detector_id == "dictionary.word"
    assert result.category == "dictionary"
    assert result.pattern_type == "dictionary_word"
    assert metadata(result) == {
        EvidenceKey.LENGTH: 8,
        EvidenceKey.RANK: 7,
        EvidenceKey.CASE_EXACT: True,
    }
    assert "password" not in repr(result)


@pytest.mark.parametrize(
    ("text", "expected_span", "expected_suffix_length"),
    [
        ("sunshine2026", (0, 12), 4),
        ("Sunshine!", (0, 9), 1),
        ("sunshine-2026!", (0, 14), 6),
    ],
)
def test_dictionary_compound_finds_word_with_bounded_suffix(
    text: str,
    expected_span: tuple[int, int],
    expected_suffix_length: int,
) -> None:
    found = detect_compounds(build_lexicon(("sunshine", 7)), text)

    assert len(found) == 1
    match = found[0]
    assert (match.start_index, match.end_index) == expected_span
    assert match.detector_id == "dictionary.compound"
    assert match.pattern_type == "dictionary_compound"
    assert metadata(match) == {
        EvidenceKey.LENGTH: expected_span[1] - expected_span[0],
        EvidenceKey.RANK: 7,
        EvidenceKey.CASE_EXACT: False if text[0].isupper() else True,
        EvidenceKey.COUNT: expected_suffix_length,
    }
    assert "sunshine" not in repr(match)


@pytest.mark.parametrize(
    "text",
    [
        "megadragon2026",
        "dragon2026x",
        "dragon",
        "dragon 2026",
        "édragon2026",
        "dragon2026\u0301",
    ],
)
def test_dictionary_compound_requires_word_boundaries_and_contiguous_suffix(
    text: str,
) -> None:
    assert detect_compounds(build_lexicon(("dragon", 1)), text) == ()


def test_dictionary_compound_uses_unicode_codepoint_spans() -> None:
    text = "\U0001f642caf\u00e92026!"
    found = detect_compounds(build_lexicon(("caf\u00e9", 2)), text)

    assert [(match.start_index, match.end_index) for match in found] == [(1, 10)]


def test_dictionary_compound_enforces_configured_suffix_bound() -> None:
    lexicon = build_lexicon(("dragon", 1))

    assert len(detect_compounds(lexicon, "dragon1234", max_suffix_length=4)) == 1
    assert detect_compounds(lexicon, "dragon12345", max_suffix_length=4) == ()


def test_dictionary_compound_synthetic_evaluation_corpus() -> None:
    corpus_path = Path(__file__).parent / "fixtures" / "dictionary-compound-synthetic-v1.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    assert corpus["schema_version"] == 1
    assert corpus["purpose"] == (
        "Synthetic rule-conformance examples; not a real-world accuracy evaluation."
    )
    assert corpus["cases"]
    assert len({case["id"] for case in corpus["cases"]}) == len(corpus["cases"])
    lexicon = DictionaryLexicon(DictionaryEntry(**entry) for entry in corpus["lexicon"])
    detector = DictionaryCompoundDetector(lexicon)
    counts = {"true_positive": 0, "false_negative": 0, "false_positive": 0, "true_negative": 0}

    for case in corpus["cases"]:
        assert case["label"] in ("positive", "negative")
        actual = tuple(
            (match.start_index, match.end_index)
            for match in detector.detect(Prepared(case["input"]))
        )
        expected = tuple(tuple(span) for span in case["expected_spans"])
        assert actual == expected, case["id"]
        is_positive = case["label"] == "positive"
        is_detected = bool(actual)
        if is_positive and is_detected:
            counts["true_positive"] += 1
        elif is_positive:
            counts["false_negative"] += 1
        elif is_detected:
            counts["false_positive"] += 1
        else:
            counts["true_negative"] += 1

    assert counts == {
        "true_positive": 6,
        "false_negative": 0,
        "false_positive": 0,
        "true_negative": 8,
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_word_length": 0},
        {"min_word_length": True},
        {"min_word_length": 129},
        {"max_suffix_length": 0},
        {"max_suffix_length": True},
        {"max_suffix_length": 129},
    ],
)
def test_dictionary_compound_rejects_invalid_limits(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        DictionaryCompoundDetector(build_lexicon(("dragon", 1)), **kwargs)  # type: ignore[arg-type]


def test_dictionary_compound_declares_lexicon_normalization_requirement() -> None:
    detector = DictionaryCompoundDetector(
        DictionaryLexicon([DictionaryEntry("caf\u00e9", 1)], normalization="nfc")
    )

    assert detector.required_normalization == "nfc"


def test_matcher_is_reusable_for_overlapping_matches() -> None:
    matcher = DictionaryMatcher(build_lexicon(("sun", 1), ("sunflower", 2), ("flower", 3)))

    assert len(tuple(matcher.find_matches("sunflower", min_word_length=3))) == 3
    assert len(tuple(matcher.find_matches("sunflower", min_word_length=3))) == 3


def test_matcher_requires_a_validated_lexicon() -> None:
    with pytest.raises(TypeError, match="DictionaryLexicon"):
        DictionaryMatcher(None)  # type: ignore[arg-type]


def test_aho_corasick_matches_bruteforce_reference_for_small_ascii_cases() -> None:
    words = [
        "".join(characters)
        for length in range(1, 4)
        for characters in product("abA", repeat=length)
    ]
    lexicon = DictionaryLexicon(
        DictionaryEntry(word, index + 1) for index, word in enumerate(words)
    )
    matcher = DictionaryMatcher(lexicon)
    entry_by_word = {entry.word: entry for entry in lexicon.entries}

    for text_length in range(6):
        for characters in product("abA", repeat=text_length):
            text = "".join(characters)
            actual = tuple(matcher.find_matches(text, min_word_length=1))
            expected: list[tuple[int, int, int, bool]] = []
            for start in range(len(text)):
                for end in range(start + 1, len(text) + 1):
                    word = text[start:end]
                    folded = word.translate(
                        str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
                    )
                    candidates = [
                        entry
                        for entry in lexicon.entries
                        if entry.word.translate(
                            str.maketrans(
                                "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
                            )
                        )
                        == folded
                    ]
                    if not candidates:
                        continue
                    exact_entry = entry_by_word.get(word)
                    selected = exact_entry or min(
                        candidates,
                        key=lambda entry: (entry.rank, entry.word, entry.source_id or ""),
                    )
                    expected.append((start, end, selected.rank, exact_entry is not None))
            expected.sort(key=lambda item: (item[1], -(item[1] - item[0])))

            assert [
                (
                    match.start_index,
                    match.end_index,
                    metadata(match)[EvidenceKey.RANK],
                    metadata(match)[EvidenceKey.CASE_EXACT],
                )
                for match in actual
            ] == expected


def test_dictionary_detector_rejects_invalid_minimum_length() -> None:
    lexicon = build_lexicon(("sunshine", 1))
    for minimum in (0, -1, True, 129):
        with pytest.raises(ValueError):
            DictionaryWordDetector(lexicon, min_word_length=minimum)  # type: ignore[arg-type]


def test_engine_runs_dictionary_with_structural_detectors_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from passpattern.structural import default_structural_detectors

    calls = []

    def prepare(password: str, config: EngineConfig) -> Prepared:
        calls.append(password)
        return Prepared(password)

    monkeypatch.setattr("passpattern.engine.prepare_password", prepare)
    detector = DictionaryWordDetector(build_lexicon(("sunshine", 5), ("dragon", 3)))
    engine = PassPatternEngine((*default_structural_detectors(), detector))

    result = engine.analyze("Sunshine1234!")

    assert calls == ["Sunshine1234!"]
    assert any(
        match.detector_id == "dictionary.word" and (match.start_index, match.end_index) == (0, 8)
        for match in result.matches
    )
    assert any(
        match.detector_id == "structural.numeric_sequence"
        and (match.start_index, match.end_index) == (8, 12)
        for match in result.matches
    )


def test_dictionary_detector_selection_and_engine_match_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from passpattern.structural import default_structural_detectors

    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    lexicon = build_lexicon(("sunshine", 5), ("123", 1))
    detectors = (*default_structural_detectors(), DictionaryWordDetector(lexicon))
    selected = PassPatternEngine(
        detectors,
        EngineConfig(detector_ids=frozenset({"dictionary.word"})),
    )

    assert {match.detector_id for match in selected.analyze("sunshine123").matches} == {
        "dictionary.word"
    }

    limited = PassPatternEngine(detectors, EngineConfig(max_matches=1))
    with pytest.raises(TooManyMatchesError):
        limited.analyze("sunshine1234")
