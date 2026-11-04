"""Shared validation for structural detector thresholds."""


def validate_minimum(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        raise ValueError(f"{name} must be an integer of at least 2.")
