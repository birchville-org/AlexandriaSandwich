#!/usr/bin/env python3
"""
scripts/inject_single_volume.py

Injects hierarchical TOC and metadata into individual volume PDFs (Volumes 1 to 6)
of Rama Nath Sharma: "The Astādhyāyī of Pāṇini".
"""

import os
import sys
import re
from pathlib import Path
import fitz  # PyMuPDF


def find_sutra_page(doc, start_page, end_page, sutra_id):
    pattern_strict = re.compile(rf"(?:^|\n)\s*{re.escape(sutra_id)}\s*[\u0900-\u097F\w]", re.MULTILINE)
    pattern_fallback = re.compile(rf"(?:^|\n)\s*{re.escape(sutra_id)}\b", re.MULTILINE)

    for p in range(start_page - 1, min(end_page, len(doc))):
        txt = doc[p].get_text()
        if pattern_strict.search(txt):
            return p + 1
    for p in range(start_page - 1, min(end_page, len(doc))):
        txt = doc[p].get_text()
        if pattern_fallback.search(txt):
            return p + 1
    return None


def find_heading_page(doc, start_page, end_page, heading_pattern, max_lines=15):
    rgx = re.compile(heading_pattern, re.IGNORECASE)
    for p in range(start_page - 1, min(end_page, len(doc))):
        lines = [l.strip() for l in doc[p].get_text().splitlines() if l.strip()][:max_lines]
        combined = "\n".join(lines)
        if rgx.search(combined):
            return p + 1
    return None


def get_volume_1_toc(doc):
    toc = [
        [1, "The Aṣṭādhyāyī of Pāṇini (Volume I: Introduction to the Aṣṭādhyāyī as a Grammatical Device)", 1],
        [2, "Title & Front Matter", 1],
    ]
    p = find_heading_page(doc, 5, 10, r"Contents")
    if p: toc.append([2, "Contents", p])
    p = find_heading_page(doc, 7, 10, r"Preface to the Second Edition")
    if p: toc.append([2, "Preface to the Second Edition", p])
    p = find_heading_page(doc, 8, 11, r"Preface to the First Edition")
    if p: toc.append([2, "Preface to the First Edition", p])
    p = find_heading_page(doc, 10, 13, r"Abbreviations") or 11
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
    return toc


def get_volume_2_toc(doc):
    toc = [
        [1, "The Aṣṭādhyāyī of Pāṇini (Volume II: English Translation of Adhyāya One)", 1],
        [2, "Title & Front Matter", 1],
    ]
    p = find_heading_page(doc, 3, 10, r"Contents") or 7
    toc.append([2, "Contents", p])
    p = find_heading_page(doc, 6, 12, r"Preface") or 7
    toc.append([2, "Preface", p])
    p = find_heading_page(doc, 11, 16, r"Abbreviations") or 13
    toc.append([2, "Abbreviations", p])
    p = find_heading_page(doc, 14, 18, r"Sivas[uū]tra") or 16
    toc.append([2, "Śivasūtra", p])

    p1_1 = find_sutra_page(doc, 16, 22, "1.1.1") or 18
    toc.append([2, "Adhyāya One", p1_1])
    toc.append([3, "Pāda 1.1 (Sūtras 1.1.1 – 1.1.75)", p1_1])
    p1_2 = find_sutra_page(doc, 80, 95, "1.2.1") or 88
    toc.append([3, "Pāda 1.2 (Sūtras 1.2.1 – 1.2.73)", p1_2])
    p1_3 = find_sutra_page(doc, 145, 165, "1.3.1") or 159
    toc.append([3, "Pāda 1.3 (Sūtras 1.3.1 – 1.3.93)", p1_3])
    p1_4 = find_sutra_page(doc, 205, 225, "1.4.1") or 215
    toc.append([3, "Pāda 1.4 (Sūtras 1.4.1 – 1.4.110)", p1_4])

    p_app = find_heading_page(doc, 315, 335, r"APPENDIX") or 327
    toc.append([2, "Appendix: Derivational History of Examples", p_app])
    p_intro = find_heading_page(doc, 320, 335, r"Introductory Remarks") or p_app
    toc.append([3, "Introductory Remarks", p_intro])
    p_deriv = find_heading_page(doc, 325, 340, r"Derivational History") or (p_app + 1)
    toc.append([3, "Derivational History of Examples", p_deriv])

    p_bib = find_heading_page(doc, 530, 545, r"Bibliography") or 538
    toc.append([2, "Bibliography", p_bib])
    p_ind_d = find_heading_page(doc, 538, 548, r"Index of Derivations") or 542
    toc.append([2, "Index of Derivations", p_ind_d])
    p_ind_t = find_heading_page(doc, 545, 554, r"Index of Terms") or 550
    toc.append([2, "Index of Terms", p_ind_t])
    p_ind_s = find_heading_page(doc, 550, 557, r"Index of S[uū]tras") or 554
    toc.append([2, "Index of Sūtras", p_ind_s])
    return toc


