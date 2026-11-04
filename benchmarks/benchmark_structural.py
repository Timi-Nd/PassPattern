"""Time structural detector execution on deterministic synthetic inputs."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from passpattern.detector import Detector
from passpattern.structural import default_structural_detectors


@dataclass(frozen=True, slots=True)
class Prepared:
    processed_text: str


def _count_matches(detector: Detector, text: str) -> int:
    return sum(1 for _ in detector.detect(Prepared(text)))  # type: ignore[arg-type]


def main() -> None:
    cases = {
        "short-12": "abc123abc123",
        "typical-24": "Aa1!bc123xyzzxyzz7890!!",
        "long-repeated-1024": "ab" * 512,
        "long-unique-1024": "".join(chr(0x1000 + index) for index in range(1024)),
        "unicode-heavy-1024": "\U0001f642\u00e9\u6f22\u5b57" * 256,
    }

    for name, text in cases.items():
        print(f"{name} ({len(text)} code points)")
        for detector in default_structural_detectors():
            started = perf_counter()
            match_count = _count_matches(detector, text)
            elapsed_ms = (perf_counter() - started) * 1000
            print(f"  {detector.detector_id}: {elapsed_ms:.3f} ms, {match_count} matches")


if __name__ == "__main__":
    main()
