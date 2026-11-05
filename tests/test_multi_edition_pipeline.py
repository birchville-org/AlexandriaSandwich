#!/usr/bin/env python3
"""
AlexandriaSandwich — tests/test_multi_edition_pipeline.py

Unit and regression tests for:
- scripts/indic_normalizer.py
- scripts/postprocess_pdf_metadata.py
- scripts/image_restoration.py
- scripts/build_multi_edition.py
"""
import unittest
from pathlib import Path
import numpy as np

from scripts.indic_normalizer import (
    to_arabic_numerals,
    to_deva_numerals,
    to_iast,
    normalize_apparatus_deva,
    normalize_apparatus_iast,
)
from scripts.image_restoration import clean_page_array
from scripts.build_multi_edition import generate_typst_content


class TestIndicNormalizer(unittest.TestCase):
    def test_numerals(self):
        self.assertEqual(to_arabic_numerals("०१२३४५६७८९"), "0123456789")
        self.assertEqual(to_deva_numerals("0123456789"), "०१२३४५६७८९")

    def test_apparatus_normalization(self):
        sample = "पं० १० ख० पु० बिम्बप्रतिबिम्बेति पाठः ।"
        res = normalize_apparatus_iast(sample)
        self.assertIn("paṃ. 10", res)
        self.assertIn("kha. pu.", res)
        self.assertTrue(res.endswith("."))

    def test_iast_transliteration(self):
        text = "यदेतत् प्रकाशरूपं शिवतत्त्वम्"
        iast = to_iast(text)
        self.assertIn("prakāśarūpaṃ", iast)
        self.assertIn("śivatattvam", iast)


class TestImageRestoration(unittest.TestCase):
    def test_clean_page_array_blank(self):
        blank = np.full((100, 100), 255, dtype=np.uint8)
        cleaned = clean_page_array(blank)
        self.assertTrue(np.all(cleaned == 255))

    def test_despeckle_isolated_dust(self):
        # Create image with a line of text and isolated speckles in the margin
        arr = np.full((200, 300), 255, dtype=np.uint8)
        # Text line (width 150)
        arr[100:106, 50:200] = 0
        # Margin speckles
        arr[20, 20] = 0
        arr[21, 20] = 0
        arr[180, 280] = 0

        cleaned = clean_page_array(arr, min_line_width=50, min_line_size=100)
        # Margin speckles should be wiped
        self.assertEqual(cleaned[20, 20], 255)
        self.assertEqual(cleaned[180, 280], 255)
        # Genuine text line should remain
        self.assertEqual(cleaned[103, 100], 0)


class TestMultiEditionGenerator(unittest.TestCase):
    def test_generate_typst_content(self):
        meta = {
            "title": "TEST TITLE",
            "author": "Author",
            "start_page": 10,
            "has_title_page": True,
        }
        pages_data = {
            10: {
                "lines_orig": ["लाइन १", "लाइन २"],
                "lines_translit": ["lāina 1", "lāina 2"],
                "lines_trans": ["Zeile 1", "Zeile 2"],
                "footnotes": ["१ टिप्पणी ।"],
                "footnotes_trans": ["1 Anmerkung."],
            }
        }
        typst = generate_typst_content("bilingual", meta, pages_data)
        self.assertIn("TEST TITLE", typst)
        self.assertIn("lāina 1", typst)
        self.assertIn("Zeile 1", typst)
        self.assertIn("1 Anmerkung.", typst)


if __name__ == "__main__":
    unittest.main()
