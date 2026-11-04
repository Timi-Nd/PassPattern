import unicodedata

import pytest

from passpattern import (
    EngineConfig,
    InputTooLargeError,
    InvalidPasswordTypeError,
    InvalidUnicodeError,
    PassPatternEngine,
    PatternMatch,
)
from passpattern.contextual import default_contextual_detectors
from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    DictionaryWordDetector,
    LeetspeakDetector,
    ReversedWordDetector,
)
from passpattern.structural import default_structural_detectors


class InspectingDetector:
    detector_id = "native_probe"

    def __init__(self) -> None:
        self.prepared_password = None
        self.processed_text = None

    def detect(self, prepared_password):
        self.prepared_password = prepared_password
        self.processed_text = prepared_password.processed_text
        if not self.processed_text:
            return ()
        return (
            PatternMatch(
                self.detector_id,
                "contextual",
                "native_probe",
                0,
                len(self.processed_text),
            ),
        )


@pytest.mark.native
def test_native_extension_processes_ascii_password() -> None:
    import passtext_native

    detector = InspectingDetector()
    result = PassPatternEngine((detector,)).analyze("Synthetic-passphrase-482!")

    assert isinstance(detector.prepared_password, passtext_native.PreparedPassword)
    assert detector.processed_text == "Synthetic-passphrase-482!"
    assert len(result.matches) == 1


@pytest.mark.native
def test_native_extension_processes_empty_password() -> None:
    detector = InspectingDetector()

    result = PassPatternEngine((detector,)).analyze("")

    assert detector.processed_text == ""
    assert result.matches == ()


@pytest.mark.native
@pytest.mark.parametrize(
    ("password", "expected"),
    [
        (
            "\u65e5\u672c\u8a9e\u043f\u0440\u0438\u0432\u0435\u0442",
            "\u65e5\u672c\u8a9e\u043f\u0440\u0438\u0432\u0435\u0442",
        ),
        ("\U0001f642\U0001f680", "\U0001f642\U0001f680"),
        ("e\u0301", "e\u0301"),
    ],
)
def test_native_extension_preserves_unicode_without_normalization(
    password: str,
    expected: str,
) -> None:
    detector = InspectingDetector()

    result = PassPatternEngine((detector,)).analyze(password)

    assert detector.processed_text == expected
    assert result.matches[0].end_index == len(expected)


@pytest.mark.native
def test_native_extension_applies_nfc_before_detector_and_span_validation() -> None:
    import passtext_native

    detector = InspectingDetector()
    engine = PassPatternEngine((detector,), EngineConfig(normalization="nfc"))

    result = engine.analyze("e\u0301\U0001f642123")

    assert isinstance(detector.prepared_password, passtext_native.PreparedPassword)
    assert detector.processed_text == "\u00e9\U0001f642123"
    assert len(result.matches) == 1
    assert result.matches[0].start_index == 0
    assert result.matches[0].end_index == len(detector.processed_text)


