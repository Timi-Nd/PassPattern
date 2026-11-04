"""Compare the previous linear numeric detector with generalized sequence analysis."""

from __future__ import annotations

from statistics import median
from time import perf_counter

from passpattern.detector import Detector
from passpattern.structural import NumericSequenceDetector
from passpattern.structural._sequences import detect_sequences


class Prepared:
    def __init__(self, processed_text: str) -> None:
        self.processed_text = processed_text


def _ascii_digit_value(character: str) -> int | None:
    if "0" <= character <= "9":
        return ord(character)
    return None


def _legacy_count(text: str) -> int:
    return sum(
        1
        for _ in detect_sequences(
            text,
            "structural.numeric_sequence",
            "numeric_sequence",
            3,
            _ascii_digit_value,
        )
    )


def _generalized_count(detector: Detector, text: str) -> int:
    return sum(1 for _ in detector.detect(Prepared(text)))  # type: ignore[arg-type]


def _median_ms(function, text: str, repetitions: int) -> float:
    function(text)
    samples = []
    for _ in range(repetitions):
        started = perf_counter()
        function(text)
        samples.append((perf_counter() - started) * 1000)
    return median(samples)


def main() -> None:
    cases = {
        "short-legacy": "x123y",
        "typical-24": "Aa1!bc123xyzzxyzz7890!!",
        "arithmetic-8": "10121416",
        "prime-sequence-6": "235711",
        "adversarial-run-32": "1" * 32,
    }
    detector = NumericSequenceDetector()
    repetitions = 100

    for name, text in cases.items():
        legacy_ms = _median_ms(_legacy_count, text, repetitions)
        generalized_ms = _median_ms(
            lambda value: _generalized_count(detector, value), text, repetitions
        )
        print(
            f"{name} ({len(text)} code points): "
            f"legacy {legacy_ms:.4f} ms; generalized {generalized_ms:.4f} ms"
        )


if __name__ == "__main__":
    main()
