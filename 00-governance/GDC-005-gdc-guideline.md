---
doc_meta:
  id: GDC-005
  title: Governance Document Contract (GDC) Guideline
  owner: Architecture Authority
  version: 0.0.1
  status: draft
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
---

# Governance Document Contract (GDC) Guideline

## 1. Context & Scope

In accordance with the [Circular Governance (Metaprogramming)](./GDC-000-governance-policy.md#12-core-philosophy-the-existential-maxims), the Governance framework must subject itself to the exact same rigorous validation criteria it imposes on downstream architectures.

As the foundational policies of the ecosystem, this artifact defines the deterministic boundaries governing **Governance Document Contracts (GDC)** themselves. This includes absolute compliance with the automation scope and criteria enforced by the Master Fitness Function (see [The Automation Scope & Domain Boundaries](GDC-001-fitness-functions.md#12-the-automation-scope--domain-boundaries)).

---

## 2. Policy Framework

### 2.1 The Schema Architecture

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/gdc.schema.json`). If you need to update a rule, modify the schema file and run: `python 06-fitness-function/generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category | Parameter | Enforcement / Value |
| :--- | :--- | :--- |
| **Metadata Rules** | Metadata Rules | <ul><li>doc_meta</li></ul> |
| **Section Rules** | Required Sections | <ul><li>Context & Scope</li><li>Policy Framework</li></ul> |
| **Section Rules** | Recommended Sections | <ul><li>Enforcement Mechanism</li><li>Enforcement Mechanism & Rule Reconciliation</li><li>Severity & Exceptions</li><li>Document Types (Glossary of Truth)</li><li>Document Lifecycle & State Management</li><li>Linter Execution Flow (CI/CD Automated Gate)</li><li>Compliance & Enforcement</li><li>The Git Workflow & Access Control</li><li>The Reconciliation Flow (Adding or Modifying Policies)</li><li>Directory Structure & Taxonomy</li><li>Directory Structure & Naming Conventions</li><li>Document Template Schema (Metadata Frontmatter)</li><li>Document Section Semantics</li><li>Semantic Versioning Classification</li><li>Appendix: Architectural Clarifications & Trade-Offs</li><li>Appendix: Architectural Trade-Offs</li></ul> |
| **Content Quality Rules** | Policy Framework (Required) | <ul><li>Semantic Definitions</li></ul> |
| **Content Quality Rules** | Semantic Definitions (Required Sub Sections) | <ul><li>Naming Conventions</li><li>Taxonomy</li><li>Directory Structure</li><li>Metadata Schema Properties</li><li>Artifact Section</li></ul> |
| **Content Quality Rules** | Metadata Schema Properties (Required Sub Sections) | <ul><li>Allowed Lifecycle Statuses</li><li>Allowed Classifications</li><li>Semantic Versioning Classification</li></ul> |

<!-- AUTO-GENERATED-SCHEMA:END -->

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

The filename must strictly adhere to the regex: `^GDC-\d{3}-[a-z0-9-]+\.md$`. If a GDC is acting as a downstream guideline, its name must end with `-guideline.md`.

#### 2.3.2 Taxonomy

All Governance Document Contracts (GDC) must be placed strictly in the root of the `00-governance/` directory. To maintain the "Fractal Triad" of automated governance (Policy, Rules, and Schemas), supplementary technical enforcement assets must be categorized into their respective subdirectories:

- `schemas/`: Contains the declarative JSON Schema definitions (`*.schema.json`) that act as the Single Source of Truth (SSOT) for metadata, structural, and declarative content requirements.
- `../engine/control/validators/domains/`: Contains the executable domain validators that enforce complex dynamic logic not expressible in static schemas.
- `templates/`: Contains non-authoritative reviewer or authoring templates. Files in this directory are excluded from artifact discovery by directory scope, never by filename suffix.

#### 2.3.3 Directory Structure

```text
codex/
├── 00-governance/
│   ├── schemas/
│   │   └── gdc.schema.json
│   ├── templates/
│   │   └── review-score-sheet.md
│   └── GDC-005-gdc-guideline.md
└── 06-fitness-function/
    └── engine/
        └── validators/
            └── domains/
                └── gdc_validator.py
```

#### 2.3.4 Metadata Schema Properties

| Metadata Field      | Type    | Description / Purpose                                               |
| ------------------- | ------- | ------------------------------------------------------------------- |
| `id`                | String  | Unique identifier (e.g., `GDC-000`).                                |
| `title`             | String  | Descriptive title of the artifact.                                  |
| `owner`             | String  | Lead Owner (e.g., Architecture Authority).                          |
| `version`           | String  | Must comply with Semantic Versioning (e.g., 1.0.0).                 |
| `status`            | Enum    | The current lifecycle state (Refers to Allowed Lifecycle Statuses). |
| `classification`    | Enum    | The data sensitivity (Refers to Classification Semantics below).    |
| `review_cycle_days` | Integer | The frequency in days for required review.                          |
| `last_reviewed`     | Date    | The date of the last formal review (YYYY-MM-DD).                    |

##### Allowed Lifecycle Statuses

| Status     | Meaning / Lifecycle Stage                                                                                                        |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `draft` | Pre-baseline Governance Control Plane contract. May use `0.x.x`, receives FULL validation, does not require `last_reviewed`, and has no architecture-admission authority |
| `approved` | Stable enforceable governance baseline. Requires `last_reviewed` and Semantic Version `1.0.0` or higher |
| `deprecated` | Previously approved baseline being retired. Remains fully validated and version-stable until retirement completes |

##### Allowed Classifications

While the exact string values are enforced by the CI Linter, their semantic meanings are:

| Classification | Meaning / Data Sensitivity                                              |
| -------------- | ----------------------------------------------------------------------- |
| `public`       | Available to anyone.                                                    |
| `internal`     | Restricted to company employees.                                        |
| `restricted`   | Restricted to specific teams or roles.                                  |
| `confidential` | Highly sensitive information restricted to a strict need-to-know basis. |

##### Semantic Versioning Classification

| Version           | Trigger / Architectural Change                                |
| ----------------- | ------------------------------------------------------------- |
| **Major (2.0.0)** | Breaking rule changes, introducing new strict policies.       |
| **Minor (1.1.0)** | Adding new optional guidelines or non-breaking constraints.   |
| **Patch (1.0.1)** | Editorial updates, typo fixes, formatting, fixing dead links. |

#### 2.3.5 Artifact Section

The linter enforces the presence of these sections. Their semantic purposes are:

| Section Name                           | Purpose / Content Requirement                                                                  |
| -------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Context & Scope**                    | Defines the boundaries, objectives, and scope of the governance policy.                        |
| **Policy Framework**                   | Documents the core guidelines, philosophies, schemas, or models being established.             |
| **Enforcement Mechanism**              | (Optional) Redefine ONLY if the artifact has domain-specific linter rules.                     |
| **Severity & Exceptions**              | (Optional) Redefine ONLY if the artifact explicitly blocks waivers or alters severity scaling. |
| **Artifact Types (Glossary of Truth)** | (Optional) Defines the glossary of truth.                                                      |
| **Artifact Lifecycle & Statuses**      | (Optional) Defines the lifecycle statuses.                                                     |

### 2.4 Artifact Lifecycle & Statuses

#### 2.4.0 GDC Draft Semantics

GDC uses the lifecycle `draft → approved → deprecated`. No bootstrap-specific document status exists.

A GDC in `draft`:

- starts in the `0.x.x` Semantic Version series
- executes the full Fitness Function validation profile
- does not require `last_reviewed`
- is not yet a stable downstream contract
- cannot authorize architecture artifact admission

Promotion to `approved` requires a stable Semantic Version of `1.0.0` or higher and a formal Git review event. Architecture admission is independently controlled by the bootstrap manifest and opens only when its declared required GDC baseline set satisfies those conditions.


#### 2.4.1 Git-Centric Audit Trail (No Backdoor Approvals)

The Genesis Bootstrap root commit may admit GDCs only in `draft` state. It is not a baseline approval event. After the root commit, a governance or architecture artifact is considered `approved` or `accepted` only when formally reviewed and merged via a Git Pull Request. Status changes outside that path are invalid. External tools (such as Jira or Confluence) are not proof of approval; the canonical Git history is the recognized chain of custody.

### 2.5 The Downstream Guideline Interface

If a Governance Document Contract (GDC) is specifically authored to serve as a **Guideline** governing a downstream architectural artifact type (e.g., EAD, PAD, SAD, STD, ADR, TDD), it is legally bound to the "Downstream Guideline Interface".

To be recognized by the Linter as a Downstream Guideline, the artifact's filename **MUST** end with the suffix `-guideline.md` (e.g., `GDC-009-pad-guideline.md`).

Any GDC adopting this interface must explicitly define the following 4 structural pillars to completely eradicate implicit knowledge:

1. **Taxonomy & Directory Structure**: Must define exactly where the downstream artifacts are allowed to be physically stored (e.g., root repo vs project repos).
2. **Naming Conventions**: Must define the exact Regex pattern the downstream artifact filenames must adhere to.
3. **Artifact Section Semantics**: Must explicitly list all required and optional markdown `##` sections the downstream artifact must contain.
4. **Metadata Schema Properties**: Must define the precise YAML frontmatter (`doc_meta`) schema required for the downstream artifact.

---

## 3. The Reconciliation Flow (Adding or Modifying Rules)

If you need to introduce a new constraint or modify an existing rule across any of the architecture artifacts, you must follow this exact flow to maintain the integrity of the CI/CD linter:

1. **Codify the Rule**: Do not edit the Markdown guidelines directly. Instead, encode the rule into the machine-readable format.
   - For declarative constraints (e.g., required sections, metadata schemas, allowed formats), edit the appropriate `00-governance/schemas/[type].schema.json`.
   - For complex dynamic logic, modify the corresponding Python validator under `engine/control/validators/`.
2. **Reconcile Documentation (Generate, Don't Duplicate)**: To maintain the Single Source of Truth (SSOT), the human-readable markdown tables inside the Guideline artifacts must be synchronized with the YAML. You **MUST** regenerate the documentation by executing:
   ```bash
   python 06-fitness-function/generators/generate_rules_doc.py
   ```
3. **Update Semantic Definitions**: The automated script only updates the machine-readable table. You **MUST** manually update the Semantic Definitions section in the corresponding Guideline artifact to explain the "Why" and "How" behind your new constraints for human readers.
4. **Qualitative Synchronization (Human Governance)**: If your rule modification impacts the qualitative evaluation of architecture (e.g., prohibiting new vague terms, demanding new quantitative NFR metrics, or altering risk disclosure requirements), you **MUST** also manually synchronize the human-driven governance artifacts:
   - Update `GDC-002-quality-rubric.md` (The 10-Parameter Qualitative Benchmark).
   - Update `00-governance/templates/review-score-sheet.md` (The Architecture Authority Peer-Review Execution Tool).

Failure to follow this reconciliation flow will result in Documentation Drift and a rejected Pull Request.

---

## 4. Enforcement Mechanism

In addition to the global structural enforcement defined in `GDC-001`, GDC artifacts are strictly governed by the following domain-specific linter components:

| Linter Component  | File                                         | Enforcement Logic                                                                                             |
| :---------------- | :------------------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| **Domain Schema** | `schemas/gdc.schema.json`                    | Specific `review_cycle_days`, strict metadata, and policy structure.                                          |
| **Python Engine** | `engine/validators/domains/gdc_validator.py` | **Taxonomy**: Validates `allowed_statuses` and `allowed_classifications` ensuring proper baseline governance. |

---

## 5. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the Architecture Authority explicitly documents the compromises of this GDC Guideline:

1. **Self-Referential Linter Rules vs Hardcoded Engine Logic**
   - _Why rejected_: Writing specific logic in the main engine `engine/cli.py` to validate `GDC` files pollutes the global execution engine with domain-specific concerns.
   - _The Trade-Off_: We accept the cognitive overhead of creating a specific `engine/validators/domains/gdc_validator.py` module and a `schemas/gdc.schema.json` to validate the files that define the rules themselves. In exchange, the global linter engine remains perfectly domain-agnostic, treating `GDC` files identically to `SAD` or `PAD` files during execution.