def get_volume_3_toc(doc):
    toc = [
        [1, "The Aṣṭādhyāyī of Pāṇini (Volume III: English Translation of Adhyāyas Two and Three)", 1],
        [2, "Title & Front Matter", 1],
    ]
    p = find_heading_page(doc, 3, 9, r"Contents") or 6
    toc.append([2, "Contents", p])
    p = find_heading_page(doc, 5, 10, r"Preface") or 6
    toc.append([2, "Preface", p])
    p = find_heading_page(doc, 8, 13, r"Abbreviations") or 9
    toc.append([2, "Abbreviations", p])

    p2_1 = find_sutra_page(doc, 10, 16, "2.1.1") or 12
    toc.append([2, "Adhyāya Two", p2_1])
    toc.append([3, "Pāda 2.1 (Sūtras 2.1.1 – 2.1.72)", p2_1])
    p2_2 = find_sutra_page(doc, 70, 85, "2.2.1") or 77
    toc.append([3, "Pāda 2.2 (Sūtras 2.2.1 – 2.2.38)", p2_2])
    p2_3 = find_sutra_page(doc, 110, 125, "2.3.1") or 115
    toc.append([3, "Pāda 2.3 (Sūtras 2.3.1 – 2.3.73)", p2_3])
    p2_4 = find_sutra_page(doc, 180, 195, "2.4.1") or 183
    toc.append([3, "Pāda 2.4 (Sūtras 2.4.1 – 2.4.85)", p2_4])

    p3_1 = find_sutra_page(doc, 235, 255, "3.1.1") or 241
    toc.append([2, "Adhyāya Three", p3_1])
    toc.append([3, "Pāda 3.1 (Sūtras 3.1.1 – 3.1.150)", p3_1])
    p3_2 = find_sutra_page(doc, 355, 375, "3.2.1") or 361
    toc.append([3, "Pāda 3.2 (Sūtras 3.2.1 – 3.2.188)", p3_2])
    p3_3 = find_sutra_page(doc, 535, 555, "3.3.1") or 543
    toc.append([3, "Pāda 3.3 (Sūtras 3.3.1 – 3.3.176)", p3_3])
    p3_4 = find_sutra_page(doc, 630, 650, "3.4.1") or 640
    toc.append([3, "Pāda 3.4 (Sūtras 3.4.1 – 3.4.117)", p3_4])

    p_app = find_heading_page(doc, 665, 685, r"APPENDIX") or 672
    toc.append([2, "Appendix: Derivational History of Examples", p_app])
    p_intro = find_heading_page(doc, 670, 685, r"Introductory Remarks") or p_app
    toc.append([3, "Introductory Remarks", p_intro])
    p_deriv = find_heading_page(doc, 675, 690, r"Derivational History") or (p_app + 5)
    toc.append([3, "Derivational History of Examples", p_deriv])

    p_bib = find_heading_page(doc, 785, 800, r"Bibliography") or 798
    toc.append([2, "Bibliography", p_bib])
    p_ind_d = find_heading_page(doc, 795, 810, r"Index of Derivations") or 801
    toc.append([2, "Index of Derivations", p_ind_d])
    p_ind_t = find_heading_page(doc, 805, 818, r"Index of Terms") or 812
    toc.append([2, "Index of Terms", p_ind_t])
    p_ind_s = find_heading_page(doc, 815, 829, r"Index of S[uū]tras") or 819
    toc.append([2, "Index of Sūtras", p_ind_s])
    return toc


