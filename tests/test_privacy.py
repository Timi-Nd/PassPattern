import pytest

from passpattern import Evidence, EvidenceKey, PatternMatch


def test_match_representation_contains_no_password_substring() -> None:
    secret = "synthetic-secret"
    result = PatternMatch(
        "test",
        "contextual",
        "sample",
        0,
        len(secret),
        (Evidence(EvidenceKey.LENGTH, len(secret)),),
    )

    assert secret not in repr(result)


def test_evidence_rejects_non_finite_numbers() -> None:
    with pytest.raises(TypeError, match="finite"):
        Evidence(EvidenceKey.LENGTH, float("inf"))
