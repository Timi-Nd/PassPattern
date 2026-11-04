# Unicode and match positions

PassPattern reports spans in the text that detectors actually inspect. Understanding
that text is important when you display or compare a match.

## Code-point offsets

`start_index` is the first code-point index in a match; `end_index` is the index just
after it. The range is half-open: `[start_index, end_index)`. Indices count Python
Unicode code points in `PreparedPassword.processed_text`, not UTF-8 bytes or
user-perceived characters.

For example, the string `🙂x2468` has the four digits at span `[2, 6)` in Python
code-point indexing. Some visible characters contain multiple code points: `é`
(the letter `e` followed by a combining acute accent) is two code points, though it
often appears as one character.

Do not use these offsets directly as byte offsets or grapheme indices in a user
interface. Convert them to the indexing system used by your UI.

## Normalization

The native text-processing dependency validates the input and optionally normalizes
it to NFC. Detectors inspect the resulting `processed_text`. When you set
`normalization="nfc"`, that text can have a different length from the submitted text,
so a span may not map directly to the original string. The analysis result does not
include the processed text; keep the exact prepared text separately if your application
needs to display matched positions.

## Matching scope

- Repeated-character and repeated-substring detectors operate on Unicode code points.
- Numeric and alphabetic sequences, dates, years, and keyboard walks use ASCII digits
  and/or letters as described in the [detector guide](detectors.md).
- Dictionary matching uses ASCII case folding, not full Unicode case folding. Similar
  looking characters are not treated as equivalent.
- A dictionary configured for NFC requires entries already normalized to NFC and the
  engine to use the same normalization mode.

Python and the native dependency may use different Unicode database versions. Exact
cross-runtime normalization can therefore depend on the installed versions; test the
versions you deploy if that distinction matters.
