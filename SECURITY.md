# Security policy

## Scope and limitations

PassPattern analyzes password text in process and returns structural metadata. It is
not a password-strength estimator and does not guarantee resistance to guessing,
credential stuffing, or other attacks. The Python and native runtimes do not guarantee
secure zeroization of password data in memory.

The compiled `passtext_native` extension is a separately published dependency. Install
it from public PyPI and verify that it is compatible with the Python interpreter and
platform. This repository does not include that extension or its Rust source.

Results and match spans can reveal information about input text. Treat them as
sensitive data. The library does not intentionally log or persist submitted passwords;
applications using it should review their own logging, telemetry, exception handling,
and storage behavior.

## Reporting a vulnerability

Do not include real passwords, tokens, or other secrets in a report. Use GitHub's
private vulnerability reporting for this repository if it is enabled. Otherwise,
contact a repository maintainer through an existing private channel. No response-time
or support guarantee is made by this policy.

Please include a concise description, affected revision, impact, and a minimal
reproduction using synthetic input. Do not publish exploit details before coordinating
with the maintainers.
