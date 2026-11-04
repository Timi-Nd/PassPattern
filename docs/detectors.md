# Detector guide

A detector looks for a particular kind of structure and returns a span plus
explanatory metadata. It does not decide whether a password is strong. You select
detectors explicitly; `PassPatternEngine()` with no arguments runs none.

The factory functions return fresh detector instances:

- `default_structural_detectors()` returns repeated-character, repeated-substring,
  numeric-sequence, and alphabetic-sequence detectors.
- `default_contextual_detectors()` returns date, year, and keyboard-walk detectors.
- Dictionary detectors require a `DictionaryLexicon` that you supply.

## Structural patterns

| Detector | Pattern type | Default rule |
|---|---|---|
| `RepeatedCharacterDetector` | `repeated_character` | Maximal runs of the same code point, at least 3. |
| `RepeatedSubstringDetector` | `repeated_substring` | Repeated primitive units; default unit length at least 2 and at least 2 repetitions. |
| `NumericSequenceDetector` | `numeric_sequence`, `arithmetic_progression`, `consecutive_prime_sequence` | ASCII digit sequences; numeric-family details below. |
| `AlphabeticSequenceDetector` | `alphabetic_sequence` | Maximal ASCII letter runs with a case-insensitive step of +1 or -1, at least 3 letters. |

Repeated patterns can occur in ordinary text and identifiers. Alphabetic sequences
do not wrap from `z` to `a`; they are not keyboard-walk detection.

## Numeric sequences

The numeric detector keeps the original digit-by-digit sequence behavior and adds
mathematical families. It looks only at contiguous ASCII digit runs. It considers
candidate terms and checks relationships using integer arithmetic, so multi-digit
terms can be recognized without floating-point comparisons.

### Supported by default

**Consecutive digits (`numeric_sequence`).** A maximal run of digits that changes by
exactly `+1` or `-1`, with at least `min_sequence_length=3` digits. For example,
`1234` is ascending and `9876` descending. It does not wrap at 9 and 0.

**Arithmetic progression (`arithmetic_progression`).** At least four terms with the
same nonzero integer difference. Differences of `+1` and `-1` remain in the legacy
`numeric_sequence` family. Examples:

| Input | Terms | Difference |
|---|---|---:|
| `2468` | 2, 4, 6, 8 | +2 |
| `13579` | 1, 3, 5, 7, 9 | +2 |
| `8642` | 8, 6, 4, 2 | -2 |
| `97531` | 9, 7, 5, 3, 1 | -2 |
| `10121416` | 10, 12, 14, 16 | +2 |
| `20304050` | 20, 30, 40, 50 | +10 |

The last two examples show why the detector considers bounded multi-digit
segmentations as well as individual digits.

**Consecutive primes (`consecutive_prime_sequence`).** At least four terms must be
adjacent primes, not just numbers that happen to be prime. For example, `235711`
is interpreted as 2, 3, 5, 7, 11; `11131719` as 11, 13, 17, 19. A prime run with
fewer than four terms is not reported.

### Experimental and off by default

Set `experimental_families` to opt in:

```python
from passpattern.structural import NumericSequenceDetector

detector = NumericSequenceDetector(
    experimental_families=frozenset({"geometric_progression", "fibonacci_like_progression"})
)
```

- **Geometric progression (`geometric_progression`):** at least four positive terms
  with one exact rational ratio. `24816` is interpreted as 2, 4, 8, 16, with ratio
  2/1.
- **Fibonacci-like progression (`fibonacci_like_progression`):** at least six
  non-negative terms, with a nondecreasing first pair, following
  `t[n] = t[n - 1] + t[n - 2]`. `11235813` is interpreted as
  1, 1, 2, 3, 5, 8, 13. The all-zero progression is not reported.

These families are experimental because short digit strings can fit mathematical
rules by coincidence. Their thresholds reduce some accidental matches but cannot
prove that a person intended a sequence.

### Segmentation, zeros, and overlaps

A multi-digit term uses canonical decimal notation and cannot start with zero. A
single `0` is valid. For example, `01020304` can be read as 0, 10, 20, 30.

Some strings have more than one valid interpretation. For example, `12345678` can
contain a legacy digit-by-digit run and the arithmetic progression 12, 34, 56, 78.
Each reported match includes its own chosen terms. If multiple term boundaries fit
the same span, `ambiguous` is true; the selected interpretation has the most terms,
then the earliest boundaries. Distinct pattern families and valid overlapping spans
are preserved rather than merged.

The legacy run can also be contained in a longer multi-digit match. For example,
`10121416` has the arithmetic progression 10, 12, 14, 16 and the legacy `012` run
at span `[1, 4)`. Seeing both results is expected.

### Numeric match metadata

Numeric results are `NumericPatternMatch` objects, a subtype of `PatternMatch`. In
addition to the match span and standard length/direction evidence, they contain:

- `terms`: integer values and half-open spans for each interpreted term.
- `parameter_numerator` and `parameter_denominator`: arithmetic difference over 1,
  or a reduced geometric ratio. Prime and Fibonacci-like matches have no parameter.
- `ambiguous`: whether multiple valid term-boundary interpretations share the span.

For `2468`, the terms are `(2, 4, 6, 8)`, the difference is `2/1`, and the direction
evidence is `1` for ascending. Span indices are into `processed_text`; see
[Unicode and positions](unicode.md).

### Numeric work limits

