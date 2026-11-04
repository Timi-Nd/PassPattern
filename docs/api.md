# API reference

This page summarizes the public Python interfaces. For usage examples, start with the
[quickstart](quickstart.md); for detector rules and limits, see the
[detector guide](detectors.md).

## Engine

```python
PassPatternEngine(
    detectors: Iterable[Detector] = (),
    config: EngineConfig | None = None,
)
PassPatternEngine.analyze(password: str) -> AnalysisResult
```

The engine prepares the input once, calls each registered detector, validates the
results, enforces the match limit, and returns deterministic ordering. With no
registered detectors it returns an empty result.

## Engine configuration

```python
EngineConfig(
    max_codepoints: int = 1024,
    max_utf8_bytes: int = 4096,
    normalization: Literal["none", "nfc"] = "none",
    max_matches: int = 1000,
    detector_ids: frozenset[str] | None = None,
)
```

`detector_ids` optionally selects a subset of registered detector IDs. Unknown IDs
are rejected. Detector IDs must be unique lowercase ASCII identifiers. A
normalization-aware detector must use the same `"none"` or `"nfc"` mode as the engine.

## Detectors and factories

`Detector` is a protocol with a `detector_id` property and
`detect(prepared_password: PreparedPassword) -> Iterable[PatternMatch]` method.
`NormalizationAwareDetector` is an optional runtime-checkable protocol for detectors
that require a specific normalization mode.

Built-in detectors are available from `passpattern.structural`,
`passpattern.contextual`, and `passpattern.dictionary`. The structural and contextual
factory functions return fresh instances. No detector family is registered
automatically.

`NumericSequenceDetector` options and defaults:

```python
NumericSequenceDetector(
    min_sequence_length=3,
    max_digit_run=32,
    max_term_digits=6,
    max_term_value=999_999,
    max_terms=8,
    max_candidates=8192,
    max_work=100_000,
    experimental_families=frozenset(),
)
```

The geometric and Fibonacci-like families are off by default. All range limits are
described in the [detector guide](detectors.md#numeric-sequences).

## Result types

- `AnalysisResult(matches: tuple[PatternMatch, ...] = ())` is an immutable tuple of
  matches. It does not store the submitted password string.
- `PatternMatch(detector_id, category, pattern_type, start_index, end_index,
  evidence=())` describes a nonempty half-open span in processed text.
- `Evidence(key: EvidenceKey, value: int | float | bool)` stores finite numeric or
  boolean metadata. An evidence key can appear only once per match.
- `EvidenceKey` includes `COUNT`, `CASE_EXACT`, `DATE_ORDER`, `DIRECTION`, `LENGTH`,
  `OFFSET`, `RANK`, `AMBIGUOUS`, `SEPARATOR_COUNT`, and `SUBSTITUTION_COUNT`.
- `NumericTerm(value, start_index, end_index)` describes a non-negative integer and
  its half-open span.
- `NumericPatternMatch` extends `PatternMatch` with `terms`,
  `parameter_numerator`, `parameter_denominator`, and `ambiguous`.

All span indices count Unicode code points in the processed text. Numeric term values
are derived from the input, so treat them as sensitive. See
[Unicode and positions](unicode.md) and [Security and privacy](security.md).

For arithmetic matches, the relationship parameters encode the common difference over
1. For geometric matches, they encode the reduced ratio. Prime and Fibonacci-like
matches have no relationship parameter.

## Errors

`analyze()` may raise:

- `NativeExtensionUnavailableError` if the required native dependency is unavailable
  or incompatible.
- `InvalidPasswordTypeError`, `InvalidUnicodeError`, or `InputTooLargeError` when
  input validation fails.
- `PasswordProcessingError` for a sanitized native-processing failure.
- `DetectorExecutionError` if a detector fails.
- `InvalidDetectorResultError` if a detector returns an invalid match.
- `TooManyMatchesError` if the configured result cap is exceeded.
- `DictionarySearchLimitError` or `NumericSequenceLimitError` if a bounded detector
  reaches its configured work limits.
- `ValueError` for invalid engine or detector configuration.

Built-in errors do not include the submitted password. Custom detectors are
application code and can define their own errors and data handling.

## Dictionary types

- `DictionaryEntry(word, rank, source_id=None)` represents an application-supplied
  entry. Rank must be a positive integer; an optional source ID must be a short ASCII
  identifier.
- `DictionaryLexicon(entries, min_word_length=1, max_word_length=128,
  max_entries=100_000, max_total_codepoints=2_000_000, normalization="none")`
  validates and bounds its entries. Exact duplicate spellings are resolved
  by lowest rank and then stable source ID; differently cased entries remain
  distinct. The lexicon records the Python Unicode database version.

PassPattern provides no bundled dictionary. See [dictionary examples](quickstart.md#add-a-dictionary-detector).
