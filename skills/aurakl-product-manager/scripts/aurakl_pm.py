#!/usr/bin/env python3
"""
Aurakl Product Management Unified CLI Facade (aurakl_pm)

Unified command-line toolkit for the aurakl-product-manager Skill:
  - elicit: 5W1H interactive requirement elicitation & slot convergence
  - validate: Five-dimensional acceptance verification across all 31 Aurakl schemas
  - calc-metrics: Direct calculation of invariant coverage (10000 bp) and negative defense ratio (>= 30%)
  - audit: Deterministic Oracle recomputation (pipeline, invariants_coverage, negative_ratio, review_consistency)
  - schemas: Inspect all 31 schemas, titles, descriptions, and required contracts
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
ORACLE_SCRIPT = SKILL_ROOT / "validators/product_lineage_oracle.py"
if not ORACLE_SCRIPT.exists():
    ORACLE_SCRIPT = SCRIPT_DIR / "product_lineage_oracle.py"
if not ORACLE_SCRIPT.exists():
    _fallback = SKILL_ROOT.parents[2] / "definitions/product-management/validators/product_lineage_oracle.py"
    if _fallback.exists():
        ORACLE_SCRIPT = _fallback

from elicit_5w1h import ElicitationEngine, format_report_console
from aurakl_validator import AuraklValidator, LumenValidator, format_verdict_console


def cmd_elicit(args: argparse.Namespace) -> int:
    engine = ElicitationEngine()
    if args.input:
        engine.ingest(args.input)

    if args.set_slot:
        k, v = args.set_slot
        try:
            parsed_v = json.loads(v)
            engine.set_slot(k, parsed_v)
        except Exception:
            engine.set_slot(k, v)

    report = engine.assess()

    if args.export:
        if not report.can_proceed:
            print(f"Error: Requirements incomplete (score {report.completeness_score}%), cannot export.", file=sys.stderr)
            for q in report.questions:
                print(f"- {q.question}", file=sys.stderr)
            return 1
        out = engine.export_requirement_analysis()
        Path(args.export).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ Successfully exported valid requirement_analysis to: {args.export}")
        return 0

    if args.json:
        out_dict = {
            "completeness_score": report.completeness_score,
            "can_proceed": report.can_proceed,
            "fulfilled_slots": report.fulfilled_slots,
            "missing_slots": report.missing_slots,
            "diagnostics": report.slot_diagnostics,
            "questions": [q.__dict__ for q in report.questions],
        }
        print(json.dumps(out_dict, ensure_ascii=False, indent=2))
    else:
        print(format_report_console(report))

    return 0 if report.can_proceed else 2


def cmd_validate(args: argparse.Namespace) -> int:
    validator = AuraklValidator()

    if args.suite:
        p = Path(args.suite)
        if not p.exists():
            print(f"Error: suite file not found: {args.suite}", file=sys.stderr)
            return 1
        suite_data = json.loads(p.read_text(encoding="utf-8"))
        verdict = validator.validate_suite_oracle(suite_data)
    elif args.artifact:
        p = Path(args.artifact)
        if not p.exists():
            print(f"Error: artifact file not found: {args.artifact}", file=sys.stderr)
            return 1
        data = json.loads(p.read_text(encoding="utf-8"))
        target_schema = args.schema or args.kind or "requirement-analysis"
        verdict = validator.validate_artifact(target_schema, data)
    else:
        print("Error: either --artifact or --suite must be provided.", file=sys.stderr)
        return 1

    if args.json:
        out = {
            "passed": verdict.passed,
            "kind": verdict.kind,
            "issues": [i.__dict__ for i in verdict.issues],
            "observations": verdict.observations,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(format_verdict_console(verdict))

    return 0 if verdict.passed else 2


def cmd_calc_metrics(args: argparse.Namespace) -> int:
    validator = AuraklValidator()
    if not args.criteria:
        print("Error: --criteria is required to calculate metrics.", file=sys.stderr)
        return 1

    crit_path = Path(args.criteria)
    if not crit_path.exists():
        print(f"Error: file not found: {args.criteria}", file=sys.stderr)
        return 1
    crit_raw = json.loads(crit_path.read_text(encoding="utf-8"))
    crit_data = crit_raw.get("acceptance_criteria_set") or crit_raw.get("acceptance_criteria") or crit_raw

    results = {
        "negative_ratio": validator.calc_negative_ratio(crit_data)
    }

    inv_data = None
    if args.invariants:
        inv_path = Path(args.invariants)
        if not inv_path.exists():
            print(f"Error: file not found: {args.invariants}", file=sys.stderr)
            return 1
        inv_raw = json.loads(inv_path.read_text(encoding="utf-8"))
        inv_data = inv_raw.get("product_invariant_set") or inv_raw.get("product_invariants") or inv_raw
    elif isinstance(crit_raw, dict) and ("product_invariant_set" in crit_raw or "product_invariants" in crit_raw):
        inv_data = crit_raw.get("product_invariant_set") or crit_raw.get("product_invariants")

    if inv_data:
        results["invariant_coverage"] = validator.calc_invariant_coverage(inv_data, crit_data)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print("=" * 65)
        print("  Aurakl SOP Stage 06 Automated Metrics Report")
        print("=" * 65)
        nr = results["negative_ratio"]
        nr_icon = "✅ Compliant" if nr["meets_safety_threshold"] else "❌ Non-Compliant (must be >= 30.0%)"
        print(f"Negative Defense Ratio: {nr['negative_ratio_pct']}% ({nr_icon})")
        print(f"  - Defensive scenarios: {nr['negative_defense_scenarios']} / Total scenarios: {nr['total_scenarios']}")

        if "invariant_coverage" in results:
            ic = results["invariant_coverage"]
            ic_icon = "✅ 100% Full Coverage" if ic["is_full_coverage"] else "❌ Non-Compliant (must be 10000 bp)"
            print(f"Invariant Coverage: {ic['coverage_pct']}% ({ic['coverage_basis_points']} bp) ({ic_icon})")
            print(f"  - Covered invariants: {ic['covered_invariants']} / Total: {ic['total_invariants']}")
            if ic["missing_invariants"]:
                print(f"  - Missing invariants: {ic['missing_invariants']}")
        print("=" * 65)

    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    if not ORACLE_SCRIPT.exists():
        print(f"Error: Oracle script not found at {ORACLE_SCRIPT}", file=sys.stderr)
        return 1

    payload_input = None
    if args.suite:
        p = Path(args.suite)
        if not p.exists():
            print(f"Error: suite file not found: {args.suite}", file=sys.stderr)
            return 1
        payload_input = json.loads(p.read_text(encoding="utf-8"))

    op = args.op or "pipeline"
    if payload_input and isinstance(payload_input, dict):
        if op == "invariants_coverage" and "invariants" not in payload_input:
            payload_input = {
                "invariants": payload_input.get("product_invariant_set") or payload_input,
                "candidate": payload_input.get("acceptance_criteria_set") or payload_input,
            }
        elif op == "negative_ratio" and "candidate" not in payload_input:
            payload_input = {
                "candidate": payload_input.get("acceptance_criteria_set") or payload_input,
            }
        elif op == "review_consistency" and "report" not in payload_input:
            payload_input = {
                "report": payload_input.get("product_readiness_review_report") or payload_input,
            }

    payload = {"operation": op, "input": payload_input}

    proc = subprocess.run(
        [sys.executable, str(ORACLE_SCRIPT), json.dumps(payload, separators=(",", ":"))],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"Error running oracle: {proc.stderr}", file=sys.stderr)
        return proc.returncode

    if args.json:
        print(proc.stdout)
    else:
        try:
            res = json.loads(proc.stdout)
            verdict = res.get("verdict")
            obs = res.get("observation", {})
            v_icon = "✅ PASSED" if verdict == "passed" else "❌ FAILED"
            print("=" * 65)
            print(f"  Aurakl Deterministic Oracle Verdict: {v_icon} (Op: {op})")
            print("=" * 65)
            if obs.get("mismatches"):
                print("[Mismatches]:")
                for m in obs["mismatches"]:
                    print(f"  • {m}")
            if obs.get("computed"):
                print(f"[Recomputed Data]: {json.dumps(obs['computed'], ensure_ascii=False, indent=2)}")
            print("=" * 65)
        except Exception:
            print(proc.stdout)

    return 0


def cmd_schemas(args: argparse.Namespace) -> int:
    validator = AuraklValidator()
    schemas = validator.list_all_schemas()
    if args.json:
        print(json.dumps(schemas, ensure_ascii=False, indent=2))
        return 0

    print("=" * 85)
    print(f"  Aurakl Product Management 31-Schema Catalog & SOP Mapping")
    print("=" * 85)
    for idx, s in enumerate(schemas, 1):
        req_summary = ", ".join(s["required_fields"][:3])
        if len(s["required_fields"]) > 3:
            req_summary += f" (+{len(s['required_fields']) - 3} more)"
        print(f"{idx:02d}. {s['filename']:<36} | {s['title']:<30}")
        if s["description"]:
            print(f"    Description: {s['description']}")
        print(f"    Required Fields: [{req_summary}]")
    print("=" * 85)
    return 0


def cmd_standards(args: argparse.Namespace) -> int:
    validator = AuraklValidator()
    standards = validator.load_standards()

    if args.json:
        print(json.dumps(standards, ensure_ascii=False, indent=2))
        return 0

    if getattr(args, "id", None):
        std_id = args.id
        if not std_id.startswith("pm-std-") and f"pm-std-{std_id}" in standards:
            std_id = f"pm-std-{std_id}"
        if std_id not in standards:
            print(f"Error: Standard '{std_id}' not found. Available standards:\n  " + "\n  ".join(standards.keys()), file=sys.stderr)
            return 1
        std = standards[std_id]
        spec = std.get("spec", {})
        meta = std.get("metadata", {})
        print("=" * 80)
        print(f"  Aurakl Quality Standard: {std_id}")
        print("=" * 80)
        print(f"Standard Name: {spec.get('name')}")
        print(f"Change Reason: {meta.get('change_reason')}")
        print(f"Governs Step: {meta.get('labels', {}).get('governs_step')}")
        print("\n[Quality Defense Rules]:")
        for idx, r in enumerate(spec.get("rules", []), 1):
            print(f"  {idx}. [{r.get('id')}]: {r.get('statement')}")
            if r.get("criterion_hint"):
                print(f"     Criterion Hint: {r.get('criterion_hint')}")
        print("=" * 80)
        return 0

    print("=" * 88)
    print(f"  Aurakl Product Management Quality Standards Catalog")
    print("=" * 88)
    for idx, (sid, std) in enumerate(sorted(standards.items()), 1):
        spec = std.get("spec", {})
        meta = std.get("metadata", {})
        step = meta.get("labels", {}).get("governs_step", "-")
        rules = spec.get("rules", [])
        print(f"{idx:02d}. {sid:<36} | Governs Step: {step:<34}")
        print(f"    Name: {spec.get('name')} ({len(rules)} quality rules)")
        for r in rules[:2]:
            print(f"      • {r.get('id')}: {r.get('statement')}")
        if len(rules) > 2:
            print(f"      • ... ({len(rules)} total rules)")
    print("=" * 88)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    from aurakl_renderer import AuraklMarkdownRenderer, LumenMarkdownRenderer, render_all_artifacts
    renderer = AuraklMarkdownRenderer()

    if getattr(args, "json_file", None) and getattr(args, "template", None):
        jp = Path(args.json_file)
        if not jp.exists():
            print(f"Error: file not found: {jp}", file=sys.stderr)
            return 1
        data = json.loads(jp.read_text(encoding="utf-8"))
        tpl_id = args.template if args.template.startswith("pm-tpl-") else f"pm-tpl-{args.template}"

        if "requirement-analysis" in tpl_id:
            md = renderer.render_requirement_analysis(data)
        elif "competitive-analysis" in tpl_id:
            md = renderer.render_competitive_analysis(data)
        elif "user-story-set" in tpl_id:
            md = renderer.render_user_stories(data)
        elif "prd" in tpl_id:
            md = renderer.render_prd(data)
        elif "product-invariants" in tpl_id:
            md = renderer.render_product_invariants(data)
        elif "acceptance-criteria" in tpl_id:
            md = renderer.render_acceptance_criteria(data)
        elif "review-report" in tpl_id:
            md = renderer.render_review_report(data)
        else:
            print(f"Error: unsupported template: {tpl_id}", file=sys.stderr)
            return 1

        if args.out:
            out_p = Path(args.out)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(md, encoding="utf-8")
            print(f"Rendered markdown written to {out_p}")
        else:
            print(md)
        return 0

    src_dir = Path(args.source or "AIP/source")
    out_dir = Path(args.out or "AIP")
    if not src_dir.exists():
        print(f"Error: source directory not found: {src_dir}", file=sys.stderr)
        return 1

    reports = render_all_artifacts(src_dir, out_dir)
    if args.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        print("=" * 65)
        print(f"  Aurakl Markdown Artifacts Batch Generation Report (Target: {out_dir})")
        print("=" * 65)
        for k, path in reports.items():
            print(f"  • [SUCCESS] {k} -> {path}")
        print("=" * 65)
    return 0


def cmd_cartesian(args: argparse.Namespace) -> int:
    from cartesian_coverage_engine import CartesianCoverageEngine

    prd_data = None
    if getattr(args, "prd", None):
        p = Path(args.prd)
        if not p.exists():
            print(f"Error: PRD file not found: {args.prd}", file=sys.stderr)
            return 1
        prd_data = json.loads(p.read_text(encoding="utf-8"))

    stories_data = None
    if getattr(args, "stories", None):
        p = Path(args.stories)
        if p.exists():
            stories_data = json.loads(p.read_text(encoding="utf-8"))

    invariants_data = None
    if getattr(args, "invariants", None):
        p = Path(args.invariants)
        if p.exists():
            invariants_data = json.loads(p.read_text(encoding="utf-8"))

    criteria_data = None
    if getattr(args, "criteria", None):
        p = Path(args.criteria)
        if p.exists():
            criteria_data = json.loads(p.read_text(encoding="utf-8"))

    engine = CartesianCoverageEngine()
    report = engine.run_full_audit(
        prd_data=prd_data,
        stories_data=stories_data,
        invariants_data=invariants_data,
        criteria_data=criteria_data,
    )

    if getattr(args, "out", None):
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if args.json or out_path.suffix == ".json":
            # Convert report dataclass to json dict
            from dataclasses import asdict
            out_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=list), encoding="utf-8")
        else:
            md_text = engine.render_markdown_report(report)
            out_path.write_text(md_text, encoding="utf-8")
        print(f"✅ Cartesian audit report exported to: {out_path}")

    if args.json:
        from dataclasses import asdict
        print(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=list))
    else:
        print(engine.render_markdown_report(report))

    return 0 if report.overall_status in ("PASSED", "WARNING") else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="aurakl_pm",
        description="Aurakl Product Management Unified CLI Toolkit",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # elicit
    p_elicit = subparsers.add_parser("elicit", help="5W1H elicitation and clarification")
    p_elicit.add_argument("--input", help="Path to brief file or raw text")
    p_elicit.add_argument("--set-slot", nargs=2, metavar=("KEY", "VAL"), help="Update specific slot")
    p_elicit.add_argument("--export", help="Export to requirement_analysis JSON")
    p_elicit.add_argument("--json", action="store_true", help="Output JSON")

    # validate
    p_val = subparsers.add_parser("validate", help="Five-dimensional acceptance gate")
    p_val.add_argument("--artifact", help="Path to artifact JSON")
    p_val.add_argument("--schema", "--kind", dest="schema", help="Schema name or filename (out of all 31 schemas)")
    p_val.add_argument("--suite", help="Path to complete suite JSON")
    p_val.add_argument("--json", action="store_true", help="Output JSON")

    # calc-metrics
    p_calc = subparsers.add_parser("calc-metrics", help="Calculate invariant coverage and negative ratio")
    p_calc.add_argument("--criteria", required=True, help="Path to acceptance criteria JSON")
    p_calc.add_argument("--invariants", help="Path to product invariants JSON")
    p_calc.add_argument("--json", action="store_true", help="Output JSON")

    # audit
    p_audit = subparsers.add_parser("audit", help="Run deterministic lineage oracle")
    p_audit.add_argument("--suite", required=True, help="Path to full golden product suite JSON")
    p_audit.add_argument("--op", choices=["pipeline", "invariants_coverage", "negative_ratio", "review_consistency"], default="pipeline")
    p_audit.add_argument("--json", action="store_true", help="Output JSON")

    # render
    p_render = subparsers.add_parser("render", help="Render stage JSON artifacts into template-conforming Markdown")
    p_render.add_argument("--source", help="Source directory containing JSON artifacts (e.g. AIP/source)")
    p_render.add_argument("--out", help="Output directory or target file path")
    p_render.add_argument("--json-file", help="Specific JSON file to render")
    p_render.add_argument("--template", help="Target template ID (e.g. pm-tpl-requirement-analysis)")
    p_render.add_argument("--json", action="store_true", help="Output JSON")

    # schemas
    p_schemas = subparsers.add_parser("schemas", help="List all 31 Aurakl schemas")
    p_schemas.add_argument("--json", action="store_true", help="Output JSON")

    # standards
    p_standards = subparsers.add_parser("standards", help="List and inspect Aurakl quality standards")
    p_standards.add_argument("--id", help="Inspect specific standard ID (e.g. pm-std-product-invariants)")
    p_standards.add_argument("--json", action="store_true", help="Output JSON")

    # cartesian
    p_cart = subparsers.add_parser("cartesian", help="Run Cartesian product completeness and closure audit")
    p_cart.add_argument("--prd", help="Path to PRD JSON")
    p_cart.add_argument("--stories", help="Path to user stories JSON")
    p_cart.add_argument("--invariants", help="Path to product invariants JSON")
    p_cart.add_argument("--criteria", help="Path to acceptance criteria JSON")
    p_cart.add_argument("--out", help="Path to export markdown or json audit report")
    p_cart.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    if args.subcommand == "elicit":
        return cmd_elicit(args)
    elif args.subcommand == "validate":
        return cmd_validate(args)
    elif args.subcommand == "calc-metrics":
        return cmd_calc_metrics(args)
    elif args.subcommand == "audit":
        return cmd_audit(args)
    elif args.subcommand == "render":
        return cmd_render(args)
    elif args.subcommand == "schemas":
        return cmd_schemas(args)
    elif args.subcommand == "standards":
        return cmd_standards(args)
    elif args.subcommand == "cartesian":
        return cmd_cartesian(args)
    else:
        parser.print_help()
        return 0



if __name__ == "__main__":
    sys.exit(main())
