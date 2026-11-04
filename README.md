# PassPattern

PassPattern is a Python reference library for finding recognizable patterns in text
used as a password. It returns explainable pattern matches so you can study or build
pattern-based systems. It does **not** calculate password strength, entropy, or
guessability.

## Patterns you can explore

- **Structural:** repeated characters (`aaaa`), repeated substrings (`abcabc`),
  letter sequences (`abcd`), and numeric sequences such as `1234`, `2468`, and
  `235711`.
- **Contextual:** selected calendar dates and years, plus keyboard walks such as
  `qwerty`.
- **Dictionary-based:** supplied words, reversed words, bounded substitutions, and
  word-plus-suffix forms. You provide the lexicon; none is bundled.

The numeric detector recognizes arithmetic progressions and consecutive primes. You
can separately opt into experimental geometric and Fibonacci-like sequences.

## How detection works

You choose which detectors to run. PassPattern prepares the input once using the
separately installed `passtext-native` component, then runs the selected detectors
over the processed text. Results are immutable metadata with zero-based, half-open
Unicode code-point spans. Matches are sorted deterministically, and valid overlaps are
preserved.

## Install and try it

From a repository checkout, install the development dependencies:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

For Linux or macOS shell syntax, see [Installation](docs/installation.md). To analyze
synthetic input interactively without echoing it, run:

```powershell
python .\scripts\analyze_password.py
```

You can also try the numeric detector directly:

```python
from passpattern import PassPatternEngine
from passpattern.structural import NumericSequenceDetector

result = PassPatternEngine([NumericSequenceDetector()]).analyze("2468")
for match in result.matches:
    values = [term.value for term in match.terms]
    print(f"{match.pattern_type}: {values}; step={match.parameter_numerator}")
```

Output:

```text
arithmetic_progression: [2, 4, 6, 8]; step=2
```

Here, `step=2` is the difference between adjacent terms. A match describes a pattern,
not whether the input is strong or weak. Use synthetic examples in documentation,
tests, and logs.

## What to know before using it

- Detectors are opt-in. The engine does not enable any detector unless you register
  it.
- The numeric detector uses bounded interpretation and raises an explicit limit error
  when its configured work, candidate, or run limits are exceeded.
- Built-in sequence, date, year, and keyboard rules are ASCII-focused. Spans refer to
  processed text, which may have changed if you enable NFC normalization.
- Pattern matches and numeric term values can reveal information about the input.
  Avoid logging real passwords or analysis results.
- The Python implementation is available here; a Rust engine is not included in this
  repository.

## Explore and contribute

- [Quickstart](docs/quickstart.md) shows the main ways to run detectors.
- [Detector guide](docs/detectors.md) explains rules, limits, and false positives.
- [API reference](docs/api.md) documents constructors and result types.
- [Architecture](docs/architecture.md) explains the analysis pipeline.
- [Unicode and spans](docs/unicode.md) explains offsets and normalization.
- [Security and privacy](docs/security.md) describes data-handling limits.
- [Python/Rust parity](docs/rust-parity.md) describes the shared behavior vectors.
- [Benchmarks](docs/benchmarks.md) shows how to measure the synthetic workloads.
- [Development guide](docs/development.md) covers tests and contributions.

Run the test suite with `python -m pytest`. To contribute, start with the
[development guide](docs/development.md): changes to detector behavior should include
focused tests and, where appropriate, reviewed shared vectors.
