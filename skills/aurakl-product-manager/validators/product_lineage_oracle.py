#!/usr/bin/env python3
"""
Aurakl Product Lineage Oracle Validator (v2.1.0)

Deterministic, version-locked validation asset for the product-management
definition package. The runtime supplies one frozen JSON argument; this script
has no Aurakl integration and never decides overall acceptance. It only
recomputes lineage, coverage and ratio claims from frozen inputs and returns
the standard CapabilityProbe verdict envelope.

Operations (input.operation):
- "pipeline"               full 7-artifact lineage recompute (step 07 audit)
- "invariants_coverage"    recompute invariant coverage from scenarios (step 06)
- "negative_ratio"         recompute negative/defense scenario ratio (step 06)
- "review_consistency"     recompute readiness gate + audit-field consistency
"""

from __future__ import annotations

import json
import sys
from typing import Any

INVARIANT_CATEGORIES = [
    "state_invariants",
    "data_integrity_invariants",
    "security_and_privacy_invariants",
    "ux_and_safety_invariants",
]
NEGATIVE_TYPES = ["negative_defense", "fault_recovery"]


def _envelope(passed: bool, algorithm: str, checks: dict, mismatches: list, computed: dict) -> dict:
    return {
        "verdict": "passed" if passed else "failed",
        "observation": {
            "algorithm": algorithm,
            "checks": checks,
            "mismatches": mismatches,
            "computed": computed,
        },
    }


def invariant_ids(invariants: dict) -> set:
    out = set()
    for cat in INVARIANT_CATEGORIES:
        for item in invariants.get(cat, []):
            if item.get("invariant_id"):
                out.add(item["invariant_id"])
    return out


def covered_invariant_ids(candidate: dict) -> set:
    return {
        s.get("verifies_invariant_id")
        for s in candidate.get("scenarios", [])
        if s.get("verifies_invariant_id")
    }


def negative_counts(candidate: dict) -> tuple[int, int]:
    scenarios = [s for s in candidate.get("scenarios", []) if s.get("scenario_type")]
    neg = sum(1 for s in scenarios if s["scenario_type"] in NEGATIVE_TYPES)
    return (neg, len(scenarios))


