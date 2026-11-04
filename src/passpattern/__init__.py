"""Public interfaces for the PassPattern foundation."""

from passpattern.config import EngineConfig
from passpattern.detector import Detector, NormalizationAwareDetector
from passpattern.engine import PassPatternEngine
from passpattern.errors import (
    DetectorExecutionError,
    DictionarySearchLimitError,
    InputTooLargeError,
    InvalidDetectorResultError,
    InvalidPasswordTypeError,
    InvalidUnicodeError,
    NativeExtensionUnavailableError,
    NumericSequenceLimitError,
    PasswordProcessingError,
    TooManyMatchesError,
)
from passpattern.models import (
    AnalysisResult,
    Evidence,
    EvidenceKey,
    NumericPatternMatch,
    NumericTerm,
    PatternMatch,
)

__all__ = [
    "AnalysisResult",
    "Detector",
    "DetectorExecutionError",
    "DictionarySearchLimitError",
    "EngineConfig",
    "Evidence",
    "EvidenceKey",
    "InputTooLargeError",
    "InvalidPasswordTypeError",
    "InvalidUnicodeError",
    "InvalidDetectorResultError",
    "NativeExtensionUnavailableError",
    "NormalizationAwareDetector",
    "NumericPatternMatch",
    "NumericSequenceLimitError",
    "NumericTerm",
    "PassPatternEngine",
    "PasswordProcessingError",
    "PatternMatch",
    "TooManyMatchesError",
]
