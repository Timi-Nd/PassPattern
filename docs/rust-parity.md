# Shared behavior across implementations

PassPattern's Python implementation defines executable detector behavior and is
tested against a language-neutral JSON fixture. The fixture makes it possible to
compare an independent implementation without relying on matching source code.

There is no Rust pattern engine in this repository. A Rust implementation would also
need an authorized native text-preparation interface; the Python adapter to
`passtext-native` is not that interface.

## The shared fixture

[`tests/vectors/passpattern-v2.json`](../tests/vectors/passpattern-v2.json) has schema
version 2. Each vector provides an input, engine configuration, detector IDs and
options, and either ordered matches or an expected error. A match includes its
detector ID, category, pattern type, half-open span, and evidence.

Numeric matches also include:

- `numeric_terms`: ordered integer values and their spans.
- `parameter`: an exact integer numerator/denominator pair or `null`.
- `ambiguous`: whether other valid term boundaries exist for the same span.

Spans count Unicode code points in `processed_text` after configured normalization.
They are not byte or grapheme offsets. Output order matters; evidence object key order
does not.

## Numeric behavior to reproduce

The fixture covers the legacy `+1`/`-1` digit family, arithmetic progressions,
consecutive primes, and opt-in geometric and Fibonacci-like patterns. For example,
`10121416` contains the arithmetic terms 10, 12, 14, 16, with difference 2. A prime
match such as `235711` must be consecutive in the prime list, not merely a set of
prime-valued terms.

Multi-digit terms use canonical decimal notation; only a single-digit term can be
zero-prefixed (that is, the term `0`). Numeric family thresholds, defaults, and
limits are in the [detector guide](detectors.md#numeric-sequences). For multiple
segmentations over the same span, select the interpretation with the most terms, then
the earliest boundaries, and mark the affected matches ambiguous.

## Comparing results

The Python tests read the fixture directly with
`python -m pytest tests/test_shared_vectors.py`. A compatible implementation should
compare every field: errors, ordering, detector and pattern identifiers, spans,
evidence, numeric terms, parameters, and ambiguity.

Treat the written detector rules as the specification; the Python implementation is
an executable reference, not a substitute for reviewing a discrepancy. If an
implementation differs, decide whether the code or the documented rule is wrong
before changing expected results.

## What parity does not cover

The fixture checks the behaviors it contains; it does not prove that two systems are
equivalent for every possible input. Add reviewed cases when you introduce a family
or clarify a boundary, and keep performance benchmarks separate from correctness
tests. The Python native adapter and any other runtime's text-preparation component
must be compared independently for Unicode and normalization behavior.
