from dataclasses import FrozenInstanceError

import pytest

from passpattern import EngineConfig, Evidence, EvidenceKey, PatternMatch


def test_pattern_match_is_immutable_and_accepts_typed_evidence() -> None:
    match = PatternMatch(
        detector_id="test",
        category="structural",
        pattern_type="sequence",
        start_index=0,
        end_index=2,
        evidence=(Evidence(EvidenceKey.LENGTH, 2),),
    )

    with pytest.raises(FrozenInstanceError):
        match.start_index = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    ("start", "end"),
    [(-1, 1), (0, 0), (2, 1)],
)
def test_pattern_match_rejects_invalid_spans(start: int, end: int) -> None:
    with pytest.raises(ValueError, match="spans"):
        PatternMatch("test", "structural", "sequence", start, end)


def test_pattern_match_rejects_arbitrary_evidence_text() -> None:
    with pytest.raises(TypeError, match="finite numbers or booleans"):
        Evidence(EvidenceKey.DIRECTION, "secret")  # type: ignore[arg-type]


def test_pattern_match_rejects_duplicate_evidence_keys() -> None:
    with pytest.raises(ValueError, match="unique"):
        PatternMatch(
            "test",
            "structural",
            "sequence",
            0,
            1,
            (Evidence(EvidenceKey.COUNT, 2), Evidence(EvidenceKey.COUNT, 3)),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_codepoints", True),
        ("max_codepoints", 0),
        ("max_codepoints", -1),
        ("max_codepoints", "2"),
        ("max_utf8_bytes", True),
        ("max_utf8_bytes", 0),
        ("max_utf8_bytes", -1),
        ("max_utf8_bytes", "2"),
    ],
)
def test_engine_config_requires_positive_integer_limits(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        EngineConfig(**{field: value})


@pytest.mark.parametrize("normalization", ["", "NFC", "none ", None])
def test_engine_config_rejects_unsupported_normalization(normalization: object) -> None:
    with pytest.raises(ValueError, match="normalization"):
        EngineConfig(normalization=normalization)  # type: ignore[arg-type]


def test_engine_config_copies_mutable_detector_selection() -> None:
    selected = {"first"}

    config = EngineConfig(detector_ids=selected)  # type: ignore[arg-type]
    selected.add("second")

    assert config.detector_ids == frozenset({"first"})
