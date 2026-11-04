# PassPattern

Python research and reference implementation for password-pattern recognition,
developed to validate a future Rust engine.

PassPattern finds structural, dictionary, and contextual patterns in a password and
returns explainable match metadata. It is not a password-strength estimator, entropy
calculator, or guessability model, and it is not published as a package.

## What it implements

- **Structural:** repeated characters, repeated substrings, ascending/descending ASCII
  digit and letter sequences.
- **Dictionary:** exact and case-insensitive words, reversed words, and bounded
  leetspeak substitutions, using a ranked lexicon you supply.
- **Contextual:** Gregorian calendar dates, four-digit years, and walks on a simplified
  US QWERTY layout.
- A deterministic engine: matches are validated, sorted, immutable, and expressed as
  half-open Unicode code-point offsets into the processed text. Overlaps are kept.

## What it does not implement

- Strength or guess-count estimation, or password policy decisions.
- A bundled password dictionary; detectors are registered explicitly and none is on by
  default.
- Non-ASCII sequence, contextual, or case-folding rules (see [Unicode](docs/unicode.md)).
- The Rust engine. That is developed separately and is not part of this repository.

## Relationship to PassText Native

Input validation, size limits, and optional NFC normalization are done by the public
[`passtext-native`](https://pypi.org/project/passtext-native/) 0.1.x binary wheel. The
adapter is [`src/passpattern/native.py`](src/passpattern/native.py). Installing it needs
no Rust toolchain and no private access. Wheels exist for CPython 3.10+ on Windows
x86-64 and Linux x86-64 (manylinux 2.28); other platforms fail at install time or
raise `NativeExtensionUnavailableError` at analysis time.

## Role as the Rust reference

The Python detectors define expected behavior. Language-neutral vectors in
[`tests/vectors/passpattern-v1.json`](tests/vectors/passpattern-v1.json) are checked by
[`tests/test_shared_vectors.py`](tests/test_shared_vectors.py), and a Rust implementation
is expected to pass the same file. See [Python/Rust parity](docs/rust-parity.md).

## Install the research environment

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

On Linux use `python3 -m venv .venv` and `. .venv/bin/activate`. Requires CPython 3.10
or newer; CI runs 3.10 and 3.14 on Windows and Linux. The `dev` extra installs
`passtext-native>=0.1.0,<0.2.0` from PyPI along with pytest, ruff, and mypy.

## Run an example

```python
from passpattern import PassPatternEngine
from passpattern.structural import default_structural_detectors

engine = PassPatternEngine(default_structural_detectors())
result = engine.analyze("aaa123abc")

for match in result.matches:
    print(match.detector_id, match.pattern_type, match.start_index, match.end_index)
```

To analyze a password interactively without echo, run
`python scripts/analyze_password.py`. Use synthetic input in examples and logs. More in
the [quickstart](docs/quickstart.md).

## Run the tests

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

## Benchmark detectors

Benchmarks live in [`benchmarks/`](benchmarks) and are not part of the test suite:

```powershell
python benchmarks/benchmark_structural.py
```

See [benchmarks](docs/benchmarks.md) for the other scripts and methodology.

## Contribute a new algorithm

Add a detector under `src/passpattern/`, register it through the engine, add unit tests,
and add shared vectors if the behavior should be matched by Rust. Preserve
determinism and code-point offsets. Details are in [development](docs/development.md).

## Documentation

[Installation](docs/installation.md) ·
[Quickstart](docs/quickstart.md) ·
[API](docs/api.md) ·
[Detectors](docs/detectors.md) ·
[Architecture](docs/architecture.md) ·
[Unicode](docs/unicode.md) ·
[Security and privacy](docs/security.md) ·
[Development](docs/development.md) ·
[Python/Rust parity](docs/rust-parity.md) ·
[Benchmarks](docs/benchmarks.md) ·
[Security policy](SECURITY.md)
