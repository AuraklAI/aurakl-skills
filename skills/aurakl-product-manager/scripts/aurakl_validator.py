#!/usr/bin/env python3
"""
Aurakl Five-Dimensional Acceptance Gatekeeper & Validator Engine

Validates single artifacts or complete product suites against Aurakl's
strict five-dimensional criteria:
1. Conformance: JSON Schema v2 adherence.
2. Coverage: 5W1H pointers, touchpoint-to-story coverage, invariant coverage.
3. Grounding: Strict blacklist rejection of unverified placeholders (TODO, TBD, PENDING).
4. Consistency: Explicit Non-Goals integrity and semantic invariant consistency.
5. Deterministic Oracle: Integration with product_lineage_oracle.py.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

# Self-contained skill package paths
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
SCHEMAS_DIR = SKILL_ROOT / "schemas"
ORACLE_SCRIPT = SKILL_ROOT / "validators/product_lineage_oracle.py"
if not ORACLE_SCRIPT.exists():
    ORACLE_SCRIPT = SCRIPT_DIR / "product_lineage_oracle.py"

# Optional fallback to repository definition if running inside aurakl repo and local schemas missing
if not SCHEMAS_DIR.exists():
    _repo_schemas = SCRIPT_DIR.parents[3] / "definitions/product-management/source/schemas"
    if _repo_schemas.exists():
        SCHEMAS_DIR = _repo_schemas
if not ORACLE_SCRIPT.exists():
    _repo_oracle = SCRIPT_DIR.parents[3] / "definitions/product-management/validators/product_lineage_oracle.py"
    if _repo_oracle.exists():
        ORACLE_SCRIPT = _repo_oracle

STANDARDS_DIR = SKILL_ROOT / "standards"
if not STANDARDS_DIR.exists():
    _repo_standards = SCRIPT_DIR.parents[3] / "definitions/product-management/source/standards"
    if _repo_standards.exists():
        STANDARDS_DIR = _repo_standards

TEMPLATES_DIR = SKILL_ROOT / "templates"
if not TEMPLATES_DIR.exists():
    _repo_templates = SCRIPT_DIR.parents[3] / "definitions/product-management/source/templates"
    if _repo_templates.exists():
        TEMPLATES_DIR = _repo_templates

# Try importing jsonschema if available, otherwise pure Python validator fallback
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

PLACEHOLDER_REGEX = re.compile(
    r"\b(TBD|TODO|UNVERIFIED|待确认|待定|暂无|后续补充|待商榷)\b", re.IGNORECASE
)

FORBIDDEN_NON_GOAL_TERMS = [
    "positive statement",
    "only supports",
    "just supports",
    "exclusively supports",
    "is not unsupported",
    "rephrase to",
    "正面陈述",
    "不是一句「不支持",
    "而不是「不支持",
    "改写成「系统仅",
    "系统仅支持",
    "仅支持",
]

CORE_STAGE_ALIASES = {
    "requirement_analysis": "requirement-analysis.v2.json",
    "requirements": "requirement-analysis.v2.json",
    "competitive_analysis": "competitive-analysis.v2.json",
    "competitive_intelligence": "competitive-analysis.v2.json",
    "user_journey": "user-journey-model.v2.json",
    "user_journey_model": "user-journey-model.v2.json",
    "user_stories": "user-story-set.v2.json",
    "user_story_set": "user-story-set.v2.json",
    "prd": "prd.v2.json",
    "comprehensive_prd": "prd.v2.json",
    "product_invariants": "product-invariants.v1.json",
    "product_invariant_set": "product-invariants.v1.json",
    "acceptance_criteria": "acceptance-criteria.v2.json",
    "acceptance_criteria_set": "acceptance-criteria.v2.json",
    "product_review_report": "product-review-report.v2.json",
    "product_readiness_review_report": "product-review-report.v2.json",
    "user_story_lingforge": "user-story-lingforge.v1.json",
    "user-story-lingforge": "user-story-lingforge.v1.json",
    "prd_lingforge": "prd-lingforge.v1.json",
    "prd-lingforge": "prd-lingforge.v1.json",
}

SCHEMA_TO_STANDARD_MAP = {
    "requirement_analysis": "pm-std-requirement-quality",
    "requirements": "pm-std-requirement-quality",
    "requirement-analysis": "pm-std-requirement-quality",
    "competitive_analysis": "pm-std-competitive-analysis",
    "competitive_intelligence": "pm-std-competitive-analysis",
    "competitive-analysis": "pm-std-competitive-analysis",
    "user_journey": "pm-std-user-journey-and-stories",
    "user_journey_model": "pm-std-user-journey-and-stories",
    "user-journey-model": "pm-std-user-journey-and-stories",
    "user_stories": "pm-std-user-story-quality",
    "user_story_set": "pm-std-user-story-quality",
    "user-story-set": "pm-std-user-story-quality",
    "prd": "pm-std-prd-quality",
    "comprehensive_prd": "pm-std-prd-quality",
    "product_invariants": "pm-std-product-invariants",
    "product_invariant_set": "pm-std-product-invariants",
    "product-invariants": "pm-std-product-invariants",
    "acceptance_criteria": "pm-std-acceptance-criteria-quality",
    "acceptance_criteria_set": "pm-std-acceptance-criteria-quality",
    "acceptance-criteria": "pm-std-acceptance-criteria-quality",
    "product_review_report": "pm-std-review-quality",
    "product_readiness_review_report": "pm-std-review-quality",
    "product-review-report": "pm-std-review-quality",
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
                        "string_too_short",
                        f"Length {len(instance)} is shorter than minLength {schema['minLength']}",
                        path,
                    )
                )
            if "pattern" in schema:
                try:
                    if not re.search(schema["pattern"], instance):
                        issues.append(
                            ValidationIssue(
                                "conformance",
                                "pattern_mismatch",
                                f"String does not match pattern {schema['pattern']}",
                                path,
                            )
                        )
                except Exception:
                    pass

        # Array constraints
        if isinstance(instance, list):
            if "minItems" in schema and len(instance) < schema["minItems"]:
                issues.append(
                    ValidationIssue(
                        "conformance",
                        "min_items_not_met",
                        f"Array has {len(instance)} items, required at least {schema['minItems']}",
                        path,
                    )
                )
            if "items" in schema and isinstance(schema["items"], dict):
                for idx, item in enumerate(instance):
                    issues.extend(cls.validate(item, schema["items"], f"{path}/{idx}"))

        # Object constraints
        if isinstance(instance, dict):
            # Required fields
            for req in schema.get("required", []):
                if req not in instance:
                    issues.append(
                        ValidationIssue(
                            "conformance",
                            "missing_required_field",
                            f"Missing required property '{req}'",
                            f"{path}/{req}",
                        )
                    )
            # Property properties
            props = schema.get("properties", {})
            for key, val in instance.items():
                if key in props and isinstance(props[key], dict):
                    issues.extend(cls.validate(val, props[key], f"{path}/{key}"))

        return issues


class AuraklValidator:
    """Core five-dimensional validator supporting all 31 Aurakl schemas."""

    def __init__(self, schemas_path: Optional[Path] = None):
        self.schemas_path = schemas_path or SCHEMAS_DIR
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._schema_index: Dict[str, Path] = {}
        self._index_schemas()

    def _index_schemas(self) -> None:
        """Dynamically indexes all 31 schemas in source/schemas directory."""
        if not self.schemas_path.exists():
            return
        for file in self.schemas_path.glob("*.json"):
            # Exact filename
            self._schema_index[file.name] = file
            # Stem and underscore variants
            self._schema_index[file.stem] = file
            self._schema_index[file.stem.replace("-", "_")] = file
            # Stem without version (.v1 / .v2)
            base = file.stem.rsplit(".", 1)[0]
            self._schema_index[base] = file
            self._schema_index[base.replace("-", "_")] = file

            # Read title and $id
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if "title" in data and data["title"]:
                    self._schema_index[data["title"]] = file
                    self._schema_index[data["title"].lower()] = file
                if "$id" in data and data["$id"]:
                    self._schema_index[data["$id"]] = file
            except Exception:
                pass

        # Core stage aliases
        for alias, target_filename in CORE_STAGE_ALIASES.items():
            target_path = self.schemas_path / target_filename
            if target_path.exists():
                self._schema_index[alias] = target_path

    def resolve_schema(self, query: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Resolves any schema name, alias, or file to (filename, schema_dict)."""
        clean_query = query.strip()
        path = self._schema_index.get(clean_query)
        if not path and clean_query.endswith(".json"):
            path = self._schema_index.get(clean_query[:-5])
        if not path:
            cand = self.schemas_path / clean_query
            if cand.exists():
                path = cand
            elif not clean_query.endswith(".json"):
                cand2 = self.schemas_path / f"{clean_query}.json"
                if cand2.exists():
                    path = cand2

        if path and path.exists():
            data = self._load_schema(path.name)
            if data:
                return (path.name, data)
        return None

    def list_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns metadata for all 31 registered schemas."""
        results = []
        for file in sorted(self.schemas_path.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                results.append({
                    "filename": file.name,
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                    "id": data.get("$id", ""),
                    "required_fields": data.get("required", []),
                })
            except Exception:
                pass
        return results

    def _load_schema(self, schema_filename: str) -> Optional[Dict[str, Any]]:
        if schema_filename in self._schema_cache:
            return self._schema_cache[schema_filename]
        path = self.schemas_path / schema_filename
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        self._schema_cache[schema_filename] = data
        return data

    def calc_invariant_coverage(self, invariants: Dict[str, Any], criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Recomputes invariant coverage metrics from scenario definitions."""
        all_inv = set()
        for cat in ["state_invariants", "data_integrity_invariants", "security_and_privacy_invariants", "ux_and_safety_invariants"]:
            for item in invariants.get(cat, []):
                if item.get("invariant_id"):
                    all_inv.add(item["invariant_id"])

        covered_inv = {
            s.get("verifies_invariant_id")
            for s in criteria.get("scenarios", [])
            if s.get("verifies_invariant_id")
        }
        total = len(all_inv)
        covered = len(all_inv & covered_inv)
        missing = sorted(all_inv - covered_inv)
        extra = sorted(covered_inv - all_inv)
        basis_points = round(covered / total * 10000) if total else 0
        return {
            "total_invariants": total,
            "covered_invariants": covered,
            "coverage_basis_points": basis_points,
            "coverage_pct": round(basis_points / 100.0, 2),
            "is_full_coverage": basis_points == 10000,
            "missing_invariants": missing,
            "extra_invariants": extra,
        }

    def calc_negative_ratio(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Recomputes negative defense scenario ratio."""
        scenarios = criteria.get("scenarios", [])
        neg = sum(1 for s in scenarios if s.get("scenario_type") in ("negative_defense", "fault_recovery"))
        total = len(scenarios)
        ratio = (neg / total * 100.0) if total else 0.0
        return {
            "total_scenarios": total,
            "negative_defense_scenarios": neg,
            "negative_ratio_pct": round(ratio, 1),
            "meets_safety_threshold": ratio >= 30.0 and total > 0,
        }

    def validate_artifact(self, kind: str, artifact: Dict[str, Any]) -> ValidationVerdict:
        """Validates a single artifact against conformance, grounding, coverage, and consistency."""
        issues: List[ValidationIssue] = []
        observations: Dict[str, Any] = {}

        # 1. Conformance check
        resolved = self.resolve_schema(kind)
        if resolved:
            schema_file, schema = resolved
            observations["resolved_schema"] = schema_file
            if HAS_JSONSCHEMA:
                try:
                    jsonschema.validate(instance=artifact, schema=schema)
                except jsonschema.ValidationError as err:
                    issues.append(
                        ValidationIssue(
                            dimension="conformance",
                            code="schema_violation",
                            message=err.message,
                            pointer="/" + "/".join(str(p) for p in err.path),
                        )
                    )
            else:
                schema_issues = PurePythonSchemaValidator.validate(artifact, schema)
                issues.extend(schema_issues)
        else:
            issues.append(
                ValidationIssue(
                    dimension="conformance",
                    code="unknown_schema",
                    message=f"No matching schema found for '{kind}'. Check available schemas with --list-schemas.",
                )
            )

        # 2. Grounding: Placeholder Blacklist Check
        placeholders_found = self._scan_placeholders(artifact)
        for path_str, word in placeholders_found:
            issues.append(
                ValidationIssue(
                    dimension="grounding",
                    code="placeholder_forbidden",
                    message=f"Detected forbidden unverified placeholder '{word}'",
                    pointer=path_str,
                )
            )

        # 3. Specific Stage Gates
        norm_kind = kind.lower().replace("-", "_")
        if norm_kind in ("requirement_analysis", "requirements", "requirement_analysis.v2"):
            self._validate_requirement_analysis_specifics(artifact, issues, observations)
        elif norm_kind in ("acceptance_criteria", "acceptance_criteria_set", "acceptance_criteria.v2"):
            self._validate_acceptance_criteria_specifics(artifact, issues, observations)

        # 4. Standard Quality Policy Evaluation
        self._evaluate_governing_standard(kind, artifact, issues, observations)

        verdict_passed = len(issues) == 0
        return ValidationVerdict(
            passed=verdict_passed,
            kind=kind,
            issues=issues,
            observations=observations,
        )

    def load_standards(self) -> Dict[str, Dict[str, Any]]:
        """Loads all standard definitions from standards directory."""
        standards = {}
        if STANDARDS_DIR.exists():
            for p in STANDARDS_DIR.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    sid = data.get("metadata", {}).get("id") or p.stem
                    standards[sid] = data
                except Exception:
                    pass
        return standards

    def get_governing_standard_id(self, schema_or_kind: str) -> Optional[str]:
        norm = schema_or_kind.lower().replace("-", "_").replace(".json", "")
        if "lingforge" in norm:
            return None
        for suffix in (".v1", ".v2", ".v3", "_v1", "_v2", "_v3"):
            norm = norm.removesuffix(suffix)
        for k, sid in SCHEMA_TO_STANDARD_MAP.items():
            k_norm = k.lower().replace("-", "_")
            if norm == k_norm or norm.startswith(k_norm) or k_norm.startswith(norm):
                return sid
        return None

    def _evaluate_governing_standard(
        self, kind: str, artifact: Dict[str, Any], issues: List[ValidationIssue], obs: Dict[str, Any]
    ) -> None:
        std_id = self.get_governing_standard_id(kind)
        if not std_id:
            return

        std_file = STANDARDS_DIR / f"{std_id}.json"
        if not std_file.exists():
            return

        try:
            std_data = json.loads(std_file.read_text(encoding="utf-8"))
        except Exception:
            return

        spec = std_data.get("spec", {})
        rules = spec.get("rules", [])
        rules_evaluated = []

        obs["governing_standard"] = {
            "id": std_id,
            "name": spec.get("name", std_id),
            "rules_evaluated": rules_evaluated,
        }

        for rule in rules:
            rid = rule.get("id", "")
            stmt = rule.get("statement", "")
            rules_evaluated.append(rid)

            if rid == "inv.all_dimensions_covered":
                for dim in ("state_invariants", "data_integrity_invariants", "security_and_privacy_invariants", "ux_and_safety_invariants"):
                    if not artifact.get(dim):
                        issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Dimension '{dim}' is missing or empty"))
            elif rid == "inv.explicit_severity_and_consequence":
                for dim in ("state_invariants", "data_integrity_invariants", "security_and_privacy_invariants", "ux_and_safety_invariants"):
                    for idx, item in enumerate(artifact.get(dim, [])):
                        if not item.get("severity") or not item.get("violation_consequence"):
                            issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Invariant in '{dim}[{idx}]' missing severity or violation_consequence"))
            elif rid == "comp.competitors_count_sufficient":
                comps = artifact.get("competitors", [])
                if len(comps) < 2:
                    issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: competitors count must be >= 2, got {len(comps)}"))
            elif rid == "comp.beachhead_strategy_defined":
                bh = artifact.get("beachhead_strategy", {})
                for k in ("target_niche", "entry_point_feature", "value_curve_differentiation"):
                    if not bh.get(k):
                        issues.append(ValidationIssue("grounding", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: beachhead_strategy missing '{k}'"))
            elif rid == "comp.why_we_win_grounded":
                win = artifact.get("why_we_win", {})
                if not win.get("core_competitive_advantages") or not win.get("defensibility_arguments"):
                    issues.append(ValidationIssue("grounding", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: why_we_win missing core_competitive_advantages or defensibility_arguments"))
            elif rid == "us.invest_principles_enforced":
                stories = artifact.get("stories", [])
                for idx, st in enumerate(stories):
                    for field in ("as_a", "i_want", "so_that", "priority", "estimate_story_points"):
                        if not st.get(field):
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: story {st.get('id', idx)} missing '{field}'"))
            elif rid in ("us.multi_role_admin_coverage", "admin_and_operational_personas_covered"):
                personas = artifact.get("personas", [])
                if personas:
                    admin_keywords = ["admin", "administrator", "operator", "dispatcher", "manager", "finance", "compliance", "计调", "管理", "运营", "主管", "财务", "审核", "风控"]
                    has_admin = any(any(kw in (p.get("role", "") + p.get("name", "")).lower() for kw in admin_keywords) for p in personas)
                    if not has_admin:
                        issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Multi-tier systems must model operational/admin personas, found: {[p.get('role') for p in personas]}"))
                    if len(personas) < 3:
                        issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Minimum 3 distinct personas required for end-to-end multi-role systems (found {len(personas)})"))
            elif rid in ("us.touchpoints_fully_covered", "all_journey_touchpoints_covered_by_stories"):
                stages = artifact.get("journey_stages", [])
                for stg_idx, stg in enumerate(stages):
                    tps = stg.get("touchpoints", [])
                    if not tps:
                        issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Stage [{stg.get('stage_id', stg_idx)}] has zero touchpoints"))
            elif rid in ("us.per_persona_journey_coverage", "each_persona_has_touchpoints"):
                personas = artifact.get("personas", [])
                stages = artifact.get("journey_stages", [])
                all_tps = [tp for stg in stages for tp in stg.get("touchpoints", [])]
                for p in personas:
                    pid = p.get("id")
                    p_tps = [tp for tp in all_tps if tp.get("actor_persona_id") == pid]
                    if len(p_tps) < 2:
                        issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' ({p.get('name')}) has only {len(p_tps)} dedicated touchpoints (minimum 2 required)"))
            elif rid in ("us.per_persona_scenario_cardinality", "each_persona_has_scenarios"):
                personas = artifact.get("personas", [])
                scenarios = artifact.get("scenarios", [])
                for p in personas:
                    pid = p.get("id")
                    p_scns = [sc for sc in scenarios if sc.get("persona_id") == pid]
                    if len(p_scns) < 2:
                        issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' ({p.get('name')}) has only {len(p_scns)} dedicated scenarios (minimum 2 required)"))
            elif rid in ("us.per_persona_story_distribution", "each_persona_has_user_stories"):
                stories = artifact.get("stories", [])
                if stories:
                    persona_story_counts = {}
                    for st in stories:
                        pid = st.get("persona_id")
                        if pid:
                            persona_story_counts[pid] = persona_story_counts.get(pid, 0) + 1
                    for pid, count in persona_story_counts.items():
                        if count < 2:
                            issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' has only {count} user stories (minimum 2 required)"))
            elif rid == "us.three_part_form":
                stories = artifact.get("stories", [])
                for idx, st in enumerate(stories):
                    as_a = st.get("as_a", "").strip()
                    if not as_a or as_a.lower() in ("system", "系统", "用户", "user"):
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: story {st.get('id', idx)} uses generic/invalid persona '{as_a}'"))
            elif rid in ("us.id_conformance_and_continuity", "journey_and_story_ids_valid_and_continuous"):
                stages = artifact.get("journey_stages", [])
                personas = artifact.get("personas", [])
                stories = artifact.get("stories", [])
                scenarios = artifact.get("scenarios", [])

                # 1. Check global uniqueness of stages, touchpoints, stories, scenarios
                stage_ids = [stg.get("stage_id") for stg in stages if stg.get("stage_id")]
                if len(stage_ids) != len(set(stage_ids)):
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Duplicate stage_id detected: {[sid for sid in stage_ids if stage_ids.count(sid) > 1]}"))

                all_tps = [tp.get("touchpoint_id") for stg in stages for tp in stg.get("touchpoints", []) if tp.get("touchpoint_id")]
                if len(all_tps) != len(set(all_tps)):
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Duplicate touchpoint_id detected: {[tid for tid in all_tps if all_tps.count(tid) > 1]}"))

                story_ids = [st.get("id") for st in stories if st.get("id")]
                if len(story_ids) != len(set(story_ids)):
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Duplicate story ID detected: {[sid for sid in story_ids if story_ids.count(sid) > 1]}"))

                scn_ids = [sc.get("scenario_id") for sc in scenarios if sc.get("scenario_id")]
                if len(scn_ids) != len(set(scn_ids)):
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Duplicate scenario_id detected: {[sid for sid in scn_ids if scn_ids.count(sid) > 1]}"))

                # 2. Check 1-to-1 Stage-to-Touchpoint mapping across all stages
                for stg in stages:
                    tps = stg.get("touchpoints", [])
                    if len(tps) != 1:
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Stage '{stg.get('stage_id')}' must contain exactly 1 touchpoint (found {len(tps)}). Bundling multiple touchpoints into a single stage causes duplicate stage IDs across markdown table rows."))

                # 3. Per-Persona domain ID continuity & start from 001
                for p in personas:
                    pid = p.get("id")
                    # Find touchpoints and stages for this persona
                    p_stages = [stg for stg in stages if any(tp.get("actor_persona_id") == pid for tp in stg.get("touchpoints", []))]
                    p_stage_ids = [stg.get("stage_id", "") for stg in p_stages]
                    if len(p_stage_ids) != len(set(p_stage_ids)):
                        issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' journey has duplicate stages: {p_stage_ids}"))

                    # Check rendered table rows stage IDs: each touchpoint row must have a unique Stage ID
                    p_row_stage_ids = [stg.get("stage_id", "") for stg in stages for tp in stg.get("touchpoints", []) if tp.get("actor_persona_id") == pid]
                    if len(p_row_stage_ids) != len(set(p_row_stage_ids)):
                        issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' journey table has duplicate stage IDs across touchpoint rows: {p_row_stage_ids}. Each touchpoint row must map 1-to-1 to a distinct progressive stage ID."))

                    # Check that each persona's stages start from 001
                    for idx, sid in enumerate(p_stage_ids, start=1):
                        seq_str = sid.split("-")[-1]
                        if seq_str != f"{idx:03d}":
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' stage ID '{sid}' sequence is discontinuous or does not start from 001 (expected sequence {idx:03d})"))

                    p_tps = [tp.get("touchpoint_id", "") for stg in p_stages for tp in stg.get("touchpoints", []) if tp.get("actor_persona_id") == pid]
                    for idx, tid in enumerate(p_tps, start=1):
                        seq_str = tid.split("-")[-1]
                        if seq_str != f"{idx:03d}":
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' touchpoint ID '{tid}' sequence is discontinuous or does not start from 001 (expected sequence {idx:03d})"))

                    p_scns = [sc for sc in scenarios if sc.get("persona_id") == pid]
                    for idx, sc in enumerate(p_scns, start=1):
                        scid = sc.get("scenario_id", "")
                        seq_str = scid.split("-")[-1]
                        if seq_str != f"{idx:03d}":
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' scenario ID '{scid}' sequence is discontinuous or does not start from 001 (expected sequence {idx:03d})"))

                # 3. Check stories per persona start from 001
                if stories:
                    persona_stories = {}
                    for st in stories:
                        pid = st.get("persona_id")
                        if pid:
                            persona_stories.setdefault(pid, []).append(st)
                    for pid, p_sts in persona_stories.items():
                        for idx, st in enumerate(p_sts, start=1):
                            sid = st.get("id", "")
                            seq_str = sid.split("-")[-1]
                            if seq_str != f"{idx:03d}":
                                issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Persona '{pid}' story ID '{sid}' sequence is discontinuous or does not start from 001 (expected sequence {idx:03d})"))
            elif rid == "prd.features_trace_to_stories":
                feats = artifact.get("features", [])
                if not feats:
                    issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: features list is empty"))
                for idx, f in enumerate(feats):
                    stories = f.get("derived_from_user_stories", [])
                    if not stories:
                        issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{f.get('feature_id', idx)}' missing derived_from_user_stories"))
            elif rid in ("prd.all_stories_covered_by_features", "all_stories_covered_by_features"):
                feats = artifact.get("features", [])
                covered_story_ids = {sid for f in feats for sid in f.get("derived_from_user_stories", [])}
                if len(covered_story_ids) < 10:
                    issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: PRD features must comprehensively cover the complete user story inventory across all tiers (found only {len(covered_story_ids)} covered stories, expected >= 10)"))
            elif rid in ("prd.all_personas_features_covered", "all_personas_covered_in_prd"):
                personas = artifact.get("user_personas", []) or artifact.get("target_users", [])
                if len(personas) < 3:
                    issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: PRD must define concrete operational features covering all personas including admin and finance roles"))
            elif rid == "prd.features_substantive_depth":
                feats = artifact.get("features", [])
                if len(feats) < 3:
                    issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: PRD must contain at least 3 concrete feature specifications, found {len(feats)}"))
                for idx, f in enumerate(feats):
                    fid = f.get("feature_id", f"FEAT-{idx}")
                    rules = f.get("business_rules", [])
                    if len(rules) < 3:
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' has only {len(rules)} business rules, minimum 3 required"))
                    for r_idx, r in enumerate(rules):
                        if not isinstance(r, str) or len(r.strip()) < 15:
                            issues.append(ValidationIssue("grounding", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' rule [{r_idx}] is too short (<15 chars) or trivial"))
                    pres = f.get("preconditions", [])
                    posts = f.get("postconditions", [])
                    if len(pres) < 2:
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' has only {len(pres)} preconditions, minimum 2 required"))
                    if len(posts) < 2:
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' has only {len(posts)} postconditions, minimum 2 required"))
            elif rid in ("prd.features_io_and_error_handling", "features_io_and_error_handling_complete"):
                feats = artifact.get("features", [])
                for idx, f in enumerate(feats):
                    fid = f.get("feature_id", f"FEAT-{idx}")
                    inputs = f.get("inputs", []) or f.get("input_specs", [])
                    outputs = f.get("outputs", []) or f.get("output_specs", [])
                    errs = f.get("error_cases", []) or f.get("exceptions", [])
                    if len(inputs) < 1:
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' must specify at least 1 input parameter"))
                    for inp in inputs:
                        if not inp.get("name") or not inp.get("type") or "required" not in inp or not inp.get("description"):
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' input parameter missing name/type/required/description"))
                    if len(outputs) < 1:
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' must specify at least 1 output artifact/response"))
                    for out in outputs:
                        if not out.get("name") or not out.get("type") or not out.get("description"):
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' output missing name/type/description"))
                    if len(errs) < 1:
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' must specify at least 1 error case"))
                    for ec in errs:
                        if not ec.get("error_code") or not ec.get("trigger_condition") or not ec.get("user_feedback") or not ec.get("recovery_action"):
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' error case missing error_code/trigger_condition/user_feedback/recovery_action"))
            elif rid in ("prd.precondition_data_closure", "precondition_data_closure_complete"):
                feats = artifact.get("features", [])
                all_feature_ids = {f.get("feature_id") for f in feats if f.get("feature_id")}
                for idx, f in enumerate(feats):
                    fid = f.get("feature_id", f"FEAT-{idx}")
                    deps = f.get("data_dependencies", [])
                    if len(deps) < 1:
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' must declare at least 1 data_dependency with closed-world source attribution"))
                    for dep in deps:
                        if not dep.get("data_entity") or not dep.get("source_type") or not dep.get("producer_reference") or not dep.get("description"):
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' data_dependency missing data_entity/source_type/producer_reference/description"))
                        stype = dep.get("source_type")
                        if stype not in ("INTERNAL_FEATURE", "COLD_START_SEED", "EXTERNAL_API", "USER_INPUT"):
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' invalid source_type '{stype}'"))
                        if stype == "INTERNAL_FEATURE":
                            pref = dep.get("producer_reference", "")
                            matched = any(p_id in pref for p_id in all_feature_ids)
                            if not matched:
                                issues.append(ValidationIssue("grounding", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' references non-existent internal producer '{pref}' (dangling precondition)"))
            elif rid == "prd.all_modules_covered":
                ia_modules = artifact.get("information_architecture", {}).get("modules", []) or artifact.get("service_modules", [])
                feats = artifact.get("features", [])
                covered_modules = {f.get("module_id") for f in feats if f.get("module_id")}
                for m in ia_modules:
                    mid = m.get("module_id") or m.get("id")
                    if mid and mid not in covered_modules:
                        issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Information Architecture module '{mid}' has zero feature specifications"))
            elif rid == "prd.state_machines_deterministic":
                sms = artifact.get("state_machines", [])
                if not sms:
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: state_machines is empty"))
                for sm_idx, sm in enumerate(sms):
                    states = sm.get("states", [])
                    transitions = sm.get("transitions", [])
                    if len(states) < 2:
                        issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: state machine [{sm_idx}] must have >= 2 states"))
                    if len(transitions) < 2:
                        issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: state machine [{sm_idx}] must have >= 2 transitions"))
                    for tr_idx, tr in enumerate(transitions):
                        ev = tr.get("trigger_event") or tr.get("event")
                        if not ev:
                            issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: transition [{tr_idx}] missing trigger_event"))
            elif rid == "prd.error_handling_and_tracking_complete":
                eh = artifact.get("error_handling_and_recovery", {})
                tp = artifact.get("tracking_plan", {})
                if isinstance(eh, dict):
                    if not eh.get("system_errors") or not eh.get("interruption_and_recovery"):
                        issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: error_handling_and_recovery incomplete"))
                elif not eh:
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: error_handling_and_recovery empty"))
                if isinstance(tp, dict):
                    if not tp.get("north_star_metric") or not tp.get("event_dictionary"):
                        issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: tracking_plan incomplete"))
                elif not tp:
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: tracking_plan empty"))
            elif rid == "prd.non_functional_requirements_exhaustive":
                nfr = artifact.get("non_functional_requirements", {})
                for req_nfr in ("performance", "security"):
                    if not nfr.get(req_nfr):
                        issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: non_functional_requirements missing '{req_nfr}'"))
            elif rid == "prd.domain_compliance":
                dp = artifact.get("domain_profile")
                if not dp:
                    issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: PRD must explicitly declare 'domain_profile' (mobile, desktop, backend, iot_hardware, hybrid)"))
                elif dp not in ("mobile", "desktop", "backend", "iot_hardware", "hybrid"):
                    issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Invalid domain_profile '{dp}'"))
                else:
                    d_specs = artifact.get("domain_specific_specifications", {})
                    # If specified, ensure the corresponding profile object or substantive NFR exists
                    if dp == "mobile" and not d_specs.get("mobile_profile") and not artifact.get("non_functional_requirements", {}).get("mobile_resilience"):
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: domain_profile is 'mobile' but missing mobile_profile or mobile_resilience specifications"))
                    elif dp == "backend" and not d_specs.get("backend_profile") and not artifact.get("non_functional_requirements", {}).get("performance"):
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: domain_profile is 'backend' but missing backend_profile specifications"))
            elif rid == "prd.rfc2119_normative_language":
                feats = artifact.get("features", [])
                vague_terms = ["酌情", "视情况", "大概", "可能可以", "适度"]
                rfc_terms = ["must", "shall", "should", "必须", "严禁", "应当", "强制", "确保"]
                for f_idx, f in enumerate(feats):
                    fid = f.get("feature_id", f"FEAT-{f_idx}")
                    for r_idx, rule in enumerate(f.get("business_rules", [])):
                        if any(vt in rule for vt in vague_terms):
                            issues.append(ValidationIssue("grounding", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' rule [{r_idx}] contains vague colloquial language"))
                        has_normative = any(rt in rule.lower() for rt in rfc_terms)
                        if not has_normative:
                            issues.append(ValidationIssue("grounding", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' rule [{r_idx}] lacks RFC 2119 normative keywords (MUST/SHALL/SHOULD/必须/严禁/确保)"))
            elif rid == "prd.upstream_stages_presence":
                feats = artifact.get("features", [])
                all_derived = [s for f in feats for s in f.get("derived_from_user_stories", [])]
                if len(all_derived) < 10:
                    issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: PRD features must derive from comprehensive upstream user stories (found {len(all_derived)} story links, expected >= 10)"))
            elif rid == "prd.business_rule_semantic_density":
                feats = artifact.get("features", [])
                for f_idx, f in enumerate(feats):
                    fid = f.get("feature_id", f"FEAT-{f_idx}")
                    for inp_idx, inp in enumerate(f.get("inputs", [])):
                        vrule = inp.get("validation_rule") or inp.get("description", "")
                        if not vrule or len(str(vrule).strip()) < 5:
                            issues.append(ValidationIssue("grounding", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' input [{inp_idx}] ({inp.get('name')}) validation_rule is too trivial (<5 chars)"))
                    for ec_idx, ec in enumerate(f.get("error_cases", [])):
                        action = ec.get("recovery_action", "")
                        if not action or len(str(action).strip()) < 10:
                            issues.append(ValidationIssue("grounding", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' error [{ec_idx}] recovery_action is too trivial (<10 chars)"))
            elif rid == "prd.priority_explicitly_graded":
                feats = artifact.get("features", [])
                p0_count = 0
                for f_idx, f in enumerate(feats):
                    fid = f.get("feature_id", f"FEAT-{f_idx}")
                    p = f.get("priority")
                    if not p or p not in ("P0", "P1", "P2"):
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: feature '{fid}' missing valid release priority (P0, P1, P2)"))
                    if p == "P0":
                        p0_count += 1
                if p0_count < 3:
                    issues.append(ValidationIssue("coverage", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: PRD must define at least 3 core P0 (launch blocker) features to establish the MVP backbone (found {p0_count})"))
            elif rid in ("prd.id_conformance_and_continuity", "prd_ids_valid_and_continuous"):
                # 1. Validate Modules
                modules = artifact.get("information_architecture", {}).get("modules", [])
                mod_ids = [m.get("module_id") for m in modules if m.get("module_id")]
                if len(mod_ids) != len(set(mod_ids)):
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Duplicate module_id detected in information_architecture: {[mid for mid in mod_ids if mod_ids.count(mid) > 1]}"))
                
                # 2. Validate Features
                feats = artifact.get("features", [])
                feat_ids = [f.get("feature_id") for f in feats if f.get("feature_id")]
                if len(feat_ids) != len(set(feat_ids)):
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Duplicate feature_id detected: {[fid for fid in feat_ids if feat_ids.count(fid) > 1]}"))

                # 3. Check Module-Feature namespace binding and monotonic sequence
                for m in modules:
                    mid = m.get("module_id", "")
                    mod_tag = mid.replace("MOD-", "")
                    mod_feats = [f for f in feats if f.get("module_id") == mid]
                    for idx, f in enumerate(mod_feats, start=1):
                        fid = f.get("feature_id", "")
                        expected_prefix = f"FEAT-{mod_tag}-"
                        if not fid.startswith(expected_prefix):
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Feature '{fid}' does not bind to parent module '{mid}' namespace (expected prefix '{expected_prefix}')"))
                        expected_fid = f"FEAT-{mod_tag}-{idx:03d}"
                        if fid != expected_fid:
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Feature ID sequence is discontinuous: expected '{expected_fid}', got '{fid}'"))

                # 4. Check error codes
                import re as _re
                err_pattern = _re.compile(r"^ERR_[A-Z0-9_]+$")
                for f in feats:
                    fid = f.get("feature_id", "")
                    for ec in f.get("error_cases", []):
                        code = ec.get("error_code", "")
                        if not err_pattern.match(code):
                            issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Feature '{fid}' has invalid error code format: '{code}'"))
            elif rid in ("prd.typography_and_pangu_spacing", "typography_and_pangu_spacing_verified"):
                import re as _re
                cjk = r"[\u4e00-\u9fff\u3400-\u4dbf]"
                latin = r"[A-Za-z0-9]"
                modules = artifact.get("information_architecture", {}).get("modules", [])
                for m in modules:
                    mname = m.get("name", "")
                    if _re.search(rf"{cjk}{latin}|{latin}{cjk}", mname):
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Module '{m.get('module_id')}' name '{mname}' violates CJK-Latin typography spacing (盘古之白)"))
                feats = artifact.get("features", [])
                for f_idx, f in enumerate(feats):
                    fid = f.get("feature_id", f"FEAT-{f_idx}")
                    fname = f.get("name", "")
                    if _re.search(rf"{cjk}{latin}|{latin}{cjk}", fname):
                        issues.append(ValidationIssue("conformance", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: Feature '{fid}' name '{fname}' violates CJK-Latin typography spacing (盘古之白)"))
            elif rid == "rev.blocking_findings_veto_ready":
                bf = artifact.get("blocking_findings", [])
                if bf and artifact.get("readiness_status") == "READY_FOR_DEV":
                    issues.append(ValidationIssue("consistency", f"standard_violation:{rid}", f"Standard rule '{rid}' violated: blocking_findings strictly forbids READY_FOR_DEV"))

    def _scan_placeholders(self, obj: Any, current_path: str = "") -> List[Tuple[str, str]]:
        found: List[Tuple[str, str]] = []
        if isinstance(obj, str):
            match = PLACEHOLDER_REGEX.search(obj)
            if match:
                found.append((current_path or "/", match.group(0)))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                p = f"{current_path}/{k}"
                found.extend(self._scan_placeholders(v, p))
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                p = f"{current_path}/{idx}"
                found.extend(self._scan_placeholders(item, p))
        return found

    def _validate_requirement_analysis_specifics(
        self, data: Dict[str, Any], issues: List[ValidationIssue], obs: Dict[str, Any]
    ) -> None:
        # Coverage: 5W1H
        five = data.get("five_w_one_h") or {}
        for key in ["why", "who", "what", "when", "where", "how"]:
            val = five.get(key)
            if not val or not str(val).strip():
                issues.append(
                    ValidationIssue(
                        "coverage",
                        f"missing_5w1h:{key}",
                        f"5W1H element '{key}' is required and cannot be empty",
                        f"/five_w_one_h/{key}",
                    )
                )

        # Grounding: Demand validation
        dv = data.get("demand_validation") or {}
        for k in ["problem_nature", "current_workarounds", "willingness_to_pay_or_suffer", "falsification_hypotheses", "validation_experiment"]:
            if not dv.get(k):
                issues.append(
                    ValidationIssue(
                        "grounding",
                        f"missing_demand_validation:{k}",
                        f"Demand validation property '{k}' must be completed",
                        f"/demand_validation/{k}",
                    )
                )

        # Consistency: Non-Goals check
        non_goals = data.get("non_goals") or []
        if len(non_goals) < 2:
            issues.append(
                ValidationIssue(
                    "consistency",
                    "insufficient_non_goals",
                    f"Non-goals must have at least 2 explicit exclusions, got {len(non_goals)}",
                    "/non_goals",
                )
            )
        for idx, ng in enumerate(non_goals):
            ng_text = json.dumps(ng, ensure_ascii=False) if isinstance(ng, dict) else str(ng)
            for phrase in FORBIDDEN_NON_GOAL_TERMS:
                if phrase in ng_text:
                    issues.append(
                        ValidationIssue(
                            "consistency",
                            "forbidden_non_goal_phrase",
                            f"Non-goal item {idx} contains forbidden positive phrasing '{phrase}'",
                            f"/non_goals/{idx}",
                        )
                    )

        # Implicit requirements
        implicit = data.get("implicit_requirements") or []
        if len(implicit) < 3:
            issues.append(
                ValidationIssue(
                    "coverage",
                    "insufficient_implicit_requirements",
                    f"Implicit requirements must declare at least 3 items, got {len(implicit)}",
                    "/implicit_requirements",
                )
            )

    def _validate_acceptance_criteria_specifics(
        self, criteria: Dict[str, Any], issues: List[ValidationIssue], obs: Dict[str, Any]
    ) -> None:
        # Recompute negative ratio
        scenarios = criteria.get("scenarios") or []
        neg = sum(1 for s in scenarios if s.get("scenario_type") in ("negative_defense", "fault_recovery"))
        total = len(scenarios)
        ratio = (neg / total * 100.0) if total else 0.0
        obs["negative_ratio_pct"] = round(ratio, 1)
        obs["scenarios_total"] = total
        obs["scenarios_negative"] = neg

        if total == 0:
            issues.append(ValidationIssue("coverage", "no_scenarios", "Acceptance criteria has no scenarios"))
        elif ratio < 30.0:
            issues.append(
                ValidationIssue(
                    "grounding",
                    "negative_ratio_below_threshold",
                    f"Negative defense scenarios ratio is {ratio:.1f}%, must be >= 30.0%",
                    "/scenarios",
                )
            )

    def validate_suite_oracle(self, suite: Dict[str, Any]) -> ValidationVerdict:
        """Executes full 7-artifact pipeline lineage recomputation via product_lineage_oracle.py."""
        issues: List[ValidationIssue] = []
        observations: Dict[str, Any] = {}

        # First validate each stage individually
        for key, artifact in suite.items():
            if isinstance(artifact, dict) and bool(self.resolve_schema(key)):
                sub_verdict = self.validate_artifact(key, artifact)
                for issue in sub_verdict.issues:
                    issue.pointer = f"/{key}{issue.pointer or ''}"
                    issues.append(issue)

        # Call oracle operations if available
        if ORACLE_SCRIPT.exists():
            import subprocess

            def _invoke_oracle(op: str, payload_input: Any) -> Optional[dict]:
                payload = {"operation": op, "input": payload_input}
                proc = subprocess.run(
                    [sys.executable, str(ORACLE_SCRIPT), json.dumps(payload, separators=(",", ":"))],
                    capture_output=True,
                    text=True,
                )
                if proc.returncode != 0:
                    issues.append(
                        ValidationIssue(
                            "oracle", f"oracle_process_failed:{op}", f"Oracle operation '{op}' exited with code {proc.returncode}: {proc.stderr}"
                        )
                    )
                    return None
                try:
                    return json.loads(proc.stdout)
                except Exception as e:
                    issues.append(
                        ValidationIssue("oracle", f"oracle_parse_error:{op}", f"Failed to parse oracle output for '{op}': {e}")
                    )
                    return None

            # 1. Pipeline
            pipe_res = _invoke_oracle("pipeline", suite)
            if pipe_res:
                observations["oracle_pipeline"] = pipe_res.get("observation", {})
                if pipe_res.get("verdict") != "passed":
                    for mm in pipe_res.get("observation", {}).get("mismatches", []):
                        issues.append(
                            ValidationIssue("oracle", f"oracle_mismatch:{mm}", f"Lineage oracle reported mismatch: {mm}")
                        )

            # 2. Invariants coverage
            inv_set = suite.get("product_invariant_set") or suite.get("product_invariants")
            crit_set = suite.get("acceptance_criteria_set") or suite.get("acceptance_criteria")
            if inv_set and crit_set:
                inv_res = _invoke_oracle("invariants_coverage", {"invariants": inv_set, "candidate": crit_set})
                if inv_res:
                    observations["oracle_invariants_coverage"] = inv_res.get("observation", {})
                    if inv_res.get("verdict") != "passed":
                        for mm in inv_res.get("observation", {}).get("mismatches", []):
                            issues.append(
                                ValidationIssue("oracle", f"oracle_mismatch:{mm}", f"Invariants coverage oracle mismatch: {mm}")
                            )

            # 3. Negative ratio
            if crit_set:
                neg_res = _invoke_oracle("negative_ratio", {"candidate": crit_set})
                if neg_res:
                    observations["oracle_negative_ratio"] = neg_res.get("observation", {})
                    if neg_res.get("verdict") != "passed":
                        for mm in neg_res.get("observation", {}).get("mismatches", []):
                            issues.append(
                                ValidationIssue("oracle", f"oracle_mismatch:{mm}", f"Negative ratio oracle mismatch: {mm}")
                            )

            # 4. Review consistency
            rep_set = suite.get("product_readiness_review_report") or suite.get("product_review_report")
            if rep_set:
                rev_res = _invoke_oracle("review_consistency", {"report": rep_set})
                if rev_res:
                    observations["oracle_review_consistency"] = rev_res.get("observation", {})
                    if rev_res.get("verdict") != "passed":
                        for mm in rev_res.get("observation", {}).get("mismatches", []):
                            issues.append(
                                ValidationIssue("oracle", f"oracle_mismatch:{mm}", f"Review consistency oracle mismatch: {mm}")
                            )
        else:
            issues.append(
                ValidationIssue("oracle", "oracle_missing", f"Oracle validator script not found at {ORACLE_SCRIPT}")
            )

        return ValidationVerdict(
            passed=len(issues) == 0,
            kind="suite",
            issues=issues,
            observations=observations,
        )


def format_verdict_console(verdict: ValidationVerdict) -> str:
    lines = []
    lines.append("=" * 65)
    lines.append(f"  Aurakl Five-Dimensional Acceptance Gatekeeper Report (Target: {verdict.kind})")
    lines.append("=" * 65)
    status_icon = "✅ PASSED" if verdict.passed else "❌ FAILED"
    lines.append(f"Verdict: {status_icon}")
    lines.append(f"Defects Found: {len(verdict.issues)}")

    if verdict.issues:
        lines.append("-" * 65)
        lines.append("[Defect Findings List]:")
        for idx, issue in enumerate(verdict.issues, 1):
            ptr = f" [{issue.pointer}]" if issue.pointer else ""
            lines.append(f"  {idx}. [{issue.dimension.upper()}] {issue.code}{ptr}")
            lines.append(f"     Reason: {issue.message}")

    if "governing_standard" in verdict.observations:
        std_info = verdict.observations["governing_standard"]
        lines.append("-" * 65)
        lines.append(f"Governing Standard: {std_info['id']} ({std_info['name']})")
        lines.append(f"Rules Checked: {len(std_info['rules_evaluated'])} [{', '.join(std_info['rules_evaluated'])}]")

    if verdict.observations:
        lines.append("-" * 65)
        clean_obs = {k: v for k, v in verdict.observations.items() if k != "governing_standard"}
        if clean_obs:
            lines.append(f"Observations: {json.dumps(clean_obs, ensure_ascii=False)}")

    lines.append("=" * 65)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aurakl Five-Dimensional Acceptance Gatekeeper (31 Schemas Supported)")
    parser.add_argument("--artifact", help="Path to artifact JSON file to validate")
    parser.add_argument("--kind", help="Kind of artifact or schema name (e.g. requirement_analysis, beachhead-strategy)")
    parser.add_argument("--schema", help="Alias for --kind (e.g. beachhead-strategy.v1.json)")
    parser.add_argument("--suite", help="Path to full golden product suite JSON file")
    parser.add_argument("--list-schemas", action="store_true", help="List all 31 registered schemas and their required fields")
    parser.add_argument("--calc-metrics", action="store_true", help="Calculate invariant coverage and negative scenario ratio")
    parser.add_argument("--invariants", help="Path to product_invariants.json (used with --calc-metrics)")
    parser.add_argument("--criteria", help="Path to acceptance_criteria.json (used with --calc-metrics)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    validator = AuraklValidator()

    if args.list_schemas:
        schemas = validator.list_all_schemas()
        if args.json:
            print(json.dumps(schemas, ensure_ascii=False, indent=2))
        else:
            print("=" * 80)
            print(f"  Aurakl Registered Schema Catalog ({len(schemas)} total)")
            print("=" * 80)
            for idx, s in enumerate(schemas, 1):
                req_str = ", ".join(s["required_fields"][:3])
                if len(s["required_fields"]) > 3:
                    req_str += f" (+{len(s['required_fields']) - 3} more)"
                print(f"{idx:02d}. {s['filename']:<36} | {s['title']:<30}")
                if s["description"]:
                    print(f"    Description: {s['description']}")
                print(f"    Required: [{req_str}]")
            print("=" * 80)
        return 0

    if args.calc_metrics:
        if not args.criteria:
            print("Error: --criteria is required for --calc-metrics", file=sys.stderr)
            return 1
        crit_data = json.loads(Path(args.criteria).read_text(encoding="utf-8"))
        res = {"negative_ratio": validator.calc_negative_ratio(crit_data)}
        if args.invariants:
            inv_data = json.loads(Path(args.invariants).read_text(encoding="utf-8"))
            res["invariant_coverage"] = validator.calc_invariant_coverage(inv_data, crit_data)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print("=" * 60)
            print("  Aurakl Metrics Report")
            print("=" * 60)
            nr = res["negative_ratio"]
            print(f"Negative Defense Ratio: {nr['negative_ratio_pct']}% (Threshold >= 30.0%, Compliant: {'✅' if nr['meets_safety_threshold'] else '❌'})")
            print(f"  - Defensive scenarios: {nr['negative_defense_scenarios']} / Total scenarios: {nr['total_scenarios']}")
            if "invariant_coverage" in res:
                ic = res["invariant_coverage"]
                print(f"Invariant Coverage: {ic['coverage_pct']}% ({ic['coverage_basis_points']} bp, Full 10000 bp, Compliant: {'✅' if ic['is_full_coverage'] else '❌'})")
                print(f"  - Covered invariants: {ic['covered_invariants']} / Total invariants: {ic['total_invariants']}")
                if ic["missing_invariants"]:
                    print(f"  - Missing invariants: {ic['missing_invariants']}")
            print("=" * 60)
        return 0

    if args.suite:
        suite_path = Path(args.suite)
        if not suite_path.exists():
            print(f"Error: suite file not found: {args.suite}", file=sys.stderr)
            return 1
        data = json.loads(suite_path.read_text(encoding="utf-8"))
        verdict = validator.validate_suite_oracle(data)
    elif args.artifact:
        art_path = Path(args.artifact)
        if not art_path.exists():
            print(f"Error: artifact file not found: {args.artifact}", file=sys.stderr)
            return 1
        data = json.loads(art_path.read_text(encoding="utf-8"))
        kind = args.schema or args.kind or "requirement_analysis"
        if kind == "suite":
            verdict = validator.validate_suite_oracle(data)
        else:
            verdict = validator.validate_artifact(kind, data)
    else:
        parser.print_help()
        return 1

    if args.json:
        out = {
            "passed": verdict.passed,
            "kind": verdict.kind,
            "issues": [asdict(i) for i in verdict.issues],
            "observations": verdict.observations,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(format_verdict_console(verdict))

    return 0 if verdict.passed else 2


if __name__ == "__main__":
    sys.exit(main())


# Backward compatibility alias
LumenValidator = AuraklValidator
