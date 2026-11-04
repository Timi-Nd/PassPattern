# Development

## Repository layout

- `src/passpattern/`: engine, immutable results, native adapter, and detector modules.
- `tests/`: unit, integration, native-integration, and shared-vector tests.
- `tests/vectors/`: language-neutral expected results shared with the Rust effort.
- `benchmarks/`: deterministic synthetic-data benchmarks; not CI performance gates.
- `scripts/`: development utilities such as `analyze_password.py`.
- `docs/`: user, API, security, and development documentation.
- `.github/workflows/ci.yml`: tests, ruff, and mypy on Windows and Linux with the
  native wheel installed from public PyPI.

## Local setup and checks

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -v
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

On Linux/macOS, substitute `python3` for `py -3.14` and use `. .venv/bin/activate`.
The `dev` extra installs the compatible native wheel from public PyPI using a
binary-only constraint, so the complete suite exercises the native pipeline without
private credentials or a Rust build.

## Adding a detector

Future detectors should implement the `Detector` protocol with a stable, unique
lowercase ASCII identifier and a deterministic `detect(prepared_password)` method.
Operate on the supplied native `processed_text`; return `PatternMatch` objects with
half-open code-point spans and typed numeric/boolean evidence. Do not put password
text, matched words, or arbitrary text in evidence, logs, or exceptions.

If a detector requires normalized input, implement the optional
`NormalizationAwareDetector` contract and reject incompatible engine configuration.
Bound work and memory in proportion to input and dictionary size, and surface exceeded
budgets with an explicit content-free error. Preserve valid overlaps and let the engine
provide final ordering and match-cap enforcement. Add tests for limits, Unicode spans,
overlap behavior, invalid values, and privacy.

## Compatibility and contribution

Keep the public Python API typed and compatible with the declared Python floor of
3.10. Preserve deterministic output and do not require Rust source or private
credentials. CI installs only the published native wheel and must not require private
artifacts. Shared expected-result fixtures and the Rust parity workflow are
specified in [Python/Rust parity](rust-parity.md).
