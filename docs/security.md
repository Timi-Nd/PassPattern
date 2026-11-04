# Security and privacy

PassPattern finds patterns in password-like text. It does not estimate password
strength, entropy, or guessability, and it is not an authentication or credential
storage system.

## What results contain

Built-in matches do not store the original password or matched substring. They do
contain spans, detector and pattern names, and numeric or boolean evidence. Numeric
sequence matches additionally contain the parsed integer terms, which can reproduce
parts of the input. Dictionary results can include ranks and case information.
Treat results as sensitive even when the full input is absent.

The built-in engine does not keep analysis history. However, your application can
retain inputs or results through custom detectors, logging, telemetry, exception
reporting, or storage. Review those parts of the application as well. Custom
detectors are trusted code and may have side effects.

## Memory and dependencies

Python and native runtime memory is not guaranteed to be securely erased. PassPattern
cannot promise removal of input data from process memory, crash dumps, debuggers, swap,
or operating-system diagnostics.

Text preparation uses the separately distributed `passtext-native` package. This
repository does not contain its implementation source. Check the dependency's
release and platform information when deciding whether it is appropriate for your
application.

## Limits and failure behavior

Default engine limits are 1,024 code points, 4,096 UTF-8 bytes, and 1,000 matches.
Numeric and dictionary detectors have additional work and state limits. A built-in
detector reports an explicit limit error rather than returning a partial result as if
analysis succeeded. Handle these errors without logging the submitted input.

## Reporting a vulnerability

Do not include real passwords, credentials, or secrets in a report. Use GitHub's
private vulnerability reporting for this repository if it is enabled. Otherwise,
contact a maintainer through an established private channel. Include the affected
revision, impact, and a minimal reproduction with synthetic input. Coordinate before
publishing vulnerability details.
