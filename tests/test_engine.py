from dataclasses import dataclass

import pytest

from passpattern import (
    DetectorExecutionError,
    DictionarySearchLimitError,
    EngineConfig,
    InputTooLargeError,
    InvalidDetectorResultError,
    NativeExtensionUnavailableError,
    PassPatternEngine,
    PatternMatch,
    TooManyMatchesError,
)
from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    DictionaryWordDetector,
    LeetspeakDetector,
)


@dataclass(frozen=True)
class Prepared:
    processed_text: str


class StaticDetector:
    def __init__(self, identifier: str, matches: tuple[PatternMatch, ...]) -> None:
        self.detector_id = identifier
        self.matches = matches
        self.received: object | None = None

    def detect(self, prepared_password: Prepared):
        self.received = prepared_password
        return self.matches


def match(
    detector_id: str,
    start: int,
    end: int,
    pattern_type: str = "sample",
) -> PatternMatch:
    return PatternMatch(detector_id, "structural", pattern_type, start, end)


def test_engine_prepares_once_preserves_overlaps_and_sorts(monkeypatch: pytest.MonkeyPatch) -> None:
    prepared = Prepared("a😀b")
    calls: list[str] = []
    configs: list[EngineConfig] = []

    def prepare(password: str, config: EngineConfig) -> Prepared:
        calls.append(password)
        configs.append(config)
        return prepared

    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        prepare,
    )
    second = StaticDetector("second", (match("second", 0, 2),))
    first = StaticDetector("first", (match("first", 0, 1), match("first", 1, 3)))

    result = PassPatternEngine((second, first)).analyze("synthetic")

    assert calls == ["synthetic"]
    assert len(configs) == 1
    assert configs[0].max_codepoints == 1024
    assert configs[0].max_utf8_bytes == 4096
    assert second.received is prepared
    assert first.received is prepared
    assert [(item.start_index, item.end_index, item.detector_id) for item in result.matches] == [
        (0, 1, "first"),
        (0, 2, "second"),
        (1, 3, "first"),
    ]


def test_engine_uses_code_point_length_for_span_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared("é😀"),
    )
    detector = StaticDetector("unicode", (match("unicode", 1, 2),))

    assert len(PassPatternEngine((detector,)).analyze("synthetic").matches) == 1


def test_engine_rejects_out_of_range_unicode_span(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared("é😀"),
    )
    detector = StaticDetector("unicode", (match("unicode", 1, 3),))

    with pytest.raises(InvalidDetectorResultError, match="outside processed_text"):
        PassPatternEngine((detector,)).analyze("synthetic")


def test_engine_rejects_unreadable_prepared_text_before_running_detectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnreadablePrepared:
        @property
        def processed_text(self) -> str:
            raise RuntimeError("native detail: synthetic-secret")

    detector = StaticDetector("probe", ())
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: UnreadablePrepared(),
    )

    with pytest.raises(InvalidDetectorResultError) as error:
        PassPatternEngine((detector,)).analyze("synthetic-secret")

    assert str(error.value) == "Native prepared-password value has no readable processed_text."
    assert "synthetic-secret" not in repr(error.value)
    assert detector.received is None


def test_engine_rejects_non_string_prepared_text_before_running_detectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = Prepared(42)  # type: ignore[arg-type]
    detector = StaticDetector("probe", ())
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: prepared,
    )

    with pytest.raises(InvalidDetectorResultError) as error:
        PassPatternEngine((detector,)).analyze("synthetic-secret")

    assert str(error.value) == "Native processed_text must be a string."
    assert "synthetic-secret" not in repr(error.value)
    assert detector.received is None


def test_engine_limits_input_before_native_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: calls.append(password) or Prepared(password),
    )
    engine = PassPatternEngine(config=EngineConfig(max_codepoints=2))

    with pytest.raises(InputTooLargeError):
        engine.analyze("abc")

    assert calls == []


def test_empty_password_is_sent_to_native_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: calls.append(password) or Prepared(""),
    )

    result = PassPatternEngine().analyze("")

    assert calls == [""]
    assert result.matches == ()


