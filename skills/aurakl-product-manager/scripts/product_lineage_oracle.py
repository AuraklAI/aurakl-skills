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

    personas = journey.get("personas", [])
    if personas:
        persona_roles = " ".join(p.get("role", "") for p in personas).lower()
        has_admin = any(any(kw in p.get("role", "").lower() for kw in ["admin", "operator", "dispatcher", "manager", "operations", "supervisor", "finance", "\u8ba1\u8c03", "\u7ba1\u7406", "\u8fd0\u8425", "\u4e3b\u7ba1", "\u8d22\u52a1"]) for p in personas)
        if not has_admin:
            mismatches.append("missing_admin_or_operational_persona")
        if len(personas) < 3:
            mismatches.append(f"personas_insufficient_for_multi_role:{len(personas)}")
        story_roles = {s.get("as_a") for s in stories.get("stories", [])}
        if len(story_roles) < 2:
            mismatches.append(f"story_roles_monolithic:{len(story_roles)}")
        
        # Per-persona touchpoint, scenario, and story cardinality checks
        stages = journey.get("journey_stages", [])
        all_tps = [tp for stg in stages for tp in stg.get("touchpoints", [])]
        scenarios = journey.get("scenarios", [])
        all_stories = stories.get("stories", [])
        for p in personas:
            pid = p.get("id")
            p_tps = [tp for tp in all_tps if tp.get("actor_persona_id") == pid]
            if len(p_tps) < 2:
                mismatches.append(f"persona_touchpoints_insufficient:{pid}")
            p_scns = [sc for sc in scenarios if sc.get("persona_id") == pid]
            if len(p_scns) < 2:
                mismatches.append(f"persona_scenarios_insufficient:{pid}")
            p_stories = [st for st in all_stories if st.get("persona_id") == pid]
            if len(p_stories) < 2:
                mismatches.append(f"persona_stories_insufficient:{pid}")

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
        if len(f.get("inputs", [])) < 1:
            mismatches.append(f"feature_inputs_missing:{fid}")
        if len(f.get("outputs", [])) < 1:
            mismatches.append(f"feature_outputs_missing:{fid}")
        if len(f.get("error_cases", [])) < 1:
            mismatches.append(f"feature_error_cases_missing:{fid}")
        if len(f.get("data_dependencies", [])) < 1:
            mismatches.append(f"feature_data_dependencies_missing:{fid}")
    ia_mods = [m.get("module_id") for m in prd.get("information_architecture", {}).get("modules", []) if m.get("module_id")]
    feat_mods = {f.get("module_id") for f in features if f.get("module_id")}
    for m in ia_mods:
        if m not in feat_mods:
            mismatches.append(f"ia_module_uncovered:{m}")

    all_story_ids = {s.get("id") for s in stories.get("stories", []) if s.get("id")}
    covered_story_ids = {sid for f in features for sid in f.get("derived_from_user_stories", [])}
    for sid in sorted(all_story_ids - covered_story_ids):
        mismatches.append(f"uncovered_user_story_in_prd:{sid}")

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

    # Invariant severity vs Feature priority order consistency check
    critical_inv_ids = set()
    for cat in INVARIANT_CATEGORIES:
        for item in invariants.get(cat, []):
            if item.get("severity") == "CRITICAL" and item.get("invariant_id"):
                critical_inv_ids.add(item["invariant_id"])

    # Build story_id -> list of features mapping
    story_to_features = {}
    for f in features:
        fid = f.get("feature_id") or f.get("id")
        prio = f.get("priority", "P1")
        for sid in f.get("derived_from_user_stories", []):
            story_to_features.setdefault(sid, []).append((fid, prio))

    # Map invariants to features via criteria scenarios and direct references
    inv_to_features = {}
    for scn in criteria.get("scenarios", []):
        inv_id = scn.get("verifies_invariant_id")
        sid = scn.get("story_id")
        if inv_id and sid and sid in story_to_features:
            for fid, prio in story_to_features[sid]:
                inv_to_features.setdefault(inv_id, set()).add((fid, prio))

    for f in features:
        fid = f.get("feature_id") or f.get("id")
        prio = f.get("priority", "P1")
        direct_invs = f.get("protects_invariants", []) or f.get("enforces_invariants", []) or []
        for inv_ref in direct_invs:
            inv_to_features.setdefault(inv_ref, set()).add((fid, prio))

    for cinv in critical_inv_ids:
        associated_features = inv_to_features.get(cinv, set())
        if associated_features:
            has_p0 = any(prio == "P0" for _, prio in associated_features)
            if not has_p0:
                feat_summary = ", ".join(f"{fid}({prio})" for fid, prio in associated_features)
                mismatches.append(
                    f"invariant_priority_conflict: Invariant '{cinv}' is CRITICAL, but all its protecting features are non-P0 ({feat_summary}). Critical invariants must be protected by at least one P0 feature."
                )

    # Temporal reality check for milestones
    import re
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    for ms in prd.get("milestones", []):
        m_date_str = (
            ms.get("target_date")
            or ms.get("target_completion_date")
            or ms.get("estimated_duration")
            or ms.get("estimated_timeline")
            or ms.get("date")
            or ""
        )
        date_matches = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", str(m_date_str))
        for ds in date_matches:
            try:
                dt = datetime.strptime(ds, "%Y-%m-%d").date()
                if (today - dt).days > 60:
                    mismatches.append(
                        f"expired_milestone_schedule: Milestone date '{ds}' is expired relative to current execution date '{today}'."
                    )
            except Exception:
                pass

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
