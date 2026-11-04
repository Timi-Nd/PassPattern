from dataclasses import dataclass
from itertools import product

import pytest

from passpattern import DictionarySearchLimitError, EvidenceKey
from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    LeetspeakDetector,
    ReversedWordDetector,
)


@dataclass(frozen=True)
class Prepared:
    processed_text: str


DEFAULT_MAP = {
    "@": ("a",),
    "4": ("a",),
    "0": ("o",),
    "3": ("e",),
    "5": ("s",),
    "$": ("s",),
    "7": ("t",),
    "1": ("i", "l"),
    "!": ("i",),
}


def build_lexicon(*words: tuple[str, int]) -> DictionaryLexicon:
    return DictionaryLexicon(DictionaryEntry(word, rank) for word, rank in words)


def matches(detector, text: str):
    return tuple(detector.detect(Prepared(text)))


def evidence(match) -> dict[EvidenceKey, int | bool]:
    return {item.key: item.value for item in match.evidence}


def spans(found):
    return [(match.start_index, match.end_index) for match in found]


@pytest.mark.parametrize(
    ("text", "word"),
    [
        ("drowssap", "password"),
        ("xxdrowssap123", "password"),
        ("DROWSSAP123", "password"),
        ("!nogard!", "dragon"),
        ("enihsnus", "sunshine"),
    ],
)
def test_reversed_words_match_ascii_case_insensitively(text: str, word: str) -> None:
    detector = ReversedWordDetector(build_lexicon((word, 7)))
    found = matches(detector, text)

    start = text.lower().index(word[::-1])
    assert any(
        (match.start_index, match.end_index) == (start, start + len(word)) for match in found
    )
    assert found[0].detector_id == "dictionary.reversed_word"
    assert found[0].pattern_type == "reversed_word"
    assert evidence(found[0])[EvidenceKey.RANK] == 7
    assert evidence(found[0])[EvidenceKey.LENGTH] == len(word)
    assert word not in repr(found[0])


def test_reversed_detector_skips_case_insensitive_palindromes() -> None:
    detector = ReversedWordDetector(build_lexicon(("level", 1), ("Madam", 2)))

    assert matches(detector, "LEVELmadam") == ()


def test_reversed_detector_preserves_overlapping_and_multiple_matches() -> None:
    detector = ReversedWordDetector(
        build_lexicon(("abc", 1), ("cba", 2), ("abcd", 3), ("dcba", 4)),
        min_word_length=3,
    )

    found = matches(detector, "dcbacba")

    assert {(match.start_index, match.end_index) for match in found} == {
        (0, 4),
        (1, 4),
        (4, 7),
    }


def test_reversed_case_variants_prefer_exact_spelling_then_lowest_rank() -> None:
    detector = ReversedWordDetector(build_lexicon(("abcd", 1), ("Abcd", 9)))

    exact_case = matches(detector, "dcbA")[0]
    non_exact_case = matches(detector, "DCBA")[0]

    assert evidence(exact_case)[EvidenceKey.RANK] == 9
    assert evidence(non_exact_case)[EvidenceKey.RANK] == 1


def test_reversed_detector_supports_exact_unicode_codepoint_reversal() -> None:
    entry = "\U0001f642\u732b\u72ac"
    detector = ReversedWordDetector(build_lexicon((entry, 5)), min_word_length=2)

    found = matches(detector, entry[::-1])

    assert spans(found) == [(0, 3)]


def test_reversed_detector_combining_marks_follow_codepoint_not_grapheme_reversal() -> None:
    entry = "e\u0301xy"
    detector = ReversedWordDetector(
        DictionaryLexicon([DictionaryEntry(entry, 1)], normalization="none"),
        min_word_length=2,
    )

    assert spans(matches(detector, entry[::-1])) == [(0, 4)]
    assert matches(detector, "yx\u00e9") == ()


def test_reversed_detector_respects_normalization_and_minimum_length() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("\u00e9xy", 1)],
        normalization="nfc",
    )
    detector = ReversedWordDetector(lexicon, min_word_length=3)

    assert detector.required_normalization == "nfc"
    assert spans(matches(detector, "yx\u00e9")) == [(0, 3)]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_word_length": 0},
        {"min_word_length": True},
        {"min_word_length": 129},
    ],
)
def test_reversed_detector_rejects_invalid_configuration(kwargs) -> None:
    with pytest.raises(ValueError):
        ReversedWordDetector(build_lexicon(("password", 1)), **kwargs)