def test_missing_native_extension_has_clear_content_free_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_extension(name: str) -> object:
        raise ModuleNotFoundError(name=name)

    monkeypatch.setattr("passpattern.native.importlib.import_module", missing_extension)

    with pytest.raises(NativeExtensionUnavailableError) as error:
        PassPatternEngine().analyze("synthetic-secret")

    assert "synthetic-secret" not in str(error.value)


def test_detector_configuration_selects_registered_detectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    selected = StaticDetector("selected", ())
    skipped = StaticDetector("skipped", ())
    engine = PassPatternEngine(
        (selected, skipped),
        EngineConfig(detector_ids=frozenset({"selected"})),
    )

    engine.analyze("synthetic")

    assert selected.received is not None
    assert skipped.received is None


def test_engine_rejects_dictionary_normalization_mismatch_without_disclosure() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("synthetic-secret", 1)],
        normalization="nfc",
    )
    detector = DictionaryWordDetector(lexicon)

    with pytest.raises(ValueError, match="normalization") as error:
        PassPatternEngine((detector,), EngineConfig(normalization="none"))

    assert "synthetic-secret" not in str(error.value)


def test_engine_rejects_multiple_dictionary_detectors_with_conflicting_requirements() -> None:
    nfc_detector = DictionaryWordDetector(
        DictionaryLexicon([DictionaryEntry("composed", 1)], normalization="nfc")
    )
    none_detector = DictionaryWordDetector(
        DictionaryLexicon([DictionaryEntry("decomposed", 1)], normalization="none")
    )

    with pytest.raises(ValueError, match="normalization"):
        PassPatternEngine(
            (nfc_detector, none_detector),
            EngineConfig(normalization="nfc"),
        )


def test_engine_rejects_dictionary_configuration_mismatch_before_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_calls: list[str] = []
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: native_calls.append(password) or Prepared(password),
    )
    detector = DictionaryWordDetector(
        DictionaryLexicon([DictionaryEntry("sunshine", 1)], normalization="nfc")
    )

    with pytest.raises(ValueError, match="normalization"):
        PassPatternEngine((detector,), EngineConfig(normalization="none"))

    assert native_calls == []


def test_structural_only_engine_allows_nfc_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from passpattern.structural import default_structural_detectors

    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    engine = PassPatternEngine(
        default_structural_detectors(),
        EngineConfig(normalization="nfc"),
    )

    assert engine.analyze("aaa").matches


def test_engine_rejects_unknown_configured_detector() -> None:
    with pytest.raises(ValueError, match="unregistered"):
        PassPatternEngine(config=EngineConfig(detector_ids=frozenset({"missing"})))


def test_engine_rejects_unsafe_detector_identifiers_without_echoing_them() -> None:
    secret = "synthetic-secret!"
    detector = StaticDetector(secret, ())

    with pytest.raises(ValueError) as error:
        PassPatternEngine((detector,))

    assert secret not in str(error.value)


def test_engine_rejects_excessive_match_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    detector = StaticDetector("many", (match("many", 0, 1), match("many", 1, 2)))

    with pytest.raises(TooManyMatchesError):
        PassPatternEngine((detector,), EngineConfig(max_matches=1)).analyze("ab")


def test_engine_propagates_explicit_dictionary_search_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared("xx"),
    )
    detector = LeetspeakDetector(
        DictionaryLexicon([DictionaryEntry("password", 1)]),
        max_work=1,
    )

    with pytest.raises(DictionarySearchLimitError, match="work limit"):
        PassPatternEngine((detector,)).analyze("synthetic")


def test_engine_sanitizes_detector_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )

    class BrokenDetector:
        detector_id = "synthetic-secret"

        def detect(self, prepared_password: Prepared):
            raise RuntimeError("synthetic-secret")

    with pytest.raises(DetectorExecutionError) as error:
        PassPatternEngine((BrokenDetector(),)).analyze("synthetic-secret")

    assert "synthetic-secret" not in str(error.value)


def test_engine_rejects_non_match_detector_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "passpattern.engine.prepare_password",
        lambda password, config: Prepared(password),
    )
    detector = StaticDetector("bad", ())
    detector.detect = lambda prepared_password: ("not-a-match",)  # type: ignore[method-assign]

    with pytest.raises(InvalidDetectorResultError, match="unsupported result"):
        PassPatternEngine((detector,)).analyze("synthetic")
