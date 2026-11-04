# Security and privacy

PassPattern recognizes patterns in password text. It is not a password-strength
estimator, entropy calculator, guessability model, authentication system, or
credential-storage component.

## Data handling

The built-in engine prepares an input once through the native extension and returns
pattern metadata without including the password or matched substrings. Built-in
evidence is restricted to finite numeric or boolean values. Errors raised by the
engine and native adapter use content-free messages rather than including input text.
The engine does not maintain password history or a persistent analysis cache. Pattern
analysis contains no network-client code.

These are properties of the current built-in implementation, not a guarantee about an
application that wraps it. Applications can register custom detectors, and those
detectors are trusted code. They can retain input-derived data, raise their own
exceptions, or perform I/O. Review injected detectors and surrounding logging,
telemetry, error reporting, and persistence.

Match locations, categories, detector IDs, dictionary ranks, and other metadata can
still reveal information. Treat results and application-supplied lexicons as
sensitive.

The Python source contains no network-client, logging, or persistent-storage code in
the analysis path. The separately built native implementation is not present in this
repository and was not independently audited here.

## Memory and dependency trust

Python and native runtime allocations are not guaranteed to be securely zeroized.
PassPattern cannot promise removal of password data from process memory, crash dumps,
debuggers, swap, or operating-system diagnostics.

`passtext_native` is a separately built dependency. Install it from public PyPI
(`passtext-native>=0.1.0,<0.2.0`) and check Python ABI, platform, and architecture
compatibility. This repository does not distribute its Rust source or binary.

## Limits and failure behavior

Default input limits are 1,024 code points and 4,096 UTF-8 bytes; the default output
cap is 1,000 matches. The native component enforces its processing limits. Dictionary
lexicons and transformation searches have additional configurable size, work, and
state budgets. When a leetspeak search exceeds a work or state budget it raises
`DictionarySearchLimitError`, not a partial success result. Applications should handle
these expected failures without logging submitted input.

## Reporting a vulnerability

Do not include real passwords, credentials, or secrets in a report. Use GitHub's
private vulnerability reporting for this repository if enabled. Otherwise, contact a
repository maintainer through an existing private channel. No response-time or support
guarantee is made. Include the affected revision, impact, and a minimal reproduction
using synthetic input. Coordinate before publishing vulnerability details.
