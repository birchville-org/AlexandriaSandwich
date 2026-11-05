#!/usr/bin/env python3
"""
test_birchville_onboard.py — Tests for admin onboarding CLI and staging logic.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.birchville_onboard import (
    generate_argon2_hash,
    load_job_options,
    save_job_options,
    stage_job,
    unstage_job,
    render_invitation_email,
)


class TestBirchvilleOnboard(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.test_dir) / "data" / "input"
        self.input_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_argon2_hash_generation(self):
        # Local hash generation should return a valid argon2id string
        pwd = "TestPassword_2026_Secure!"
        pw_hash = generate_argon2_hash(pwd, synology_host=None)
        self.assertTrue(pw_hash.startswith("$argon2id$"))
        self.assertIn("m=65536,t=3,p=4", pw_hash)

    def test_invitation_email_bilingual(self):
        email_text = render_invitation_email(
            username="scholar_test",
            display_name="Prof. Test Scholar",
            email="scholar@test.edu",
            password="GeneratedPass123",
            job_id="test_manuscript_vol1"
        )
        # Check German section
        self.assertIn("Ihr Zugang zu den Birchville-Forschungsdiensten", email_text)
        self.assertIn("Benutzername: scholar_test", email_text)
        self.assertIn("Initialpasswort: GeneratedPass123", email_text)
        self.assertIn("test_manuscript_vol1", email_text)
        self.assertIn("https://alex.birchville.org/jobs/test_manuscript_vol1", email_text)
        self.assertIn("https://auth.birchville.org", email_text)

        # Check English section
        self.assertIn("Subject: Your access credentials for Birchville Scholarly Services", email_text)
        self.assertIn("Dear Prof. Test Scholar,", email_text)
        self.assertIn("Pre-formulated Job:", email_text)

    def test_stage_and_unstage_job(self):
        job_id = "sample_corpus_job"
        job_dir = self.input_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        with patch("scripts.birchville_onboard.DATA_INPUT", self.input_dir):
            # 1. Stage job
            ok = stage_job(job_id, "indologist_user")
            self.assertTrue(ok)

            opts = load_job_options(job_id)
            self.assertEqual(opts.get("assigned_to"), "indologist_user")
            self.assertTrue(opts.get("is_staged"))

            # 2. Unstage job
            ok_unstage = unstage_job(job_id)
            self.assertTrue(ok_unstage)

            opts2 = load_job_options(job_id)
            self.assertFalse(opts2.get("is_staged"))
            # Assigned to is retained
            self.assertEqual(opts2.get("assigned_to"), "indologist_user")


if __name__ == "__main__":
    unittest.main()
