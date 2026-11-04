# Architecture

PassPattern is a Python reference library. It does not prepare password text itself
or ship the separately distributed `passtext_native` extension.

## Responsibilities

- **`passtext_native`** validates text, enforces native code-point and
  UTF-8 byte limits, optionally normalizes to NFC, and produces the prepared text.
- **PassPattern** registers explicitly selected detectors, invokes them over the same
  prepared value, validates their results, enforces its match limit, and returns
  deterministic metadata without retaining the password string.
- **Detectors** recognize patterns. Built-ins are deterministic and side-effect-free;
  applications can implement the `Detector` protocol, which is a trust boundary.

```text
Caller: password + EngineConfig + selected detectors
                    |
                    v
          PassPatternEngine.analyze()
                    |
       one prepare_password() call
                    v
             passtext_native
    type + Unicode + size + normalization
                    |
         PreparedPassword.processed_text
                    v
   detectors in registration order (same value)
                    |
          PatternMatch validation
       + max_matches enforcement
                    |
                    v
 AnalysisResult(sorted immutable metadata)
```

## Data flow and limits

`PassPatternEngine` defaults to an empty detector collection. Applications opt in to
the structural, dictionary, and contextual detectors they want. Detector identifiers
must be unique lowercase ASCII identifiers; normalization-aware detectors must agree
with the engine's configured `"none"` or `"nfc"` mode.

Before native preparation, the engine rejects strings longer than `max_codepoints`.
The native extension remains authoritative for input type, Unicode validity, the
configured UTF-8 byte limit, and normalization. The defaults are 1,024 code points, 4,096 UTF-8
bytes, and 1,000 matches per analysis. Dictionary transformations have additional
detector-specific state and work limits.

The engine prepares the input once and passes the same prepared value to each selected
detector. Built-in detectors inspect its `processed_text`; no detector is given the
original input as a separate argument. The engine does not keep analysis history.

## Results

`PatternMatch` describes a detector, category, pattern type, half-open span, and typed
evidence. Numeric matches use the compatible `NumericPatternMatch` subtype to include
parsed integer terms, their boundaries, the exact relation parameter when applicable,
and segmentation ambiguity. Indices count Unicode code points in native
`processed_text`, not bytes, grapheme clusters, or necessarily the original input when
NFC is enabled. Arbitrary strings and matched text are not part of the result model.

After validating detector identifiers, match types, and spans, the engine sorts
results by start and end indices, detector ID, category, pattern type, then evidence.
Valid overlaps are retained. The immutable `AnalysisResult` contains no password or
prepared-password object. Numeric term values reproduce numeric content from the
password, and spans/ranks can reveal information; protect analysis results accordingly.

The numeric detector retains the previous linear ±1 recognizer and adds bounded
candidate interpretation with a shared work budget. Its resource-limit error is
propagated explicitly by the engine rather than converted to a generic detector error.

The proposed production Rust component boundaries and the Python-to-Rust acceptance
process are documented in [Python/Rust parity](rust-parity.md). No Rust production
implementation or private Rust dependency is present in this repository.
