# Aurakl Skills: Industrial-Grade Agent Skills Suite

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](./plugin.json)
[![Python](https://img.shields.io/badge/python-3.9+-brightgreen.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-orange.svg)](./LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-0%20(Pure%20Stdlib)-success.svg)](./requirements.txt)
[![Tests](https://img.shields.io/badge/tests-71%2F71%20passed-brightgreen.svg)](./tests/)

**Aurakl Skills** is an enterprise-grade agent skills suite designed for AI pair-programming systems (Google Antigravity, Claude Code, Cursor, and Agent Skills specifications). It bundles production-hardened **Product Management** and **Software Architecture** capabilities powered by mathematical invariants, Cartesian completeness audits, and pure-Python validation engines.

---

## 🌟 Key Highlights

- **Dual-Layer SOP & Formal Verification**: Moves beyond LLM text generation to strict engineering deliverables audited by deterministic Python oracles.
- **Dynamic Language Matching**: Automatically detects and mirrors the user's natural language (100% pure Chinese or 100% pure English), forbidding mixed-language artifacts while preserving canonical technical identifiers.
- **Zero Hallucination & Zero Placeholder**: Enforces strict anti-placeholder policies (`TODO`, `TBD`, `待定`, `占位符` are rejected at the validator gate).
- **Closed-World Data Closure**: Preconditions and input parameters must trace to explicit upstream sources (user input, DB entity, or third-party service).
- **Zero External Dependencies**: All validation, rendering, and calculation engines run on Python 3.9+ standard library (`json`, `argparse`, `pathlib`, `re`, `unittest`). No `pip install` required.

---

## 📦 Bundled Skills

```
aurakl-skills/
├── plugin.json                    # Plugin manifest
├── rules/
│   └── AGENTS.md                  # Automatic agent quality invariants & behavioral rules
├── skills/
│   ├── aurakl-product-manager/    # Product Management Skill
│   └── aurakl-software-architect/ # Software Architecture Skill
```

### 1. `aurakl-product-manager` (工业级产品需求工程规约)
Adheres to **ISO/IEC/IEEE 29148** requirements engineering standards across a 7-stage pipeline:
- **Stage 01**: 5W1H interactive elicitation, problem falsification (`painkiller` vs `vitamin`), and 4-archetype domain adaptation (Mobile, Desktop, Backend, IoT).
- **Stage 02**: Market & competitive intelligence with structured multi-dimension barrier matrix.
- **Stage 03**: Multi-persona journeys ($\ge 3$ personas) and 100% touchpoint-covered INVEST user stories.
- **Stage 04**: Design-by-Contract PRD authoring with RFC 2119 business rules and closed-world data closure.
- **Stage 05**: Formal product invariants across State Machine, Algebraic Conservation, Security/Permissions, and UX Safeguards.
- **Stage 06**: Acceptance test matrix with 100% invariant coverage (10,000 bp) and $\ge 30\%$ negative defensive scenarios.
- **Stage 07**: Deterministic Lineage Oracle gatekeeper audit and dynamic Markdown deliverable rendering.

### 2. `aurakl-software-architect` (工业级软件架构设计规约)
Adheres to the **Linus Torvalds Pragmatic Architecture Philosophy** across a 9-stage blueprint:
- **Stage 01**: Architecture Decision Records (ADR) tech selection matrix with multi-candidate weighted scoring.
- **Stage 02**: 3-layer modular monolith topological architecture with explicit boundaries.
- **Stage 03**: 100% PRD domain model coverage, rich entities, value objects, and physical invariants.
- **Stage 04**: Physical relational database schema & index design with copy-pasteable PostgreSQL/MySQL DDL and rollback migrations.
- **Stage 05**: Strongly-typed, backward-compatible API contracts with complete request/response JSON examples and business error mappings.
- **Stage 06**: 3-path sequence flows (Success, Validation/Business Rejection, System Timeout/Degradation).
- **Stage 07**: 9-dimension architecture invariant defense matrices.
- **Stage 08**: Acyclic technical dependency DAG verification.
- **Stage 09**: Cartesian completeness audit, One-Vote Veto Lineage Oracle gatekeeper, and Markdown rendering.

---

## 🚀 Installation & Usage

### Method 1: Standard Agent Skills Installation (Recommended, Universal)
Install seamlessly into **Antigravity, Claude Code, Cursor, Codex, Cline, Amp**, and any Agent Skills-compliant environment via `npx skills`:

```bash
# 1. Install all skills into your current project workspace (.agents/skills/):
npx skills add AuraklAI/aurakl-skills

# 2. Or install a specific skill:
npx skills add AuraklAI/aurakl-skills -s aurakl-product-manager
npx skills add AuraklAI/aurakl-skills -s aurakl-software-architect

# 3. Install globally across all projects on your machine:
npx skills add AuraklAI/aurakl-skills -g

# 4. Instant local workspace test (if already in this repository):
npx skills add . -y
```

### Method 2: Native Antigravity Plugin Bundle (Workspace or Global)
If you are using Google Antigravity and wish to bundle both the skills and `rules/AGENTS.md` quality invariants:
```bash
# Workspace level (in your project root):
mkdir -p .agents/plugins
git clone https://github.com/AuraklAI/aurakl-skills.git .agents/plugins/aurakl-skills

# Global level (across all projects):
mkdir -p ~/.gemini/config/plugins
git clone https://github.com/AuraklAI/aurakl-skills.git ~/.gemini/config/plugins/aurakl-skills
```

### Method 3: Python CLI & CI/CD Pipeline Automation (`pip`)
For continuous integration, pre-commit hooks, or standalone terminal execution of the deterministic validation engines:
```bash
cd aurakl-skills
pip install -e .
aurakl status
```

---

## 🛠️ CLI Toolkit Guide

### Product Management CLI (`aurakl pm`)
```bash
# 5W1H Requirement Elicitation
aurakl pm elicit --input brief.json

# Five-dimensional Acceptance Validation
aurakl pm validate --artifact output.json --schema prd.v2.json

# Invariant Coverage & Defensive Scenario Metrics Calculation
aurakl pm calc-metrics --criteria acceptance_criteria.json --invariants product_invariants.json

# Full Deterministic Lineage Oracle Audit
aurakl pm audit --suite suite.json

# Multi-dimensional Markdown Document Rendering
aurakl pm render --source source/ --output requirement/
```

### Software Architecture CLI (`aurakl arch`)
```bash
# Architecture Validation (Single stage or full suite with upstream PRD binding)
aurakl arch validate <path_to_json> --suite --upstream-prd <path_to_prd>

# Markdown Blueprint Rendering (English / Chinese)
aurakl arch render <path_to_json> --lang en -o architecture.md
aurakl arch render <path_to_json> --lang zh -o architecture.zh.md

# Cartesian Completeness Audit
aurakl arch cartesian <path_to_suite_json>

# One-Vote Veto Lineage Oracle Verification
aurakl arch oracle <path_to_suite_json> --upstream-prd <path_to_prd>
```

---

## 🧪 Verification & Testing

Verify plugin integrity and run all 65+ unit tests:
```bash
# Using unified CLI:
./bin/aurakl test

# Or via Python unittest:
python3 tests/test_plugin_integrity.py -v
```

---

## 📄 License

Licensed under the [Apache License, Version 2.0](./LICENSE).
