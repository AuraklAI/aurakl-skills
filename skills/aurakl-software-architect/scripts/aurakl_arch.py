#!/usr/bin/env python3
"""
Aurakl Software Architecture Unified CLI Tool (aurakl_arch)

Provides a single command-line interface for:
1. `validate`: Five-dimensional architecture acceptance validator (conformance, coverage, grounding, consistency, oracle).
2. `render`: Markdown renderer converting machine-readable JSON deliverables into template-conforming Markdown with dynamic language matching.
3. `cartesian`: Mathematical Cartesian completeness engine auditing failure classes, SxE transitions, DAG closure, and invariant coverage.
4. `oracle`: Direct lineage oracle gatekeeper verifying 100% requirement coverage, acyclicity, and one-vote veto.
5. `standards`: Inspects quality standards and rules.
6. `schemas`: Lists supported architecture JSON schemas.
7. `templates`: Lists supported architecture Markdown templates.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any, Dict, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

# Add script directory to sys.path
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from arch_validator import AuraklArchitectureValidator
from arch_renderer import AuraklArchitectureRenderer
from arch_cartesian_engine import AuraklArchCartesianEngine
from architecture_lineage_oracle import AuraklArchitectureOracle, validate_pipeline


def cmd_validate(args: argparse.Namespace) -> int:
    file_path = Path(args.path)
    if not file_path.exists():
        print(f"Error: file '{args.path}' not found", file=sys.stderr)
        return 1

    data = json.loads(file_path.read_text(encoding="utf-8"))
    if getattr(args, "upstream_prd", None):
        u_path = Path(args.upstream_prd)
        if u_path.exists():
            data["upstream_prd"] = json.loads(u_path.read_text(encoding="utf-8"))
    validator = AuraklArchitectureValidator()

    if args.suite or "tech_stack_decision" in data:
        verdict = validator.validate_suite(data)
    else:
        kind = args.kind or data.get("kind") or file_path.stem
        verdict = validator.validate_artifact(kind, data)

    if args.json:
        print(json.dumps(asdict(verdict), indent=2, ensure_ascii=False))
    else:
        status_str = "PASSED" if verdict.passed else "FAILED"
        print(f"=== Aurakl Architecture Validation [{status_str}]: {verdict.kind} ===")
        if verdict.issues:
            print(f"Found {len(verdict.issues)} issues:")
            for issue in verdict.issues:
                ptr = f" at {issue.pointer}" if issue.pointer else ""
                print(f"  [{issue.dimension.upper()}] ({issue.code}){ptr}: {issue.message}")
        else:
            print("All five dimensional validation checks passed successfully!")

    return 0 if verdict.passed else 1


def cmd_render(args: argparse.Namespace) -> int:
    file_path = Path(args.path)
    if not file_path.exists():
        print(f"Error: file '{args.path}' not found", file=sys.stderr)
        return 1

    data = json.loads(file_path.read_text(encoding="utf-8"))
    renderer = AuraklArchitectureRenderer()

    if "tech_stack_decision" in data or "system_architecture_spec" in data:
        output_md = renderer.render_suite(data, args.lang)
    else:
        kind = args.kind or data.get("kind") or file_path.stem
        clean = kind.lower().replace("-", "_")
        render_map = {
            "tech_stack_decision": renderer.render_tech_stack_decision,
            "system_architecture_spec": renderer.render_system_architecture,
            "domain_model_spec": renderer.render_domain_model,
            "database_design_spec": renderer.render_database_design,
            "api_contract_suite": renderer.render_api_contracts,
            "business_flow_spec": renderer.render_business_flow,
            "architecture_invariants_spec": renderer.render_architecture_invariants,
            "technical_dependency_dag_spec": renderer.render_dependency_guidance,
            "architecture_readiness_review_report": renderer.render_review_report,
        }
        fn = render_map.get(clean)
        if not fn:
            print(f"Error: unknown kind '{kind}'", file=sys.stderr)
            return 1
        output_md = fn(data, args.lang)

    if args.output:
        Path(args.output).write_text(output_md, encoding="utf-8")
        print(f"Successfully rendered markdown to {args.output}")
    else:
        print(output_md)

    return 0


def cmd_cartesian(args: argparse.Namespace) -> int:
    file_path = Path(args.path)
    if not file_path.exists():
        print(f"Error: file '{args.path}' not found", file=sys.stderr)
        return 1

    data = json.loads(file_path.read_text(encoding="utf-8"))
    report = AuraklArchCartesianEngine.audit_suite(data)

    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        status_str = "COMPLETE" if report.is_complete else "INCOMPLETE"
        print(f"=== Aurakl Architecture Cartesian Completeness Audit [{status_str}] ===")
        print(f"- Must-Have Requirement Coverage: {report.requirement_coverage_pct}% ({'100% Satisfied' if not report.uncovered_requirements else 'Gaps Detected'})")
        print(f"- Dependency DAG Acyclicity: {'PASSED (Acyclic)' if report.dag_acyclic else 'FAILED (Cycles Detected)'}")
        print(f"- Critical Path Length: {report.critical_path_length} nodes")
        print(f"- Architecture Invariant Dimensions: {9 - len(report.missing_invariant_dimensions)}/9 Covered")
        print(f"- Failure Modes Coverage: {report.defended_failure_cells}/{report.total_failure_cells} ({report.failure_coverage_pct}%)")
        if report.unhandled_transitions:
            print(f"- State Transition Edge Cases: {len(report.unhandled_transitions)} unhandled pairs detected")
        if report.gaps:
            print(f"\nIdentified Architectural Gaps ({len(report.gaps)}):")
            for gap in report.gaps:
                print(f"  * {gap}")
        else:
            print("\n✅ Zero Architectural Gaps! System passes Cartesian completeness verification.")

    return 0 if report.is_complete else 1


def cmd_oracle(args: argparse.Namespace) -> int:
    file_path = Path(args.path)
    if not file_path.exists():
        print(f"Error: file '{args.path}' not found", file=sys.stderr)
        return 1

    data = json.loads(file_path.read_text(encoding="utf-8"))
    result = validate_pipeline(data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("verdict") == "passed" else 1


def cmd_standards(args: argparse.Namespace) -> int:
    standards_dir = SKILL_ROOT / "standards"
    files = sorted(standards_dir.glob("*.json"))
    print(f"=== Aurakl Architecture Quality Standards ({len(files)}) ===")
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        spec = data.get("spec", {})
        print(f"\n[{data.get('metadata', {}).get('id')}] {spec.get('name')}")
        if "rules" in spec:
            for r in spec.get("rules", []):
                print(f"  - {r.get('id')}: {r.get('statement')}")
        elif "principles" in spec:
            for p in spec.get("principles", []):
                print(f"  * {p}")
    return 0


def cmd_schemas(args: argparse.Namespace) -> int:
    schemas_dir = SKILL_ROOT / "schemas"
    files = sorted(schemas_dir.glob("*.json"))
    print(f"=== Aurakl Architecture Schemas ({len(files)}) ===")
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        title = data.get("title", f.stem)
        desc = data.get("description", "")
        print(f"- {f.name}: {title} ({desc[:60]}...)")
    return 0


def cmd_templates(args: argparse.Namespace) -> int:
    templates_dir = SKILL_ROOT / "templates"
    files = sorted(templates_dir.glob("*.json"))
    print(f"=== Aurakl Architecture Markdown Templates ({len(files)}) ===")
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        spec = data.get("spec", {})
        print(f"- {f.name}: {spec.get('name')}")
        for sec in spec.get("sections", []):
            print(f"    [{sec.get('id')}] {sec.get('title')}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Aurakl Software Architecture Unified Tool (aurakl_arch)")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # validate
    p_val = subparsers.add_parser("validate", help="Validate deliverable or architecture suite")
    p_val.add_argument("path", help="Path to JSON deliverable or suite")
    p_val.add_argument("--kind", help="Kind of deliverable if validating single artifact")
    p_val.add_argument("--suite", action="store_true", help="Validate as complete architecture suite")
    p_val.add_argument("--upstream-prd", help="Path to upstream PRD JSON for lineage & coverage verification")
    p_val.add_argument("--json", action="store_true", help="Output validation verdict as JSON")
    p_val.set_defaults(func=cmd_validate)

    # render
    p_ren = subparsers.add_parser("render", help="Render deliverable or suite into Markdown")
    p_ren.add_argument("path", help="Path to JSON deliverable or suite")
    p_ren.add_argument("--kind", help="Kind of deliverable if not full suite")
    p_ren.add_argument("--lang", choices=["en", "zh"], help="Target output language (en or zh)")
    p_ren.add_argument("-o", "--output", help="Output file path (default stdout)")
    p_ren.set_defaults(func=cmd_render)

    # cartesian
    p_car = subparsers.add_parser("cartesian", help="Run Cartesian completeness audit")
    p_car.add_argument("path", help="Path to architecture suite JSON")
    p_car.add_argument("--json", action="store_true", help="Output audit report as JSON")
    p_car.set_defaults(func=cmd_cartesian)

    # oracle
    p_ora = subparsers.add_parser("oracle", help="Execute architecture lineage oracle pipeline")
    p_ora.add_argument("path", help="Path to architecture suite JSON")
    p_ora.set_defaults(func=cmd_oracle)

    # standards
    p_std = subparsers.add_parser("standards", help="List quality standards and rules")
    p_std.set_defaults(func=cmd_standards)

    # schemas
    p_sch = subparsers.add_parser("schemas", help="List available schemas")
    p_sch.set_defaults(func=cmd_schemas)

    # templates
    p_tpl = subparsers.add_parser("templates", help="List available markdown templates")
    p_tpl.set_defaults(func=cmd_templates)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
