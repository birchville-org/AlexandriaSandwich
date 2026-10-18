"""
AlexandriaSandwich — tests/test_ui_safety.py

Unit tests for UI validation, path traversal defense, ZIP slip/bomb protection,
TOC parsing, and security boundary functions.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import HTTPException
from ui.main import (
    _safe_path,
    _validate_job,
    _validate_run_id,
    _validate_lang,
    _validate_threshold,
    _validate_limit,
    _check_csrf_origin,
    _extract_zip,
    parse_toc_content,
)


class TestValidation(unittest.TestCase):
    def test_validate_job_valid(self):
        self.assertEqual(_validate_job("golden_smoke"), "golden_smoke")
        self.assertEqual(_validate_job("job-1.2_alpha"), "job-1.2_alpha")
        self.assertEqual(_validate_job("Job2026"), "Job2026")

    def test_validate_job_traversal(self):
        for bad in ["..", "../etc", "foo/bar", "a/../b", "/root"]:
            with self.assertRaises(HTTPException):
                _validate_job(bad)

    def test_validate_job_invalid_chars(self):
        for bad in ["job name", "job;rm", "job$1", "job|cat", "job<xml>", ""]:
            with self.assertRaises(HTTPException):
                _validate_job(bad)

    def test_validate_run_id(self):
        self.assertEqual(_validate_run_id("run-20261018_120000"), "run-20261018_120000")
        with self.assertRaises(HTTPException):
            _validate_run_id("../run1")
        with self.assertRaises(HTTPException):
            _validate_run_id("")

    def test_validate_lang(self):
        self.assertEqual(_validate_lang("deu+eng"), "deu+eng")
        self.assertEqual(_validate_lang("san"), "san")
        self.assertEqual(_validate_lang("deu+san_fast"), "deu+san_fast")
        # Invalid characters fallback safely to deu+eng
        self.assertEqual(_validate_lang("deu; rm -rf"), "deu+eng")
        self.assertEqual(_validate_lang(""), "deu+eng")

    def test_validate_threshold(self):
        self.assertEqual(_validate_threshold(0), 0)
        self.assertEqual(_validate_threshold(85), 85)
        self.assertEqual(_validate_threshold(100), 100)
        self.assertEqual(_validate_threshold("50"), 50)
        for bad in [-1, 101, "abc", None]:
            with self.assertRaises(HTTPException):
                _validate_threshold(bad)

    def test_validate_limit(self):
        self.assertEqual(_validate_limit(0), 0)
        self.assertEqual(_validate_limit(10), 10)
        self.assertEqual(_validate_limit(100000), 100000)
        for bad in [-1, 100001, "invalid", None]:
            with self.assertRaises(HTTPException):
                _validate_limit(bad)


class TestPathSafety(unittest.TestCase):
    def test_safe_path_valid(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td).resolve()
            sub = (base / "valid_dir").resolve()
            sub.mkdir()
            target = _safe_path(base, "valid_dir")
            self.assertEqual(target, sub)

    def test_safe_path_traversal_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            with self.assertRaises(ValueError):
                _safe_path(base, "../outside.txt")
            with self.assertRaises(ValueError):
                _safe_path(base, "sub/../../escape.txt")


class TestZipExtractionSafety(unittest.TestCase):
    def test_extract_valid_zip(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zip_file = td_path / "test.zip"
            target_dir = td_path / "extracted"

            with zipfile.ZipFile(zip_file, "w") as zf:
                zf.writestr("page-001.png", b"\x89PNG\r\n\x1a\nfakeimagebytes")
                zf.writestr("page-002.png", b"\x89PNG\r\n\x1a\nfakeimagebytes2")

            extracted = _extract_zip(zip_file, target_dir)
            self.assertEqual(len(extracted), 2)
            self.assertTrue((target_dir / "page-001.png").is_file())
            self.assertTrue((target_dir / "page-002.png").is_file())

    def test_extract_zip_slip_neutralized(self):
        """ZipSlip attack with relative directories must flatten to basename within target_dir."""
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zip_file = td_path / "slip.zip"
            target_dir = td_path / "extracted"

            with zipfile.ZipFile(zip_file, "w") as zf:
                zf.writestr("../../evil.png", b"\x89PNG\r\n\x1a\nevildata")

            extracted = _extract_zip(zip_file, target_dir)
            self.assertEqual(len(extracted), 1)
            # Extracted file must reside inside target_dir as evil.png, NOT in parent directory
            self.assertTrue((target_dir / "evil.png").is_file())
            self.assertFalse((td_path / "evil.png").is_file())

    def test_extract_zip_bomb_entry_limit(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            zip_file = td_path / "bomb.zip"
            target_dir = td_path / "extracted"

            with zipfile.ZipFile(zip_file, "w") as zf:
                for i in range(2005):
                    zf.writestr(f"p_{i}.txt", b"x")

            with self.assertRaises(ValueError) as ctx:
                _extract_zip(zip_file, target_dir)
            self.assertIn("zu viele Einträge", str(ctx.exception))


class TestTocParser(unittest.TestCase):
    def test_parse_json_toc(self):
        raw = '[[1, "Chapter 1: Basics", 1], [2, "Alphabet", 3]]'
        res = parse_toc_content(raw)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0], [1, "Chapter 1: Basics", 1])
        self.assertEqual(res[1], [2, "Alphabet", 3])

    def test_parse_markdown_headings(self):
        raw = """
# Introduction 1
## Background 3
# Chapter 1: Phonetics 15
        """
        res = parse_toc_content(raw)
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0], [1, "Introduction", 1])
        self.assertEqual(res[1], [2, "Background", 3])
        self.assertEqual(res[2], [1, "Chapter 1: Phonetics", 15])

    def test_parse_dot_leaders(self):
        raw = """
Preface ........................ 5
Grammar Rules .................. 19
        """
        res = parse_toc_content(raw)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0], [1, "Preface", 5])
        self.assertEqual(res[1], [1, "Grammar Rules", 19])


class TestCsrfOriginCheck(unittest.TestCase):
    def test_allowed_origins(self):
        for origin in ["http://localhost:8080", "http://127.0.0.1:8080", "http://alex.local"]:
            req = MagicMock()
            req.headers = {"origin": origin, "host": "127.0.0.1:8080"}
            # Should not raise
            _check_csrf_origin(req)

    def test_blocked_origin(self):
        req = MagicMock()
        req.headers = {"origin": "https://malicious-website.com", "host": "127.0.0.1:8080"}
        with self.assertRaises(HTTPException) as ctx:
            _check_csrf_origin(req)
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
