#!/usr/bin/env python3
"""
Test suite for unclamped layout calibration, recto/verso gutter detection,
and dynamic typography extraction in AlexandriaSandwich (Phase 2).
"""
import tempfile
import unittest
from pathlib import Path

import sys
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from render_digital_pdf import build_typst_document, calibrate_layout_from_pdf


class TestUnclampedLayoutCalibration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_build_typst_document_with_unclamped_margins_and_typography(self):
        book_data = {
            "metadata": {"title": "Sanskrit Studies", "author": "Max Müller"},
            "pages": [
                {
                    "page_num": 1,
                    "blocks": [
                        {"type": "h1", "text": "First Chapter"},
                        {"type": "p", "text": "Historical text with generous margins."}
                    ]
                }
            ]
        }

        template_path = Path(__file__).resolve().parent.parent / "templates" / "book.typ"

        # Calibration with generous historical margins (> 42pt) and asymmetric gutter
        layout_cal = {
            "width": 500.0,
            "height": 750.0,
            "inside": 68.0,
            "outside": 48.0,
            "left": 68.0,
            "right": 48.0,
            "top": 60.0,
            "bottom": 72.0,
            "is_asymmetric_gutter": True,
            "font_size_pt": 9.5,
            "leading_pt": 3.2,
        }

        typst_src = build_typst_document(
            book_data,
            template_path=str(template_path),
            layout_calibration=layout_cal,
            preserve_pages=True,
        )

        # Verify width and height
        self.assertIn("width: 500.0pt", typst_src)
        self.assertIn("height: 750.0pt", typst_src)

        # Verify unclamped asymmetric gutter margin
        self.assertIn("margin: (inside: 68.0pt, outside: 48.0pt, top: 60.0pt, bottom: 72.0pt)", typst_src)

        # Verify dynamic typography parameters
        self.assertIn("font_size: 9.5pt", typst_src)
        self.assertIn("leading: 3.2pt", typst_src)

    def test_build_typst_document_with_symmetric_margins(self):
        book_data = {
            "metadata": {"title": "Sanskrit Studies", "author": "Max Müller"},
            "pages": [
                {
                    "page_num": 1,
                    "blocks": [
                        {"type": "h1", "text": "First Chapter"},
                        {"type": "p", "text": "Symmetric margins text."}
                    ]
                }
            ]
        }

        template_path = Path(__file__).resolve().parent.parent / "templates" / "book.typ"

        layout_cal = {
            "width": 450.0,
            "height": 700.0,
            "left": 55.0,
            "right": 55.0,
            "inside": 55.0,
            "outside": 55.0,
            "top": 50.0,
            "bottom": 50.0,
            "is_asymmetric_gutter": False,
            "font_size_pt": 10.0,
            "leading_pt": 2.5,
        }

        typst_src = build_typst_document(
            book_data,
            template_path=str(template_path),
            layout_calibration=layout_cal,
            preserve_pages=True,
        )

        self.assertIn("margin: (left: 55.0pt, right: 55.0pt, top: 50.0pt, bottom: 50.0pt)", typst_src)
        self.assertIn("font_size: 10.0pt", typst_src)
        self.assertIn("leading: 2.5pt", typst_src)


if __name__ == "__main__":
    unittest.main()
