# Quickstart

These examples use synthetic inputs. Install PassPattern from a checkout before
running them; see [Installation](installation.md). Analysis also requires a compatible
`passtext-native` wheel.

## Find an arithmetic sequence

You choose and register detectors. This example runs only the numeric detector:

```python
from passpattern import PassPatternEngine
from passpattern.structural import NumericSequenceDetector

engine = PassPatternEngine([NumericSequenceDetector()])
result = engine.analyze("2468")

for match in result.matches:
    values = [term.value for term in match.terms]
    print(
        f"{match.pattern_type} [{match.start_index}, {match.end_index}): "
        f"terms={values}, difference={match.parameter_numerator}"
    )
```

Expected output:

```text
arithmetic_progression [0, 4): terms=[2, 4, 6, 8], difference=2
```

The span `[0, 4)` means the match starts at code-point index 0 and ends before index
4. The terms explain how the detector interpreted the digits; the difference is an
exact integer. This result is not a strength score.

## Inspect more structural patterns

`default_structural_detectors()` registers repeated-character, repeated-substring,
numeric, and alphabetic detectors:

```python
from passpattern import PassPatternEngine
from passpattern.structural import default_structural_detectors

engine = PassPatternEngine(default_structural_detectors())
result = engine.analyze("aaa1212abc")
for match in result.matches:
    print(match.pattern_type, (match.start_index, match.end_index))
```

The engine sorts results by span and detector metadata. It keeps valid overlaps
instead of merging different pattern types.

## Try the interactive analyzer

From the repository root, run:

```powershell
python .\scripts\analyze_password.py
```

The analyzer asks for input through a hidden prompt and prints match types, spans,
and evidence. It requires an interactive terminal; it does not accept a password as a
command-line argument or through a pipe. Use synthetic inputs while learning the
output format.

The tool registers structural and contextual detectors by default. To enable its
dictionary detectors, create a JSON lexicon:

```json
{
  "entries": [
    {"word": "example", "rank": 1},
    {"word": "garden", "rank": 2, "source_id": "sample"}
  ]
}
```

Then pass the file path:

```powershell
python .\scripts\analyze_password.py --dictionary .\my-words.json
```

Use only a lexicon you are authorized to use. PassPattern does not bundle a password
list.

## Add a dictionary detector

You can supply a small lexicon directly in Python. This example reports the span of
`Example` in a synthetic input:

```python
from passpattern import PassPatternEngine
from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    DictionaryWordDetector,
)

lexicon = DictionaryLexicon((DictionaryEntry("example", rank=1),))
engine = PassPatternEngine((DictionaryWordDetector(lexicon),))
result = engine.analyze("myExample42")
print([(match.pattern_type, match.start_index, match.end_index) for match in result.matches])
```

Expected output:

```text
[('dictionary_word', 2, 9)]
```

Dictionary matching is opt-in because applications should choose entries appropriate
to their use case. See the [detector guide](detectors.md) for compound words,
reversed-word, and leetspeak detectors.

## Add contextual detectors

The contextual factory registers date, year, and default US QWERTY keyboard-walk
detectors:

```python
from passpattern import PassPatternEngine
from passpattern.contextual import default_contextual_detectors

engine = PassPatternEngine(default_contextual_detectors())
result = engine.analyze("2026-11-02 Qwerty")
print([(match.pattern_type, match.start_index, match.end_index) for match in result.matches])
```

Dates and years are recognized only within their documented ranges and formats.
Keyboard walks depend on the selected layout. None of these matches estimates
guessability.

For all date formats, numeric-family options, and safety limits, read the
[detector guide](detectors.md).
