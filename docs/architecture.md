# How PassPattern works

PassPattern separates text preparation, pattern detection, and result validation.
This keeps detector code focused on recognition rules and makes it easier to compare
the Python behavior with another implementation.

## Analysis flow

1. You pass a string, an `EngineConfig`, and the detectors you want to run.
2. The engine checks its code-point limit and calls `passtext-native` once. That
   component validates Unicode and byte limits and applies optional NFC normalization.
3. Each selected detector inspects the same `processed_text`.
4. The engine validates detector results, applies the match-count cap, sorts the
   results, and returns an immutable `AnalysisResult`.

The native dependency is separate from this repository; PassPattern does not prepare
or normalize text itself.

## Choosing detectors

The engine runs no detectors by default. You can register structural, contextual, or
dictionary detectors independently, or use the structural and contextual factory
functions. Dictionary detectors require an application-supplied lexicon.

The engine requires unique detector IDs. A detector that declares a normalization
requirement must agree with the engine configuration. Built-in detectors are
deterministic and do not perform I/O.

## Results and ordering

`PatternMatch` describes a detector, pattern family, span, and typed evidence.
Numeric results use `NumericPatternMatch` to expose integer terms, term spans,
relationship parameters, and ambiguity. Results do not retain the original input
string, but numeric term values and match locations can still disclose information.

Spans are zero-based, half-open Unicode code-point offsets into post-normalization
`processed_text`. The engine sorts results by start and end, detector ID, category,
pattern type, and evidence. It does not merge overlapping matches.

## Resource limits and failures

By default, the engine allows up to 1,024 code points, 4,096 UTF-8 bytes, and 1,000
matches per analysis. The native component enforces its processing limits; detector
families may also impose their own work or state budgets. When a built-in detector
reaches a documented budget, it raises a specific error instead of returning a
success-shaped partial result.

The engine wraps unexpected custom-detector failures in `DetectorExecutionError`.
Expected built-in search-limit errors remain distinguishable. Custom detectors are
trusted application code and may have different side effects or privacy behavior.

## Python and other implementations

This repository contains the Python reference implementation and shared behavior
vectors. It does not contain a Rust engine. See
[Python/Rust parity](rust-parity.md) for how the vectors describe behavior that an
independent implementation can reproduce.
