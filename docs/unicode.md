# Unicode and match positions

## Processed text and code-point spans

Input validation and optional NFC normalization are performed by the separate native
dependency. Detectors inspect `PreparedPassword.processed_text`.
`PatternMatch.start_index` and `end_index` are zero-based, half-open Python string
indices: they count Unicode code points in that processed string.

These offsets are not UTF-8 byte positions or grapheme-cluster positions. A visible
grapheme may contain multiple code points (for example a base letter plus a combining
mark, or an emoji sequence). A UI must not treat a code-point index as a user-perceived
character index without converting it.

With `normalization="nfc"`, the processed string can have different code points and a
different length from the submitted string. Use spans only with the processed text
from the same native preparation if you need to map them to text; the engine does not
return that text in its result.

## Unicode scalar values and runtime versions

Python strings can contain surrogate code points even though they are not Unicode
scalar values. Native input validation rejects unsupported Unicode before detection.
`DictionaryEntry` independently rejects surrogate code points. `DictionaryLexicon`
records `unicodedata.unidata_version`; the native library uses the Unicode
data compiled into its build. This repository does not guarantee that the Python and
native Unicode database versions match. Verify the installed native build and Python
runtime together when exact cross-runtime normalization behavior matters.

## Matching policies

Structural repeated-character and repeated-substring detection operate on Unicode code
points. Numeric and alphabetic sequence detectors intentionally accept only ASCII
digits and letters. Contextual dates, years, and keyboard walks also use ASCII
characters.

Dictionary matching uses ASCII-only case folding, not full Unicode `casefold()`.
Non-ASCII letters are preserved as supplied; visually similar characters are not
treated as equivalent. NFC dictionary lexicons require entries already normalized to
NFC, and their normalization mode must match the engine.

These policies are deliberate scope boundaries, not claims that Unicode text has one
universal representation. Applications should choose normalization and dictionaries
that match their own authentication system.
