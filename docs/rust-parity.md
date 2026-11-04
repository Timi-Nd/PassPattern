# Python/Rust parity workflow

PassPattern is the Python research and reference implementation. The intended
production pattern engine, PassPattern-Core, is not present in this repository and is
not yet implemented. This document proposes component boundaries and a review process;
it does not create a Rust crate or assume access to a private Rust dependency.

## Component boundaries

The current Python implementation provides the behavior to specify:

| Responsibility | Python reference | Rust implementation boundary |
| --- | --- | --- |
| Input preparation | `passpattern/native.py` adapts to the published `passtext_native` API. | Call an authorized Rust-facing PassText API directly; do not call Python bindings or vendor private source. The dependency/interface must be established before implementation. |
| Configuration and limits | `passpattern/config.py` | Typed engine configuration with matching limits and normalization contract. |
| Detector contract and output | `passpattern/detector.py`, `passpattern/models.py` | Detector trait and result types preserving category, type, evidence, and half-open spans. |
| Coordination and errors | `passpattern/engine.py`, `passpattern/errors.py` | Prepare once, invoke selected detectors, validate outputs, preserve documented errors, and deterministically order results. |
| Recognition algorithms | `passpattern/structural/`, `passpattern/dictionary/`, `passpattern/contextual/` | Implement detectors in small parity-approved increments, preserving each documented rule and metadata. |
| Correctness fixtures | `tests/vectors/passpattern-v2.json` | Consume the same JSON fixture and compare every field defined by its schema. |

A reasonable initial Rust module layout, once its repository and dependency are
authorized, is `config`, `text`, `model`, `errors`, `engine`, and `detectors` with
structural, dictionary, and contextual submodules. Keep detector modules independent
from the binding layer. The Python adapter remains the interface to the native Python
wheel; it is not the Rust-to-Rust integration API.

## Shared vector format

The versioned fixture at `tests/vectors/passpattern-v2.json` is language-neutral JSON.
Each vector includes:

- A stable ID, input value, detector IDs and options, and engine configuration.
- Either ordered match expectations or an expected error code.
- Match detector ID, category, pattern type, `span` as `[start, end]`, and typed
  evidence values.

Schema version 2 additionally serializes numeric match metadata: `numeric_terms` is an
ordered list of `{value, span}` objects, `parameter` is an exact integer
`[numerator, denominator]` pair or `null`, and `ambiguous` reports alternate valid
term boundaries for the same span. Numeric family identifiers, canonical term
segmentation, defaults, thresholds, and resource limits are specified in
[detectors](detectors.md#structural). In particular, prime matches must represent
consecutive primes; they are not satisfied by an arbitrary list of prime values.
When one family and span has multiple valid segmentations, select the one with the most
terms, then the earliest boundaries; mark all affected matches for that span as
ambiguous.

`schema_version` governs format changes. Spans are zero-based, half-open Unicode
code-point offsets into the processed text after configured normalization; they are
not UTF-8 byte offsets or grapheme indices. Output list order is significant and must
match the engine's documented deterministic ordering. Evidence object key order is
not significant. Rust parity must compare all numeric term values, term spans,
parameters, and ambiguity status, not just the enclosing match span.

Expected results are specified from the reviewed detector rules in
[detectors](detectors.md) and hand-checked cases, not generated from the Python
implementation at test time. Add a vector when a rule, boundary, Unicode behavior,
overlap, metadata field, or error contract is clarified. A Rust consumer should fail
on unknown schema versions or detector IDs instead of silently skipping a case.

## Equivalence and review cycle

For each detector, work in this order:

1. Refine the Python prototype and its documented intended behavior.
2. Add focused Python tests and reviewed shared vectors.
3. Implement the specified component in Rust without treating Python output alone as
   the specification. Numeric parity must preserve the unit-step compatibility path,
   canonical bounded segmentation (including the single-digit zero rule), exact
   integer relationships, opt-in experimental families, and content-free limit
   errors.
4. Run the same fixture against both implementations and compare errors, output
   ordering, detector/category/type, spans, and all evidence.
5. Investigate every discrepancy against the written rule; update the specification
   and expected fixture only after review.
6. Benchmark deterministic synthetic cases separately from correctness tests, then
   approve the component before starting the next one.

The vectors are correctness gates, not benchmarks. Existing Python benchmark scripts
use deterministic synthetic inputs and do not belong in correctness tests or timing
thresholds.

## First implementation milestone

The smallest useful first detector is **repeated characters**: recognize maximal runs
of an identical Unicode scalar value, apply the configured minimum run length, report
the exact count, and use half-open code-point spans. The shared vectors already
exercise non-ASCII scalar indexing and NFC-processed indexing. Before coding it,
establish the authorized Rust repository and Rust-facing PassText interface; neither
is configured or included here. Do not create a new repository or expose private
source as part of this milestone.
