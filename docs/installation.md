# Installation

PassPattern is a research repository installed from a checkout; it is not published to
PyPI. Analysis requires the public `passtext-native` 0.1.x binary wheel, which the
`dev` extra installs from PyPI. No Rust toolchain, private credentials, or private
source is needed.

## Requirements

- CPython 3.10 or newer. CI runs 3.10 and 3.14 on Windows and Linux.
- Native wheel platforms: Windows x86-64 and Linux x86-64 (manylinux 2.28), CPython
  3.10+ via the stable ABI. macOS, ARM, musl Linux, and PyPy are not verified; pip
  fails to resolve a wheel there rather than attempting a Rust build, and analysis
  raises `NativeExtensionUnavailableError` if the wheel is absent.

## Windows PowerShell

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Linux

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

To install only the runtime pieces, install the wheel and the package separately:

```sh
python -m pip install --only-binary ":all:" "passtext-native>=0.1.0,<0.2.0"
python -m pip install -e .
```

Do not copy native binaries or implementation source into the repository.

## Common issues

- **Import works but analysis fails:** `passtext-native` is missing, or its wheel does
  not match your platform or Python. Reinstall it in the same environment.
- **The extension has the wrong API:** install a 0.1.x release; PassPattern reports
  this without exposing internal exception details.
- **PowerShell activation is blocked:** run `.venv\Scripts\python.exe` directly instead
  of changing the system execution policy.
