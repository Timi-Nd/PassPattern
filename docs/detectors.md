# Detectors

PassPattern detects recognizable patterns; it does not estimate password strength.
All detectors are opt-in. The structural and contextual factory functions return
fresh instances. Dictionary detectors require an application-supplied lexicon.

## Structural

| Class | ID / type | Defaults and rule | Limitations and likely false positives |
|---|---|---|---|
| `RepeatedCharacterDetector` | `structural.repeated_character` / `repeated_character` | `min_repetitions=3`; finds maximal consecutive identical Unicode code points. | Repeated punctuation or intentional text can match. |
| `RepeatedSubstringDetector` | `structural.repeated_substring` / `repeated_substring` | `min_unit_length=2`, `min_repetitions=2`; emits tandem repeats of primitive units. | Periodic identifiers and deliberate repetition can match. Meaningful overlapping spans are retained. |
| `NumericSequenceDetector` | `structural.numeric_sequence` / `numeric_sequence`, `arithmetic_progression`, `consecutive_prime_sequence` (experimental types: `geometric_progression`, `fibonacci_like_progression`) | `min_sequence_length=3` for maximal ASCII ±1 runs; also recognizes arithmetic progressions and consecutive-prime runs with at least four terms. | Non-ASCII digits are excluded. Numeric-looking substrings can be coincidental; run, term, candidate, and work limits apply. |
| `AlphabeticSequenceDetector` | `structural.alphabetic_sequence` / `alphabetic_sequence` | `min_sequence_length=3`; maximal ASCII letters with constant case-insensitive step +1 or -1. | Does not wrap (z→a); keyboard adjacency is not used. |

Structural minimum/repetition thresholds reject booleans and values below their
documented minima.
`default_structural_detectors()` constructs all four using these defaults.

`NumericSequenceDetector` accepts `min_sequence_length=3` for the compatible
unit-step detector and these bounded interpretation options:

```python
NumericSequenceDetector(
    max_digit_run=32,
    max_term_digits=6,
    max_term_value=999_999,
    max_terms=8,
    max_candidates=8192,
    max_work=100_000,
    experimental_families=frozenset(),
)
```

The limits may be lowered within their supported ranges; the maximums are fixed at
32 ASCII digits per contiguous run, six digits and 999,999 per term, 16 terms, 32,768
valid candidates, and 100,000 units of interpretation/primality work per detector
invocation. Exceeding a limit raises the content-free `NumericSequenceLimitError`;
the detector does not silently truncate. The engine's existing input and total-match
limits remain in force.

Numeric interpretation first preserves the previous maximal single-digit +1/-1
matches. Other families use bounded, contiguous terms: a multi-digit term is canonical
decimal (no leading zero), while `0` is permitted as a single-digit term. Arithmetic
progressions use exact integer differences; consecutive-prime matches require the
terms to be adjacent in the prime sequence, not merely prime. Terminations and
overlaps remain visible, including the legacy run inside a longer numeric string.
Strings with multiple valid term-boundary interpretations are marked `ambiguous`;
duplicate matches for the same family, span, and interpretation are coalesced. When
one family and span have multiple segmentations, the reported terms use the greatest
term count, then the earliest available boundaries; all distinct interpretations still
contribute to the ambiguity flag.

Experimental families are off by default. Pass
`experimental_families=frozenset({"geometric_progression"})` to opt into exact
integer geometric ratios (at least four positive terms), and/or
`"fibonacci_like_progression"` to opt into the recurrence
`t[n] = t[n - 1] + t[n - 2]` (at least six terms). The latter accepts non-negative
terms with a nondecreasing first pair and rejects the all-zero recurrence; its reported
direction is ascending. These thresholds reduce accidental matches but do not establish
that a numeric substring was intentional or predictable to a human.

Numeric matches are `NumericPatternMatch` values, a `PatternMatch` subtype. They carry
each integer term and its half-open code-point span, direction, a reduced numerator /
denominator for arithmetic or geometric relationships, and the ambiguity flag. Prime
matches have no ratio or difference parameter. Term values reproduce numeric content
from the input, so protect these results like other sensitive password-derived data.
Future families should reuse the bounded term interpreter, state their recurrence and
minimum term count, use exact integer arithmetic, and add tests, shared vectors, and
benchmark cases before being enabled by default.

## Dictionary

All dictionary detectors use an explicit `DictionaryLexicon`. There is no included
authoritative password list. Matching scans processed text and returns metadata, not
the word, input substring, or source ID.

