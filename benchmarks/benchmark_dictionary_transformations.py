"""Benchmark reversed and leetspeak dictionary matching on synthetic data."""

from __future__ import annotations

import platform
import statistics
import sys
import tracemalloc
from dataclasses import dataclass
from time import perf_counter

from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    LeetspeakDetector,
    ReversedWordDetector,
)


@dataclass(frozen=True, slots=True)
class _Prepared:
    processed_text: str


_REPETITIONS = 5


def _encoded_word(value: int) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    characters: list[str] = []
    for _ in range(8):
        value, remainder = divmod(value, len(alphabet))
        characters.append(alphabet[remainder])
    return "entry" + "".join(reversed(characters))


def _construct(
    supplied_entries: list[DictionaryEntry],
) -> tuple[DictionaryLexicon, ReversedWordDetector, LeetspeakDetector]:
    lexicon = DictionaryLexicon(
        supplied_entries,
        min_word_length=4,
        max_word_length=128,
        max_entries=25_000,
        max_total_codepoints=500_000,
    )
    return lexicon, ReversedWordDetector(lexicon), LeetspeakDetector(lexicon)


def _median_build_and_peak(
    supplied_entries: list[DictionaryEntry],
) -> tuple[DictionaryLexicon, ReversedWordDetector, LeetspeakDetector, float, float, float, int]:
    lexicon_timings: list[float] = []
    reversed_timings: list[float] = []
    leetspeak_timings: list[float] = []

    for _ in range(_REPETITIONS):
        started = perf_counter()
        lexicon = DictionaryLexicon(
            supplied_entries,
            min_word_length=4,
            max_word_length=128,
            max_entries=25_000,
            max_total_codepoints=500_000,
        )
        lexicon_timings.append((perf_counter() - started) * 1000)

        started = perf_counter()
        reversed_detector = ReversedWordDetector(lexicon)
        reversed_timings.append((perf_counter() - started) * 1000)

        started = perf_counter()
        leetspeak_detector = LeetspeakDetector(lexicon)
        leetspeak_timings.append((perf_counter() - started) * 1000)

    del lexicon, reversed_detector, leetspeak_detector
    peak_increments: list[int] = []
    tracemalloc.start()
    for _ in range(_REPETITIONS):
        tracemalloc.reset_peak()
        baseline, _ = tracemalloc.get_traced_memory()
        lexicon, reversed_detector, leetspeak_detector = _construct(supplied_entries)
        _, peak = tracemalloc.get_traced_memory()
        peak_increments.append(max(0, peak - baseline))
        del lexicon, reversed_detector, leetspeak_detector
    tracemalloc.stop()

    lexicon, reversed_detector, leetspeak_detector = _construct(supplied_entries)
    return (
        lexicon,
        reversed_detector,
        leetspeak_detector,
        statistics.median(lexicon_timings),
        statistics.median(reversed_timings),
        statistics.median(leetspeak_timings),
        max(peak_increments),
    )


def _measure_matches(detector, text: str) -> tuple[float, int]:
    timings: list[float] = []
    match_count = 0
    prepared = _Prepared(text)
    for _ in range(_REPETITIONS):
        started = perf_counter()
        match_count = sum(1 for _ in detector.detect(prepared))
        timings.append((perf_counter() - started) * 1000)
    return statistics.median(timings), match_count


def _measure_peak_bytes(detector, text: str) -> int:
    peaks: list[int] = []
    prepared = _Prepared(text)
    tracemalloc.start()
    try:
        for _ in range(_REPETITIONS):
            tracemalloc.reset_peak()
            baseline, _ = tracemalloc.get_traced_memory()
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
    print(f"Median of {_REPETITIONS} runs; synthetic data only.")

    for size in (100, 5_000, 20_000):
        entries = [DictionaryEntry(_encoded_word(index), index + 1) for index in range(size)]
        entries.extend(
            (
                DictionaryEntry("test", size + 1),
                DictionaryEntry("i" * 32, size + 2),
                DictionaryEntry("l" * 32, size + 3),
            )
        )
        (
            lexicon,
            reversed_detector,
            leetspeak_detector,
            lexicon_ms,
            reversed_build_ms,
            leetspeak_build_ms,
            peak_bytes,
        ) = _median_build_and_peak(entries)
        leetspeak_one = LeetspeakDetector(lexicon, max_substitutions=1)
        leetspeak_six = LeetspeakDetector(lexicon, max_substitutions=6)

        print(
            f"entries={len(lexicon.entries)} "
            f"lexicon_build={lexicon_ms:.2f}ms "
            f"reversed_build={reversed_build_ms:.2f}ms "
            f"leetspeak_build={leetspeak_build_ms:.2f}ms "
            f"max_compile_peak_increment={peak_bytes / (1024 * 1024):.2f}MiB "
            "max_substitutions=3"
        )

        base_word = _encoded_word(size // 2)
        leetspeak_word = base_word.replace("e", "3", 1)
        reversed_word = base_word[::-1]
        many_reversed = "~".join((reversed_word,) * 65)
        many_leetspeak = "~".join((leetspeak_word,) * 65)
        unicode_heavy = ("🙂漢字e\u0301" * 256)[:1024]
        cases = {
            "short": ("tset", "t3st"),
            "typical": (f"prefix-{reversed_word}-2026", f"prefix-{leetspeak_word}-123"),
            "maximum_no_match": ("~" * 1024, "~" * 1024),
            "highly_ambiguous": ("1" * 1024, "1" * 1024),
            "many_matches": (many_reversed[:1024], many_leetspeak[:1024]),
            "unicode_heavy": (unicode_heavy, unicode_heavy),
        }
        for case_name, (reversed_text, leetspeak_text) in cases.items():
            for detector_name, detector, text in (
                ("reversed", reversed_detector, reversed_text),
                ("leetspeak", leetspeak_detector, leetspeak_text),
            ):
                elapsed_ms, match_count = _measure_matches(detector, text)
                peak_match_bytes = _measure_peak_bytes(detector, text)
                print(
                    f"  {case_name}/{detector_name}: {elapsed_ms:.3f}ms, "
                    f"{match_count} matches, "
                    f"{peak_match_bytes / 1024:.2f}KiB peak traced"
                )

        ambiguous_input = "1" * 1024
        for limit, detector in ((1, leetspeak_one), (3, leetspeak_detector), (6, leetspeak_six)):
            elapsed_ms, match_count = _measure_matches(detector, ambiguous_input)
            print(
                f"  ambiguous_max_substitutions_{limit}: {elapsed_ms:.3f}ms, {match_count} matches"
            )


if __name__ == "__main__":
    main()
