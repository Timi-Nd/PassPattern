"""Benchmark contextual detectors on deterministic synthetic inputs."""

from __future__ import annotations

import platform
import statistics
import sys
import tracemalloc
from dataclasses import dataclass
from time import perf_counter

from passpattern.contextual import default_contextual_detectors

_REPETITIONS = 5


@dataclass(frozen=True, slots=True)
class _Prepared:
    processed_text: str


def _measure(detector, prepared: _Prepared) -> tuple[float, int]:
    timings: list[float] = []
    count = 0
    for _ in range(_REPETITIONS):
        started = perf_counter()
        count = sum(1 for _ in detector.detect(prepared))
        timings.append((perf_counter() - started) * 1000)
    return statistics.median(timings), count


def _measure_suite(detectors, prepared: _Prepared) -> tuple[float, int]:
    timings: list[float] = []
    count = 0
    for _ in range(_REPETITIONS):
        started = perf_counter()
        count = sum(1 for detector in detectors for _ in detector.detect(prepared))
        timings.append((perf_counter() - started) * 1000)
    return statistics.median(timings), count


def _peak_suite_bytes(detectors, prepared: _Prepared) -> int:
    peaks: list[int] = []
    tracemalloc.start()
    try:
        for _ in range(_REPETITIONS):
            tracemalloc.reset_peak()
            baseline, _ = tracemalloc.get_traced_memory()
            for detector in detectors:
                sum(1 for _ in detector.detect(prepared))
            _, peak = tracemalloc.get_traced_memory()
            peaks.append(max(0, peak - baseline))
    finally:
        tracemalloc.stop()
    return max(peaks, default=0)


def main() -> None:
    print(f"OS: {platform.platform()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"CPU: {platform.processor() or platform.machine()}")
    print(f"Median of {_REPETITIONS} execution runs; inputs are synthetic.")

    cases = {
        "short": "abc",
        "typical": "Summer2026!qwerty",
        "maximum_length": ("Ab9!xy" * 171)[:1024],
        "date_heavy": ("2024-02-29/" * 93)[:1024],
        "year_heavy": ("Summer2026!" * 93)[:1024],
        "keyboard_heavy": ("qwerty-1qaz-" * 86)[:1024],
        "random_looking": ("gK7!mQ2@vZ5#pL8$xR3%" * 52)[:1024],
        "unicode_heavy": ("🙂漢字e\u0301" * 205)[:1024],
        "adversarial_digits": "1" * 1024,
    }
    detectors = default_contextual_detectors()
    detector_names = ("calendar_date", "year", "keyboard_walk")

    for case_name, text in cases.items():
        prepared = _Prepared(text)
        print(f"{case_name} (length={len(text)}):")
        for detector, name in zip(detectors, detector_names, strict=True):
            elapsed_ms, match_count = _measure(detector, prepared)
            print(f"  {name}: {elapsed_ms:.4f}ms, {match_count} matches")
        elapsed_ms, match_count = _measure_suite(detectors, prepared)
        peak_bytes = _peak_suite_bytes(detectors, prepared)
        print(
            f"  total: {elapsed_ms:.4f}ms, {match_count} matches, "
            f"{peak_bytes / 1024:.2f}KiB peak traced"
        )


if __name__ == "__main__":
    main()
