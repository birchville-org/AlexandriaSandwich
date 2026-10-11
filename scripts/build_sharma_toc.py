#!/usr/bin/env python3
"""
scripts/build_sharma_toc.py

Comprehensive TOC injection for Rama Nath Sharma:
"The Astādhyāyī of Pāṇini" (All Six Volumes)
Total: 3907 pages.

Covers:
- Volume 1: Introduction to the Astadhyayi as a Grammatical Device (11 Chapters, Indices)
- Volume 2: Adhyaya 1 (Padas 1.1, 1.2, 1.3, 1.4, Sivasutras, Appendix, Indices)
- Volume 3: Adhyayas 2 & 3 (Padas 2.1-2.4, 3.1-3.4, Appendix, Indices)
- Volume 4: Adhyayas 4 & 5 (Padas 4.1-4.4, 5.1-5.4, Appendix, Indices)
- Volume 5: Adhyaya 6 (Padas 6.1-6.4, Appendix, Indices)
- Volume 6: Adhyayas 7 & 8 (Padas 7.1-7.4, 8.1-8.4, Appendix, Indices)
"""

import sys
import re
from pathlib import Path
import fitz  # PyMuPDF


def find_sutra_page(doc, start_page, end_page, sutra_id, header_hint=""):
    """
    Finds the first page where `sutra_id` (e.g. '1.2.1') is introduced as a main sutra entry.
    Sutra entries typically appear as 'X.Y.Z <Devanagari>' or 'X.Y.Z\n<Devanagari>'.
    """
    pattern_strict = re.compile(rf"(?:^|\n)\s*{re.escape(sutra_id)}\s*[\u0900-\u097F\w]", re.MULTILINE)
    pattern_fallback = re.compile(rf"(?:^|\n)\s*{re.escape(sutra_id)}\b", re.MULTILINE)

    for p in range(start_page - 1, end_page):
        txt = doc[p].get_text()
        if pattern_strict.search(txt):
            return p + 1
    for p in range(start_page - 1, end_page):
        txt = doc[p].get_text()
        if pattern_fallback.search(txt):
            return p + 1
    return None


def find_heading_page(doc, start_page, end_page, heading_pattern, max_lines=15):
    """Finds the first page where a heading matches in the top N lines."""
    rgx = re.compile(heading_pattern, re.IGNORECASE)
    for p in range(start_page - 1, end_page):
        lines = [l.strip() for l in doc[p].get_text().splitlines() if l.strip()][:max_lines]
        combined = "\n".join(lines)
        if rgx.search(combined):
            return p + 1
    return None