@pytest.mark.native
def test_default_codepoint_and_utf8_byte_limits_reach_native(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import passtext_native

    native_process_password = passtext_native.process_password
    observed_configs = []

    def process_password(password, config=None):
        observed_configs.append(config)
        return native_process_password(password, config)

    monkeypatch.setattr(passtext_native, "process_password", process_password)
    PassPatternEngine().analyze("\U0001f600" * 1024)

    assert len(observed_configs) == 1
    assert len("\U0001f600" * 1024) == 1024
    assert len(("\U0001f600" * 1024).encode("utf-8")) == 4096
    assert observed_configs[0].max_codepoints == 1024
    assert observed_configs[0].max_utf8_bytes == 4096


@pytest.mark.native
def test_custom_limits_are_passed_to_native_and_enforced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import passtext_native

    native_process_password = passtext_native.process_password
    observed_configs = []

    def process_password(password, config=None):
        observed_configs.append(config)
        return native_process_password(password, config)

    monkeypatch.setattr(passtext_native, "process_password", process_password)
    engine = PassPatternEngine(
        config=EngineConfig(max_codepoints=10, max_utf8_bytes=2, normalization="nfc")
    )

    with pytest.raises(InputTooLargeError):
        engine.analyze("e\u0301")

    assert len(observed_configs) == 1
    assert observed_configs[0].max_codepoints == 10
    assert observed_configs[0].max_utf8_bytes == 2
    assert observed_configs[0].normalization == "nfc"


@pytest.mark.native
def test_default_codepoint_limit_rejects_long_input() -> None:
    with pytest.raises(InputTooLargeError):
        PassPatternEngine().analyze("a" * 1025)


@pytest.mark.native
def test_native_invalid_unicode_is_classified_without_disclosure() -> None:
    with pytest.raises(InvalidUnicodeError) as error:
        PassPatternEngine().analyze("\ud800")

    assert "d800" not in str(error.value)


@pytest.mark.native
def test_native_invalid_input_type_is_classified_without_disclosure() -> None:
    with pytest.raises(InvalidPasswordTypeError) as error:
        PassPatternEngine().analyze(123)  # type: ignore[arg-type]

    assert "123" not in str(error.value)


@pytest.mark.native
def test_native_process_password_is_called_once_per_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import passtext_native

    native_process_password = passtext_native.process_password
    calls = []

    def process_password(password, config=None):
        calls.append(password)
        return native_process_password(password, config)

    monkeypatch.setattr(passtext_native, "process_password", process_password)
    detector = InspectingDetector()

    PassPatternEngine((detector,)).analyze("synthetic-one")
    PassPatternEngine((detector,)).analyze("synthetic-two")

    assert calls == ["synthetic-one", "synthetic-two"]
    assert isinstance(detector.prepared_password, passtext_native.PreparedPassword)


@pytest.mark.native
def test_real_native_pipeline_runs_all_structural_detectors_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import passtext_native

    native_process_password = passtext_native.process_password
    calls = []

    def process_password(password, config=None):
        calls.append(password)
        return native_process_password(password, config)

    monkeypatch.setattr(passtext_native, "process_password", process_password)
    text = "aaa1212121234AbCd\U0001f642\U0001f642\U0001f642"
    result = PassPatternEngine(default_structural_detectors()).analyze(text)

    assert calls == [text]
    assert {
        "structural.repeated_character",
        "structural.repeated_substring",
        "structural.numeric_sequence",
        "structural.alphabetic_sequence",
    } == {match.detector_id for match in result.matches}
    assert any(
        match.detector_id == "structural.repeated_character"
        and (match.start_index, match.end_index) == (0, 3)
        for match in result.matches
    )
    assert any(
        match.detector_id == "structural.repeated_substring"
        and (match.start_index, match.end_index) == (3, 11)
        for match in result.matches
    )
    assert any(
        match.detector_id == "structural.numeric_sequence"
        and (match.start_index, match.end_index) == (9, 13)
        for match in result.matches
    )
    assert any(
        match.detector_id == "structural.alphabetic_sequence"
        and (match.start_index, match.end_index) == (13, 17)
        for match in result.matches
    )
    assert any(
        match.detector_id == "structural.repeated_character"
        and (match.start_index, match.end_index) == (17, 20)
        for match in result.matches
    )
    assert not any(
        (match.start_index, match.end_index) == (3, 11)
        and match.detector_id == "structural.numeric_sequence"
        for match in result.matches
    )
    assert text not in repr(result)


@pytest.mark.native
def test_real_native_nfc_pipeline_uses_processed_text_codepoint_spans() -> None:
    engine = PassPatternEngine(
        (default_structural_detectors()[0],),
        EngineConfig(normalization="nfc"),
    )

    result = engine.analyze("e\u0301e\u0301e\u0301")

    assert len(result.matches) == 1
    assert result.matches[0].detector_id == "structural.repeated_character"
    assert (result.matches[0].start_index, result.matches[0].end_index) == (0, 3)


@pytest.mark.native
def test_real_native_pipeline_integrates_dictionary_and_structural_detectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import passtext_native

    native_process_password = passtext_native.process_password
    calls = []

    def process_password(password, config=None):
        calls.append(password)
        return native_process_password(password, config)

    monkeypatch.setattr(passtext_native, "process_password", process_password)
    lexicon = DictionaryLexicon([DictionaryEntry("sunshine", 7), DictionaryEntry("sun", 12)])
    detector = DictionaryWordDetector(lexicon)
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
    assert any(
        match.detector_id == "dictionary.word" and (match.start_index, match.end_index) == (0, 3)
        for match in result.matches
    )
    assert "Sunshine" not in repr(result)


@pytest.mark.native
def test_real_native_nfc_dictionary_entries_match_normalized_text() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("caf\u00e9", 3)],
        normalization="nfc",
    )
    engine = PassPatternEngine(
        (DictionaryWordDetector(lexicon),),
        EngineConfig(normalization="nfc"),
    )

    result = engine.analyze("xxcafe\u0301123")

    assert len(result.matches) == 1
    assert (result.matches[0].start_index, result.matches[0].end_index) == (2, 6)