def get_volume_4_toc(doc):
    toc = [
        [1, "The Aṣṭādhyāyī of Pāṇini (Volume IV: English Translation of Adhyāyas Four and Five)", 1],
        [2, "Title & Front Matter", 1],
    ]
    p = find_heading_page(doc, 3, 9, r"Contents") or 6
    toc.append([2, "Contents", p])
    p = find_heading_page(doc, 5, 10, r"Preface") or 6
    toc.append([2, "Preface", p])
    p = find_heading_page(doc, 8, 13, r"Abbreviations") or 10
    toc.append([2, "Abbreviations", p])

    p4_1 = find_sutra_page(doc, 10, 16, "4.1.1") or 11
    toc.append([2, "Adhyāya Four", p4_1])
    toc.append([3, "Pāda 4.1 (Sūtras 4.1.1 – 4.1.178)", p4_1])
    p4_2 = find_sutra_page(doc, 155, 170, "4.2.1") or 161
    toc.append([3, "Pāda 4.2 (Sūtras 4.2.1 – 4.2.145)", p4_2])
    p4_3 = find_sutra_page(doc, 255, 275, "4.3.1") or 264
    toc.append([3, "Pāda 4.3 (Sūtras 4.3.1 – 4.3.168)", p4_3])
    p4_4 = find_sutra_page(doc, 385, 405, "4.4.1") or 397
    toc.append([3, "Pāda 4.4 (Sūtras 4.4.1 – 4.4.144)", p4_4])

    p5_1 = find_sutra_page(doc, 430, 450, "5.1.1") or 439
    toc.append([2, "Adhyāya Five", p5_1])
    toc.append([3, "Pāda 5.1 (Sūtras 5.1.1 – 5.1.136)", p5_1])
    p5_2 = find_sutra_page(doc, 515, 535, "5.2.1") or 525
    toc.append([3, "Pāda 5.2 (Sūtras 5.2.1 – 5.2.140)", p5_2])
    p5_3 = find_sutra_page(doc, 625, 645, "5.3.1") or 635
    toc.append([3, "Pāda 5.3 (Sūtras 5.3.1 – 5.3.119)", p5_3])
    p5_4 = find_sutra_page(doc, 705, 725, "5.4.1") or 715
    toc.append([3, "Pāda 5.4 (Sūtras 5.4.1 – 5.4.160)", p5_4])

    p_app = find_heading_page(doc, 760, 780, r"APPENDIX") or 771
    toc.append([2, "Appendix: Derivational History of Examples", p_app])
    p_bib = find_heading_page(doc, 790, 805, r"Bibliography") or 800
    toc.append([2, "Bibliography", p_bib])
    p_ind_d = find_heading_page(doc, 795, 810, r"Index of Derivations") or 802
    toc.append([2, "Index of Derivations", p_ind_d])
    p_ind_t = find_heading_page(doc, 800, 812, r"Index of Terms") or 805
    toc.append([2, "Index of Terms", p_ind_t])
    p_ind_s = find_heading_page(doc, 805, 817, r"Index of S[uū]tras") or 809
    toc.append([2, "Index of Sūtras", p_ind_s])
    return toc


