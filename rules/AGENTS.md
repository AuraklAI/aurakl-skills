# Aurakl Skills Agent Behavioral Guidelines & Quality Invariants

When `aurakl-skills` is active, all agents executing product management or software architecture workflows MUST strictly enforce the following invariants:

## 1. Dynamic Language Matching & End-to-End Alignment (铁律一：动态语言同构)
- **Zero Mixed-Language Deliverables**:
  - The agent MUST dynamically detect and mirror the primary natural language of the user prompt and upstream requirements.
  - If the user prompt (or upstream PRD) is in **Chinese**, all intermediate machine-readable JSON artifacts (`source/*.json`) and all rendered Markdown documentation MUST be 100% in Chinese (headings, descriptions, ADR rationales, table headers, schema comments).
  - If the user prompt is in **English**, all intermediate JSON artifacts and rendered Markdown documentation MUST be 100% in English.
- **Canonical Token Preservation**:
  - Formal identifier keys, enum constants, schema properties, and standard tags (e.g., `REQ-*`, `INV-*`, `FEAT-*`, `AC-*`, `ADR-*`, `HTTP status codes`) MUST remain canonical English tokens as specified by the schemas.

## 2. Zero-Placeholder & Production-Grade Depth (铁律二：零占位符与拒绝空壳)
- **Absolute Prohibition of Placeholders**:
  - Never emit placeholders such as `TODO`, `TBD`, `待定`, `暂略`, `占位符`, `后续补充`, `等等`, `依此类推`, or empty stub structures (`{}`).
- **Concrete & Implementable Blueprints**:
  - Every entity in the domain model must define actual physical attributes, types, nullability, and relations.
  - Every API contract must contain complete request/response JSON examples and explicit business step validations.
  - Every database design must include copy-pasteable PostgreSQL/MySQL DDL with explicit primary keys, foreign keys, and indexes.

## 3. Mathematical Invariants & Lineage Closure (铁律三：不变量防御与血缘闭包)
- **Mathematical Invariant Coverage**:
  - Product specifications must define cross-cutting invariants across State Machine, Algebraic Conservation, Security/Permissions, and UX Safeguards.
  - Architecture specifications must satisfy 9-dimension architectural invariants and 100% requirements coverage.
- **Closed-World Data Closure**:
  - Every input parameter or precondition required by a feature must be traceable to an explicit upstream source: user input, database entity, or upstream third-party service.
  - No feature may assume data magically exists without an explicit generation/retrieval mechanism.

## 4. Verification Before Delivery (铁律四：交付前必经 Oracle 门禁验证)
- The agent MUST NOT declare a task or artifact "Done" based on hallucinated self-assertion.
- All JSON deliverables must be verified by executing the Python validation and oracle tools (`aurakl pm validate/audit` or `aurakl arch validate/oracle`).
- Only when the automated validator returns `PASSED` with 0 blocking errors may the artifact be presented to the user.
