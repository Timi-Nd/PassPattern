# Benchmarks

Benchmarks help you measure the current Python implementation on repeatable synthetic
inputs. They are not security tests, CI thresholds, or guarantees about production
traffic. Run them from the repository root:

```powershell
python .\benchmarks\benchmark_structural.py
python .\benchmarks\benchmark_numeric_sequences.py
python .\benchmarks\benchmark_dictionary.py
python .\benchmarks\benchmark_dictionary_transformations.py
python .\benchmarks\benchmark_contextual.py
```

The scripts report elapsed time and match counts; they do not print their synthetic
input values. The structural and numeric scripts compare detector behavior; the
dictionary scripts separate lexicon or matcher construction from scans; the
contextual script times date, year, and keyboard detectors.

## Numeric detector comparison

`benchmark_numeric_sequences.py` compares the previous linear `+1`/`-1` scan with
the generalized numeric detector. They do different amounts of work: the generalized
detector also considers arithmetic and prime interpretations. In one local run on
Windows and CPython 3.14.6, the median times over 100 warmed repetitions were:

| Synthetic input | Previous scan | Generalized detector |
|---|---:|---:|
| Short legacy sequence | 0.0045 ms | 0.0467 ms |
| Typical 23-code-point string | 0.0114 ms | 0.1104 ms |
| Arithmetic sequence | 0.0050 ms | 0.1994 ms |
| Consecutive-prime sequence | 0.0016 ms | 0.1789 ms |
| 32-digit run | 0.0070 ms | 2.0487 ms |

These are illustrative local measurements, not a controlled comparison of equivalent
workloads or a performance claim. The longer generalized times reflect the extra
interpretation work. Re-run the script on your own environment before drawing
conclusions.

## Other recorded measurements

The tables below preserve historical synthetic benchmark snapshots. They were
recorded on Windows 11 / CPython 3.14.6; hardware, runtime, operating system, and
input shape affect the results. Dictionary and transformation scan times are medians
over five runs. Construction and scan costs were measured separately.

Dictionary transformation build measurements:

| Entries | Lexicon build | Reversed build | Leetspeak build | Peak compile allocation |
|---:|---:|---:|---:|---:|
| 103 | 0.17 ms | 3.16 ms | 0.59 ms | 0.75 MiB |
| 5,003 | 11.89 ms | 260.57 ms | 36.32 ms | 35.67 MiB |
| 20,003 | 31.33 ms | 1,033.15 ms | 102.56 ms | 140.22 MiB |

Dictionary transformation scan times (reversed / leetspeak, milliseconds):

| Entries | Short | Typical | 1,024-char no-match | 1,024-char ambiguous | Many matches | Unicode-heavy |
|---:|---:|---:|---:|---:|---:|---:|
| 103 | 0.013 / 0.022 | 0.017 / 0.053 | 0.160 / 0.698 | 0.158 / 7.492 | 0.408 / 2.434 | 0.339 / 1.381 |
| 5,003 | 0.005 / 0.011 | 0.009 / 0.033 | 0.159 / 0.713 | 0.146 / 4.900 | 0.389 / 1.727 | 0.203 / 0.862 |
| 20,003 | 0.005 / 0.011 | 0.010 / 0.036 | 0.161 / 0.710 | 0.158 / 5.343 | 0.382 / 1.428 | 0.202 / 0.861 |

At 20,003 entries, the 1,024-character ambiguous input took 2.252 ms with one
substitution, 4.988 ms with three, and 8.376 ms with six. Matching allocation peaks
were at or below 3.18 KiB in those cases.

Dictionary exact-matching measurements:

| Entries | Lexicon build | Matcher build | Peak compile allocation | 1,024-char no-match scan | 256-char many-prefix scan |
|---:|---:|---:|---:|---:|---:|
| 164 | 1.26 ms | 4.49 ms | 0.10 MiB | 0.46 ms | 96.07 ms |
| 5,064 | 35.83 ms | 128.68 ms | 2.95 MiB | 0.34 ms | 92.20 ms |
| 20,064 | 93.75 ms | 446.98 ms | 11.70 MiB | 0.26 ms | 78.90 ms |

The many-prefix scan produced 14,368 matches, so its time includes result construction.

Contextual detector measurements (milliseconds):

| Synthetic case | Code points | Calendar | Year | Keyboard | Combined | Matches | Peak traced |
|---|---:|---:|---:|---:|---:|---:|---:|
| Short | 3 | 0.0016 | 0.0011 | 0.0039 | 0.0051 | 0 | 1.07 KiB |
| Typical | 17 | 0.0062 | 0.0134 | 0.0330 | 0.0494 | 2 | 2.77 KiB |
| Maximum length | 1,024 | 0.3720 | 0.2143 | 0.6782 | 1.2664 | 0 | 17.29 KiB |
| Date-heavy | 1,023 | 1.6203 | 0.7432 | 0.5780 | 2.9198 | 186 | 17.28 KiB |
| Year-heavy | 1,023 | 0.3648 | 0.6791 | 1.0945 | 2.3597 | 93 | 17.25 KiB |
| Keyboard-heavy | 1,024 | 0.3271 | 0.1992 | 2.8471 | 3.5466 | 171 | 17.26 KiB |
| Random-looking | 1,024 | 0.6695 | 0.2471 | 1.0125 | 1.7426 | 0 | 17.26 KiB |
| Unicode-heavy | 1,024 | 0.1710 | 0.2117 | 0.4867 | 0.8759 | 0 | 17.26 KiB |
| Adversarial digits | 1,024 | 0.2801 | 0.1686 | 0.6853 | 1.1512 | 0 | 17.26 KiB |

Allocation measurements use `tracemalloc` and exclude pre-created input entries.
Lexicon construction can be expensive, so build lexicons and detectors during
application setup rather than once per input. Timing varies with workload, hardware,
Python version, allocator, and operating system. None of these snapshots predicts
production performance.
