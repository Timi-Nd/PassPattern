# Development guide

This guide helps you set up the repository, run its checks, and make a focused
contribution. The Python implementation is the current executable reference.

## Repository map

- `src/passpattern/`: engine, models, native adapter, and detector implementations.
- `tests/`: unit, integration, and native-integration tests.
- `tests/vectors/`: language-neutral expected results for parity checks.
- `benchmarks/`: deterministic synthetic workloads; not CI performance gates.
- `scripts/`: development tools, including the interactive analyzer.
- `docs/`: user guides, API details, and implementation references.

## Set up and check your changes

From the repository root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

On Linux or macOS, use `python3 -m venv .venv` and
`. .venv/bin/activate`. The development extra installs the compatible public native
wheel and the test, lint, formatting, and type-checking tools. A Rust compiler or
private repository is not required.

## Add or change a detector

Implement the `Detector` protocol with a stable, unique lowercase ASCII ID. Inspect
the prepared text passed to `detect()` and return `PatternMatch` values with
half-open code-point spans. Keep results deterministic and do not put matched text,
passwords, or arbitrary strings into evidence, logs, or errors.

If the detector needs normalized input, implement the optional
`NormalizationAwareDetector` contract. Bound work and memory, then surface an explicit
content-free error if a limit is reached. Preserve valid overlaps unless the rule
specifically excludes them.

For a numeric-family change, define the recurrence or relationship and minimum term
count first. Reuse canonical ASCII term interpretation, exact integer arithmetic, the
work limits, and `NumericPatternMatch` metadata. State how leading zeros and ambiguous
segmentations are handled. See [numeric sequence rules](detectors.md#numeric-sequences).

## Test and document behavior

Add focused tests for positive and negative examples, boundaries, resource limits,
overlaps, Unicode positions, and deterministic ordering. Update a shared vector when a
change affects language-neutral behavior; keep its expected result hand-reviewed.
When changing public behavior, update the corresponding reader guide and API page.

Run benchmarks separately from correctness tests. The synthetic timing scripts are
not performance gates; report the tested inputs and environment rather than promising
production performance.

## Python compatibility

The project supports Python 3.10 and newer. Keep public types explicit, avoid
unnecessary dependencies, and run the checks above before sharing a change. The
current shared-vector format and its intended cross-language use are described in
[Python/Rust parity](rust-parity.md).