@pytest.mark.native
def test_python_dataset_validation_and_rust_nfc_agree_on_normalization_samples() -> None:
    import passtext_native

    samples = (
        "cafe\u0301",
        "A\u030a",
        "\u1100\u1161",
        "\u03b1\u0313",
    )
    python_version = tuple(int(part) for part in unicodedata.unidata_version.split("."))
    rust_version = tuple(passtext_native.UNICODE_NORMALIZATION_VERSION)

    assert len(python_version) >= 2
    assert len(rust_version) == 3
    for decomposed in samples:
        python_nfc = unicodedata.normalize("NFC", decomposed)
        rust_nfc = passtext_native.process_password(
            decomposed,
            passtext_native.PassTextConfig(normalization="nfc"),
        ).processed_text
        assert python_nfc == rust_nfc
        assert (
            DictionaryLexicon(
                [DictionaryEntry(python_nfc, 1)],
                normalization="nfc",
            )
            .entries[0]
            .word
            == rust_nfc
        )


@pytest.mark.native
def test_nfc_dictionary_matches_combining_sequence_at_nonzero_processed_index() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("caf\u00e9", 1)],
        normalization="nfc",
    )
    engine = PassPatternEngine(
        (DictionaryWordDetector(lexicon),),
        EngineConfig(normalization="nfc"),
    )

    result = engine.analyze("\U0001f642--cafe\u0301--")

    assert len(result.matches) == 1
    assert (result.matches[0].start_index, result.matches[0].end_index) == (3, 7)


@pytest.mark.native
def test_real_native_pipeline_runs_all_dictionary_transformations_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import passtext_native

    native_process_password = passtext_native.process_password
    calls = []

    def process_password(password, config=None):
        calls.append(password)
        return native_process_password(password, config)

    class PreparedCapture:
        detector_id = "integration.capture"

        def __init__(self) -> None:
            self.prepared = None

        def detect(self, prepared_password):
            self.prepared = prepared_password
            return ()

    monkeypatch.setattr(passtext_native, "process_password", process_password)
    lexicon = DictionaryLexicon(
        [
            DictionaryEntry("password", 1),
            DictionaryEntry("dragon", 2),
        ]
    )
    capture = PreparedCapture()
    engine = PassPatternEngine(
        (
            *default_structural_detectors(),
            DictionaryWordDetector(lexicon),
            ReversedWordDetector(lexicon),
            LeetspeakDetector(lexicon),
            capture,
        )
    )
    password = "p@ssw0rd1234 drowssap!"

    result = engine.analyze(password)

    assert calls == [password]
    assert isinstance(capture.prepared, passtext_native.PreparedPassword)
    assert any(
        match.detector_id == "dictionary.leetspeak"
        and (match.start_index, match.end_index) == (0, 8)
        for match in result.matches
    )
    assert any(
        match.detector_id == "structural.numeric_sequence"
        and (match.start_index, match.end_index) == (8, 12)
        for match in result.matches
    )
    assert any(
        match.detector_id == "dictionary.reversed_word"
        and (match.start_index, match.end_index) == (13, 21)
        for match in result.matches
    )
    assert password not in repr(result)


