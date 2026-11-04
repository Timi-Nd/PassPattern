"""Benchmark lexicon compilation and dictionary matching on synthetic data."""

from __future__ import annotations

import platform
import statistics
import sys
import tracemalloc
from time import perf_counter

from passpattern.dictionary import DictionaryEntry, DictionaryLexicon, DictionaryMatcher

_REPETITIONS = 5


def _encoded_word(value: int) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    characters: list[str] = []
    for _ in range(8):
        value, remainder = divmod(value, len(alphabet))
        characters.append(alphabet[remainder])
    return "entry" + "".join(reversed(characters))


def _measure_matches(matcher: DictionaryMatcher, text: str) -> tuple[float, int]:
    timings: list[float] = []
    count = 0
    for _ in range(_REPETITIONS):
        started = perf_counter()
        count = sum(1 for _ in matcher.find_matches(text))
        timings.append((perf_counter() - started) * 1000)
    return statistics.median(timings), count


def main() -> None:
    print(f"OS: {platform.platform()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"CPU: {platform.processor() or platform.machine()}")
    print(f"Median of {_REPETITIONS} matching runs; synthetic data only.")
    prefix_entries = [DictionaryEntry("a" * length, length) for length in range(1, 65)]
    sizes = (100, 5_000, 20_000)

    for size in sizes:
        supplied_entries = [
            DictionaryEntry(_encoded_word(index), index + 1) for index in range(size)
        ]
        supplied_entries.extend(prefix_entries)

        lexicon_timings: list[float] = []
        matcher_timings: list[float] = []
        peak_allocations: list[int] = []
        tracemalloc.start()
        for _ in range(_REPETITIONS):
            tracemalloc.reset_peak()
            baseline, _ = tracemalloc.get_traced_memory()
            started = perf_counter()
            lexicon = DictionaryLexicon(
                supplied_entries,
                min_word_length=1,
                max_word_length=128,
                max_entries=25_000,
                max_total_codepoints=500_000,
            )
            lexicon_timings.append((perf_counter() - started) * 1000)
            _, peak = tracemalloc.get_traced_memory()
            peak_allocations.append(max(0, peak - baseline))

            tracemalloc.reset_peak()
            baseline, _ = tracemalloc.get_traced_memory()
            started = perf_counter()
            matcher = DictionaryMatcher(lexicon)
            matcher_timings.append((perf_counter() - started) * 1000)
            _, peak = tracemalloc.get_traced_memory()
            peak_allocations.append(max(0, peak - baseline))
        tracemalloc.stop()
        lexicon_ms = statistics.median(lexicon_timings)
        matcher_ms = statistics.median(matcher_timings)
        peak_bytes = max(peak_allocations)

        print(
            f"entries={len(lexicon.entries)} "
            f"lexicon_build={lexicon_ms:.2f}ms "
            f"matcher_build={matcher_ms:.2f}ms "
            f"max_compile_peak_increment={peak_bytes / (1024 * 1024):.2f}MiB"
        )

        base_word = _encoded_word(size // 2)
        cases = {
            "short": base_word[:8],
            "typical": f"{base_word}123{_encoded_word(size // 3)}",
            "maximum_no_match": "~" * 1024,
            "many_overlapping_prefix_matches": "a" * 256,
            "unicode_heavy": "\U0001f642\u00e9\u6f22\u5b57" * 256,
        }
        for case_name, synthetic_text in cases.items():
            elapsed_ms, match_count = _measure_matches(matcher, synthetic_text)
            print(f"  {case_name}: {elapsed_ms:.3f}ms, {match_count} matches")


if __name__ == "__main__":
    main()
