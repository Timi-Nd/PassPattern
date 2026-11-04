"""Content-free errors raised by PassPattern."""


class PassPatternError(Exception):
    """Base class for PassPattern errors."""


class NativeExtensionUnavailableError(PassPatternError):
    """The required compiled PassText extension is unavailable."""


class PasswordProcessingError(PassPatternError):
    """Native password processing failed without exposing its input."""


class InvalidPasswordTypeError(PassPatternError):
    """The submitted value is not a string accepted by the native processor."""


class InvalidUnicodeError(PassPatternError):
    """The submitted string contains Unicode unsupported by the native processor."""


class InputTooLargeError(PassPatternError):
    """The password exceeds the configured processing limit."""


class InvalidDetectorResultError(PassPatternError):
    """A detector returned an unsupported or invalid match."""


class DetectorExecutionError(PassPatternError):
    """A detector failed while processing a password."""


class TooManyMatchesError(PassPatternError):
    """The analysis exceeded its configured match limit."""


class DictionarySearchLimitError(PassPatternError):
    """A transformation-aware dictionary search exceeded its configured work budget."""
