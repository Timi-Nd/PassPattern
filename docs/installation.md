# Installation

PassPattern is installed from this repository; it is not published as a PyPI package.
You need a checkout and a compatible `passtext-native` wheel to analyze text. The
development install below adds that dependency along with the test and quality tools.

## Requirements

- CPython 3.10 or newer.
- A `passtext-native` 0.1.x wheel compatible with your Python version, operating
  system, and CPU architecture.

The published wheels currently target 64-bit Windows and 64-bit Linux (manylinux
2.28). Other combinations, including macOS, ARM, musl-based Linux, and PyPy, are not
verified here. Wheel availability can change; check the package's
[PyPI page](https://pypi.org/project/passtext-native/) for the current release.
PassPattern does not build the native extension from source.

## Windows PowerShell

Run these commands from the repository root:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If PowerShell prevents environment activation, use the environment's executable
directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Linux and macOS

Run these commands from the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

The native wheel may not be available for every operating system or architecture.
Installing the development dependencies will report that directly if no compatible
wheel can be found.

## Runtime-only install

If you do not need the development tools, install the native dependency and the
checkout separately:

```sh
python -m pip install --only-binary=:all: "passtext-native>=0.1.0,<0.2.0"
python -m pip install -e .
```

## Troubleshooting

- **`import passpattern` works, but `analyze()` fails:** verify that the native wheel
  is installed in the same Python environment.
- **No matching wheel is available:** check the Python version, platform, and
  architecture on the native dependency's PyPI page. PassPattern does not compile it
  locally.
- **An API compatibility error appears:** use a supported `passtext-native` 0.1.x
  release.

For a first analysis, continue to the [quickstart](quickstart.md).
