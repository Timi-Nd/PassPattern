# API reference

The public root exports are listed in `passpattern.__all__`. Detector constructors are
available from their respective `passpattern.structural`, `passpattern.dictionary`,
and `passpattern.contextual` modules.

## Engine and configuration

```python
PassPatternEngine(detectors: Iterable[Detector] = (), config: EngineConfig | None = None)
PassPatternEngine.analyze(password: str) -> AnalysisResult
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
EngineConfig(
    max_codepoints: int = 1024,
    max_utf8_bytes: int = 4096,
    normalization: Literal["none", "nfc"] = "none",
    max_matches: int = 1000,
    detector_ids: frozenset[str] | None = None,
)
```

`detector_ids` optionally selects registered IDs; unknown IDs are rejected. The engine
requires unique lowercase ASCII detector identifiers and checks that normalization-
aware detectors match its normalization setting.

`analyze()` prepares once and returns immutable matches. It may raise:

- `NativeExtensionUnavailableError` if `passtext_native` is missing or incompatible.
- `InvalidPasswordTypeError`, `InvalidUnicodeError`, or `InputTooLargeError` for
  rejected input.
- `PasswordProcessingError` for a sanitized native-processing failure.
- `DetectorExecutionError` if a detector fails.
- `InvalidDetectorResultError` for malformed results or spans.
- `TooManyMatchesError` if the configured result cap is exceeded.
- `DictionarySearchLimitError` if a bounded dictionary transformation reaches its
  work or state cap.
- `NumericSequenceLimitError` if numeric sequence interpretation reaches a configured
  run, term-count, candidate, or work cap.
- `ValueError` during engine/configuration validation.

Error messages are intended not to include submitted password text.

## Detector protocols

`Detector` is a protocol with a stable `detector_id` property and
`detect(prepared_password: PreparedPassword) -> Iterable[PatternMatch]`. The native
prepared type is exposed structurally via a protocol with a `processed_text: str`
property. `NormalizationAwareDetector` is an optional runtime-checkable protocol whose
`required_normalization` property must be `"none"` or `"nfc"` and match the engine.

Built-in detectors and the default factories are exported under their group modules.
`default_structural_detectors()` and `default_contextual_detectors()` return fresh
detector instances. No detector group is registered automatically.

## Result types

- `PatternMatch(detector_id, category, pattern_type, start_index, end_index,
  evidence=())`: frozen half-open code-point span into processed text. Identifiers
  must be lowercase ASCII tokens. The span must be nonempty and nonnegative.
- `NumericTerm(value, start_index, end_index)`: a non-negative integer term with a
  half-open code-point span.
- `NumericPatternMatch`: a `PatternMatch` subtype with a tuple of contiguous numeric
  terms, optional exact `parameter_numerator` / `parameter_denominator`, and an
  `ambiguous` flag. Arithmetic parameters are difference/1; geometric parameters are
  the reduced ratio. Consecutive-prime and Fibonacci-like matches have no parameter.
- `Evidence(key: EvidenceKey, value: int | float | bool)`: frozen typed evidence.
  Values must be finite numbers or booleans; keys are unique per match.
- `EvidenceKey`: `COUNT`, `CASE_EXACT`, `DATE_ORDER`, `DIRECTION`, `LENGTH`,
  `OFFSET`, `RANK`, `AMBIGUOUS`, `SEPARATOR_COUNT`, and `SUBSTITUTION_COUNT`.
  Not every key is emitted by current detectors.
- `AnalysisResult(matches: tuple[PatternMatch, ...] = ())`: frozen sequence-like
  container of validated matches. It does not retain the analyzed password.

These are immutable dataclasses (including nested evidence tuples). Numeric ranks,
spans, and pattern metadata can still be sensitive. `NumericPatternMatch.terms`
contains numeric values from the processed password and must be treated as sensitive.

The numeric detector recognizes legacy ±1 digit runs, arithmetic progressions with at
least four terms, and consecutive-prime runs with at least four terms. Geometric
progressions and the recurrence `t[n] = t[n - 1] + t[n - 2]` (six terms minimum,
nondecreasing first pair) are opt-in with `experimental_families`. Numeric terms use
canonical decimal spelling: multi-digit terms cannot start with zero; a one-digit `0`
is valid. Fixed upper limits are 32 digits per run, six digits and 999,999 per term,
16 terms, 32,768 candidates, and 100,000 work units. See
[detector rules](detectors.md#structural) for the precise false-positive and ambiguity
behavior.

## Dictionary types

- `DictionaryCompoundDetector(lexicon, *, min_word_length=3,
  max_suffix_length=16)` finds a supplied dictionary word at a Unicode-aware boundary,
  followed by a bounded run of ASCII digits and/or punctuation. It is opt-in and
  requires no bundled lexicon.
- `DictionaryEntry(word: str, rank: int, source_id: str | None = None)` requires a
  nonempty valid Unicode-scalar word and positive integer rank. `source_id`, if given,
  must be a short ASCII identifier.
- `DictionaryLexicon(entries, *, min_word_length=1, max_word_length=128,
  max_entries=100_000, max_total_codepoints=2_000_000, normalization="none")`
  validates bounded entries, resolves exact duplicate spellings deterministically, and
  records the Python Unicode database version in `unicode_data_version`.

No system or bundled lexicon is provided.