The detector bounds run length, term size, candidate count, term count, and total
interpretation work. `min_sequence_length` defaults to 3 and must be at least 2.
Other defaults and maximum supported values are:

| Option | Default | Maximum |
|---|---:|---:|
| `max_digit_run` | 32 | 32 digits |
| `max_term_digits` | 6 | 6 digits |
| `max_term_value` | 999,999 | 999,999 |
| `max_terms` | 8 | 16 |
| `max_candidates` | 8,192 | 32,768 |
| `max_work` | 100,000 | 100,000 work units |

You can lower these limits within their supported ranges. A longer digit run raises
`NumericSequenceLimitError`; it is not silently truncated. The engine also applies its
input and total-match limits. Configure and catch these errors according to your
application's needs.

## Dictionary patterns

Dictionary detectors scan only entries in your `DictionaryLexicon`; PassPattern does
not include an authoritative word or password list.

| Detector | Pattern type | Default behavior |
|---|---|---|
| `DictionaryWordDetector` | `dictionary_word` | Finds supplied words with exact or ASCII case-insensitive matching; minimum word length 3. |
| `DictionaryCompoundDetector` | `dictionary_compound` | Finds a word at a Unicode-aware boundary followed by 1–16 ASCII digits and/or punctuation, ending at a word boundary. |
| `ReversedWordDetector` | `reversed_word` | Finds reversed entries case-insensitively; minimum length 4; skips palindromes. |
| `LeetspeakDetector` | `leetspeak_word` | Finds bounded, length-preserving substitutions; default maximum is 3 substitutions and minimum word length is 4. |

Ordinary words, names, and deliberate substitutions may match by coincidence. Ranks
and exact-case status come from the supplied data; they are not estimates of password
strength. Dictionary and transformation detectors have their own input, state, and
work bounds. A transformation search that exceeds its budget raises
`DictionarySearchLimitError`, not a partial result.

`DictionaryLexicon` defaults to word lengths 1–128, at most 100,000 entries, and at
most 2,000,000 total code points across supplied entries. Its normalization mode is
`"none"` or `"nfc"` and must agree with the engine. With NFC mode, entries must
already be normalized. Exact duplicate spellings are resolved by lowest rank and
then stable source ID; differently cased spellings remain distinct.

The compound detector requires a boundary before the dictionary word and after its
suffix. The suffix is a nonempty contiguous run of ASCII digits and/or punctuation;
it can mix both, as in `example-2026!`. Its `LENGTH` evidence covers the whole match,
`RANK` and `CASE_EXACT` describe the word, and `COUNT` is the suffix length.

Leetspeak substitutions are length-preserving. By default, `@` and `4` can represent
`a`, `0` can represent `o`, `3` can represent `e`, `5` and `$` can represent `s`, `7`
can represent `t`, `1` can represent `i` or `l`, and `!` can represent `i`. The
detector has a 4,096-active-state limit and a 1,000,000-work limit in addition to its
three-substitution default.

The
[synthetic compound-detector examples](../tests/fixtures/dictionary-compound-synthetic-v1.json)
exercise exact matching rules; they do not measure real-world detection accuracy.

## Contextual patterns

| Detector | Pattern type | Default behavior |
|---|---|---|
| `CalendarDateDetector` | `calendar_date` | Valid dates from 1900–2099 in year-month-day, day-month-year, or month-day-year forms; compact dates are off by default. |
| `YearDetector` | `four_digit_year` | Maximal four-digit ASCII years from 1900–2099. |
| `KeyboardWalkDetector` | `keyboard_walk` | ASCII letter/digit paths on a simplified US QWERTY layout; minimum length 4 and at most one direction change. |

The accepted separated date formats are `YYYY-MM-DD`, `YYYY/MM/DD`, `DD-MM-YYYY`,
`DD/MM/YYYY`, `MM-DD-YYYY`, and `MM/DD/YYYY`; each date uses one separator throughout.
Dates are checked against Gregorian calendar rules. Valid-looking dates and years may
be identifiers rather than intentional dates, and a year inside a date is also
reported as a year match.

`CalendarDateDetector` accepts inclusive `min_year`, `max_year`, `date_order`
(`"auto"`, `"dmy"`, `"mdy"`, or `"ymd"`), and `allow_compact`. Compact `YYYYMMDD`
dates are enabled only for `"auto"` or `"ymd"`. In `"auto"` mode, ambiguous
day/month interpretations are marked instead of duplicated. `DATE_ORDER` evidence
uses 0 for an ambiguous auto result, 1 for year-month-day, 2 for day-month-year, and
3 for month-day-year. `"dmy"` and `"mdy"` select a preferred interpretation when both
are valid but accept a sole valid alternative. `"ymd"` accepts only year-first forms.

`YearDetector` accepts inclusive `min_year` and `max_year`. The keyboard detector
accepts a caller-supplied `KeyboardLayout` with ASCII letters or digits mapped to
integer `(x, y)` coordinates. It uses eight movement directions, rejects repeated
consecutive keys and immediate reversals, and counts direction changes as turns.
Overlapping valid walks are kept. Shifted punctuation and mobile keyboards are not
modeled.

## Ordering and overlaps

Detectors run in registration order. The engine then sorts matches deterministically
by span, detector ID, category, pattern type, and evidence. It preserves valid
overlaps, such as a year inside a date or a repeated substring alongside a dictionary
match.
