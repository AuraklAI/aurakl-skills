#!/usr/bin/env python3
"""
Unit Tests for Aurakl Architecture Quality Standards
"""

import json
from pathlib import Path
import unittest

STANDARDS_DIR = Path(__file__).resolve().parent.parent / "standards"


class TestArchStandards(unittest.TestCase):

    def test_all_ten_standards_exist_and_valid(self):
        files = list(STANDARDS_DIR.glob("*.json"))
        self.assertEqual(len(files), 10, f"Expected 10 standards but found {len(files)}")

        for f in files:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)

            self.assertEqual(data.get("api_version"), "aurakl.dev/v1")
            self.assertEqual(data.get("kind"), "Standard")
            meta = data.get("metadata", {})
            self.assertTrue(meta.get("id").startswith("arch-std-"))
            self.assertEqual(meta.get("created_by"), "aurakl")

            spec = data.get("spec", {})
            self.assertTrue("name" in spec)
            # Must either have rules or principles
            has_rules = "rules" in spec and len(spec["rules"]) > 0
            has_principles = "principles" in spec and len(spec["principles"]) > 0
            self.assertTrue(has_rules or has_principles, f"Standard {f.name} missing both rules and principles")


if __name__ == "__main__":
    unittest.main()
