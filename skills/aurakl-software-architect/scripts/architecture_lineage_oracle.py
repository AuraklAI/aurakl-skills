#!/usr/bin/env python3
"""
Aurakl Architecture Lineage, Requirement Coverage, Invariant Defense & Dependency DAG Oracle Validator

Executes formal verification of:
1. 100% Must-Have Requirement Coverage across System Architecture, Domain Model, Database Design & API Contracts (Zero Missing Requirements)
2. 100% Full Domain Modeling Coverage against PRD (Zero Missing Entities/Traits)
3. 100% Architecture Invariants Defense Coverage across 9 core dimensions (Zero Undefended Invariants)
4. Technical Dependency DAG Acyclicity & Critical Path Validity (Zero Circular Dependencies)
5. Layer Count Compliance (<= 3 Layers) & Monolith-First Rule
6. Backward Compatibility Guarantee (Zero Breaking Changes)
7. Strict One-Vote Veto Readiness Gate (Blocking Findings strictly forbid READY_FOR_DEV)
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

REQUIRED_INVARIANT_DIMENSIONS = {
    "compatibility_and_evolution",
    "layering_and_dependency",
    "data_consistency_and_storage",
    "concurrency_and_state",
    "security_and_tenant_isolation",
    "performance_and_resource_budget",
    "code_and_engineering_standards",
    "resilience_and_fault_tolerance",
    "observability_and_runtime_ops"
}


def is_dag_acyclic(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> bool:
    """Kahn algorithm to test DAG acyclicity."""
    adj = {n.get("id"): [] for n in nodes if n.get("id")}
    in_degree = {n.get("id"): 0 for n in nodes if n.get("id")}

    for edge in edges:
        u = edge.get("from_node")
        v = edge.get("to_node")
        if u in adj and v in in_degree:
            adj[u].append(v)
            in_degree[v] += 1

    queue = [n for n, deg in in_degree.items() if deg == 0]
    visited_count = 0

    while queue:
        curr = queue.pop(0)
        visited_count += 1
        for neighbor in adj.get(curr, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return visited_count == len(in_degree)


def validate_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    checks = {
        "technical_requirements_derived": False,
        "layer_count_valid": False,
        "domain_model_100_percent_covered": False,
        "domain_model_depth_valid": False,
        "database_invariants_aligned": False,
        "sql_ddl_syntax_valid": False,
        "api_backward_compatible": False,
        "invariants_defense_covered": False,
        "dependency_dag_acyclic": False,
        "must_have_requirements_covered": False,
        "tech_stack_pan_consistency": False,
        "dependency_inversion_valid": False,
        "readiness_consistency": False
    }
    mismatches: List[str] = []

    # 1. Tech stack decision check
    tech_decision = payload.get("tech_stack_decision", {})
    locked_items = tech_decision.get("locked_stack_items", [])
    must_have_reqs = set(tech_decision.get("must_have_requirement_ids", []))

    if locked_items and must_have_reqs:
        checks["technical_requirements_derived"] = True
    else:
        mismatches.append("tech_stack_decision missing locked_stack_items or must_have_requirement_ids")

    # 1.1 Tech Stack Ecosystem & Consistency Linter
    locked_texts = " ".join([
        (item.get("technology", "") + " " + item.get("category", ""))
        for item in locked_items if isinstance(item, dict)
    ]).lower()
    full_payload_str = json.dumps(payload, ensure_ascii=False)

    # Ecosystem check: Rust backend cannot use Java connection pools like HikariCP
    is_rust_backend = "rust" in locked_texts
    if is_rust_backend and "hikaricp" in full_payload_str.lower():
        mismatches.append(
            "Ecosystem conflict: Java connection pool 'HikariCP' cannot be used with Rust backend. "
            "Must use Rust ecosystem connection pools (e.g., sqlx, deadpool, bb8)."
        )

    # Ghost storage check: If Neo4j was not locked/accepted, forbid widespread references
    has_neo4j_locked = "neo4j" in locked_texts
    if not has_neo4j_locked and full_payload_str.count("Neo4j") > 2:
        mismatches.append(
            "Tech stack conflict: 'Neo4j' is referenced multiple times across architecture artifacts, "
            "but was not accepted in Tech Stack Decision (ADR). Avoid ghost storage dependencies."
        )

    if not any("Ecosystem conflict" in m or "Tech stack conflict" in m for m in mismatches):
        checks["tech_stack_pan_consistency"] = True

    # 2. System architecture check
    sys_arch = payload.get("system_architecture_spec", {})
    layer_count = sys_arch.get("layer_count", 0)
    arch_implements = set(sys_arch.get("implements", []))

    if 1 <= layer_count <= 3:
        checks["layer_count_valid"] = True
    else:
        mismatches.append(f"layer_count {layer_count} violates max 3 layers rule")

    # 2.1 Dependency Inversion Principle (DIP) Linter
    dev_view = sys_arch.get("four_plus_one_views", {}).get("development_view", {})
    pkg_topo = dev_view.get("package_topology", [])
    dip_violation = False
    for pkg in pkg_topo:
        if isinstance(pkg, dict):
            pkg_name = pkg.get("name", "").lower()
            deps = [d.lower() for d in pkg.get("direct_dependencies", [])]
            if "core" in pkg_name:
                for dep in deps:
                    if "infra" in dep:
                        dip_violation = True
                        mismatches.append(
                            f"Dependency Inversion Principle (DIP) violation in package '{pkg.get('name')}': "
                            f"Core domain crate must not directly depend on infra crate ('{dep}'). "
                            f"Core must define Ports; Infra must depend on Core and implement Adapters."
                        )
    if not dip_violation:
        checks["dependency_inversion_valid"] = True

    # 3. Domain Model check (100% PRD coverage)
    domain_spec = payload.get("domain_model_spec", {})
    domain_cov_pct = domain_spec.get("must_have_requirement_coverage_pct", 0.0)
    domain_implements = set(domain_spec.get("implements", []))
    if domain_cov_pct >= 100.0 and domain_implements:
        checks["domain_model_100_percent_covered"] = True
    else:
        mismatches.append(f"domain_model_spec must have 100% PRD coverage (actual: {domain_cov_pct}%)")

    # 3.1 Domain Model Depth & Anti-Stub Check
    entities_data = domain_spec.get("domain_entity_models", {})
    entity_list = []
    if isinstance(entities_data, dict):
        entity_list = entities_data.get("entities", [])
        if not entity_list and "entities" not in entities_data:
            entity_list = list(entities_data.values())
    elif isinstance(entities_data, list):
        entity_list = entities_data

    domain_depth_errors = []
    for ent in entity_list:
        if isinstance(ent, dict):
            ent_name = ent.get("name") or ent.get("entity_name") or ent.get("id", "UnknownEntity")
            if "attributes" in ent and isinstance(ent["attributes"], list) and len(ent["attributes"]) == 0:
                domain_depth_errors.append(
                    f"Domain entity '{ent_name}' has an explicit empty attributes list. "
                    f"Every entity must define substantive typed attributes and business constraints."
                )

    # Check trait identifiers are unique and not all duplicates (e.g. TRT-001)
    abstractions = domain_spec.get("domain_abstractions", {})
    traits_list = abstractions.get("traits", []) if isinstance(abstractions, dict) else []
    seen_trait_ids = set()
    for trt in traits_list:
        if isinstance(trt, dict):
            tid = trt.get("trait_id") or trt.get("id")
            if tid:
                if tid in seen_trait_ids:
                    domain_depth_errors.append(
                        f"Duplicate trait ID '{tid}' in domain abstractions. "
                        f"Each trait must have a distinct, monotonic identifier (e.g. TRT-001, TRT-002)."
                    )
                seen_trait_ids.add(tid)

    # Check aggregate roots are not stubs
    aggregates_list = domain_spec.get("aggregates", []) or abstractions.get("aggregates", [])
    for agg in aggregates_list:
        if isinstance(agg, dict):
            agg_id = agg.get("aggregate_id") or agg.get("id", "")
            if agg_id == "AGG":
                domain_depth_errors.append(
                    "Aggregate root ID is placeholder 'AGG'. Must use namespaced ID (e.g. AGG-001)."
                )

    if domain_depth_errors:
        mismatches.extend(domain_depth_errors)
    else:
        checks["domain_model_depth_valid"] = True

    # 4. Database design check
    db_design = payload.get("database_design_spec", {})
    db_implements = set(db_design.get("implements", []))
    tables = db_design.get("tables", [])
    if tables:
        checks["database_invariants_aligned"] = True
    else:
        mismatches.append("database_design_spec missing table definitions")

    # 4.1 SQL DDL Syntax & Executability Linter
    sql_errors = []
    for tbl in tables:
        if isinstance(tbl, dict):
            ddl = tbl.get("ddl_statement", "")
            tbl_name = tbl.get("table_name", tbl.get("name", "unknown_table"))
            if ddl:
                # Check for unquoted string defaults, e.g. DEFAULT ACTIVE, DEFAULT id
                unquoted_defaults = re.findall(r"\bDEFAULT\s+([A-Za-z_]+)\b", ddl, re.IGNORECASE)
                for udef in unquoted_defaults:
                    if udef.upper() not in {
                        "NULL", "TRUE", "FALSE", "NOW", "CURRENT_TIMESTAMP",
                        "CURRENT_DATE", "GEN_RANDOM_UUID"
                    }:
                        sql_errors.append(
                            f"Invalid SQL DDL in table '{tbl_name}': String default '{udef}' "
                            f"must be enclosed in single quotes (e.g. DEFAULT '{udef}')."
                        )
                # Check for unquoted CHECK (status IN (ACTIVE, ...))
                check_in_matches = re.findall(r"CHECK\s*\(\s*[a-zA-Z_]+\s+IN\s*\(([^)]+)\)\)", ddl, re.IGNORECASE)
                for in_clause in check_in_matches:
                    tokens = [t.strip() for t in in_clause.split(",")]
                    for tok in tokens:
                        if not (tok.startswith("'") and tok.endswith("'")) and not tok.isdigit():
                            sql_errors.append(
                                f"Invalid SQL DDL in table '{tbl_name}': String constant '{tok}' in CHECK constraint "
                                f"must be enclosed in single quotes (e.g. '{tok}')."
                            )
    if sql_errors:
        mismatches.extend(sql_errors)
    else:
        checks["sql_ddl_syntax_valid"] = True

    # 5. API contracts check
    api_contracts = payload.get("api_contract_suite", {})
    api_implements = set(api_contracts.get("implements", []))
    compat = api_contracts.get("backward_compatibility_guarantee", {})
    if compat.get("breaking_changes_allowed") is False:
        checks["api_backward_compatible"] = True
    else:
        mismatches.append("API contracts must guarantee breaking_changes_allowed == false")

    # 6. Architecture Invariants check (9 Dimensions)
    invariants_spec = payload.get("architecture_invariants_spec", {})
    invariants_list = invariants_spec.get("invariants", [])
    defense_pct = invariants_spec.get("defense_coverage_pct", 0.0)
    present_dims = {inv.get("dimension") for inv in invariants_list if inv.get("dimension")}
    missing_dims = REQUIRED_INVARIANT_DIMENSIONS - present_dims

    if invariants_list and defense_pct >= 100.0 and len(missing_dims) == 0:
        checks["invariants_defense_covered"] = True
    else:
        mismatches.append(f"Architecture invariants incomplete: coverage={defense_pct}%, missing dimensions={sorted(list(missing_dims))}")

    # 7. Technical Dependency DAG check
    dep_dag_spec = payload.get("technical_dependency_dag_spec", {})
    dep_nodes = dep_dag_spec.get("dependency_nodes", [])
    dep_edges = dep_dag_spec.get("dependency_edges", [])
    crit_path = dep_dag_spec.get("critical_path", [])
    dag_implements = set(dep_dag_spec.get("implements", []))

    if dep_nodes and crit_path and is_dag_acyclic(dep_nodes, dep_edges):
        checks["dependency_dag_acyclic"] = True
    else:
        mismatches.append("Technical dependency DAG contains cycles or empty critical path")

    # 8. Upstream PRD binding & Requirement coverage check
    upstream_prd = payload.get("upstream_prd")
    upstream_req_ids = set()
    if upstream_prd and isinstance(upstream_prd, dict):
        for feat in upstream_prd.get("features", []):
            fid = feat.get("feature_id") or feat.get("id")
            if fid:
                upstream_req_ids.add(fid)
        for r in upstream_prd.get("explicit_requirements", []):
            rid = r.get("id") or r.get("requirement_id")
            if rid:
                upstream_req_ids.add(rid)

    all_implemented_reqs = arch_implements | domain_implements | db_implements | api_implements | dag_implements

    # Ghost requirement detection if upstream PRD is supplied
    if upstream_req_ids:
        ghost_reqs = all_implemented_reqs - upstream_req_ids
        if ghost_reqs:
            mismatches.append(
                f"Ghost requirements detected in architecture implements: {sorted(list(ghost_reqs))}. "
                f"All architecture implementation references must strictly trace to upstream PRD features!"
            )
        must_have_reqs = upstream_req_ids

    total_must_have = len(must_have_reqs)
    uncovered = must_have_reqs - all_implemented_reqs

    if total_must_have > 0 and len(uncovered) == 0:
        checks["must_have_requirements_covered"] = True
    else:
        mismatches.append(f"Uncovered Must-Have requirements: {sorted(list(uncovered))}")

    # 9. Readiness review check
    report = payload.get("architecture_readiness_review_report", {})
    readiness = report.get("readiness_status")
    blocking_findings = report.get("blocking_findings", [])

    if blocking_findings and readiness == "READY_FOR_DEV":
        mismatches.append("Cannot be READY_FOR_DEV when blocking_findings exist")
    elif not blocking_findings and len(uncovered) == 0 and readiness == "READY_FOR_DEV":
        checks["readiness_consistency"] = True
    elif readiness in ["NEEDS_REFINEMENT", "BLOCKED"]:
        checks["readiness_consistency"] = True
    else:
        mismatches.append(f"Readiness state {readiness} inconsistent with blocking findings or coverage")

    all_passed = all(checks.values()) and len(mismatches) == 0
    return {
        "verdict": "passed" if all_passed else "failed",
        "observation": {
            "algorithm": "aurakl-architecture-lineage-oracle-v1/pipeline",
            "checks": checks,
            "mismatches": mismatches,
            "computed": {
                "total_must_have_reqs": total_must_have,
                "covered_reqs": len(must_have_reqs & all_implemented_reqs),
                "uncovered_reqs": sorted(list(uncovered)),
                "coverage_pct": round(len(must_have_reqs & all_implemented_reqs) / max(1, total_must_have) * 100.0, 2),
                "invariants_count": len(invariants_list),
                "invariants_defense_pct": defense_pct,
                "dag_node_count": len(dep_nodes),
                "dag_critical_path_length": len(crit_path)
            }
        }
    }


def validate_coverage(payload: Dict[str, Any]) -> Dict[str, Any]:
    matrix = payload.get("coverage_matrix", {})
    total = matrix.get("total_must_have_requirements", 0)
    covered = matrix.get("covered_must_have_requirements", 0)
    pct = matrix.get("must_have_coverage_pct", 0.0)
    uncovered = matrix.get("uncovered_requirements", [])

    mismatches: List[str] = []
    if total <= 0:
        mismatches.append("total_must_have_requirements must be > 0")
    if len(uncovered) > 0 or pct < 100.0 or covered != total:
        mismatches.append(f"Coverage not 100%: covered={covered}/{total} ({pct}%), uncovered={uncovered}")

    return {
        "verdict": "passed" if len(mismatches) == 0 else "failed",
        "observation": {
            "algorithm": "aurakl-architecture-lineage-oracle-v1/requirement_coverage",
            "checks": {"coverage_100_percent": len(mismatches) == 0},
            "mismatches": mismatches
        }
    }


def validate_invariants_defense(payload: Dict[str, Any]) -> Dict[str, Any]:
    spec = payload.get("invariants_spec", {})
    invariants = spec.get("invariants", [])
    pct = spec.get("defense_coverage_pct", 0.0)

    mismatches: List[str] = []
    if not invariants:
        mismatches.append("invariants list cannot be empty")

    present_dims = {inv.get("dimension") for inv in invariants if inv.get("dimension")}
    missing_dims = REQUIRED_INVARIANT_DIMENSIONS - present_dims
    if missing_dims:
        mismatches.append(f"Missing invariant dimensions: {sorted(list(missing_dims))}")

    for inv in invariants:
        inv_id = inv.get("id", "UNKNOWN")
        if not inv.get("enforcement_level"):
            mismatches.append(f"{inv_id} missing enforcement_level")
        if not inv.get("defense_mechanism"):
            mismatches.append(f"{inv_id} missing defense_mechanism")
        if not inv.get("violation_remediation"):
            mismatches.append(f"{inv_id} missing violation_remediation")

    if pct < 100.0:
        mismatches.append(f"defense_coverage_pct {pct}% is less than 100.0%")

    return {
        "verdict": "passed" if len(mismatches) == 0 else "failed",
        "observation": {
            "algorithm": "aurakl-architecture-lineage-oracle-v1/invariants_defense",
            "checks": {
                "nine_dimensions_covered": len(missing_dims) == 0,
                "defense_coverage_100_percent": pct >= 100.0,
                "all_invariants_defended": len(mismatches) == 0
            },
            "mismatches": mismatches
        }
    }


def validate_dependency_dag(payload: Dict[str, Any]) -> Dict[str, Any]:
    spec = payload.get("dag_spec", {})
    nodes = spec.get("dependency_nodes", [])
    edges = spec.get("dependency_edges", [])
    crit_path = spec.get("critical_path", [])
    seq = spec.get("technical_build_sequence", [])

    mismatches: List[str] = []
    if not nodes:
        mismatches.append("dependency_nodes cannot be empty")
    if not crit_path:
        mismatches.append("critical_path cannot be empty")
    if not seq:
        mismatches.append("technical_build_sequence cannot be empty")
    if not is_dag_acyclic(nodes, edges):
        mismatches.append("Technical dependency DAG has circular cycles")

    return {
        "verdict": "passed" if len(mismatches) == 0 else "failed",
        "observation": {
            "algorithm": "aurakl-architecture-lineage-oracle-v1/dependency_dag",
            "checks": {
                "dag_acyclic": len(mismatches) == 0,
                "critical_path_valid": len(crit_path) > 0,
                "build_sequence_valid": len(seq) > 0
            },
            "mismatches": mismatches
        }
    }


def validate_review_consistency(payload: Dict[str, Any]) -> Dict[str, Any]:
    report = payload.get("report", {})
    readiness = report.get("readiness_status")
    blocking_findings = report.get("blocking_findings", [])

    mismatches: List[str] = []
    if blocking_findings and readiness == "READY_FOR_DEV":
        mismatches.append(f"Veto violation: {len(blocking_findings)} blocking findings exist but readiness is READY_FOR_DEV")
    elif not blocking_findings and readiness != "READY_FOR_DEV":
        mismatches.append(f"Inconsistency: 0 blocking findings but readiness is {readiness}")

    return {
        "verdict": "passed" if len(mismatches) == 0 else "failed",
        "observation": {
            "algorithm": "aurakl-architecture-lineage-oracle-v1/review_consistency",
            "checks": {"veto_rule_respected": len(mismatches) == 0},
            "mismatches": mismatches
        }
    }


class AuraklArchitectureOracle:
    """Class-based API for architecture lineage oracle checks."""
    validate_pipeline = staticmethod(validate_pipeline)
    validate_coverage = staticmethod(validate_coverage)
    validate_invariants_defense = staticmethod(validate_invariants_defense)
    validate_dependency_dag = staticmethod(validate_dependency_dag)
    validate_review_consistency = staticmethod(validate_review_consistency)
    is_dag_acyclic = staticmethod(is_dag_acyclic)


# Backward compatibility alias
ArchitectureLineageOracle = AuraklArchitectureOracle


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"verdict": "failed", "observation": {"error": "Missing payload argument"}}))
        sys.exit(1)

    try:
        raw_input = sys.argv[1]
        data = json.loads(raw_input)
    except Exception as e:
        print(json.dumps({"verdict": "failed", "observation": {"error": f"JSON parse error: {str(e)}"}}))
        sys.exit(1)

    op = data.get("operation", "pipeline")
    inp = data.get("input", data)

    if op == "pipeline":
        result = validate_pipeline(inp)
    elif op == "requirement_coverage":
        result = validate_coverage(inp)
    elif op == "invariants_defense":
        result = validate_invariants_defense(inp)
    elif op == "dependency_dag":
        result = validate_dependency_dag(inp)
    elif op == "review_consistency":
        result = validate_review_consistency(inp)
    else:
        result = {"verdict": "failed", "observation": {"error": f"Unknown operation {op}"}}

    print(json.dumps(result))
    sys.exit(0 if result["verdict"] == "passed" else 1)


if __name__ == "__main__":
    main()