def generate_toc(doc):
    toc = []

    # =========================================================================
    # VOLUME 1: Pages 1 - 262
    # =========================================================================
    v1_start = 1
    toc.append([1, "Volume I: Introduction to the Aṣṭādhyāyī as a Grammatical Device", 1])
    toc.append([2, "Title & Front Matter", 1])
    
    p = find_heading_page(doc, 5, 10, r"Contents")
    if p: toc.append([2, "Contents", p])
    
    p = find_heading_page(doc, 7, 10, r"Preface to the Second Edition")
    if p: toc.append([2, "Preface to the Second Edition", p])
    
    p = find_heading_page(doc, 8, 11, r"Preface to the First Edition")
    if p: toc.append([2, "Preface to the First Edition", p])
    
    p = find_heading_page(doc, 10, 13, r"Abbreviations")
    if not p: p = 11
    toc.append([2, "Abbreviations", p])

    v1_chapters = [
        ("Chapter 1: Pāṇini and the Pāṇinīyas", 11, 15, r"Panini and the Paniniyas", 12),
        ("Chapter 2: The Aṣṭādhyāyī and its Related Texts", 35, 50, r"The Astadhyayi and its Related Texts", 43),
        ("Chapter 3: Grammar and Rule", 45, 60, r"Grammar and Rule", 53),
        ("Chapter 4: Domain, Recurrence and Reference", 65, 80, r"Domain, Recurrence and Reference", 71),
        ("Chapter 5: The Structure of the Aṣṭādhyāyī", 80, 95, r"The Structure of the Astadhyay", 85),
        ("Chapter 6: Types of Rules", 95, 110, r"Types of Rules", 100),
        ("Chapter 7: Saṃjñās and Paribhāṣās", 125, 140, r"Samjnas and Paribhasas", 132),
        ("Chapter 8: Some Additional Paribhāṣās", 135, 145, r"Some Additional Paribh", 138),
        ("Chapter 9: Kāraka and Vibhakti", 145, 160, r"K[aā]raka and Vibhakti", 152),
        ("Chapter 10: Derivational System", 165, 185, r"Derivational System", 176),
        ("Chapter 11: Derivation of Compounds", 185, 205, r"Derivation of Compounds", 198),
        ("Bibliography", 215, 230, r"Bibliography", 224),
        ("Index of Sūtras", 225, 240, r"Index of S[uū]tras", 232),
        ("Index of Terms", 250, 262, r"Index of Terms", 259),
    ]

    for title, s, e, pat, default_p in v1_chapters:
        pg = find_heading_page(doc, s, e, pat) or default_p
        toc.append([2, title, pg])

    # =========================================================================
    # VOLUME 2: Pages 263 - 819 (Adhyāya 1)
    # =========================================================================
    toc.append([1, "Volume II: English Translation of Adhyāya One", 263])
    toc.append([2, "Title & Front Matter", 263])
    
    p = find_heading_page(doc, 265, 272, r"Contents")
    if p: toc.append([2, "Contents", p])
    
    p = find_heading_page(doc, 268, 274, r"Preface")
    if p: toc.append([2, "Preface", p])
    
    p = find_heading_page(doc, 273, 277, r"Abbreviations") or 274
    toc.append([2, "Abbreviations", p])
    
    p = find_heading_page(doc, 276, 280, r"Sivas[uū]tra") or 278
    toc.append([2, "Śivasūtra", p])

    toc.append([2, "Adhyāya One", 280])
    
    # Pādas in Adhyāya 1
    p1_1 = find_sutra_page(doc, 279, 285, "1.1.1") or 280
    toc.append([3, "Pāda 1.1 (Sūtras 1.1.1 – 1.1.75)", p1_1])
    
    p1_2 = find_sutra_page(doc, 345, 355, "1.2.1") or 350
    toc.append([3, "Pāda 1.2 (Sūtras 1.2.1 – 1.2.73)", p1_2])
    
    p1_3 = find_sutra_page(doc, 410, 420, "1.3.1") or 414
    toc.append([3, "Pāda 1.3 (Sūtras 1.3.1 – 1.3.93)", p1_3])
    
    p1_4 = find_sutra_page(doc, 470, 485, "1.4.1") or 478
    toc.append([3, "Pāda 1.4 (Sūtras 1.4.1 – 1.4.110)", p1_4])

    # Appendix & Indices Vol 2
    p_app = find_heading_page(doc, 580, 600, r"APPENDIX") or 589
    toc.append([2, "Appendix: Derivational History of Examples", p_app])
    p_intro = find_heading_page(doc, 585, 600, r"Introductory Remarks") or p_app
    toc.append([3, "Introductory Remarks", p_intro])
    p_deriv = find_heading_page(doc, 590, 610, r"Derivational History") or 595
    toc.append([3, "Derivational History of Examples", p_deriv])
    
    p_bib = find_heading_page(doc, 795, 805, r"Bibliography") or 800
    toc.append([2, "Bibliography", p_bib])
    
    p_ind_d = find_heading_page(doc, 800, 810, r"Index of Derivations") or 804
    toc.append([2, "Index of Derivations", p_ind_d])
    
    p_ind_t = find_heading_page(doc, 810, 818, r"Index of Terms") or 812
    toc.append([2, "Index of Terms", p_ind_t])
    
    p_ind_s = find_heading_page(doc, 814, 820, r"Index of S[uū]tras") or 816
    toc.append([2, "Index of Sūtras", p_ind_s])

    # =========================================================================
    # VOLUME 3: Pages 820 - 1648 (Adhyāyas 2 & 3)
    # =========================================================================
    toc.append([1, "Volume III: English Translation of Adhyāyas Two and Three", 820])
    toc.append([2, "Title & Front Matter", 820])
    
    p = find_heading_page(doc, 822, 827, r"Contents") or 825
    toc.append([2, "Contents", p])
    
    p = find_heading_page(doc, 824, 828, r"Preface") or 826
    toc.append([2, "Preface", p])
    
    p = find_heading_page(doc, 827, 831, r"Abbreviations") or 828
    toc.append([2, "Abbreviations", p])

    # Adhyāya Two
    p2_1 = find_sutra_page(doc, 828, 835, "2.1.1") or 830
    toc.append([2, "Adhyāya Two", p2_1])
    toc.append([3, "Pāda 2.1 (Sūtras 2.1.1 – 2.1.72)", p2_1])
    
    p2_2 = find_sutra_page(doc, 890, 905, "2.2.1") or 896
    toc.append([3, "Pāda 2.2 (Sūtras 2.2.1 – 2.2.38)", p2_2])
    
    p2_3 = find_sutra_page(doc, 930, 950, "2.3.1") or 941
    toc.append([3, "Pāda 2.3 (Sūtras 2.3.1 – 2.3.73)", p2_3])
    
    p2_4 = find_sutra_page(doc, 1000, 1020, "2.4.1") or 1009
    toc.append([3, "Pāda 2.4 (Sūtras 2.4.1 – 2.4.85)", p2_4])

    # Adhyāya Three
    p3_1 = find_sutra_page(doc, 1050, 1070, "3.1.1") or 1060
    toc.append([2, "Adhyāya Three", p3_1])
    toc.append([3, "Pāda 3.1 (Sūtras 3.1.1 – 3.1.150)", p3_1])
    
    p3_2 = find_sutra_page(doc, 1180, 1205, "3.2.1") or 1195
    toc.append([3, "Pāda 3.2 (Sūtras 3.2.1 – 3.2.188)", p3_2])
    
    p3_3 = find_sutra_page(doc, 1340, 1365, "3.3.1") or 1354
    toc.append([3, "Pāda 3.3 (Sūtras 3.3.1 – 3.3.176)", p3_3])
    
    p3_4 = find_sutra_page(doc, 1445, 1470, "3.4.1") or 1459
    toc.append([3, "Pāda 3.4 (Sūtras 3.4.1 – 3.4.117)", p3_4])

    # Appendix & Indices Vol 3
    p_app3 = find_heading_page(doc, 1490, 1515, r"APPENDIX") or 1502
    toc.append([2, "Appendix: Derivational History of Examples", p_app3])
    p_intro3 = find_heading_page(doc, 1495, 1515, r"Introductory Remarks") or p_app3
    toc.append([3, "Introductory Remarks", p_intro3])
    p_deriv3 = find_heading_page(doc, 1500, 1520, r"Derivational History of Examples") or (p_app3 + 5)
    toc.append([3, "Derivational History of Examples", p_deriv3])
    
    p_bib3 = find_heading_page(doc, 1610, 1625, r"Bibliography") or 1618
    toc.append([2, "Bibliography", p_bib3])
    
    p_ind_d3 = find_heading_page(doc, 1618, 1630, r"Index of Derivations") or 1621
    toc.append([2, "Index of Derivations", p_ind_d3])
    
    p_ind_t3 = find_heading_page(doc, 1628, 1640, r"Index of Terms") or 1632
    toc.append([2, "Index of Terms", p_ind_t3])
    
    p_ind_s3 = find_heading_page(doc, 1635, 1648, r"Index of S[uū]tras") or 1639
    toc.append([2, "Index of Sūtras", p_ind_s3])

    # =========================================================================
    # VOLUME 4: Pages 1649 - 2465 (Adhyāyas 4 & 5)
    # =========================================================================
    toc.append([1, "Volume IV: English Translation of Adhyāyas Four and Five", 1649])
    toc.append([2, "Title & Front Matter", 1649])
    
    p = find_heading_page(doc, 1652, 1657, r"Contents") or 1654
    toc.append([2, "Contents", p])
    
    p = find_heading_page(doc, 1654, 1658, r"Preface") or 1655
    toc.append([2, "Preface", p])
    
    p = find_heading_page(doc, 1656, 1660, r"Abbreviations") or 1657
    toc.append([2, "Abbreviations", p])

    # Adhyāya Four
    p4_1 = find_sutra_page(doc, 1658, 1665, "4.1.1") or 1659
    toc.append([2, "Adhyāya Four", p4_1])
    toc.append([3, "Pāda 4.1 (Sūtras 4.1.1 – 4.1.178)", p4_1])
    
    p4_2 = find_sutra_page(doc, 1800, 1820, "4.2.1") or 1808
    toc.append([3, "Pāda 4.2 (Sūtras 4.2.1 – 4.2.145)", p4_2])
    
    p4_3 = find_sutra_page(doc, 1910, 1930, "4.3.1") or 1920
    toc.append([3, "Pāda 4.3 (Sūtras 4.3.1 – 4.3.168)", p4_3])
    
    p4_4 = find_sutra_page(doc, 2030, 2055, "4.4.1") or 2045
    toc.append([3, "Pāda 4.4 (Sūtras 4.4.1 – 4.4.144)", p4_4])

    # Adhyāya Five
    p5_1 = find_sutra_page(doc, 2080, 2105, "5.1.1") or 2088
    toc.append([2, "Adhyāya Five", p5_1])
    toc.append([3, "Pāda 5.1 (Sūtras 5.1.1 – 5.1.136)", p5_1])
    
    p5_2 = find_sutra_page(doc, 2170, 2195, "5.2.1") or 2182
    toc.append([3, "Pāda 5.2 (Sūtras 5.2.1 – 5.2.140)", p5_2])
    
    p5_3 = find_sutra_page(doc, 2270, 2295, "5.3.1") or 2283
    toc.append([3, "Pāda 5.3 (Sūtras 5.3.1 – 5.3.119)", p5_3])
    
    p5_4 = find_sutra_page(doc, 2360, 2385, "5.4.1") or 2374
    toc.append([3, "Pāda 5.4 (Sūtras 5.4.1 – 5.4.160)", p5_4])

    # Appendix & Indices Vol 4
    p_app4 = find_heading_page(doc, 2415, 2435, r"APPENDIX") or 2422
    toc.append([2, "Appendix: Derivational History of Examples", p_app4])
    
    p_bib4 = find_heading_page(doc, 2440, 2455, r"Bibliography") or 2450
    toc.append([2, "Bibliography", p_bib4])
    
    p_ind_d4 = find_heading_page(doc, 2448, 2458, r"Index of Derivations") or 2452
    toc.append([2, "Index of Derivations", p_ind_d4])
    
    p_ind_t4 = find_heading_page(doc, 2452, 2462, r"Index of Terms") or 2455
    toc.append([2, "Index of Terms", p_ind_t4])
    
    p_ind_s4 = find_heading_page(doc, 2456, 2465, r"Index of S[uū]tras") or 2459
    toc.append([2, "Index of Sūtras", p_ind_s4])

    # =========================================================================
    # VOLUME 5: Pages 2466 - 3076 (Adhyāya 6)
    # =========================================================================
    toc.append([1, "Volume V: English Translation of Adhyāya Six", 2466])
    toc.append([2, "Title & Front Matter", 2466])
    
    p = find_heading_page(doc, 2470, 2475, r"Contents") or 2472
    toc.append([2, "Contents", p])
    
    p = find_heading_page(doc, 2472, 2476, r"Preface") or 2473
    toc.append([2, "Preface", p])
    
    p = find_heading_page(doc, 2474, 2478, r"Abbreviations") or 2475
    toc.append([2, "Abbreviations", p])

    # Adhyāya Six
    p6_1 = find_sutra_page(doc, 2475, 2482, "6.1.1") or 2477
    toc.append([2, "Adhyāya Six", p6_1])
    toc.append([3, "Pāda 6.1 (Sūtras 6.1.1 – 6.1.223)", p6_1])
    
    p6_2 = find_sutra_page(doc, 2640, 2665, "6.2.1") or 2652
    toc.append([3, "Pāda 6.2 (Sūtras 6.2.1 – 6.2.199)", p6_2])
    
    p6_3 = find_sutra_page(doc, 2760, 2785, "6.3.1") or 2772
    toc.append([3, "Pāda 6.3 (Sūtras 6.3.1 – 6.3.139)", p6_3])
    
    p6_4 = find_sutra_page(doc, 2860, 2885, "6.4.1") or 2872
    toc.append([3, "Pāda 6.4 (Sūtras 6.4.1 – 6.4.175)", p6_4])

    # Appendix & Indices Vol 5
    p_app5 = find_heading_page(doc, 3030, 3050, r"APPENDIX") or 3038
    toc.append([2, "Appendix: Derivational History of Examples", p_app5])
    
    p_bib5 = find_heading_page(doc, 3050, 3060, r"Bibliography") or 3053
    toc.append([2, "Bibliography", p_bib5])
    
    p_ind_d5 = find_heading_page(doc, 3054, 3064, r"Index of Derivations") or 3056
    toc.append([2, "Index of Derivations", p_ind_d5])
    
    p_ind_t5 = find_heading_page(doc, 3056, 3068, r"Index of Terms") or 3059
    toc.append([2, "Index of Terms", p_ind_t5])
    
    p_ind_s5 = find_heading_page(doc, 3062, 3076, r"Index of S[uū]tras") or 3065
    toc.append([2, "Index of Sūtras", p_ind_s5])

    # =========================================================================
    # VOLUME 6: Pages 3077 - 3907 (Adhyāyas 7 & 8)
    # =========================================================================
    toc.append([1, "Volume VI: English Translation of Adhyāyas Seven and Eight", 3077])
    toc.append([2, "Title & Front Matter", 3077])
    
    p = find_heading_page(doc, 3080, 3085, r"Contents") or 3083
    toc.append([2, "Contents", p])
    
    p = find_heading_page(doc, 3082, 3086, r"Preface") or 3084
    toc.append([2, "Preface", p])
    
    p = find_heading_page(doc, 3085, 3090, r"Abbreviations") or 3087
    toc.append([2, "Abbreviations", p])

    # Adhyāya Seven
    p7_1 = find_sutra_page(doc, 3087, 3093, "7.1.1") or 3089
    toc.append([2, "Adhyāya Seven", p7_1])
    toc.append([3, "Pāda 7.1 (Sūtras 7.1.1 – 7.1.103)", p7_1])
    
    p7_2 = find_sutra_page(doc, 3215, 3240, "7.2.1") or 3228
    toc.append([3, "Pāda 7.2 (Sūtras 7.2.1 – 7.2.118)", p7_2])
    
    p7_3 = find_sutra_page(doc, 3340, 3365, "7.3.1") or 3352
    toc.append([3, "Pāda 7.3 (Sūtras 7.3.1 – 7.3.120)", p7_3])
    
    p7_4 = find_sutra_page(doc, 3450, 3475, "7.4.1") or 3462
    toc.append([3, "Pāda 7.4 (Sūtras 7.4.1 – 7.4.97)", p7_4])

    # Adhyāya Eight (Sapādasaptādhyāyī + Tripādī)
    p8_1 = find_sutra_page(doc, 3510, 3535, "8.1.1") or 3522
    toc.append([2, "Adhyāya Eight", p8_1])
    toc.append([3, "Pāda 8.1 (Sūtras 8.1.1 – 8.1.74)", p8_1])
    
    p8_2 = find_sutra_page(doc, 3585, 3610, "8.2.1") or 3598
    toc.append([3, "Pāda 8.2 (Sūtras 8.2.1 – 8.2.108; Start of Tripādī)", p8_2])
    
    p8_3 = find_sutra_page(doc, 3700, 3725, "8.3.1") or 3712
    toc.append([3, "Pāda 8.3 (Sūtras 8.3.1 – 8.3.119)", p8_3])
    
    p8_4 = find_sutra_page(doc, 3810, 3835, "8.4.1") or 3822
    toc.append([3, "Pāda 8.4 (Sūtras 8.4.1 – 8.4.68)", p8_4])

    # Indices Vol 6
    p_bib6 = find_heading_page(doc, 3870, 3885, r"Bibliography") or 3878
    toc.append([2, "Bibliography", p_bib6])
    
    p_ind_d6 = find_heading_page(doc, 3880, 3895, r"Index of Derivations") or 3886
    toc.append([2, "Index of Derivations", p_ind_d6])
    
    p_ind_t6 = find_heading_page(doc, 3885, 3900, r"Index of Terms") or 3889
    toc.append([2, "Index of Terms", p_ind_t6])
    
    p_ind_s6 = find_heading_page(doc, 3890, 3907, r"Index of S[uū]tras") or 3894
    toc.append([2, "Index of Sūtras", p_ind_s6])

    return toc


