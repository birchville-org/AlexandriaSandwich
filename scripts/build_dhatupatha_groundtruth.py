#!/usr/bin/env python3
"""
AlexandriaSandwich — scripts/build_dhatupatha_groundtruth.py

Fetches canonical Pāṇinīya Dhātupāṭha data (from ashtadhyayi-com/data repository),
normalizes the entries across all 10 Gaṇas, adds IAST transliteration, and writes
a standardized, canonical reference database to data/dhatupatha_canonical.json.
"""
from __future__ import annotations

import json
import ssl
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

GANA_MAP = {
    1: ("भ्वादिः", "Bhvādi"),
    2: ("अदादिः", "Adādi"),
    3: ("जुहोत्यादिः", "Juhotyādi"),
    4: ("दिवादिः", "Divādi"),
    5: ("स्वादिः", "Svādi"),
    6: ("तुदादिः", "Tudādi"),
    7: ("रुधादिः", "Rudhādi"),
    8: ("तनादिः", "Tanādi"),
    9: ("क्र्यादिः", "Kryādi"),
    10: ("चुरादिः", "Curādi"),
}

PADA_MAP = {
    "P": "parasmaipada",
    "A": "ātmanepada",
    "U": "ubhayapada",
}

SET_MAP = {
    "S": "seṭ",
    "A": "aniṭ",
    "V": "veṭ",
}

KARMA_MAP = {
    "A": "akarmaka",
    "S": "sakarmaka",
    "D": "dvikarmaka",
}

DEV_TO_IAST = {
    "अ": "a", "आ": "ā", "इ": "i", "ई": "ī", "उ": "u", "ऊ": "ū", "ऋ": "ṛ", "ॠ": "ṝ", "ऌ": "ḷ", "ॡ": "ḹ",
    "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au", "ं": "ṃ", "ः": "ḥ",
    "क": "ka", "ख": "kha", "ग": "ga", "घ": "gha", "ङ": "ṅa",
    "च": "ca", "छ": "cha", "ज": "ja", "झ": "jha", "ञ": "ña",
    "ट": "ṭa", "ठ": "ṭha", "ड": "ḍa", "ढ": "ḍha", "ण": "ṇa",
    "त": "ta", "थ": "tha", "द": "da", "ध": "dha", "न": "na",
    "प": "pa", "फ": "pha", "ब": "ba", "भ": "bha", "म": "ma",
    "य": "ya", "र": "ra", "ल": "la", "व": "va",
    "श": "śa", "ष": "ṣa", "स": "sa", "ह": "ha",
    "ा": "ā", "ि": "i", "ी": "ī", "ु": "u", "ू": "ū", "ृ": "ṛ", "ॄ": "ṝ", "ॢ": "ḷ", "ॣ": "ḹ",
    "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "्": "", "ऽ": "'", "ँ": "m̐"
}


def deva_to_iast(text: str) -> str:
    """Deterministic Devanāgarī to IAST transliteration."""
    res: List[str] = []
    i = 0
    chars = list(text)
    consonants = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह"
    vowels = "ािीुूृॄॢॣेैोौ"
    nasals = "ंःँ"

    while i < len(chars):
        c = chars[i]
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if c in consonants:
            base = DEV_TO_IAST[c][:-1]
            if nxt == "्":
                res.append(base)
                i += 2
                continue
            elif nxt and nxt in vowels:
                res.append(base + DEV_TO_IAST.get(nxt, ""))
                i += 2
                continue
            elif nxt and nxt in nasals:
                res.append(base + "a" + DEV_TO_IAST.get(nxt, ""))
                i += 2
                continue
            else:
                res.append(base + "a")
                i += 1
                continue
        res.append(DEV_TO_IAST.get(c, c))
        i += 1
    return "".join(res)


def fetch_raw_data() -> List[Dict[str, Any]]:
    url = "https://raw.githubusercontent.com/ashtadhyayi-com/data/master/dhatu/data.txt"
    print(f"Fetching canonical data from {url}...", file=sys.stderr)
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={"User-Agent": "AlexandriaSandwich/1.2"})
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
        raw_text = resp.read().decode("utf-8")
    parsed = json.loads(raw_text)
    return parsed.get("data", [])


def normalize_dhatupatha(raw_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    for item in raw_entries:
        baseindex = item.get("baseindex", "").strip()
        dhatu = item.get("dhatu", "").strip()
        aupadeshik = item.get("aupadeshik", "").strip() or dhatu
        gana_str = item.get("gana", "1").strip()
        try:
            gana = int(gana_str)
        except ValueError:
            gana = 1

        gana_name, gana_iast = GANA_MAP.get(gana, (f"गणः {gana}", f"Gaṇa {gana}"))
        pada = PADA_MAP.get(item.get("pada", ""), item.get("pada", ""))
        settva = SET_MAP.get(item.get("settva", ""), item.get("settva", ""))
        karma = KARMA_MAP.get(item.get("karma", ""), item.get("karma", ""))
        artha = item.get("artha", "").strip()
        artha_english = item.get("artha_english", "").strip()
        artha_hindi = item.get("artha_hindi", "").strip()
        tags = item.get("tags", "").strip()
        sk_sutra = item.get("sk_sutra", "").strip()
        note = item.get("dhaturoopnandini_note", "").strip()

        iast_dhatu = deva_to_iast(dhatu)
        iast_aupadeshik = deva_to_iast(aupadeshik)
        iast_artha = deva_to_iast(artha)

        norm_entry = {
            "id": baseindex,
            "gana": gana,
            "gana_name": gana_name,
            "gana_iast": gana_iast,
            "dhatu": dhatu,
            "aupadeshik": aupadeshik,
            "iast_dhatu": iast_dhatu,
            "iast_aupadeshik": iast_aupadeshik,
            "pada": pada,
            "settva": settva,
            "karma": karma,
            "artha": artha,
            "iast_artha": iast_artha,
            "artha_english": artha_english,
            "artha_hindi": artha_hindi,
            "tags": tags,
            "sk_sutra": sk_sutra,
            "commentary_note": note,
        }
        normalized.append(norm_entry)

    # Sort deterministically by baseindex (e.g. 01.0001)
    normalized.sort(key=lambda x: x["id"])
    return normalized


def main():
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data"
    out_file = data_dir / "dhatupatha_canonical.json"

    raw_items = fetch_raw_data()
    print(f"Received {len(raw_items)} raw entries.", file=sys.stderr)

    normalized_items = normalize_dhatupatha(raw_items)
    print(f"Normalized {len(normalized_items)} canonical Dhātus.", file=sys.stderr)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(normalized_items, f, ensure_ascii=False, indent=2)

    file_size_kb = out_file.stat().st_size / 1024
    print(f"Successfully wrote {out_file} ({file_size_kb:.1f} KB).", file=sys.stderr)


if __name__ == "__main__":
    main()
