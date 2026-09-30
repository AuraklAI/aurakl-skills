#!/usr/bin/env python3
"""
Aurakl Plugin Unified CLI Tool (aurakl)

Central entry point dispatching commands to:
  - `aurakl pm`: Product Management Engine (elicit, validate, calc-metrics, audit, render)
  - `aurakl arch`: Software Architecture Engine (validate, render, cartesian, oracle)
  - `aurakl status`: Inspect plugin health, loaded skills, schemas, and standards
  - `aurakl test`: Execute complete test suite (65+ tests) verifying plugin integrity
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import List

PLUGIN_ROOT = Path(__file__).resolve().parent
PM_SCRIPT = PLUGIN_ROOT / "skills" / "aurakl-product-manager" / "scripts" / "aurakl_pm.py"
if not PM_SCRIPT.exists():
    PM_SCRIPT = PLUGIN_ROOT / "skills" / "aurakl-product-manager" / "scripts" / "lumen_pm.py"
ARCH_SCRIPT = PLUGIN_ROOT / "skills" / "aurakl-software-architect" / "scripts" / "aurakl_arch.py"


def cmd_status() -> int:
    print("=" * 60)
    print(" Aurakl Skills - Enterprise Agent Skills Suite")
    print("=" * 60)
    print(f"Skills Root : {PLUGIN_ROOT}")
    print(f"Python Exec : {sys.executable} (v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro})")
    
    pm_status = "READY" if PM_SCRIPT.exists() else "MISSING"
    arch_status = "READY" if ARCH_SCRIPT.exists() else "MISSING"
    
    print(f"Skill [aurakl-product-manager]   : {pm_status} ({PM_SCRIPT})")
    print(f"Skill [aurakl-software-architect] : {arch_status} ({ARCH_SCRIPT})")
    print("=" * 60)
    return 0 if (PM_SCRIPT.exists() and ARCH_SCRIPT.exists()) else 1


def cmd_test() -> int:
    print("Running Aurakl Skills Test Suites...")
    test_runner = PLUGIN_ROOT / "tests" / "test_plugin_integrity.py"
    if test_runner.exists():
        return subprocess.run([sys.executable, str(test_runner)], check=False).returncode
    return 1


def main(argv: List[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help"):
        print("Usage: aurakl <subcommand> [args...]")
        print("\nAvailable subcommands:")
        print("  pm        Product Management engine (elicit, validate, audit, render)")
        print("  arch      Software Architecture engine (validate, render, cartesian, oracle)")
        print("  status    Inspect status and loaded skills")
        print("  test      Run all verification and unit test suites")
        print("  --version Show suite version")
        return 0

    subcommand = argv[0]
    rest = argv[1:]

    if subcommand in ("-v", "--version"):
        manifest = PLUGIN_ROOT / "plugin.json"
        if manifest.exists():
            import json
            data = json.loads(manifest.read_text(encoding="utf-8"))
            print(f"aurakl-skills v{data.get('version', 'unknown')}")
        else:
            print("aurakl-skills v1.0.0")
        return 0

    if subcommand == "status":
        return cmd_status()

    if subcommand == "test":
        return cmd_test()

    if subcommand == "pm":
        if not PM_SCRIPT.exists():
            print(f"Error: PM script not found at {PM_SCRIPT}", file=sys.stderr)
            return 1
        return subprocess.run([sys.executable, str(PM_SCRIPT)] + rest, check=False).returncode

    if subcommand == "arch":
        if not ARCH_SCRIPT.exists():
            print(f"Error: Architecture script not found at {ARCH_SCRIPT}", file=sys.stderr)
            return 1
        return subprocess.run([sys.executable, str(ARCH_SCRIPT)] + rest, check=False).returncode

    print(f"Error: Unknown subcommand '{subcommand}'. Run 'aurakl --help' for usage.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
