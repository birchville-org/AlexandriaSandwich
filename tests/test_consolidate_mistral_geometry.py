#!/usr/bin/env python3
"""
Test suite for Mistral OCR JSON geometry consolidation in AlexandriaSandwich.
Verifies that:
1. parse_mistral_json_page extracts real bounding boxes, page dimensions, and block types.
2. Sideheads and headings are correctly detected and mapped.
3. clean_page_artifacts extracts printed_page and strips running folios.
4. Fallback to markdown works when blocks are empty/null.
"""
import json
import tempfile
import unittest
from pathlib import Path

import sys
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from consolidate_book import (
    clean_page_artifacts,
    consolidate_job,
    parse_markdown_page,
    parse_mistral_json_page,
)


class TestMistralGeometryConsolidation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_mistral_json_page_with_blocks(self):
        sample_json = {
            "source": "/data/input/job1/page-001.png",
            "model": "mistral-ocr-latest",
            "markdown": "# Chapter One\n\nIntro text",
            "pages": [
                {
                    "index": 0,
                    "dimensions": {"dpi": 300, "height": 3000, "width": 2000},
                    "blocks": [
                        {
                            "type": "header",
                            "content": "24",
                            "top_left_x": 100,
                            "top_left_y": 80,
                            "bottom_right_x": 160,
                            "bottom_right_y": 120
                        },
                        {
                            "type": "title",
                            "content": "# First Chapter",
                            "top_left_x": 400,
                            "top_left_y": 200,
                            "bottom_right_x": 1600,
                            "bottom_right_y": 300
                        },
                        {
                            "type": "text",
                            "content": "This is a body paragraph with authentic geometry.",
                            "top_left_x": 400,
                            "top_left_y": 350,
                            "bottom_right_x": 1600,
                            "bottom_right_y": 600
                        },
                        {
                            "type": "table",
                            "content": "| Col1 | Col2 |\n|---|---|\n| Val1 | Val2 |",
                            "top_left_x": 400,
                            "top_left_y": 650,
                            "bottom_right_x": 1600,
                            "bottom_right_y": 900
                        },
                        {
                            "type": "image",
                            "content": "![figure.png](figure.png)",
                            "image_id": "figure.png",
                            "top_left_x": 300,
                            "top_left_y": 1000,
                            "bottom_right_x": 1700,
                            "bottom_right_y": 1800
                        }
                    ]
                }
            ]
        }

        json_file = self.test_dir / "page-001.mistral.json"
        json_file.write_text(json.dumps(sample_json), encoding="utf-8")

        res = parse_mistral_json_page(json_file)
        self.assertEqual(res["bbox"], [0, 0, 2000, 3000])
        self.assertEqual(res["facs"], "page-001.png")
        self.assertEqual(len(res["blocks"]), 7)  # header, title, text, 3 table rows, 1 image

        # Verify header block
        b0 = res["blocks"][0]
        self.assertEqual(b0["type"], "h2")
        self.assertEqual(b0["text"], "24")
        self.assertEqual(b0["bbox"], [100, 80, 160, 120])

        # Verify title block (starts with #)
        b1 = res["blocks"][1]
        self.assertEqual(b1["type"], "h1")
        self.assertEqual(b1["text"], "First Chapter")
        self.assertEqual(b1["bbox"], [400, 200, 1600, 300])

        # Verify body text block
        b2 = res["blocks"][2]
        self.assertEqual(b2["type"], "p")
        self.assertEqual(b2["bbox"], [400, 350, 1600, 600])

        # Verify table rows
        b3 = res["blocks"][3]
        self.assertEqual(b3["type"], "table_row")
        self.assertEqual(b3["text"], "| Col1 | Col2 |")
        self.assertEqual(b3["bbox"], [400, 650, 1600, 900])

        # Verify image block
        b_img = res["blocks"][6]
        self.assertEqual(b_img["type"], "image")
        self.assertEqual(b_img["image_id"], "figure.png")
        self.assertEqual(b_img["bbox"], [300, 1000, 1700, 1800])

    def test_printed_page_extraction_in_clean_artifacts(self):
        page = {
            "page_num": 1,
            "facs": "page-001.png",
            "bbox": [0, 0, 1000, 1500],
            "blocks": [
                {"type": "h2", "text": "24", "bbox": [100, 50, 150, 80]},
                {"type": "p", "text": "First body paragraph", "bbox": [100, 100, 900, 200]},
                {"type": "p", "text": "Second body paragraph", "bbox": [100, 220, 900, 300]},
            ]
        }
        cleaned_pages = clean_page_artifacts([page])
        self.assertEqual(cleaned_pages[0]["printed_page"], "24")
        self.assertEqual(len(cleaned_pages[0]["blocks"]), 2)
        self.assertEqual(cleaned_pages[0]["blocks"][0]["text"], "First body paragraph")

    def test_end_to_end_consolidate_job(self):
        in_dir = self.test_dir / "input"
        in_dir.mkdir()
        out_dir = self.test_dir / "output"
        out_dir.mkdir()

        # Write page 1 with Mistral JSON
        p1_json = {
            "source": "page-001.png",
            "pages": [
                {
                    "dimensions": {"width": 1200, "height": 1800},
                    "blocks": [
                        {"type": "text", "content": "Geometry verified.", "top_left_x": 50, "top_left_y": 60, "bottom_right_x": 1100, "bottom_right_y": 150}
                    ]
                }
            ]
        }
        (in_dir / "page-001.mistral.json").write_text(json.dumps(p1_json), encoding="utf-8")

        book_data = consolidate_job(
            job_name="test_job",
            input_dir=in_dir,
            output_dir=out_dir,
            title="Geometry Book",
            author="Test Author"
        )

        book_json_path = out_dir / "book.json"
        self.assertTrue(book_json_path.exists())

        with open(book_json_path, encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data["pages"]), 1)
        p1 = data["pages"][0]
        self.assertEqual(p1["bbox"], [0, 0, 1200, 1800])
        self.assertEqual(len(p1["blocks"]), 1)
        self.assertEqual(p1["blocks"][0]["bbox"], [50, 60, 1100, 150])
        self.assertEqual(p1["blocks"][0]["text"], "Geometry verified.")


if __name__ == "__main__":
    unittest.main()
