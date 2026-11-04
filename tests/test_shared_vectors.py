"""Verify reviewed, language-neutral parity vectors against the Python reference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from passpattern import (
    EngineConfig,
    InputTooLargeError,
    InvalidPasswordTypeError,
    InvalidUnicodeError,
    NumericPatternMatch,
    NumericSequenceLimitError,
    PassPatternEngine,
)
from passpattern.contextual import (
    CalendarDateDetector,
    KeyboardLayout,
    KeyboardWalkDetector,
    YearDetector,
)
from passpattern.dictionary import (
    DictionaryCompoundDetector,
    DictionaryEntry,
    DictionaryLexicon,
    DictionaryWordDetector,
    LeetspeakDetector,
    ReversedWordDetector,
)
from passpattern.structural import (
    AlphabeticSequenceDetector,
    NumericSequenceDetector,
    RepeatedCharacterDetector,
    RepeatedSubstringDetector,
)

_FIXTURE_PATH = Path(__file__).parent / "vectors" / "passpattern-v2.json"
_FIXTURES = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
_EXPECTED_ERRORS = {
    "input_too_large": InputTooLargeError,
    "invalid_password_type": InvalidPasswordTypeError,
    "invalid_unicode": InvalidUnicodeError,
    "numeric_sequence_limit": NumericSequenceLimitError,
}


def test_shared_vector_document_schema() -> None:
    assert _FIXTURES["schema_version"] == 2
    assert _FIXTURES["numeric_match_fields"] == [
        "numeric_terms",
        "parameter",
        "ambiguous",
    ]
    assert _FIXTURES["indexing"] == (
        "zero-based half-open Unicode code-point offsets into post-normalization processed_text"
    )
    vectors = _FIXTURES["vectors"]
    assert vectors
    assert len({vector["id"] for vector in vectors}) == len(vectors)
    for vector in vectors:
        assert {"input", "config", "detectors", "expected"} <= vector.keys()
        assert ("matches" in vector["expected"]) ^ ("error" in vector["expected"])


@pytest.mark.native
@pytest.mark.parametrize("vector", _FIXTURES["vectors"], ids=lambda vector: vector["id"])
def test_shared_vector_matches_python_reference(vector: dict[str, Any]) -> None:
    config = EngineConfig(**vector["config"])
    detectors = tuple(_build_detector(spec, config.normalization) for spec in vector["detectors"])
    engine = PassPatternEngine(detectors, config)
    expected_error = vector["expected"].get("error")

    if expected_error is not None:
        with pytest.raises(_EXPECTED_ERRORS[expected_error]):
            engine.analyze(vector["input"])
        return

    result = engine.analyze(vector["input"])
    actual_matches: list[dict[str, Any]] = []
    for match in result.matches:
        serialized_match: dict[str, Any] = {
            "detector_id": match.detector_id,
            "category": match.category,
            "pattern_type": match.pattern_type,
            "span": [match.start_index, match.end_index],
            "evidence": {item.key.value: item.value for item in match.evidence},
        }
        if isinstance(match, NumericPatternMatch):
            serialized_match["numeric_terms"] = [
                {"value": term.value, "span": [term.start_index, term.end_index]}
                for term in match.terms
            ]
            serialized_match["parameter"] = (
                [match.parameter_numerator, match.parameter_denominator]
                if match.parameter_numerator is not None
                else None
            )
            serialized_match["ambiguous"] = match.ambiguous
        actual_matches.append(serialized_match)
    assert actual_matches == vector["expected"]["matches"]


def _build_detector(spec: dict[str, Any], normalization: str) -> object:
    detector_id = spec["id"]
    options = dict(spec.get("options", {}))
    if detector_id == "structural.alphabetic_sequence":
        return AlphabeticSequenceDetector(**options)
    if detector_id == "structural.numeric_sequence":
        return NumericSequenceDetector(**options)
    if detector_id == "structural.repeated_character":
        return RepeatedCharacterDetector(**options)
    if detector_id == "structural.repeated_substring":
        return RepeatedSubstringDetector(**options)
    if detector_id == "contextual.calendar_date":
        return CalendarDateDetector(**options)
    if detector_id == "contextual.keyboard_walk":
        layout = options.get("layout")
        if isinstance(layout, dict):
            options["layout"] = KeyboardLayout(
                name=layout["name"],
                positions={key: tuple(position) for key, position in layout["positions"].items()},
            )
        return KeyboardWalkDetector(**options)
    if detector_id == "contextual.year":
        return YearDetector(**options)
    if detector_id in (
        "dictionary.word",
        "dictionary.compound",
        "dictionary.reversed_word",
        "dictionary.leetspeak",
    ):
        entries = [DictionaryEntry(**entry) for entry in options.pop("entries")]
        lexicon_options = options.pop("lexicon", {})
        lexicon = DictionaryLexicon(
            entries,
            normalization=normalization,
            **lexicon_options,
        )
        if detector_id == "dictionary.word":
            return DictionaryWordDetector(lexicon, **options)
        if detector_id == "dictionary.compound":
            return DictionaryCompoundDetector(lexicon, **options)
        if detector_id == "dictionary.reversed_word":
            return ReversedWordDetector(lexicon, **options)
        return LeetspeakDetector(lexicon, **options)
    raise ValueError(f"Unknown shared-vector detector: {detector_id}")