| Class | ID / type | Defaults and rule | Limitations and likely false positives |
|---|---|---|---|
| `DictionaryWordDetector` | `dictionary.word` / `dictionary_word` | `min_word_length=3`; exact spelling and ASCII case-folded variants. | Ordinary words embedded in names or phrases can match. Case-sensitive matching semantics are limited to ASCII case folding; ranks come from the supplied data. |
| `DictionaryCompoundDetector` | `dictionary.compound` / `dictionary_compound` | `min_word_length=3`, `max_suffix_length=16`; finds a supplied word at a Unicode-aware boundary followed by 1–16 ASCII digits and/or punctuation. | Requires a word boundary before the dictionary word and after the suffix. Does not recognize spaces, non-ASCII suffix characters, prefixes, or infixes. |
| `ReversedWordDetector` | `dictionary.reversed_word` / `reversed_word` | `min_word_length=4`; detects reversed entries case-insensitively and skips palindromes. | Short accidental reverse substrings can match. |
| `LeetspeakDetector` | `dictionary.leetspeak` / `leetspeak_word` | `max_substitutions=3`, `min_word_length=4`, `max_active_states=4096`, `max_work=1_000_000`. Length-preserving alternatives default to `@/4→a`, `0→o`, `3→e`, `5/$→s`, `7→t`, `1→i/l`, `!→i`. | Deliberate or ambiguous substitutions can match. A work/state limit raises `DictionarySearchLimitError`; it does not silently truncate. |

`DictionaryLexicon` defaults to word lengths 1–128, 100,000 supplied entries, and
2,000,000 total supplied code points. It permits `"none"` or `"nfc"` normalization;
NFC entries must already be NFC-normalized. Exact duplicate spellings resolve to the
lowest rank then stable source ID. Case variants remain separate. A normalization-
aware dictionary detector must agree with `EngineConfig.normalization`.

`DictionaryCompoundDetector` uses only the supplied lexicon. Its `max_suffix_length`
must be between 1 and 128; the default is 16. A suffix is a contiguous run of ASCII
digits or ASCII punctuation and may contain both (for example `-2026!`). It must
contain at least one character. `LENGTH` reports the full compound span, `RANK` and
`CASE_EXACT` describe the matched word, and `COUNT` reports suffix characters. Results
contain spans and numeric/boolean evidence, not the matched word or suffix.

The labeled synthetic examples in
[`tests/fixtures/dictionary-compound-synthetic-v1.json`](../tests/fixtures/dictionary-compound-synthetic-v1.json)
exercise the documented rules and exact span positions. Their pass counts are
rule-conformance checks only; these hand-authored examples do not estimate real-world
false-positive or false-negative rates.

## Contextual

| Class | ID / type | Defaults and rule | Limitations and likely false positives |
|---|---|---|---|
| `CalendarDateDetector` | `contextual.calendar_date` / `calendar_date` | Years 1900–2099, `date_order="auto"`, compact dates disabled. Recognizes `YYYY-MM-DD`, `YYYY/MM/DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, `MM-DD-YYYY`, and `MM/DD/YYYY`, with the same separator within each date. | Numeric identifiers resembling valid dates can match; ambiguous day/month forms are marked. |
| `YearDetector` | `contextual.year` / `four_digit_year` | Inclusive 1900–2099; maximal runs of exactly four ASCII digits. | Years in dates intentionally overlap date matches; other 4-digit IDs can match. |
| `KeyboardWalkDetector` | `contextual.keyboard_walk` / `keyboard_walk` | `min_walk_length=4`, `max_turns=1`, `layout="us_qwerty"`. ASCII letter/digit paths on a simplified adjacency model. `layout` may be a caller-supplied `KeyboardLayout`. | No built-in non-US layouts, shifted punctuation, or mobile keyboards; ordinary key sequences may match. |

`CalendarDateDetector` also accepts `min_year`, `max_year`, `date_order` (`"auto"`,
`"dmy"`, `"mdy"`, `"ymd"`), and `allow_compact=False`. `YearDetector` accepts inclusive
`min_year` and `max_year`. `KeyboardWalkDetector` accepts `"us_qwerty"` or a
`KeyboardLayout` instance. A custom layout supplies a mapping from lowercase ASCII
letters or digits to integer `(x, y)` key coordinates; adjacency uses the same
documented physical-spacing rule as `US_QWERTY`.
`default_contextual_detectors()` creates all three defaults.

For day/month dates, `"dmy"` and `"mdy"` select the preferred interpretation when both
are valid; a sole valid alternative is still accepted. `"auto"` records ambiguity
instead of emitting duplicate spans. `"ymd"` accepts only year-first forms.
`allow_compact=True` enables `YYYYMMDD` only for `"auto"` or `"ymd"`. Date `DATE_ORDER`
evidence is an integer code: 0 means an ambiguous auto interpretation, 1 year-month-day,
2 day-month-year, and 3 month-day-year. Dates are validated with Gregorian calendar
rules and bounded by the configured inclusive years.

The keyboard detector accepts ASCII letters/digits only, is case-insensitive, and
rejects repeated consecutive keys and immediate reversals. It classifies changes in
eight directions as turns. `max_turns` controls the number of direction runs in a
reported window; overlapping valid windows are retained. The default US layout is
unchanged; custom layouts let applications model additional physical key arrangements.

## Overlaps and ordering

Detectors run sequentially in registration order, but the engine sorts final results
deterministically. It does not merge different patterns or remove valid overlaps:
examples include a four-digit year inside a date and a repeated substring alongside a
dictionary word.