def get_volume_5_toc(doc):
    toc = [
        [1, "The Aṣṭādhyāyī of Pāṇini (Volume V: English Translation of Adhyāya Six)", 1],
        [2, "Title & Front Matter", 1],
    ]
    p = find_heading_page(doc, 3, 9, r"Contents") or 7
    toc.append([2, "Contents", p])
    p = find_heading_page(doc, 5, 10, r"Preface") or 7
    toc.append([2, "Preface", p])
    p = find_heading_page(doc, 8, 13, r"Abbreviations") or 11
    toc.append([2, "Abbreviations", p])

    p6_1 = find_sutra_page(doc, 10, 16, "6.1.1") or 12
    toc.append([2, "Adhyāya Six", p6_1])
    toc.append([3, "Pāda 6.1 (Sūtras 6.1.1 – 6.1.223)", p6_1])
    p6_2 = find_sutra_page(doc, 180, 195, "6.2.1") or 187
    toc.append([3, "Pāda 6.2 (Sūtras 6.2.1 – 6.2.199)", p6_2])
    p6_3 = find_sutra_page(doc, 300, 315, "6.3.1") or 307
    toc.append([3, "Pāda 6.3 (Sūtras 6.3.1 – 6.3.139)", p6_3])
    p6_4 = find_sutra_page(doc, 400, 415, "6.4.1") or 407
    toc.append([3, "Pāda 6.4 (Sūtras 6.4.1 – 6.4.175)", p6_4])

    p_app = find_heading_page(doc, 565, 580, r"APPENDIX") or 575
    toc.append([2, "Appendix: Derivational History of Examples", p_app])
    p_bib = find_heading_page(doc, 580, 595, r"Bibliography") or 591
    toc.append([2, "Bibliography", p_bib])
    p_ind_d = find_heading_page(doc, 588, 598, r"Index of Derivations") or 594
    toc.append([2, "Index of Derivations", p_ind_d])
    p_ind_t = find_heading_page(doc, 592, 602, r"Index of Terms") or 597
    toc.append([2, "Index of Terms", p_ind_t])
    p_ind_s = find_heading_page(doc, 598, 611, r"Index of S[uū]tras") or 603
    toc.append([2, "Index of Sūtras", p_ind_s])
    return toc


def get_volume_6_toc(doc):
    toc = [
        [1, "The Aṣṭādhyāyī of Pāṇini (Volume VI: English Translation of Adhyāyas Seven and Eight)", 1],
        [2, "Title & Front Matter", 1],
    ]
    p = find_heading_page(doc, 3, 9, r"Contents") or 7
    toc.append([2, "Contents", p])
    p = find_heading_page(doc, 5, 10, r"Preface") or 7
    toc.append([2, "Preface", p])
    p = find_heading_page(doc, 8, 14, r"Abbreviations") or 12
    toc.append([2, "Abbreviations", p])

    p7_1 = find_sutra_page(doc, 10, 16, "7.1.1") or 13
    toc.append([2, "Adhyāya Seven", p7_1])
    toc.append([3, "Pāda 7.1 (Sūtras 7.1.1 – 7.1.103)", p7_1])
    p7_2 = find_sutra_page(doc, 140, 160, "7.2.1") or 149
    toc.append([3, "Pāda 7.2 (Sūtras 7.2.1 – 7.2.118)", p7_2])
    p7_3 = find_sutra_page(doc, 265, 285, "7.3.1") or 276
    toc.append([3, "Pāda 7.3 (Sūtras 7.3.1 – 7.3.120)", p7_3])
    p7_4 = find_sutra_page(doc, 375, 395, "7.4.1") or 386
    toc.append([3, "Pāda 7.4 (Sūtras 7.4.1 – 7.4.97)", p7_4])

    p8_1 = find_sutra_page(doc, 425, 445, "8.1.1") or 434
    toc.append([2, "Adhyāya Eight", p8_1])
    toc.append([3, "Pāda 8.1 (Sūtras 8.1.1 – 8.1.74)", p8_1])
    p8_2 = find_sutra_page(doc, 505, 525, "8.2.1") or 518
    toc.append([3, "Pāda 8.2 (Sūtras 8.2.1 – 8.2.108; Start of Tripādī)", p8_2])
    p8_3 = find_sutra_page(doc, 615, 635, "8.3.1") or 626
    toc.append([3, "Pāda 8.3 (Sūtras 8.3.1 – 8.3.119)", p8_3])
    p8_4 = find_sutra_page(doc, 730, 750, "8.4.1") or 743
    toc.append([3, "Pāda 8.4 (Sūtras 8.4.1 – 8.4.68)", p8_4])

    p_bib = find_heading_page(doc, 795, 810, r"Bibliography") or 806
    toc.append([2, "Bibliography", p_bib])
    p_ind_d = find_heading_page(doc, 805, 820, r"Index of Derivations") or 814
    toc.append([2, "Index of Derivations", p_ind_d])
    p_ind_t = find_heading_page(doc, 810, 824, r"Index of Terms") or 817
    toc.append([2, "Index of Terms", p_ind_t])
    p_ind_s = find_heading_page(doc, 815, 831, r"Index of S[uū]tras") or 822
    toc.append([2, "Index of Sūtras", p_ind_s])
    return toc


