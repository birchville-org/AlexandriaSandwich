#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/indic_normalizer.py

Normalizes Indic script text, transliteration, and manuscript apparatus notations:
- Transliteration between Devanāgarī and IAST (ISO 15919 / International Alphabet of Sanskrit Transliteration).
- Numeral conversion between Devanāgarī (०-९) and Arabic (0-9) digits.
- Apparatus notation expansion (e.g. पं० -> paṃ., ख० पु० -> kha. pu.).
- Punctuation normalization (daṇḍas, avagrahas, quotes).
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import Optional

try:
    from indic_transliteration import sanscript
except ImportError:
    sanscript = None

# Numeral translation tables
DEV_DIGITS = "०१२३४५६७८९"
ARABIC_DIGITS = "0123456789"
TO_ARABIC_TABLE = str.maketrans(DEV_DIGITS, ARABIC_DIGITS)
TO_DEV_TABLE = str.maketrans(ARABIC_DIGITS, DEV_DIGITS)


def to_arabic_numerals(text: str) -> str:
    """Converts Devanāgarī numerals (०-९) to Arabic numerals (0-9)."""
    return text.translate(TO_ARABIC_TABLE)


def to_deva_numerals(text: str) -> str:
    """Converts Arabic numerals (0-9) to Devanāgarī numerals (०-९)."""
    return text.translate(TO_DEV_TABLE)


def to_iast(text: str) -> str:
    """
    Transliterates Devanāgarī text to IAST with normalized anusvāra (ṃ).
    Preserves existing ASCII characters, quotes, and punctuation.
    """
    if sanscript is None:
        raise ImportError("indic_transliteration package is required for to_iast()")
    t = sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
    t = t.replace("ṁ", "ṃ")
    return t


def to_devanagari(text: str) -> str:
    """Transliterates IAST romanized text to Devanāgarī script."""
    if sanscript is None:
        raise ImportError("indic_transliteration package is required for to_devanagari()")
    return sanscript.transliterate(text, sanscript.IAST, sanscript.DEVANAGARI)


def normalize_apparatus_deva(text: str) -> str:
    """
    Normalizes typical Devanāgarī critical apparatus abbreviations.
    Standardizes abbreviation circles/dots: पं० -> पं., ख० पु० -> ख. पु.
    """
    t = text
    t = re.sub(r'पं[०.]', 'पं.', t)
    t = re.sub(r'ख[०.]\s*पु[०.]', 'ख. पु.', t)
    t = re.sub(r'क[०.]\s*पु[०.]', 'क. पु.', t)
    t = re.sub(r'ग[०.]\s*पु[०.]', 'ग. पु.', t)
    t = re.sub(r'पु[०.]', 'पु.', t)
    return t


def normalize_apparatus_iast(text: str) -> str:
    """
    Normalizes and transliterates a Devanāgarī apparatus line into IAST:
    - Resolves manuscript sigla (paṃ., kha. pu., ka. pu., etc.).
    - Translates numerals to Arabic digits.
    - Normalizes punctuation: daṇḍa (।) to period (.), double daṇḍa (॥) to //, avagraha (ऽ) to '.
    """
    t = normalize_apparatus_deva(text)
    t = re.sub(r'पं\.', 'paṃ. ', t)
    t = re.sub(r'ख\.\s*पु\.', 'kha. pu. ', t)
    t = re.sub(r'क\.\s*पु\.', 'ka. pu. ', t)
    t = re.sub(r'ग\.\s*पु\.', 'ga. pu. ', t)
    t = re.sub(r'पु\.', 'pu. ', t)
    
    res = to_iast(t)
    res = res.translate(TO_ARABIC_TABLE)
    res = res.replace("||", "//")
    res = res.replace("|", ".")
    res = res.replace("।", ".")
    res = res.replace("॥", "//")
    res = res.replace("ऽ", "'")
    res = re.sub(r" +", " ", res)
    return res.strip()


def main():
    parser = argparse.ArgumentParser(description="Indic text and transliteration normalizer")
    parser.add_argument("text", nargs="?", help="Text to normalize (or read from stdin)")
    parser.add_argument("--to-iast", action="store_true", help="Transliterate to IAST")
    parser.add_argument("--to-deva", action="store_true", help="Transliterate to Devanagari")
    parser.add_argument("--to-arabic-digits", action="store_true", help="Convert Devanagari digits to Arabic")
    parser.add_argument("--to-deva-digits", action="store_true", help="Convert Arabic digits to Devanagari")
    parser.add_argument("--apparatus", action="store_true", help="Normalize apparatus entry to IAST")
    args = parser.parse_args()

    content = args.text or sys.stdin.read().strip()
    if not content:
        parser.print_help()
        sys.exit(1)

    if args.apparatus:
        print(normalize_apparatus_iast(content))
    elif args.to_iast:
        print(to_iast(content))
    elif args.to_deva:
        print(to_devanagari(content))
    elif args.to_arabic_digits:
        print(to_arabic_numerals(content))
    elif args.to_deva_digits:
        print(to_deva_numerals(content))
    else:
        # Default: demonstrate IAST transliteration and apparatus
        print("IAST:", to_iast(content))
        print("Apparatus:", normalize_apparatus_iast(content))


if __name__ == "__main__":
    main()
