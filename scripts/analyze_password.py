"""Interactively inspect PassPattern results without echoing or logging the input."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from passpattern import Detector, EngineConfig, PassPatternEngine
from passpattern.config import TextNormalization
from passpattern.contextual import default_contextual_detectors
from passpattern.dictionary import (
    DictionaryEntry,
    DictionaryLexicon,
    DictionaryWordDetector,
    LeetspeakDetector,
    ReversedWordDetector,
)
from passpattern.errors import PassPatternError
from passpattern.models import AnalysisResult
from passpattern.structural import default_structural_detectors


def load_dictionary(path: Path, normalization: TextNormalization) -> DictionaryLexicon:
    """Load a JSON array of ranked words without echoing its contents in errors."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        message = error.strerror or "file error"
        raise ValueError(f"Cannot read dictionary file: {message}.") from None
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Dictionary file is not valid JSON (line {error.lineno}, column {error.colno})."
        ) from None

    entries_data = data.get("entries") if isinstance(data, dict) else data
    if not isinstance(entries_data, list):
        raise ValueError(
            "Dictionary JSON must be an array of entries or an object with an entries array."
        )

    entries: list[DictionaryEntry] = []
    for index, item in enumerate(entries_data, start=1):
        if not isinstance(item, dict) or set(item) - {"word", "rank", "source_id"}:
            raise ValueError(
                f"Dictionary entry {index} must contain word, rank, and optional source_id."
            )
        if "word" not in item or "rank" not in item:
            raise ValueError(f"Dictionary entry {index} must contain word and rank.")
        try:
            entries.append(DictionaryEntry(**item))
        except (TypeError, ValueError):
            raise ValueError(f"Dictionary entry {index} has invalid values.") from None

    try:
        return DictionaryLexicon(entries, normalization=normalization)
    except (TypeError, ValueError):
        raise ValueError("Dictionary entries or normalization settings are invalid.") from None


def build_engine(
    normalization: TextNormalization,
    dictionary_path: Path | None = None,
) -> PassPatternEngine:
    """Create the built-in detector suite, adding dictionary detectors when requested."""
    detectors: tuple[Detector, ...] = (
        *default_structural_detectors(),
        *default_contextual_detectors(),
    )
    if dictionary_path is not None:
        lexicon = load_dictionary(dictionary_path, normalization)
        detectors += (
            DictionaryWordDetector(lexicon),
            ReversedWordDetector(lexicon),
            LeetspeakDetector(lexicon),
        )
    return PassPatternEngine(detectors, EngineConfig(normalization=normalization))


def print_results(result: AnalysisResult) -> None:
    """Print every match field while keeping the password and matched text private."""
    print(f"\nDetected {len(result.matches)} pattern(s).")
    if not result.matches:
        print("No patterns detected.")
        return

    for index, match in enumerate(result.matches, start=1):
        print(f"\n{index}. {match.pattern_type}")
        print(f"   Detector: {match.detector_id}")
        print(f"   Category: {match.category}")
        print(f"   Span:     [{match.start_index}, {match.end_index})")
        if match.evidence:
            evidence = ", ".join(f"{item.key.value}={item.value}" for item in match.evidence)
            print(f"   Evidence: {evidence}")
        else:
            print("   Evidence: none")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Interactively analyze one password with PassPattern. Input is hidden."
    )
    parser.add_argument(
        "--normalization",
        choices=("none", "nfc"),
        default="none",
        help="Text normalization mode (default: none). Match spans refer to processed text.",
    )
    parser.add_argument(
        "--dictionary",
        type=Path,
        metavar="JSON_FILE",
        help="Optional JSON lexicon; enables dictionary, reversed-word, and leetspeak detectors.",
    )
    args = parser.parse_args(argv)

    if not sys.stdin.isatty() or not sys.stderr.isatty():
        parser.error(
            "an interactive terminal is required so password input cannot be echoed or piped"
        )

    try:
        engine = build_engine(args.normalization, args.dictionary)
    except ValueError as error:
        parser.error(str(error))

    try:
        password = getpass.getpass("Password (input hidden): ")
    except (EOFError, KeyboardInterrupt):
        print("\nInput cancelled.", file=sys.stderr)
        return 130

    try:
        result = engine.analyze(password)
    except PassPatternError as error:
        print(f"Analysis failed: {error}", file=sys.stderr)
        return 1

    print_results(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