def run_pipeline(data: dict) -> dict:
    req = data.get("requirement_analysis", {})
    comp = data.get("competitive_intelligence", {})
    journey = data.get("user_journey_model", {})
    stories = data.get("user_story_set", {})
    prd = data.get("comprehensive_prd", {})
    invariants = data.get("product_invariant_set", {})
    criteria = data.get("acceptance_criteria_set", {})
    report = data.get("product_readiness_review_report", {})
    mismatches: list[str] = []

    five = req.get("five_w_one_h", {})
    for k in ["why", "who", "what", "when", "where", "how"]:
        if not five.get(k):
            mismatches.append(f"missing_5w1h:{k}")

    dv = req.get("demand_validation", {})
    if not dv.get("problem_nature") or not dv.get("current_workarounds"):
        mismatches.append("demand_validation_incomplete")

    competitors = comp.get("competitors", [])
    if len(competitors) < 2:
        mismatches.append(f"competitor_count:{len(competitors)}")
    if not comp.get("why_we_win"):
        mismatches.append("missing_why_we_win")

    touchpoints = [
        tp.get("touchpoint_id")
        for stage in journey.get("journey_stages", [])
        for tp in stage.get("touchpoints", [])
    ]
    covered_tp = {s.get("related_touchpoint_id") for s in stories.get("stories", [])}
    for tp in touchpoints:
        if tp and tp not in covered_tp:
            mismatches.append(f"touchpoint_uncovered:{tp}")

    eh = prd.get("error_handling_and_recovery", {})
    if not eh.get("system_errors") or not eh.get("interruption_and_recovery"):
        mismatches.append("prd_error_handling_incomplete")
    tp_plan = prd.get("tracking_plan", {})
    if not tp_plan.get("north_star_metric") or not tp_plan.get("event_dictionary"):
        mismatches.append("prd_tracking_plan_incomplete")

    features = prd.get("features", [])
    if len(features) < 3:
        mismatches.append(f"prd_features_insufficient:{len(features)}")
    for f in features:
        fid = f.get("feature_id", "UNKNOWN")
        if len(f.get("business_rules", [])) < 3:
            mismatches.append(f"feature_rules_insufficient:{fid}")
        if len(f.get("preconditions", [])) < 2 or len(f.get("postconditions", [])) < 2:
            mismatches.append(f"feature_pre_post_insufficient:{fid}")
    ia_mods = [m.get("module_id") for m in prd.get("information_architecture", {}).get("modules", []) if m.get("module_id")]
    feat_mods = {f.get("module_id") for f in features if f.get("module_id")}
    for m in ia_mods:
        if m not in feat_mods:
            mismatches.append(f"ia_module_uncovered:{m}")

    all_inv = invariant_ids(invariants)
    cov_inv = covered_invariant_ids(criteria)
    missing_inv = sorted(all_inv - cov_inv)
    for inv in missing_inv:
        mismatches.append(f"invariant_uncovered:{inv}")

    neg, total = negative_counts(criteria)
    ratio = (neg / total * 100.0) if total else 0.0
    if ratio < 30.0:
        mismatches.append(f"negative_ratio:{ratio:.1f}")

    if report.get("readiness_status") != "READY_FOR_DEV":
        mismatches.append(f"readiness_status:{report.get('readiness_status')}")

    computed = {
        "invariant_total": len(all_inv),
        "invariant_covered": len(all_inv & cov_inv),
        "negative_ratio_pct": round(ratio, 1),
        "touchpoint_total": len(touchpoints),
        "touchpoint_covered": len([t for t in touchpoints if t in covered_tp]),
    }
    checks = {
        "five_w_one_h": not any(m.startswith("missing_5w1h") for m in mismatches),
        "demand_validation": "demand_validation_incomplete" not in mismatches,
        "competitors": not any(m.startswith("competitor_count") for m in mismatches),
        "touchpoint_coverage": not any(m.startswith("touchpoint_uncovered") for m in mismatches),
        "prd_contracts": "prd_error_handling_incomplete" not in mismatches
        and "prd_tracking_plan_incomplete" not in mismatches,
        "prd_features_substantive": not any(m.startswith("prd_features") or m.startswith("feature_") or m.startswith("ia_module") for m in mismatches),
        "invariant_coverage": not missing_inv,
        "negative_ratio": ratio >= 30.0,
        "readiness": report.get("readiness_status") == "READY_FOR_DEV",
    }
    return _envelope(not mismatches, "product-lineage-oracle-v2/pipeline", checks, mismatches, computed)


def run_invariants_coverage(data: dict) -> dict:
    invariants = data.get("invariants") or {}
    candidate = data.get("candidate") or {}
    mismatches: list[str] = []

    all_inv = invariant_ids(invariants)
    cov_inv = covered_invariant_ids(candidate)
    missing = sorted(all_inv - cov_inv)
    extra = sorted(cov_inv - all_inv)
    for inv in missing:
        mismatches.append(f"invariant_uncovered:{inv}")
    for inv in extra:
        mismatches.append(f"scenario_references_unknown_invariant:{inv}")
    if not all_inv:
        mismatches.append("no_invariants_declared")

    ratio_bp = round(len(all_inv & cov_inv) / len(all_inv) * 10000) if all_inv else 0

    # producer self-reported matrix must agree with the recomputation
    matrix = candidate.get("invariant_coverage_matrix") or {}
    claimed = {
        "total_invariants_count": matrix.get("total_invariants_count"),
        "covered_invariants_count": matrix.get("covered_invariants_count"),
        "coverage_ratio_basis_points": matrix.get("coverage_ratio_basis_points"),
    }
    actual = {
        "total_invariants_count": len(all_inv),
        "covered_invariants_count": len(all_inv & cov_inv),
        "coverage_ratio_basis_points": ratio_bp,
    }
    for k in claimed:
        if claimed[k] != actual[k]:
            mismatches.append(f"matrix_field_drift:{k}:{claimed[k]}!={actual[k]}")
    if matrix.get("all_invariants_covered") is not True:
        mismatches.append("matrix_all_covered_flag_not_true")

    checks = {
        "coverage_complete": not missing and not extra and bool(all_inv),
        "matrix_consistent": not any(m.startswith("matrix_") for m in mismatches),
    }
    computed = dict(actual, missing=missing, extra=extra)
    return _envelope(not mismatches, "product-lineage-oracle-v2/invariants-coverage", checks, mismatches, computed)