def test_engine_rejects_transformation_detector_normalization_mismatch() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("password", 1)],
        normalization="nfc",
    )

    with pytest.raises(ValueError, match="normalization"):
        PassPatternEngine(
            (ReversedWordDetector(lexicon), LeetspeakDetector(lexicon)),
            EngineConfig(normalization="none"),
        )


@pytest.mark.native
def test_real_native_nfc_reversed_match_uses_processed_codepoint_indices() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("\u00e9xy", 1)],
        normalization="nfc",
    )
    engine = PassPatternEngine(
        (ReversedWordDetector(lexicon, min_word_length=3),),
        EngineConfig(normalization="nfc"),
    )

    result = engine.analyze("--yx\u0065\u0301--")

    assert len(result.matches) == 1
    assert (result.matches[0].start_index, result.matches[0].end_index) == (2, 5)


@pytest.mark.native
def test_real_native_nfc_leetspeak_match_uses_processed_codepoint_indices() -> None:
    lexicon = DictionaryLexicon(
        [DictionaryEntry("password", 1)],
        normalization="nfc",
    )
    engine = PassPatternEngine(
        (LeetspeakDetector(lexicon),),
        EngineConfig(normalization="nfc"),
    )

    result = engine.analyze("cafe\u0301--p@ssword")

    assert len(result.matches) == 1
    assert (result.matches[0].start_index, result.matches[0].end_index) == (6, 14)


@pytest.mark.native
def test_real_native_pipeline_integrates_contextual_and_existing_detectors_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import passtext_native

    native_process_password = passtext_native.process_password
    calls = []

    def process_password(password, config=None):
        calls.append(password)
        return native_process_password(password, config)

    class RecordingDetector:
        def __init__(self, detector) -> None:
            self.detector = detector
            self.detector_id = detector.detector_id
            self.prepared = None

        @property
        def required_normalization(self):
            return "nfc"

        def detect(self, prepared_password):
            self.prepared = prepared_password
            return self.detector.detect(prepared_password)

    monkeypatch.setattr(passtext_native, "process_password", process_password)
    lexicon = DictionaryLexicon(
        [DictionaryEntry("password", 1), DictionaryEntry("dragon", 2)],
        normalization="nfc",
    )
    detectors = (
        *default_structural_detectors(),
        DictionaryWordDetector(lexicon),
        ReversedWordDetector(lexicon),
        LeetspeakDetector(lexicon),
        *default_contextual_detectors(),
    )
    recorded = tuple(RecordingDetector(detector) for detector in detectors)
    password = "e\u0301\U0001f642p@ssword2026-11-02Qwerty!drowssap"

    result = PassPatternEngine(
        recorded,
        EngineConfig(normalization="nfc"),
    ).analyze(password)

    assert calls == [password]
    assert len({id(detector.prepared) for detector in recorded}) == 1
    assert isinstance(recorded[0].prepared, passtext_native.PreparedPassword)
    spans_by_detector = {
        detector_id: {
            (match.start_index, match.end_index)
            for match in result.matches
            if match.detector_id == detector_id
        }
        for detector_id in (
            "dictionary.leetspeak",
            "dictionary.reversed_word",
            "contextual.calendar_date",
            "contextual.year",
            "contextual.keyboard_walk",
        )
    }
    assert spans_by_detector == {
        "dictionary.leetspeak": {(2, 10)},
        "dictionary.reversed_word": {(27, 35)},
        "contextual.calendar_date": {(10, 20)},
        "contextual.year": {(10, 14)},
        "contextual.keyboard_walk": {(19, 26)},
    }
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
    assert password not in repr(result)
    assert "password" not in repr(result)
    assert "Qwerty" not in repr(result)


@pytest.mark.native
def test_native_rejects_invalid_unicode_before_contextual_detection() -> None:
    with pytest.raises(InvalidUnicodeError) as error:
        PassPatternEngine(default_contextual_detectors()).analyze("\ud800")

    assert "d800" not in str(error.value)
