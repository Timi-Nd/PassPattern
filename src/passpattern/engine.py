"""Sequential password-analysis orchestration."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator

from passpattern.config import EngineConfig
from passpattern.detector import Detector, NormalizationAwareDetector
from passpattern.errors import (
    DetectorExecutionError,
    DictionarySearchLimitError,
    InputTooLargeError,
    InvalidDetectorResultError,
    TooManyMatchesError,
)
from passpattern.models import AnalysisResult, PatternMatch
from passpattern.native import PreparedPassword, prepare_password

_IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,79}\Z")


class PassPatternEngine:
    """Prepare each input once and run selected detectors in registration order."""

    def __init__(
        self,
        detectors: Iterable[Detector] = (),
        config: EngineConfig | None = None,
    ) -> None:
        self._config = config if config is not None else EngineConfig()
        registered = tuple(detectors)
        for detector in registered:
            if isinstance(detector, NormalizationAwareDetector):
                if detector.required_normalization not in ("none", "nfc"):
                    raise ValueError("A detector declares an unsupported text normalization mode.")
                if detector.required_normalization != self._config.normalization:
                    raise ValueError(
                        "Detector text normalization does not match engine configuration."
                    )
        identifiers = tuple(detector.detector_id for detector in registered)
        if any(
            not isinstance(identifier, str) or not _IDENTIFIER.fullmatch(identifier)
            for identifier in identifiers
        ):
            raise ValueError("Detector identifiers must be lowercase ASCII identifiers.")
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Detector identifiers must be unique.")
        detector_entries = tuple(zip(registered, identifiers, strict=True))
        if self._config.detector_ids is not None:
            unknown = self._config.detector_ids.difference(identifiers)
            if unknown:
                raise ValueError("Engine configuration selects an unregistered detector.")
            detector_entries = tuple(
                (detector, identifier)
                for detector, identifier in detector_entries
                if identifier in self._config.detector_ids
            )
        self._detectors = detector_entries

    def analyze(self, password: str) -> AnalysisResult:
        """Prepare and analyze one password without retaining it in the result."""
        if isinstance(password, str) and len(password) > self._config.max_codepoints:
            raise InputTooLargeError("Password exceeds the configured input-size limit.")

        prepared = prepare_password(password, self._config)
        try:
            processed_text = prepared.processed_text
        except Exception:
            raise InvalidDetectorResultError(
                "Native prepared-password value has no readable processed_text."
            ) from None
        if not isinstance(processed_text, str):
            raise InvalidDetectorResultError("Native processed_text must be a string.")

        found: list[PatternMatch] = []
        for detector, detector_id in self._detectors:
            for match in self._run_detector(detector, prepared):
                if not isinstance(match, PatternMatch):
                    raise InvalidDetectorResultError(
                        "A detector returned an unsupported result type."
                    )
                if match.detector_id != detector_id:
                    raise InvalidDetectorResultError(
                        "A detector returned a match with a different identifier."
                    )
                if match.end_index > len(processed_text):
                    raise InvalidDetectorResultError(
                        "A detector returned a span outside processed_text."
                    )
                found.append(match)
                if len(found) > self._config.max_matches:
                    raise TooManyMatchesError("Analysis exceeded the configured match limit.")

        found.sort(
            key=lambda match: (
                match.start_index,
                match.end_index,
                match.detector_id,
                match.category,
                match.pattern_type,
                tuple((item.key.value, item.value) for item in match.evidence),
            )
        )
        return AnalysisResult(tuple(found))

    @staticmethod
    def _run_detector(
        detector: Detector,
        prepared_password: PreparedPassword,
    ) -> Iterator[object]:
        try:
            results = detector.detect(prepared_password)
            iterator = iter(results)
        except DictionarySearchLimitError:
            raise
        except Exception:
            raise DetectorExecutionError("A detector failed.") from None

        while True:
            try:
                yield next(iterator)
            except StopIteration:
                return
            except DictionarySearchLimitError:
                raise
            except Exception:
                raise DetectorExecutionError("A detector failed.") from None
