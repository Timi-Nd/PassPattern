from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from passpattern import (
    EngineConfig,
    InputTooLargeError,
    InvalidPasswordTypeError,
    InvalidUnicodeError,
    NativeExtensionUnavailableError,
    PasswordProcessingError,
)
from passpattern.native import prepare_password


class NativeInvalidInputTypeError(Exception):
    pass


class NativeInvalidUnicodeError(Exception):
    pass


class NativeProcessingLimitError(Exception):
    pass


class FakePassTextConfig:
    def __init__(
        self,
        *,
        max_codepoints: int,
        max_utf8_bytes: int,
        normalization: str,
    ) -> None:
        self.max_codepoints = max_codepoints
        self.max_utf8_bytes = max_utf8_bytes
        self.normalization = normalization


def fake_native(process_password: Any) -> SimpleNamespace:
    return SimpleNamespace(
        PassTextConfig=FakePassTextConfig,
        process_password=process_password,
        InvalidInputTypeError=NativeInvalidInputTypeError,
        InvalidUnicodeError=NativeInvalidUnicodeError,
        ProcessingLimitError=NativeProcessingLimitError,
    )


@pytest.mark.parametrize(
    ("native_error", "expected_error"),
    [
        (NativeInvalidInputTypeError, InvalidPasswordTypeError),
        (NativeInvalidUnicodeError, InvalidUnicodeError),
        (NativeProcessingLimitError, InputTooLargeError),
    ],
)
def test_native_errors_are_translated_without_disclosing_input(
    monkeypatch: pytest.MonkeyPatch,
    native_error: type[Exception],
    expected_error: type[Exception],
) -> None:
    secret = "synthetic-secret"

    def process_password(password: str, config: FakePassTextConfig) -> None:
        raise native_error(f"native rejected {password}")

    monkeypatch.setattr(
        "passpattern.native.importlib.import_module",
        lambda name: fake_native(process_password),
    )

    with pytest.raises(expected_error) as error:
        prepare_password(secret, EngineConfig())

    assert secret not in str(error.value)
    assert error.value.__cause__ is None


def test_native_processing_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "synthetic-secret"

    def process_password(password: str, config: FakePassTextConfig) -> None:
        raise RuntimeError(f"native failure for {password}")

    monkeypatch.setattr(
        "passpattern.native.importlib.import_module",
        lambda name: fake_native(process_password),
    )

    with pytest.raises(PasswordProcessingError) as error:
        prepare_password(secret, EngineConfig())

    assert str(error.value) == "Native password processing failed."
    assert secret not in repr(error.value)
    assert error.value.__cause__ is None


def test_native_config_failure_is_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "synthetic-secret"
    native = fake_native(lambda password, config: None)

    def fail_config(**kwargs: object) -> None:
        raise RuntimeError(f"native config failed for {secret}")

    native.PassTextConfig = fail_config
    monkeypatch.setattr("passpattern.native.importlib.import_module", lambda name: native)

    with pytest.raises(PasswordProcessingError) as error:
        prepare_password(secret, EngineConfig())

    assert str(error.value) == "Native password processing failed."
    assert secret not in repr(error.value)


def test_native_processing_receives_engine_limits_and_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, FakePassTextConfig]] = []
    prepared = SimpleNamespace(processed_text="prepared")

    def process_password(password: str, config: FakePassTextConfig) -> object:
        observed.append((password, config))
        return prepared

    monkeypatch.setattr(
        "passpattern.native.importlib.import_module",
        lambda name: fake_native(process_password),
    )
    config = EngineConfig(
        max_codepoints=21,
        max_utf8_bytes=84,
        normalization="nfc",
    )

    result = prepare_password("synthetic", config)

    assert result is prepared
    assert len(observed) == 1
    password, native_config = observed[0]
    assert password == "synthetic"
    assert native_config.max_codepoints == 21
    assert native_config.max_utf8_bytes == 84
    assert native_config.normalization == "nfc"


def test_missing_native_api_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "passpattern.native.importlib.import_module",
        lambda name: SimpleNamespace(),
    )

    with pytest.raises(NativeExtensionUnavailableError) as error:
        prepare_password("synthetic-secret", EngineConfig())

    assert (
        str(error.value) == "The installed passtext_native wheel does not expose the required API."
    )
    assert "synthetic-secret" not in repr(error.value)


def test_native_import_error_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_import(name: str) -> object:
        raise ImportError("native loader detail")

    monkeypatch.setattr("passpattern.native.importlib.import_module", fail_import)

    with pytest.raises(NativeExtensionUnavailableError) as error:
        prepare_password("synthetic-secret", EngineConfig())

    assert "native loader detail" not in str(error.value)
    assert "synthetic-secret" not in str(error.value)


@pytest.mark.parametrize(
    "export",
    [
        "InvalidInputTypeError",
        "InvalidUnicodeError",
        "ProcessingLimitError",
    ],
)
def test_non_exception_native_error_export_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    export: str,
) -> None:
    native = fake_native(lambda password, config: (_ for _ in ()).throw(RuntimeError("failure")))
    setattr(native, export, "not-an-exception")
    monkeypatch.setattr("passpattern.native.importlib.import_module", lambda name: native)

    with pytest.raises(NativeExtensionUnavailableError) as error:
        prepare_password("synthetic-secret", EngineConfig())

    assert (
        str(error.value) == "The installed passtext_native wheel does not expose the required API."
    )
    assert "synthetic-secret" not in repr(error.value)


@pytest.mark.parametrize("export", ["PassTextConfig", "process_password"])
def test_non_callable_native_function_export_is_reported_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    export: str,
) -> None:
    native = fake_native(lambda password, config: None)
    setattr(native, export, "not-callable")
    monkeypatch.setattr("passpattern.native.importlib.import_module", lambda name: native)

    with pytest.raises(NativeExtensionUnavailableError):
        prepare_password("synthetic-secret", EngineConfig())
