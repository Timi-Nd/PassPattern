# Benchmarks

The benchmark scripts use deterministic synthetic inputs and are development tools,
not security measures, CI thresholds, or production performance guarantees. They
print timing and match counts, not password text. Run from the repository root:

```powershell
python .\benchmarks\benchmark_structural.py
python .\benchmarks\benchmark_dictionary.py
python .\benchmarks\benchmark_dictionary_transformations.py
python .\benchmarks\benchmark_contextual.py
```

The structural benchmark reports per-detector elapsed time and match counts over
short, typical, repetitive, unique, and Unicode-heavy synthetic inputs. It has no
absolute-time assertions and consumes detector iterators incrementally. The
repository's historical record did not include a structural timing-results table.

## Methodology and environment

The recorded measurements below were taken locally on Windows 11 / CPython 3.14.6,
Intel64 Family 6 Model 170 CPU. The contextual run also recorded Python UCD 16.0.0
and native Rust normalization version `(16, 0, 0)`. Treat these as historical
measurements on that machine and environment; no current CI result or future hardware
is implied.

Dictionary and transformation timings are medians over five runs. Lexicon/detector
builds and scan time are measured separately. Peak incremental allocations use
`tracemalloc` during compilation or detector work and exclude already-created input
entries. The contextual benchmark records per-detector and combined medians over five
runs; combined time is measured independently and need not equal the sum of medians.
Large-output timings include result construction.

## Dictionary transformations

Synthetic entry counts were about 100, 5,000, and 20,000, with 1,024-code-point
no-match/ambiguous inputs and a many-match case. The compilation table covers
lexicon, reversed automaton, and leetspeak automaton construction.

| Entries | Lexicon build | Reversed build | Leetspeak build | Peak compile allocation |
| ---: | ---: | ---: | ---: | ---: |
| 103 | 0.17 ms | 3.16 ms | 0.59 ms | 0.75 MiB |
| 5,003 | 11.89 ms | 260.57 ms | 36.32 ms | 35.67 MiB |
| 20,003 | 31.33 ms | 1,033.15 ms | 102.56 ms | 140.22 MiB |

Median scan time in milliseconds (reversed / leetspeak):

| Entries | Short | Typical | 1,024-char no-match | 1,024-char ambiguous | Many matches (65 each) | Unicode-heavy |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 103 | 0.013 / 0.022 | 0.017 / 0.053 | 0.160 / 0.698 | 0.158 / 7.492 | 0.408 / 2.434 | 0.339 / 1.381 |
| 5,003 | 0.005 / 0.011 | 0.009 / 0.033 | 0.159 / 0.713 | 0.146 / 4.900 | 0.389 / 1.727 | 0.203 / 0.862 |
| 20,003 | 0.005 / 0.011 | 0.010 / 0.036 | 0.161 / 0.710 | 0.158 / 5.343 | 0.382 / 1.428 | 0.202 / 0.861 |

At 20,003 entries, the 1,024-character ambiguous input took 2.252 ms with one
substitution allowed, 4.988 ms with three, and 8.376 ms with six. It produced no
matches in each configuration because the input exceeded those per-match bounds.
Matching allocation peaks remained at or below 3.18 KiB in the recorded cases.

## Dictionary exact matching

This benchmark used deterministic lexicons with increasing sizes and many-prefix
synthetic entries. It reports lexicon/matcher build medians, compilation allocation,
and scan medians. The 256-character many-prefix input intentionally produced 14,368
matches, so its scan time includes match object construction.

| Synthetic entries | Lexicon build | Matcher build | Max compile allocation | 1,024-char no-match scan | 256-char many-prefix scan |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 164 (about 100 plus prefixes) | 1.26 ms | 4.49 ms | 0.10 MiB | 0.46 ms | 96.07 ms |
| 5,064 (about 5,000 plus prefixes) | 35.83 ms | 128.68 ms | 2.95 MiB | 0.34 ms | 92.20 ms |
| 20,064 (about 20,000 plus prefixes) | 93.75 ms | 446.98 ms | 11.70 MiB | 0.26 ms | 78.90 ms |

## Contextual detection

The contextual benchmark includes short, typical, maximum-length, date-heavy,
year-heavy, keyboard-heavy, random-looking, Unicode-heavy, and adversarial-digit
synthetic cases. Allocation is peak incremental traced memory for one combined
detector run.

| Synthetic case | Code points | Calendar | Year | Keyboard | Combined | Matches | Peak traced |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| short | 3 | 0.0016 ms | 0.0011 ms | 0.0039 ms | 0.0051 ms | 0 | 1.07 KiB |
| typical | 17 | 0.0062 ms | 0.0134 ms | 0.0330 ms | 0.0494 ms | 2 | 2.77 KiB |
| maximum length | 1,024 | 0.3720 ms | 0.2143 ms | 0.6782 ms | 1.2664 ms | 0 | 17.29 KiB |
| date-heavy | 1,023 | 1.6203 ms | 0.7432 ms | 0.5780 ms | 2.9198 ms | 186 | 17.28 KiB |
| year-heavy | 1,023 | 0.3648 ms | 0.6791 ms | 1.0945 ms | 2.3597 ms | 93 | 17.25 KiB |
| keyboard-heavy | 1,024 | 0.3271 ms | 0.1992 ms | 2.8471 ms | 3.5466 ms | 171 | 17.26 KiB |
| random-looking | 1,024 | 0.6695 ms | 0.2471 ms | 1.0125 ms | 1.7426 ms | 0 | 17.26 KiB |
| Unicode-heavy | 1,024 | 0.1710 ms | 0.2117 ms | 0.4867 ms | 0.8759 ms | 0 | 17.26 KiB |
| adversarial digits | 1,024 | 0.2801 ms | 0.1686 ms | 0.6853 ms | 1.1512 ms | 0 | 17.26 KiB |

## Interpretation and limitations

Compilation cost and memory grow with dictionary size; callers should construct
lexicons and detectors during application setup rather than once per password. Highly
ambiguous leetspeak inputs can consume more bounded work. A many-match run can be
dominated by output construction. Timing variance, Python version, operating system,
CPU, memory allocator, and data shape affect results. No extrapolation to production
traffic or user passwords is justified.
