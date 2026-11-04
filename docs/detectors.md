# Detectors

PassPattern detects recognizable patterns; it does not estimate password strength.
All detectors are opt-in. The structural and contextual factory functions return
fresh instances. Dictionary detectors require an application-supplied lexicon.

## Structural

| Class | ID / type | Defaults and rule | Limitations and likely false positives |
|---|---|---|---|
| `RepeatedCharacterDetector` | `structural.repeated_character` / `repeated_character` | `min_repetitions=3`; finds maximal consecutive identical Unicode code points. | Repeated punctuation or intentional text can match. |
| `RepeatedSubstringDetector` | `structural.repeated_substring` / `repeated_substring` | `min_unit_length=2`, `min_repetitions=2`; emits tandem repeats of primitive units. | Periodic identifiers and deliberate repetition can match. Meaningful overlapping spans are retained. |
| `NumericSequenceDetector` | `structural.numeric_sequence` / `numeric_sequence` | `min_sequence_length=3`; maximal ASCII digits with constant step +1 or -1. | Does not wrap (9→0), and non-ASCII digits are not considered. |
| `AlphabeticSequenceDetector` | `structural.alphabetic_sequence` / `alphabetic_sequence` | `min_sequence_length=3`; maximal ASCII letters with constant case-insensitive step +1 or -1. | Does not wrap (z→a); keyboard adjacency is not used. |

Each threshold accepts integers of at least two; booleans and non-integers are rejected.
`default_structural_detectors()` constructs all four using these defaults.

## Dictionary

All dictionary detectors use an explicit `DictionaryLexicon`. There is no included
authoritative password list. Matching scans processed text and returns metadata, not
the word, input substring, or source ID.

| Class | ID / type | Defaults and rule | Limitations and likely false positives |
|---|---|---|---|
| `DictionaryWordDetector` | `dictionary.word` / `dictionary_word` | `min_word_length=3`; exact spelling and ASCII case-folded variants. | Ordinary words embedded in names or phrases can match. Case-sensitive matching semantics are limited to ASCII case folding; ranks come from the supplied data. |
| `ReversedWordDetector` | `dictionary.reversed_word` / `reversed_word` | `min_word_length=4`; detects reversed entries case-insensitively and skips palindromes. | Short accidental reverse substrings can match. |
| `LeetspeakDetector` | `dictionary.leetspeak` / `leetspeak_word` | `max_substitutions=3`, `min_word_length=4`, `max_active_states=4096`, `max_work=1_000_000`. Length-preserving alternatives default to `@/4→a`, `0→o`, `3→e`, `5/$→s`, `7→t`, `1→i/l`, `!→i`. | Deliberate or ambiguous substitutions can match. A work/state limit raises `DictionarySearchLimitError`; it does not silently truncate. |

`DictionaryLexicon` defaults to word lengths 1–128, 100,000 supplied entries, and
2,000,000 total supplied code points. It permits `"none"` or `"nfc"` normalization;
NFC entries must already be NFC-normalized. Exact duplicate spellings resolve to the
lowest rank then stable source ID. Case variants remain separate. A normalization-
aware dictionary detector must agree with `EngineConfig.normalization`.

## Contextual

| Class | ID / type | Defaults and rule | Limitations and likely false positives |
|---|---|---|---|
| `CalendarDateDetector` | `contextual.calendar_date` / `calendar_date` | Years 1900–2099, `date_order="auto"`, compact dates disabled. Recognizes `YYYY-MM-DD`, `YYYY/MM/DD`, `DD-MM-YYYY`, `DD/MM/YYYY`, `MM-DD-YYYY`, and `MM/DD/YYYY`, with the same separator within each date. | Numeric identifiers resembling valid dates can match; ambiguous day/month forms are marked. |
| `YearDetector` | `contextual.year` / `four_digit_year` | Inclusive 1900–2099; maximal runs of exactly four ASCII digits. | Years in dates intentionally overlap date matches; other 4-digit IDs can match. |
| `KeyboardWalkDetector` | `contextual.keyboard_walk` / `keyboard_walk` | `min_walk_length=4`, `max_turns=1`, `layout="us_qwerty"`. ASCII letter/digit paths on a simplified US QWERTY adjacency model. | Not other layouts, shifted punctuation, or mobile keyboards; ordinary key sequences may match. |

`CalendarDateDetector` also accepts `min_year`, `max_year`, `date_order` (`"auto"`,
`"dmy"`, `"mdy"`, `"ymd"`), and `allow_compact=False`. `YearDetector` accepts inclusive
`min_year` and `max_year`. `KeyboardWalkDetector` accepts only `"us_qwerty"`.
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
reported window; overlapping valid windows are retained.

## Overlaps and ordering

Detectors run sequentially in registration order, but the engine sorts final results
deterministically. It does not merge different patterns or remove valid overlaps:
examples include a four-digit year inside a date and a repeated substring alongside a
dictionary word.
