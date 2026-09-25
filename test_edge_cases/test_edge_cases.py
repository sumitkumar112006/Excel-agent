"""Execute the 200 PDF fixtures against the real backend extractor."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

from extractor import process_single_pdf  # noqa: E402


MANIFEST = json.loads((HERE / "case_manifest.json").read_text(encoding="utf-8"))


class EdgeCasePDFTests(unittest.TestCase):
    maxDiff = None


def make_test(case: dict):
    def test(self):
        pdf = HERE / "pdfs" / case["filename"]
        self.assertTrue(pdf.exists(), f"Missing fixture: {pdf}")
        records = process_single_pdf(str(pdf))
        self.assertIsInstance(records, list, case["id"])
        expected = case["expected"]
        self.assertEqual(len(records), expected["record_count"], case["description"])
        self.assertTrue(records, case["description"])
        statuses = {r.get("validation_status") for r in records}
        self.assertIn(expected["status"], statuses, case["description"])
        if expected.get("field"):
            for field, value in expected["field"].items():
                self.assertEqual(records[0].get(field), value, case["description"])
        for record in records:
            self.assertIn(record.get("validation_status"), {"PASS", "REVIEW"})
            self.assertIn("validation_errors", record)
            self.assertIn("validation_checks", record)

    return test


for _case in MANIFEST:
    setattr(EdgeCasePDFTests, f"test_{_case['id']}_{_case['category']}", make_test(_case))


class FixtureIntegrityTests(unittest.TestCase):
    def test_exactly_200_separate_pdfs_exist(self):
        files = sorted((HERE / "pdfs").glob("*.pdf"))
        self.assertEqual(len(files), 200)
        self.assertEqual({p.name for p in files}, {c["filename"] for c in MANIFEST})

    def test_manifest_has_200_unique_cases(self):
        self.assertEqual(len(MANIFEST), 200)
        self.assertEqual(len({c["id"] for c in MANIFEST}), 200)
        self.assertEqual(len({c["description"] for c in MANIFEST}), 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
