"""Lazy integration with the compiled ``passtext_native`` extension."""

from __future__ import annotations

import importlib
from typing import Protocol, cast

from passpattern.config import EngineConfig
from passpattern.errors import (
    InputTooLargeError,
    InvalidPasswordTypeError,
    InvalidUnicodeError,
    NativeExtensionUnavailableError,
    PasswordProcessingError,
)


class PreparedPassword(Protocol):
    """Structural type for the native prepared-password value."""

    @property
    def processed_text(self) -> str:
        """Text prepared by the native extension."""


def prepare_password(password: str, config: EngineConfig) -> PreparedPassword:
    """Prepare a password once through the compiled extension."""
    try:
        native = importlib.import_module("passtext_native")
    except ImportError:
        raise NativeExtensionUnavailableError(
            "The passtext_native wheel is missing or could not be loaded. Install "
            "'passtext-native>=0.1.0,<0.2.0' (published wheels cover CPython 3.10+ on "
            "Windows x86-64 and Linux x86-64; other platforms are unsupported)."
        ) from None

    try:
        pass_text_config = native.PassTextConfig
        process_password = native.process_password
        native_invalid_input_type_error = native.InvalidInputTypeError
        native_invalid_unicode_error = native.InvalidUnicodeError
        native_processing_limit_error = native.ProcessingLimitError
    except AttributeError:
        raise NativeExtensionUnavailableError(
            "The installed passtext_native wheel does not expose the required API."
        ) from None
    if not callable(pass_text_config) or not callable(process_password):
        raise NativeExtensionUnavailableError(
            "The installed passtext_native wheel does not expose the required API."
        )
    if any(
        not isinstance(native_error, type) or not issubclass(native_error, Exception)
        for native_error in (
            native_invalid_input_type_error,
            native_invalid_unicode_error,
            native_processing_limit_error,
        )
    ):
        raise NativeExtensionUnavailableError(
            "The installed passtext_native wheel does not expose the required API."
        )

    try:
        native_config = pass_text_config(
            max_codepoints=config.max_codepoints,
            max_utf8_bytes=config.max_utf8_bytes,
            normalization=config.normalization,
        )
        return cast(PreparedPassword, process_password(password, native_config))
    except native_invalid_input_type_error:
        raise InvalidPasswordTypeError("Password must be a string.") from None
    except native_invalid_unicode_error:
        raise InvalidUnicodeError("Password contains unsupported Unicode.") from None
    except native_processing_limit_error:
        raise InputTooLargeError("Password exceeds configured native processing limits.") from None
    except Exception:
        raise PasswordProcessingError("Native password processing failed.") from None
