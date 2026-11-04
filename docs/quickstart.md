# Quickstart

All examples use synthetic data. A compatible `passtext-native` 0.1.x binary wheel
from public PyPI is required to call `analyze()`. Install it into the same environment:

```powershell
python -m pip install --only-binary=:all: "passtext-native>=0.1.0,<0.2.0"
```

Without the extension, analysis raises `NativeExtensionUnavailableError`.

## Interactive analyzer

From the repository root, install the development dependencies and run:

```powershell
python -m pip install -e ".[dev]"
python .\scripts\analyze_password.py
```

Enter the password at the hidden prompt. The script runs all structural and
contextual detectors and prints every match's detector, category, pattern type,
processed-text span, and evidence. It does not print or save the password or matched
text. Spans are zero-based, half-open Unicode code-point offsets; with NFC
normalization they refer to normalized text. To enable the three dictionary
detectors, supply a JSON file containing ranked entries:

```json
{
  "entries": [
    {"word": "example", "rank": 1},
    {"word": "garden", "rank": 2, "source_id": "sample"}
  ]
}
```

```powershell
python .\scripts\analyze_password.py --dictionary .\my-words.json
```

Use only a private lexicon you are authorized to use. The tool requires an
interactive terminal and does not accept a password as a command-line argument or
from a pipe, to reduce accidental exposure.

## Structural patterns

```python
from passpattern import PassPatternEngine
from passpattern.structural import default_structural_detectors

engine = PassPatternEngine(default_structural_detectors())
result = engine.analyze("aaa1212abc")
for match in result.matches:
    print(match.detector_id, match.pattern_type, match.start_index, match.end_index)
```

## Dictionary words

PassPattern does not bundle an authoritative password dictionary; supply entries
appropriate to your application.

```python
from passpattern import PassPatternEngine
from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    DictionaryWordDetector,
)

lexicon = DictionaryLexicon(
    (
        DictionaryEntry("example", rank=1, source_id="synthetic"),
        DictionaryEntry("garden", rank=2, source_id="synthetic"),
    )
)
engine = PassPatternEngine((DictionaryWordDetector(lexicon),))
result = engine.analyze("myExample42")
```

Dictionary matching accepts case-insensitive ASCII variants; exact case can be
reported as numeric/boolean evidence. Dictionary normalization must agree with the
engine configuration.

For a supplied word followed by digits or punctuation, use the separate compound
detector:

```python
from passpattern import PassPatternEngine
from passpattern.dictionary import (
    DictionaryCompoundDetector,
    DictionaryEntry,
    DictionaryLexicon,
)

lexicon = DictionaryLexicon((DictionaryEntry("example", rank=1),))
engine = PassPatternEngine((DictionaryCompoundDetector(lexicon),))
result = engine.analyze("example-2026!")
```

The compound detector is opt-in and reports the full word-plus-suffix span. It requires
a word boundary on either side and uses a bounded ASCII suffix; see the
[detector guide](detectors.md) for its limits.

## Dictionary transformations

```python
from passpattern import PassPatternEngine
from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    LeetspeakDetector,
    ReversedWordDetector,
)

lexicon = DictionaryLexicon((DictionaryEntry("garden", rank=1),))
engine = PassPatternEngine((ReversedWordDetector(lexicon), LeetspeakDetector(lexicon)))
result = engine.analyze("nedrag g@rden")
```

Leetspeak substitutions are bounded and length-preserving. Both transformation
detectors enforce explicit work limits and raise `DictionarySearchLimitError` rather
than silently dropping work when a configured limit is exceeded.

## Contextual patterns

```python
from passpattern import PassPatternEngine
from passpattern.contextual import default_contextual_detectors

engine = PassPatternEngine(default_contextual_detectors())
result = engine.analyze("2026-11-02 Qwerty")
```

Contextual detectors recognize selected date formats, four-digit years, and US QWERTY
walks. Recognition is not a strength or guessability score.

## Combined registration

```python
from passpattern import PassPatternEngine
from passpattern.contextual import default_contextual_detectors
from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    DictionaryWordDetector,
    LeetspeakDetector,
    ReversedWordDetector,
)
from passpattern.structural import default_structural_detectors

lexicon = DictionaryLexicon((DictionaryEntry("garden", rank=1),))
detectors = (
    *default_structural_detectors(),
    DictionaryWordDetector(lexicon),
    ReversedWordDetector(lexicon),
    LeetspeakDetector(lexicon),
    *default_contextual_detectors(),
)
engine = PassPatternEngine(detectors)
result = engine.analyze("g@rden2026")
```

Detector registration order controls execution, but output matches are sorted
deterministically. Overlapping matches from different detectors are preserved. Avoid
printing real passwords, complete input strings, or analysis output in production.