def main():
    pdf_path = Path("data/input/RamaNathSharma-TheAstadhyayiOfPanini-ALL SIX VOLUMES.pdf")
    if not pdf_path.is_file():
        print(f"Error: PDF not found at {pdf_path}", file=sys.stderr)
        return 1

    print(f"Opening PDF: {pdf_path} ({pdf_path.stat().st_size / 1e6:.1f} MB)...")
    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")

    print("Generating comprehensive TOC...")
    toc = generate_toc(doc)
    print(f"Generated {len(toc)} TOC outline entries.")

    for lvl, title, page_num in toc:
        indent = "  " * (lvl - 1)
        print(f"{indent}[L{lvl}] {title} -> Page {page_num}")

    # Set metadata
    meta = doc.metadata or {}
    meta["title"] = "The Aṣṭādhyāyī of Pāṇini (Volumes I–VI)"
    meta["author"] = "Rama Nath Sharma"
    meta["subject"] = "Complete 6-Volume Set of the Aṣṭādhyāyī of Pāṇini with English Translation, Analysis, and Sūtrapāṭha"
    meta["keywords"] = "Panini; Astadhyayi; Sanskrit Grammar; Rama Nath Sharma; Sutrapatha; Kasika; Linguistics"
    meta["creator"] = "AlexandriaSandwich / PyMuPDF TOC Injection"
    meta["producer"] = "PyMuPDF"
    doc.set_metadata(meta)

    # Set TOC
    doc.set_toc(toc)

    # Save to a temporary file in same directory then atomic replace
    temp_path = pdf_path.parent / f"_tmp_{pdf_path.name}"
    print(f"Saving PDF to {temp_path}...")
    doc.save(str(temp_path), deflate=True, garbage=3)
    doc.close()

    print(f"Replacing original file with {temp_path}...")
    temp_path.replace(pdf_path)
    print(f"Successfully injected TOC into {pdf_path} ({pdf_path.stat().st_size / 1e6:.1f} MB)!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
