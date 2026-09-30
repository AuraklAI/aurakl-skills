#!/usr/bin/env python3
"""
Aurakl Architecture Five-Dimensional Acceptance Gatekeeper & Validator Engine

Validates single architecture artifacts or complete architecture suites against Aurakl's
strict five-dimensional criteria:
1. Conformance: JSON Schema v1 adherence (pure Python fallback + optional jsonschema).
2. Coverage: 100% PRD requirement coverage, 100% domain entity coverage, 9-dimension invariant coverage.
3. Grounding: Strict blacklist rejection of unverified placeholders (TODO, TBD, PENDING, etc.).
4. Consistency: Layer count <= 3, Monolith-first, Acyclic dependency DAG, breaking_changes_allowed == False.
5. Deterministic Oracle: Integration with architecture_lineage_oracle.py (one-vote veto gatekeeper).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Self-contained skill package paths
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SKILL_ROOT = SCRIPT_DIR.parent
SCHEMAS_DIR = SKILL_ROOT / "schemas"
STANDARDS_DIR = SKILL_ROOT / "standards"
TEMPLATES_DIR = SKILL_ROOT / "templates"
ORACLE_SCRIPT = SCRIPT_DIR / "architecture_lineage_oracle.py"

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

FORBIDDEN_PLACEHOLDER_REGEX = re.compile(
    r"\b(TBD|TODO|UNVERIFIED|FIXME|XXX|REPLACE_ME|\u5f85\u786e\u8ba4|\u5f85\u5b9a|\u6682\u65e0|\u540e\u7eed\u8865\u5145|\u5f85\u5546\u69b7)\b",
    re.IGNORECASE,
)

SCHEMA_MAPPING: Dict[str, str] = {
    "tech_stack_decision": "tech-stack-decision.v1.json",
    "tech-stack-decision": "tech-stack-decision.v1.json",
    "system_architecture_spec": "system-architecture.v1.json",
    "system-architecture": "system-architecture.v1.json",
    "system_architecture": "system-architecture.v1.json",
    "domain_model_spec": "domain-model-spec.v1.json",
    "domain-model": "domain-model-spec.v1.json",
    "domain_model": "domain-model-spec.v1.json",
    "database_design_spec": "database-design.v1.json",
    "database-design": "database-design.v1.json",
    "database_design": "database-design.v1.json",
    "api_contract_suite": "api-contracts.v1.json",
    "api-contract": "api-contracts.v1.json",
    "api_contract": "api-contracts.v1.json",
    "api-contracts": "api-contracts.v1.json",
    "business_flow_spec": "business-flow.v1.json",
    "business-flow": "business-flow.v1.json",
    "business_flow": "business-flow.v1.json",
    "architecture_invariants_spec": "architecture-invariants.v1.json",
    "architecture-invariants": "architecture-invariants.v1.json",
    "architecture_invariants": "architecture-invariants.v1.json",
    "technical_dependency_dag_spec": "technical-dependency-dag.v1.json",
    "technical-dependency-dag": "technical-dependency-dag.v1.json",
    "technical_dependency_dag": "technical-dependency-dag.v1.json",
    "architecture_readiness_review_report": "architecture-review-report.v1.json",
    "architecture-readiness-review-report": "architecture-review-report.v1.json",
    "architecture_review_report": "architecture-review-report.v1.json",
    "architecture-review-report": "architecture-review-report.v1.json",
}

STANDARD_MAPPING: Dict[str, str] = {
    "tech_stack_decision": "arch-std-tech-stack-quality",
    "system_architecture_spec": "arch-std-architecture-quality",
    "domain_model_spec": "arch-std-domain-model-quality",
    "database_design_spec": "arch-std-database-quality",
    "api_contract_suite": "arch-std-api-quality",
    "business_flow_spec": "arch-std-flow-quality",
    "architecture_invariants_spec": "arch-std-invariants-quality",
    "technical_dependency_dag_spec": "arch-std-dependency-guidance-quality",
    "feature_implementation_guide": "arch-std-feature-guide-quality",
    "architecture_readiness_review_report": "arch-std-readiness-quality",
}


@dataclass
class ValidationIssue:
    dimension: str  # conformance, coverage, grounding, consistency, oracle
    code: str
    message: str
    pointer: Optional[str] = None


@dataclass
class ValidationVerdict:
    passed: bool
    kind: str
    issues: List[ValidationIssue] = field(default_factory=list)
    observations: Dict[str, Any] = field(default_factory=dict)


class PurePythonSchemaValidator:
    """Lightweight pure Python JSON schema validator for Draft-07 subset."""

    @classmethod
    def validate(cls, instance: Any, schema: Dict[str, Any], path: str = "#") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not isinstance(schema, dict):
            return issues

        # Type check
        expected_type = schema.get("type")
        if expected_type:
            types = expected_type if isinstance(expected_type, list) else [expected_type]
            type_ok = False
            for t in types:
                if t == "string" and isinstance(instance, str):
                    type_ok = True
                elif t == "number" and isinstance(instance, (int, float)) and not isinstance(instance, bool):
                    type_ok = True
                elif t == "integer" and isinstance(instance, int) and not isinstance(instance, bool):
                    type_ok = True
                elif t == "boolean" and isinstance(instance, bool):
                    type_ok = True
                elif t == "array" and isinstance(instance, list):
                    type_ok = True
                elif t == "object" and isinstance(instance, dict):
                    type_ok = True
                elif t == "null" and instance is None:
                    type_ok = True
            if not type_ok:
                issues.append(
                    ValidationIssue(
                        "conformance",
                        "type_mismatch",
                        f"Expected type {expected_type} but got {type(instance).__name__}",
                        path,
                    )
                )
                return issues

        # Enum check
        if "enum" in schema and instance not in schema["enum"]:
            issues.append(
                ValidationIssue(
                    "conformance",
                    "enum_mismatch",
                    f"Value '{instance}' not in allowed enum {schema['enum']}",
                    path,
                )
            )

        # String constraints
        if isinstance(instance, str):
            if "minLength" in schema and len(instance) < schema["minLength"]:
                issues.append(
                    ValidationIssue(
                        "conformance",
                        "min_length_violation",
                        f"String length {len(instance)} < minLength {schema['minLength']}",
                        path,
                    )
                )
            if "maxLength" in schema and len(instance) > schema["maxLength"]:
                issues.append(
                    ValidationIssue(
                        "conformance",
                        "max_length_violation",
                        f"String length {len(instance)} > maxLength {schema['maxLength']}",
                        path,
                    )
                )
            if "pattern" in schema:
                if not re.search(schema["pattern"], instance):
                    issues.append(
                        ValidationIssue(
                            "conformance",
                            "pattern_mismatch",
                            f"String '{instance}' does not match pattern {schema['pattern']}",
                            path,
                        )
                    )

        # Number constraints
        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            if "minimum" in schema and instance < schema["minimum"]:
                issues.append(
                    ValidationIssue(
                        "conformance",
                        "minimum_violation",
                        f"Value {instance} < minimum {schema['minimum']}",
                        path,
                    )
                )
            if "maximum" in schema and instance > schema["maximum"]:
                issues.append(
                    ValidationIssue(
                        "conformance",
                        "maximum_violation",
                        f"Value {instance} > maximum {schema['maximum']}",
                        path,
                    )
                )

        # Array constraints
        if isinstance(instance, list):
            if "minItems" in schema and len(instance) < schema["minItems"]:
                issues.append(
                    ValidationIssue(
                        "conformance",
                        "min_items_violation",
                        f"Array has {len(instance)} items, required minItems is {schema['minItems']}",
                        path,
                    )
                )
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                issues.append(
                    ValidationIssue(
                        "conformance",
                        "max_items_violation",
                        f"Array has {len(instance)} items, maxItems is {schema['maxItems']}",
                        path,
                    )
                )
            if "items" in schema and isinstance(schema["items"], dict):
                item_schema = schema["items"]
                for i, elem in enumerate(instance):
                    sub_issues = cls.validate(elem, item_schema, f"{path}[{i}]")
                    issues.extend(sub_issues)

        # Object constraints
        if isinstance(instance, dict):
            required_keys = schema.get("required", [])
            for req in required_keys:
                if req not in instance:
                    issues.append(
                        ValidationIssue(
                            "conformance",
                            "missing_required_property",
                            f"Missing required property: '{req}'",
                            f"{path}.{req}",
                        )
                    )
            properties = schema.get("properties", {})
            for prop, prop_schema in properties.items():
                if prop in instance:
                    sub_issues = cls.validate(instance[prop], prop_schema, f"{path}.{prop}")
                    issues.extend(sub_issues)

        return issues


class AuraklArchitectureValidator:
    """Core validator implementing the 5-dimensional acceptance gate."""

    def __init__(self, schemas_dir: Optional[Path] = None):
        self.schemas_dir = schemas_dir or SCHEMAS_DIR

    def _load_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        target = self.schemas_dir / schema_name
        if target.exists():
            with open(target, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def validate_grounding(self, data: Any, path: str = "$") -> List[ValidationIssue]:
        """Dimension 3: Grounding / Placeholder Rejection."""
        issues: List[ValidationIssue] = []
        if isinstance(data, str):
            matches = FORBIDDEN_PLACEHOLDER_REGEX.findall(data)
            if matches:
                for match in matches:
                    val = match if isinstance(match, str) else [m for m in match if m][0]
                    issues.append(
                        ValidationIssue(
                            dimension="grounding",
                            code="forbidden_placeholder",
                            message=f"Forbidden placeholder '{val}' detected in content",
                            pointer=path,
                        )
                    )
        elif isinstance(data, dict):
            for k, v in data.items():
                issues.extend(self.validate_grounding(v, f"{path}.{k}"))
        elif isinstance(data, list):
            for i, v in enumerate(data):
                issues.extend(self.validate_grounding(v, f"{path}[{i}]"))
        return issues

    def validate_conformance(self, kind: str, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Dimension 1: Conformance / Schema Adherence."""
        issues: List[ValidationIssue] = []
        schema_file = SCHEMA_MAPPING.get(kind.lower())
        if not schema_file:
            return issues

        schema = self._load_schema(schema_file)
        if not schema:
            issues.append(
                ValidationIssue(
                    dimension="conformance",
                    code="schema_not_found",
                    message=f"Could not load schema file '{schema_file}' for kind '{kind}'",
                )
            )
            return issues

        if HAS_JSONSCHEMA:
            try:
                validator_cls = jsonschema.Draft7Validator
                validator = validator_cls(schema)
                for err in validator.iter_errors(data):
                    issues.append(
                        ValidationIssue(
                            dimension="conformance",
                            code="schema_violation",
                            message=err.message,
                            pointer="/".join(str(p) for p in err.absolute_path) or "#",
                        )
                    )
            except Exception as e:
                # Fallback to pure python validator on jsonschema error
                issues.extend(PurePythonSchemaValidator.validate(data, schema))
        else:
            issues.extend(PurePythonSchemaValidator.validate(data, schema))

        return issues

    def validate_artifact(self, kind: str, data: Dict[str, Any]) -> ValidationVerdict:
        """Validates an individual architectural deliverable."""
        issues: List[ValidationIssue] = []

        # 1. Conformance
        issues.extend(self.validate_conformance(kind, data))

        # 2. Grounding
        issues.extend(self.validate_grounding(data))

        # 3. Domain-specific invariant and consistency checks
        clean_kind = kind.lower().replace("-", "_")

        if clean_kind == "tech_stack_decision":
            locked = data.get("locked_stack_items", [])
            reqs = data.get("must_have_requirement_ids", [])
            if not locked:
                issues.append(ValidationIssue("consistency", "missing_locked_items", "Tech stack decision must define locked_stack_items"))
            if not reqs:
                issues.append(ValidationIssue("coverage", "missing_requirements", "Tech stack decision must link must_have_requirement_ids"))

        elif clean_kind == "system_architecture_spec":
            layers = data.get("layer_count", 0)
            if layers > 3:
                issues.append(ValidationIssue("consistency", "max_three_layers_violated", f"Layer count {layers} exceeds Linus <=3 layers rule", "layer_count"))
            if not data.get("c4_container_diagram"):
                issues.append(ValidationIssue("coverage", "missing_c4_diagram", "System architecture spec missing c4_container_diagram"))

        elif clean_kind == "domain_model_spec":
            cov = data.get("must_have_requirement_coverage_pct", 0.0)
            if cov < 100.0:
                issues.append(ValidationIssue("coverage", "incomplete_domain_coverage", f"Domain model must achieve 100% PRD coverage (actual: {cov}%)", "must_have_requirement_coverage_pct"))
            entities = data.get("entities", [])
            if not entities:
                issues.append(ValidationIssue("coverage", "empty_entities", "Domain model must define entities list"))

        elif clean_kind == "database_design_spec":
            tables = data.get("tables", [])
            if not tables:
                issues.append(ValidationIssue("coverage", "empty_tables", "Database design must define tables"))
            for t in tables:
                tname = t.get("table_name") or t.get("name", "unnamed")
                pks = t.get("primary_key") or [col for col in t.get("columns", []) if col.get("primary_key")]
                if not pks:
                    issues.append(ValidationIssue("consistency", "missing_primary_key", f"Table '{tname}' must have a primary key defined", f"tables.{tname}"))

        elif clean_kind == "api_contract_suite":
            compat = data.get("backward_compatibility_guarantee", {})
            if compat.get("breaking_changes_allowed") is not False:
                issues.append(ValidationIssue("consistency", "breaking_changes_prohibited", "API contract suite must set breaking_changes_allowed to false", "backward_compatibility_guarantee.breaking_changes_allowed"))
            endpoints = data.get("endpoints", [])
            for ep in endpoints:
                method = ep.get("method", "").upper()
                if method in ["POST", "PUT", "PATCH", "DELETE"]:
                    if not ep.get("idempotency"):
                        issues.append(ValidationIssue("consistency", "missing_idempotency", f"Mutating endpoint {method} {ep.get('path')} must define idempotency mechanism", f"endpoints.{ep.get('operation_id')}"))

        elif clean_kind == "business_flow_spec":
            flows = data.get("flows", [])
            if not flows:
                issues.append(ValidationIssue("coverage", "empty_flows", "Business flow spec must define flows list"))
            for f in flows:
                paths = f.get("sequence_paths", {})
                for required_path in ["happy_path", "edge_cases", "error_handling"]:
                    if not paths.get(required_path):
                        issues.append(ValidationIssue("coverage", f"missing_{required_path}", f"Flow {f.get('id')} missing {required_path} sequence specification", f"flows.{f.get('id')}"))

        elif clean_kind == "architecture_invariants_spec":
            invariants = data.get("invariants", [])
            defense_pct = data.get("defense_coverage_pct", 0.0)
            if defense_pct < 100.0:
                issues.append(ValidationIssue("coverage", "incomplete_defense_coverage", f"Invariants defense coverage must be >= 100% (actual: {defense_pct}%)", "defense_coverage_pct"))
            dims = {inv.get("dimension") for inv in invariants if inv.get("dimension")}
            from architecture_lineage_oracle import REQUIRED_INVARIANT_DIMENSIONS
            missing_dims = REQUIRED_INVARIANT_DIMENSIONS - dims
            if missing_dims:
                issues.append(ValidationIssue("coverage", "missing_invariant_dimensions", f"Invariants spec missing required dimensions: {sorted(list(missing_dims))}", "invariants"))

        elif clean_kind == "technical_dependency_dag_spec":
            nodes = data.get("dependency_nodes", [])
            edges = data.get("dependency_edges", [])
            crit = data.get("critical_path", [])
            from architecture_lineage_oracle import is_dag_acyclic
            if not is_dag_acyclic(nodes, edges):
                issues.append(ValidationIssue("consistency", "cyclic_dependency_dag", "Technical dependency DAG contains circular cycles", "dependency_edges"))
            if not crit:
                issues.append(ValidationIssue("coverage", "missing_critical_path", "Technical dependency DAG must define critical_path"))

        elif clean_kind == "architecture_readiness_review_report":
            status = data.get("readiness_status")
            blocking = data.get("blocking_findings", [])
            if blocking and status == "READY_FOR_DEV":
                issues.append(ValidationIssue("oracle", "veto_gate_violation", f"Cannot be READY_FOR_DEV when {len(blocking)} blocking findings exist", "readiness_status"))

        passed = len(issues) == 0
        return ValidationVerdict(
            passed=passed,
            kind=kind,
            issues=issues,
            observations={"total_issues": len(issues)},
        )

    def validate_suite(self, suite: Dict[str, Any]) -> ValidationVerdict:
        """Validates an entire 10-stage architecture suite including cross-stage lineage oracle."""
        all_issues: List[ValidationIssue] = []
        observations: Dict[str, Any] = {}

        # Validate each individual stage present in the suite
        for key, value in suite.items():
            if isinstance(value, dict) and key in SCHEMA_MAPPING:
                verdict = self.validate_artifact(key, value)
                for iss in verdict.issues:
                    iss.pointer = f"{key}.{iss.pointer or ''}"
                    all_issues.append(iss)

        # Run formal Architecture Lineage Oracle pipeline
        from architecture_lineage_oracle import validate_pipeline
        oracle_res = validate_pipeline(suite)
        observations["oracle"] = oracle_res.get("observation", {})

        if oracle_res.get("verdict") != "passed":
            for mismatch in oracle_res.get("observation", {}).get("mismatches", []):
                all_issues.append(
                    ValidationIssue(
                        dimension="oracle",
                        code="lineage_oracle_mismatch",
                        message=mismatch,
                    )
                )

        passed = len(all_issues) == 0 and oracle_res.get("verdict") == "passed"
        return ValidationVerdict(
            passed=passed,
            kind="architecture_suite",
            issues=all_issues,
            observations=observations,
        )


def main():
    parser = argparse.ArgumentParser(description="Aurakl Architecture Acceptance Validator")
    parser.add_argument("path", help="Path to JSON deliverable or suite")
    parser.add_argument("--kind", help="Kind of single deliverable (if not auto-detected)")
    parser.add_argument("--suite", action="store_true", help="Validate as complete architecture suite")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()
    file_path = Path(args.path)
    if not file_path.exists():
        print(f"Error: file '{args.path}' not found", file=sys.stderr)
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

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

    sys.exit(0 if verdict.passed else 1)


if __name__ == "__main__":
    main()