@pytest.mark.parametrize(
    ("text", "word", "substitution_count"),
    [
        ("p@ssword", "password", 1),
        ("passw0rd", "password", 1),
        ("p@ssw0rd", "password", 2),
        ("dr4g0n", "dragon", 2),
        ("s3curity", "security", 1),
        ("s3cur1ty", "security", 2),
        ("P@SSW0RD", "password", 2),
    ],
)
def test_leetspeak_detects_supported_substitutions(
    text: str,
    word: str,
    substitution_count: int,
) -> None:
    detector = LeetspeakDetector(build_lexicon((word, 12)))
    found = matches(detector, text)

    assert spans(found) == [(0, len(text))]
    assert found[0].detector_id == "dictionary.leetspeak"
    assert found[0].pattern_type == "leetspeak_word"
    assert evidence(found[0]) == {
        EvidenceKey.LENGTH: len(word),
        EvidenceKey.RANK: 12,
        EvidenceKey.SUBSTITUTION_COUNT: substitution_count,
    }
    assert word not in repr(found[0])


def test_leetspeak_finds_embedded_words_and_overlapping_spans() -> None:
    detector = LeetspeakDetector(build_lexicon(("password", 1), ("assword", 2)))

    found = matches(detector, "xxp@ssword123")

    assert {(match.start_index, match.end_index) for match in found} == {
        (2, 10),
        (3, 10),
    }


def test_leetspeak_requires_an_actual_substitution() -> None:
    detector = LeetspeakDetector(build_lexicon(("password", 1)))

    assert matches(detector, "password") == ()


def test_leetspeak_resolves_ambiguous_alternatives_and_equivalent_paths() -> None:
    detector = LeetspeakDetector(build_lexicon(("security", 8), ("securilty", 3)))

    found = matches(detector, "s3cur1ty")

    assert len(found) == 1
    assert evidence(found[0])[EvidenceKey.RANK] == 8
    assert evidence(found[0])[EvidenceKey.SUBSTITUTION_COUNT] == 2


def test_leetspeak_chooses_lowest_substitution_count_then_rank() -> None:
    detector = LeetspeakDetector(
        build_lexicon(("aia", 9), ("ala", 1)),
        min_word_length=3,
    )

    found = matches(detector, "a1a")

    assert len(found) == 1
    assert evidence(found[0])[EvidenceKey.RANK] == 1
    assert evidence(found[0])[EvidenceKey.SUBSTITUTION_COUNT] == 1


def test_leetspeak_honors_maximum_substitution_count() -> None:
    detector = LeetspeakDetector(
        build_lexicon(("password", 1)),
        max_substitutions=1,
    )

    assert matches(detector, "p@ssw0rd") == ()
    assert spans(matches(detector, "p@ssword")) == [(0, 8)]


def test_leetspeak_unicode_is_exact_outside_ascii_substitution_rules() -> None:
    detector = LeetspeakDetector(
        build_lexicon(("\u732bpass", 2), ("stra\u00dfe", 3)),
        min_word_length=4,
    )

    assert spans(matches(detector, "\U0001f642\u732bp@ss")) == [(1, 6)]
    assert matches(detector, "STRASSE") == ()
    assert matches(detector, "\u0130") == ()


def test_leetspeak_uses_nfc_processed_text_and_original_indices() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("caf\u00e9", 1)],
        normalization="nfc",
    )
    detector = LeetspeakDetector(lexicon, min_word_length=4)

    assert spans(matches(detector, "caf\u00e9")) == []
    assert detector.required_normalization == "nfc"


@pytest.mark.parametrize(
    ("kwargs", "substitutions"),
    [
        ({"max_substitutions": 0}, DEFAULT_MAP),
        ({"max_substitutions": True}, DEFAULT_MAP),
        ({"min_word_length": 0}, DEFAULT_MAP),
        ({"max_active_states": 0}, DEFAULT_MAP),
        ({"max_work": 0}, DEFAULT_MAP),
        ({}, {"a": ("b",)}),
        ({}, {"@": "a"}),
        ({}, {"@": ("é",)}),
        ({}, {"@": ()}),
        ({}, {"@": tuple("abcdefghi")}),
        ({}, {f"<{index}>": ("a",) for index in range(65)}),
    ],
)
def test_leetspeak_rejects_invalid_limits_or_mapping(kwargs, substitutions) -> None:
    with pytest.raises(ValueError):
        LeetspeakDetector(
            build_lexicon(("password", 1)),
            substitutions=substitutions,
            **kwargs,
        )