def process_pdf(pdf_path: Path):
    if not pdf_path.is_file():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        return 1

    print(f"Processing: {pdf_path}")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"Page count: {total_pages}")

    name = pdf_path.name.lower()
    if "vol1" in name or "volume1" in name or total_pages == 262:
        print("Detected Volume 1")
        toc = get_volume_1_toc(doc)
        title = "The Aṣṭādhyāyī of Pāṇini (Volume I: Introduction to the Aṣṭādhyāyī as a Grammatical Device)"
        subject = "Introduction to the Aṣṭādhyāyī as a Grammatical Device"
    elif "vol2" in name or "volume2" in name or total_pages == 557:
        print("Detected Volume 2")
        toc = get_volume_2_toc(doc)
        title = "The Aṣṭādhyāyī of Pāṇini (Volume II: English Translation of Adhyāya One)"
        subject = "English Translation of Adhyāya One with Sanskrit Text, Transliteration, Word-Boundary, Anuvṛtti, Vṛtti"
    elif "vol3" in name or "volume3" in name or total_pages == 829:
        print("Detected Volume 3")
        toc = get_volume_3_toc(doc)
        title = "The Aṣṭādhyāyī of Pāṇini (Volume III: English Translation of Adhyāyas Two and Three)"
        subject = "English Translation of Adhyāyas Two and Three with Sanskrit Text, Transliteration, Word-Boundary"
    elif "vol4" in name or "volume4" in name or total_pages == 817:
        print("Detected Volume 4")
        toc = get_volume_4_toc(doc)
        title = "The Aṣṭādhyāyī of Pāṇini (Volume IV: English Translation of Adhyāyas Four and Five)"
        subject = "English Translation of Adhyāyas Four and Five with Sanskrit Text, Transliteration, Word-Boundary"
    elif "vol5" in name or "volume5" in name or total_pages == 611:
        print("Detected Volume 5")
        toc = get_volume_5_toc(doc)
        title = "The Aṣṭādhyāyī of Pāṇini (Volume V: English Translation of Adhyāya Six)"
        subject = "English Translation of Adhyāya Six with Sanskrit Text, Transliteration, Word-Boundary"
    elif "vol6" in name or "volume6" in name or total_pages == 831:
        print("Detected Volume 6")
        toc = get_volume_6_toc(doc)
        title = "The Aṣṭādhyāyī of Pāṇini (Volume VI: English Translation of Adhyāyas Seven and Eight)"
        subject = "English Translation of Adhyāyas Seven and Eight with Sanskrit Text, Transliteration, Word-Boundary"
    else:
        print(f"Unknown volume configuration (name={name}, pages={total_pages}), skipping.")
        doc.close()
        return 1

    print(f"Generated {len(toc)} TOC entries:")
    for lvl, t, p in toc:
        indent = "  " * (lvl - 1)
        print(f"{indent}[L{lvl}] {t} -> Page {p}")

    meta = doc.metadata or {}
    meta["title"] = title
    meta["author"] = "Rama Nath Sharma"
    meta["subject"] = subject
    meta["keywords"] = "Panini; Astadhyayi; Sanskrit Grammar; Rama Nath Sharma; Linguistics"
    meta["creator"] = "AlexandriaSandwich / PyMuPDF TOC Injection"
    meta["producer"] = "PyMuPDF"
    doc.set_metadata(meta)
    doc.set_toc(toc)

    temp_path = pdf_path.parent / f"_tmp_{pdf_path.name}"
    print(f"Saving to {temp_path}...")
    doc.save(str(temp_path), deflate=True, garbage=3)
    doc.close()

    print(f"Replacing {pdf_path}...")
    temp_path.replace(pdf_path)

    os.system(f'chflags nohidden "{pdf_path}" 2>/dev/null || true')
    print(f"Successfully injected TOC into {pdf_path} ({pdf_path.stat().st_size / 1e6:.1f} MB)!")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path("data/input/003_vol3_RamaNathSharma-TheAstadhyayiOfPanini.pdf")
    sys.exit(process_pdf(target))
