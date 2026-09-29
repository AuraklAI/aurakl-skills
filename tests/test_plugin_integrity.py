#!/usr/bin/env python3
"""
Aurakl Plugin Integrity & Verification Test Suite

Verifies:
1. Plugin manifest (plugin.json) validity and schema conformance
2. Rules (rules/AGENTS.md) presence and content
3. Skills directory structure, YAML frontmatter, and backward-compatible symlinks
4. Unified CLI entrypoint (aurakl_cli.py & bin/aurakl) execution
5. Comprehensive unit test pass rate across all bundled skills (65+ tests)
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


class TestPluginIntegrity(unittest.TestCase):
    def setUp(self):
        self.plugin_root = PLUGIN_ROOT
        self.manifest_path = self.plugin_root / "plugin.json"
        self.rules_path = self.plugin_root / "rules" / "AGENTS.md"
        self.skills_dir = self.plugin_root / "skills"

    def test_plugin_manifest_is_valid(self):
        self.assertTrue(self.manifest_path.exists(), "plugin.json must exist at root")
        content = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(content.get("name"), "aurakl-plugin")
        self.assertTrue(content.get("version"), "version must be present")
        self.assertTrue(content.get("description"), "description must be present")
        self.assertEqual(content.get("license"), "Apache-2.0")

    def test_plugin_rules_exist(self):
        self.assertTrue(self.rules_path.exists(), "rules/AGENTS.md must exist")
        text = self.rules_path.read_text(encoding="utf-8")
        self.assertIn("Dynamic Language Matching", text)
        self.assertIn("Zero-Placeholder", text)
        self.assertIn("Mathematical Invariants", text)

    def test_skills_exist_and_have_valid_frontmatter(self):
        expected_skills = [
            ("aurakl-product-manager", "aurakl-product-manager"),
            ("aurakl-software-architect", "aurakl-software-architect")
        ]
        for dir_name, expected_name in expected_skills:
            skill_dir = self.skills_dir / dir_name
            self.assertTrue(skill_dir.exists(), f"Skill directory {dir_name} must exist")
            skill_md = skill_dir / "SKILL.md"
            self.assertTrue(skill_md.exists(), f"SKILL.md must exist in {dir_name}")
            content = skill_md.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---"), "SKILL.md must start with YAML frontmatter")
            self.assertIn(f"name: {expected_name}", content)
            self.assertIn("description:", content)

    def test_backward_compatibility_symlinks(self):
        lumen_pm = self.skills_dir / "lumen-product-manager"
        lumen_arch = self.skills_dir / "lumen-software-architect"
        self.assertTrue(lumen_pm.exists(), "lumen-product-manager alias must exist")
        self.assertTrue(lumen_arch.exists(), "lumen-software-architect alias must exist")

    def test_unified_cli_status(self):
        cli_py = self.plugin_root / "aurakl_cli.py"
        self.assertTrue(cli_py.exists(), "aurakl_cli.py must exist")
        res = subprocess.run([sys.executable, str(cli_py), "status"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"aurakl status failed: {res.stderr}")
        self.assertIn("Aurakl Plugin", res.stdout)
        self.assertIn("aurakl-product-manager", res.stdout)
        self.assertIn("aurakl-software-architect", res.stdout)

    def test_all_skill_unit_tests_pass(self):
        pm_tests = self.skills_dir / "aurakl-product-manager" / "tests"
        arch_tests = self.skills_dir / "aurakl-software-architect" / "tests"

        # PM Tests
        res_pm = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(pm_tests)],
            capture_output=True, text=True
        )
        self.assertEqual(res_pm.returncode, 0, f"PM unit tests failed:\n{res_pm.stderr}")
        self.assertIn("OK", res_pm.stderr)

        # Architect Tests
        res_arch = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(arch_tests)],
            capture_output=True, text=True
        )
        self.assertEqual(res_arch.returncode, 0, f"Architect unit tests failed:\n{res_arch.stderr}")
        self.assertIn("OK", res_arch.stderr)


if __name__ == "__main__":
    unittest.main()