def test_leetspeak_copies_and_freezes_custom_substitution_mapping() -> None:
    supplied = {"%": ["a"]}
    detector = LeetspeakDetector(
        build_lexicon(("password", 1)),
        substitutions=supplied,
    )
    supplied["%"].append("o")

    assert detector.substitutions["%"] == ("a",)
    with pytest.raises(TypeError):
        detector.substitutions["%"] = ("o",)  # type: ignore[index]


def test_leetspeak_rejects_an_unbounded_custom_target_iterator() -> None:
    with pytest.raises(ValueError, match="collection"):
        LeetspeakDetector(
            build_lexicon(("password", 1)),
            substitutions={"%": iter(("a",))},
        )


def test_leetspeak_active_state_and_work_limits_fail_explicitly() -> None:
    lexicon = build_lexicon(("i" * 32, 1), ("l" * 32, 2))
    state_limited = LeetspeakDetector(
        lexicon,
        min_word_length=4,
        max_active_states=1,
    )
    work_limited = LeetspeakDetector(
        lexicon,
        min_word_length=4,
        max_work=1,
    )

    with pytest.raises(DictionarySearchLimitError, match="active-state"):
        matches(state_limited, "1" * 32)
    with pytest.raises(DictionarySearchLimitError, match="work limit"):
        matches(work_limited, "x" * 32)


@pytest.mark.parametrize("text", ["", "x", "1" * 1024, "0" * 1024, "10" * 512])
def test_leetspeak_handles_adversarial_inputs_with_bounded_failure(text: str) -> None:
    detector = LeetspeakDetector(
        build_lexicon(("password", 1), ("security", 2), ("lollipop", 3)),
        max_work=100_000,
    )

    assert isinstance(matches(detector, text), tuple)


def _brute_force_leet_matches(text: str, entries: tuple[DictionaryEntry, ...]):
    expected: dict[tuple[int, int], tuple[int, int, str]] = {}
    for start in range(len(text)):
        for end in range(start + 1, min(len(text), start + 8) + 1):
            segment = text[start:end]
            for entry in entries:
                if len(entry.word) != len(segment):
                    continue
                states = {0}
                for input_character, target_character in zip(
                    segment, entry.word.lower(), strict=True
                ):
                    interpretations = {input_character.lower()}
                    interpretations.update(DEFAULT_MAP.get(input_character, ()))
                    states = {
                        count + (replacement != input_character.lower())
                        for count in states
                        for replacement in interpretations
                        if replacement == target_character
                    }
                    if not states:
                        break
                counts = [count for count in states if 1 <= count <= 2]
                if counts:
                    candidate = (min(counts), entry.rank, entry.word)
                    span = (start, end)
                    if span not in expected or candidate < expected[span]:
                        expected[span] = candidate
    return expected


def test_leetspeak_exhaustive_small_inputs_match_bruteforce_reference() -> None:
    entries = (DictionaryEntry("aia", 4), DictionaryEntry("ala", 2), DictionaryEntry("aba", 1))
    lexicon = DictionaryLexicon(entries)
    detector = LeetspeakDetector(
        lexicon,
        max_substitutions=2,
        min_word_length=3,
    )
    alphabet = ("a", "i", "l", "1", "@")

    for length in range(5):
        for characters in product(alphabet, repeat=length):
            text = "".join(characters)
            actual = {
                (match.start_index, match.end_index): (
                    evidence(match)[EvidenceKey.SUBSTITUTION_COUNT],
                    evidence(match)[EvidenceKey.RANK],
                )
                for match in matches(detector, text)
            }
            expected = {
                span: (candidate[0], candidate[1])
                for span, candidate in _brute_force_leet_matches(text, lexicon.entries).items()
            }
            assert actual == expected


def test_leetspeak_reuses_automaton_without_retaining_password_text() -> None:
    detector = LeetspeakDetector(build_lexicon(("password", 1)))
    automaton = detector._automaton
    found = matches(detector, "SyntheticSentinel p@ssword")

    assert detector._automaton is automaton
    assert "SyntheticSentinel" not in repr(automaton)
    assert "p@ssword" not in repr(found)
