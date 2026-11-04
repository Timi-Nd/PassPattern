"""Reusable lexicons and detectors for explicit dictionary word matching."""

from passpattern.dictionary.compound_detector import DictionaryCompoundDetector
from passpattern.dictionary.entries import DictionaryEntry
from passpattern.dictionary.leetspeak_detector import LeetspeakDetector
from passpattern.dictionary.lexicon import DictionaryLexicon, NormalizationMode
from passpattern.dictionary.matcher import DictionaryMatcher
from passpattern.dictionary.reversed_detector import ReversedWordDetector
from passpattern.dictionary.word_detector import DictionaryWordDetector

__all__ = [
    "DictionaryEntry",
    "DictionaryCompoundDetector",
    "DictionaryLexicon",
    "DictionaryMatcher",
    "DictionaryWordDetector",
    "LeetspeakDetector",
    "NormalizationMode",
    "ReversedWordDetector",
]