def run_negative_ratio(data: dict) -> dict:
    candidate = data.get("candidate") or {}
    mismatches: list[str] = []

    neg, total = negative_counts(candidate)
    ratio = (neg / total * 100.0) if total else 0.0
    if total == 0:
        mismatches.append("no_scenarios")
    if ratio < 30.0:
        mismatches.append(f"negative_ratio_below_threshold:{ratio:.1f}")

    dist = candidate.get("negative_case_distribution") or {}
    claimed = {
        "total_scenarios_count": dist.get("total_scenarios_count"),
        "negative_defense_scenarios_count": dist.get("negative_defense_scenarios_count"),
    }
    actual = {
        "total_scenarios_count": total,
        "negative_defense_scenarios_count": neg,
    }
    for k in claimed:
        if claimed[k] != actual[k]:
            mismatches.append(f"distribution_field_drift:{k}:{claimed[k]}!={actual[k]}")
    if dist.get("meets_safety_threshold") is not True:
        mismatches.append("threshold_flag_not_true")

    checks = {"ratio_meets_threshold": ratio >= 30.0 and total > 0,
              "distribution_consistent": not any(m.startswith("distribution_") for m in mismatches)}
    computed = dict(actual, negative_percentage=round(ratio, 1))
    return _envelope(not mismatches, "product-lineage-oracle-v2/negative-ratio", checks, mismatches, computed)


def run_review_consistency(data: dict) -> dict:
    report = data.get("report") or {}
    mismatches: list[str] = []

    blocking = report.get("blocking_findings") or []
    status = report.get("readiness_status")
    if blocking and status == "READY_FOR_DEV":
        mismatches.append("blocking_findings_forbid_ready_status")
    if not blocking and status != "READY_FOR_DEV":
        mismatches.append("no_blocking_findings_but_not_ready")

    trace = report.get("traceability_audit") or {}
    for k in [
        "requirements_to_stories_coverage_pct",
        "stories_to_features_coverage_pct",
        "invariants_to_criteria_coverage_pct",
    ]:
        if trace.get(k) != 100.0:
            mismatches.append(f"traceability_not_full:{k}:{trace.get(k)}")
    if trace.get("broken_reference_count") != 0:
        mismatches.append(f"broken_reference_count:{trace.get('broken_reference_count')}")

    inv_audit = report.get("invariant_enforcement_audit") or {}
    if inv_audit.get("has_unprotected_invariants") is not False:
        mismatches.append("unprotected_invariants_flag_not_false")
    total_inv = inv_audit.get("total_invariants")
    enforced = inv_audit.get("critically_enforced_count")
    if not isinstance(total_inv, int) or total_inv < 1 or not isinstance(enforced, int) or enforced < 1 or enforced > total_inv:
        mismatches.append("invariant_enforcement_counts_inconsistent")

    checks = {
        "readiness_gate": not any("readiness" in m or "blocking" in m for m in mismatches),
        "traceability_full": not any(m.startswith("traceability") or m.startswith("broken") for m in mismatches),
        "invariant_enforcement": not any(m.startswith("unprotected") or m.startswith("invariant_enforcement") for m in mismatches),
    }
    computed = {
        "blocking_finding_count": len(blocking),
        "readiness_status": status,
        "traceability_pct": {k: trace.get(k) for k in [
            "requirements_to_stories_coverage_pct",
            "stories_to_features_coverage_pct",
            "invariants_to_criteria_coverage_pct",
        ]},
        "broken_reference_count": trace.get("broken_reference_count"),
    }
    return _envelope(not mismatches, "product-lineage-oracle-v2/review-consistency", checks, mismatches, computed)


OPS = {
    "pipeline": run_pipeline,
    "invariants_coverage": run_invariants_coverage,
    "negative_ratio": run_negative_ratio,
    "review_consistency": run_review_consistency,
}


def main() -> int:
    try:
        payload = json.loads(sys.argv[1])
        op = payload.get("operation")
        handler = OPS.get(op)
        if handler is None:
            print(json.dumps({
                "verdict": "inconclusive",
                "observation": {"error": f"unknown_operation:{op}", "mismatches": ["unknown_operation"]},
            }, ensure_ascii=False))
            return 0
        result = handler(payload.get("input") or payload)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (KeyError, TypeError, ValueError, IndexError, json.JSONDecodeError) as error:
        print(json.dumps({
            "verdict": "inconclusive",
            "observation": {"error": str(error), "mismatches": ["invalid_input"]},
        }, ensure_ascii=False, separators=(",", ":")))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
