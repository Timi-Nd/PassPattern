from __future__ import annotations

import json

import pytest

from passpattern import AnalysisResult, Evidence, EvidenceKey, PatternMatch
from scripts.analyze_password import build_engine, load_dictionary, print_results


@pytest.mark.native
def test_build_engine_enables_all_structural_and_contextual_detectors() -> None:
    engine = build_engine("none")

    result = engine.analyze("aaa abab 123 abc 2024-02-29 qwer")

    assert {match.detector_id for match in result.matches} == {
        "structural.repeated_character",
        "structural.repeated_substring",
        "structural.numeric_sequence",
        "structural.alphabetic_sequence",
        "contextual.calendar_date",
        "contextual.year",
        "contextual.keyboard_walk",
    }


@pytest.mark.native
def test_optional_dictionary_adds_all_dictionary_detectors(tmp_path) -> None:
    dictionary_file = tmp_path / "words.json"
    dictionary_file.write_text(
        json.dumps({"entries": [{"word": "garden", "rank": 1}]}),
        encoding="utf-8",
    )

    engine = build_engine("none", dictionary_file)

    result = engine.analyze("garden nedrag g@rden")

    assert {match.detector_id for match in result.matches} >= {
        "dictionary.word",
        "dictionary.reversed_word",
        "dictionary.leetspeak",
    }


def test_load_dictionary_rejects_malformed_entries_without_echoing_words(tmp_path) -> None:
    dictionary_file = tmp_path / "words.json"
    dictionary_file.write_text(
        json.dumps([{"word": "private-entry", "rank": 0}]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as error:
        load_dictionary(dictionary_file, "none")

    assert "private-entry" not in str(error.value)


def test_print_results_reports_match_fields_but_not_matched_text(capsys) -> None:
    match = PatternMatch(
        "structural.numeric_sequence",
        "structural",
        "numeric_sequence",
        1,
        4,
        (Evidence(EvidenceKey.LENGTH, 3), Evidence(EvidenceKey.DIRECTION, 1)),
    )

    print_results(AnalysisResult((match,)))

    output = capsys.readouterr().out
    assert "numeric_sequence" in output
    assert "structural.numeric_sequence" in output
    assert "[1, 4)" in output
    assert "length=3, direction=1" in output
