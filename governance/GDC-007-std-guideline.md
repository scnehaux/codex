---
doc_meta:
  id: GDC-007
  title: Enterprise Standards (STD) Guideline
  owner: Architecture Authority
  version: 1.0.0
  status: approved
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
  last_reviewed: 2026-11-11
---

# Enterprise Standards (STD) Guideline

## 1. Context & Scope

The `standards` directory is the authoritative collection of mandatory rules, constraints, patterns, and methodologies governing software development and architecture across the Scnehaux enterprise. Its scope encompasses lower-level technical instructions such as API Design guidelines, coding styles, and database schemas.

### 1.1 STD vs ADR (Living Law vs Historical Log)

- **ADR (Architecture Decision Record)** captures a point-in-time decision, explaining _why_ a choice was made and its context. ADRs may become superseded or deprecated, but their historical text remains immutable.
- **STD (Standard)** is a _living document_. It represents the active, mandatory ruleset that engineers must follow _today_. When rules change, the STD file is updated to reflect the current state of truth.

---

## 2. Policy Framework

### 2.1 Specificity & Opinionation

- **Specificity Policy**: Standards (STDs) are **not** meant to be agnostic. They exist to enforce strict, concrete, and opinionated technical baselines. If a policy is purely abstract, it belongs in an Enterprise Architecture Document (EAD) as a Principle.
- **Global Standards**: Define enterprise-wide technical constraints (e.g., universal API payloads, central logging schemas). While they may start as high-level abstract policies, once a specific technology becomes an enterprise baseline (e.g., via an ADR), global STDs must aggressively mandate its usage.
- **Domain & Local Standards**: Must be fiercely technology-specific and framework-opinionated. They map global requirements directly to concrete code implementations (e.g., "Use React 18", "Use Prisma" in the `ui-platform` repo).

### 2.2 The Schema Architecture

In addition to the global structural enforcement defined in **[GDC-001](GDC-001-fitness-functions.md)**, the STD specification is strictly governed by the following domain-specific linter schemas:

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/std.schema.json`). If you need to update a rule, modify the schema file and run: `python generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category             | Parameter               | Enforcement / Value                                                                                                                    |
| :------------------------ | :---------------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| **Metadata Rules**        | Metadata Rules          | <ul><li>doc_meta</li></ul>                                                                                                             |
| **Section Rules**         | Required Sections       | <ul><li>Objective & Scope</li><li>Design Principles</li><li>Normative Rules</li><li>Exceptions</li><li>Enforcement Mechanism</li></ul> |
| **Section Rules**         | Recommended Sections    | <ul></ul>                                                                                                                              |
| **Content Quality Rules** | Exceptions (Prohibited) | <ul><li>waiver</li><li>ADR</li><li>ARB</li><li>Approval Requirements</li></ul>                                                         |

<!-- AUTO-GENERATED-SCHEMA:END -->

| Linter Component  | File                                                 | Enforcement Logic                                                                                                                                                                  |
| :---------------- | :--------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Domain Schema** | `schemas/std.schema.json`                            | Requires the five sections of §2.3.5 and the filename pattern of §2.3.1; reports `prohibited_words` (ERROR) for `waiver`, `ADR`, `ARB` or `Approval Requirements` in `Exceptions`. |
| **Python Engine** | `engine/control/validators/domains/std_validator.py` | **Hold check**: reports `operational_stability_violation` (ERROR) when the STD's own `status` is `hold`. Allowed statuses and classifications come from the schema.                |

**Engine Execution Mechanics**: the linter does not read which technologies an STD mandates. Technology `hold` blocks apply to the `technologies` metadata of SADs and TDDs ([GDC-004 §3.1](GDC-004-tech-lifecycle.md)). For an STD, only its own `hold` status is checked, and `ERROR` is a blocking severity.

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

`schemas/std.schema.json` checks filenames against `^STD-[A-Z]+(?:-[A-Z]+)?-\d{3}-[a-z0-9-]+\.md$`: one or two uppercase segments, a three-digit sequence and a lowercase slug.

- **Enterprise Naming Convention**: `STD-[DOMAIN]-[N]-[slug].md` (Global, e.g., `STD-GLB-001-api-design.md`) or `STD-[DOMAIN]-[CAPABILITY]-[N]-[slug].md` (Domain).
- **Project Naming Convention**: `STD-[REPO]-[COMPONENT]-[N]-[slug].md`.

#### 2.3.2 Taxonomy

Because STDs are authored at both the Root Enterprise level and the Local Project level, they must utilize different structural taxonomies appropriate for their scope.

**Enterprise Level (Architecture Repo)** Enterprise standards must strictly adhere to a **Domain-Driven Taxonomy** within the `standards/` directory.

- **Rule 1 (Max Depth)**: Directory nesting is strictly capped at Level 3 (`Root -> Domain -> Capability`). Creating further subdirectories inside a capability folder (Level 4+) is prohibited to prevent the "Russian Doll" anti-pattern.
- **Rule 2 (Sequential Grouping)**: To group multi-part documents without violating the Max Depth rule, place them in the same capability folder with consecutive sequence numbers (e.g., `001`, `002`). The filename pattern of §2.3.1 rejects letter suffixes such as `001A`.

**Project Level (Local Repo)** Because a project repository inherently represents a single Domain or System, Domain-Driven Taxonomy is redundant. Local standards must utilize **Module/Feature-Driven Taxonomy** to closely mirror the source code structure.

#### 2.3.3 Directory Structure

**Enterprise Level (Architecture Repo)**

```text
architecture/
└── standards/                    # (Domain-Driven Taxonomy)
    ├── _global/
    │   └── STD-GLB-001-api-design.md
    └── ui-platform/
        └── design-tokens/
            ├── STD-UIP-TKN-001-architecture.md
            └── STD-UIP-TKN-002-tier1-core-tokens.md
```

**Project Level (Local Repo)** Must reside in the `docs/01-standards/` directory.

```text
scnehaux-ui-platform/                # (Project Repository)
└── docs/
    └── 01-standards/                # (Module-Driven Taxonomy)
        ├── core-components/
        │   └── STD-UIP-CORE-001-button-api.md
        └── form-components/
            └── STD-UIP-FORM-001-validation.md
```

#### 2.3.4 Metadata Schema Properties

**Enterprise Level (Architecture Repo)**

```yaml
doc_meta:
  id: STD-[DOM]-[Seq] | STD-[DOM]-[CAP]-[Seq] # e.g., STD-GLB-001 or STD-UIP-TKN-001
  title: Short Descriptive Title
  owner: Lead Domain Architect Name / Team
  version: Y.Y.Y
  status: adopted | trial | assessed | hold
  classification: public | internal | restricted | confidential
  created_date: YYYY-MM-DD
  governed_by: [Parent Context ID] # Required: at least one EAD, PAD or GDC id
```

**Project/Local Level (Project Repo)**

```yaml
doc_meta:
  id: STD-[REPO]-[COMPONENT]-[Seq] # e.g., STD-UIP-CORE-001
  title: Short Descriptive Title
  owner: Lead System Engineer / Team Name
  version: Y.Y.Y
  status: adopted | trial | assessed | hold
  classification: public | internal | restricted | confidential
  created_date: YYYY-MM-DD
  parent_std: [Parent Enterprise Standard ID] # e.g., STD-GLB-001 (traceability link; not checked by the linter)
  governed_by: [Parent Context ID] # Required: at least one EAD, PAD or GDC id
```

| Metadata Field   | Type            | Description / Purpose                                            |
| ---------------- | --------------- | ---------------------------------------------------------------- |
| `id`             | String          | Unique identifier.                                               |
| `title`          | String          | Descriptive title of the artifact.                               |
| `owner`          | String or array | Lead System Engineer / Team Name.                                |
| `version`        | String          | Must comply with Semantic Versioning (e.g., 1.0.0).              |
| `status`         | Enum            | The current lifecycle state (must match Allowed Statuses below). |
| `classification` | Enum            | The data sensitivity (must match Allowed Classifications below). |
| `created_date`   | Date            | The date the artifact was created (YYYY-MM-DD).                  |
| `governed_by`    | Array           | At least one EAD, PAD or GDC id (`relationships.yaml`).          |

##### Allowed Lifecycle Statuses

| Status     | Meaning / Lifecycle Stage                                                            |
| ---------- | ------------------------------------------------------------------------------------ |
| `adopted`  | Formally accepted and enforced.                                                      |
| `trial`    | In evaluation or POC phase.                                                          |
| `assessed` | Evaluated but not necessarily adopted.                                               |
| `hold`     | Retirement. The STD fails validation with `operational_stability_violation` (ERROR). |

##### Allowed Classifications

| Classification | Meaning / Data Sensitivity             |
| -------------- | -------------------------------------- |
| `public`       | Available to anyone.                   |
| `internal`     | Restricted to company employees.       |
| `restricted`   | Restricted to specific teams or roles. |
| `confidential` | Need-to-know access only.              |

##### Semantic Versioning Classification

| Version           | Trigger / Architectural Change                                                                                                                               |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Major (2.0.0)** | Radically changing a mandatory baseline (e.g., swapping approved database engines or introducing a new mandatory compliance layer). Breaks existing systems. |
| **Minor (1.1.0)** | Adding a new supplemental best-practice or an optional paved road. Backwards-compatible.                                                                     |
| **Patch (1.0.1)** | Editorial updates, typo fixes, formatting, fixing dead links.                                                                                                |

#### 2.3.5 Artifact Section

The linter enforces the presence of these sections. Their semantic purposes are:

| Section Name              | Objective                                                                                                                                                                                                                                                                                                                                                                                     | Requirement                                                                                   |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Objective & Scope**     | Defines what the standard covers and who it applies to.                                                                                                                                                                                                                                                                                                                                       | Must define the boundary of the standard and explicitly list any exclusions.                  |
| **Design Principles**     | The architectural philosophy behind the standard (the "why").                                                                                                                                                                                                                                                                                                                                 | Must justify the technical axioms guiding the standard.                                       |
| **Normative Rules**       | The core constraints and DOs/DONTs. _(Optional: Include Examples/Snippets directly under the relevant rules to provide clarity)._                                                                                                                                                                                                                                                             | Must use RFC-2119 terminology (MUST, SHOULD, MUST NOT) for clear compliance.                  |
| **Exceptions**            | A direct mapping of normative rules to the specific technical conditions under which they may be bypassed. If no valid exceptions exist, this section must explicitly state `None.`.<br>**Constraint**: Prohibited keywords include `waiver`, `ADR`, `ARB`, `Approval Requirements`. Governance procedures must NOT be documented here; this section only describes technical boundary edges. | Must strictly define boundary conditions for deviation. Do NOT include governance procedures. |
| **Enforcement Mechanism** | How compliance is measured (e.g., CI/CD Linter, Architecture Authority Review). _(Optional: Specify the Severity of the violation)._                                                                                                                                                                                                                                                          | Must specify the automated linter, pipeline hook, or review process enforcing the standard.   |

### 2.4 Lifecycle & Audit

#### 2.4.1 Standard Maturity Model

To prevent rigid compliance grids from stifling innovation, every enterprise standard must declare a maturity phase in its `status` field.

> **Authoritative Source**: The canonical definitions of the four maturity phases (Assessed, Trial, Adopted, Hold), including their adoption requirements, deviation policies, and sunset procedures, are defined and maintained in **[GDC-004 — Technology Lifecycle & Standards Governance](GDC-004-tech-lifecycle.md)**.

All STD artifacts must declare one of the four phases defined in GDC-004 in their `status` metadata field.

_Current automation_: `schemas/std.schema.json` accepts the four phases and also `draft`, `proposed`, `approved` and `deprecated`, so the linter does not reject a status that is not a phase. `governance/framework/contracts/lifecycle.yaml` gives STDs lifecycle classes only for `draft` (relaxed validation; fails with `lifecycle_age_violation` 30 days after `created_date`), `approved` and `deprecated`. A phase status gets full validation, and an STD in `hold` fails validation (§2.2). The ARB checks the phase in review.

#### 2.4.2 The Living Specification Principle (Mutability & Versioning)

Unlike ADRs (which are immutable historical logs of a specific point-in-time decision), **STDs are living specifications** that represent the _currently active_ engineering mandates.

1. **Direct Mutability**: When technologies, standards, or rules evolve, the existing STD file is edited directly. Creating new standard files for minor/major updates to the same domain is prohibited.
2. **Versioning Doctrine (SemVer)**: Every update to an STD must increment the `version` metadata field following Semantic Versioning (X.Y.Z):
   - **Major (X.0.0)**: Introducing new mandatory restrictions, breaking changes, or deprecating existing active paths.
   - **Minor (1.X.0)**: Adding optional recommendations, non-breaking rules, or clarifying examples.
   - **Patch (1.0.X)**: Fixing typos, broken links, or minor metadata updates.
3. **ADR Authorization Invariant**: Any change resulting in a **Major (X.0.0)** version bump of an enterprise standard MUST be authorized by an approved ADR. The STD must cite that ADR (id and link) in its `Design Principles` section.

`governance/framework/contracts/relationships.yaml` accepts only EAD, GDC and PAD ids in an STD's `governed_by`, so the authorizing ADR is cited in the text, not in `governed_by`.

---

## 3. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the Architecture Authority explicitly documents the compromises of this STD Guideline:

1. **Living Mutability vs. Immutable Standard Versions**
   - _Why rejected_: Storing every past version of a standard as a separate immutable file creates a "graveyard" of artifacts, leading to engineer confusion about which standard is currently active.
   - _The Trade-Off_: We lose out-of-the-box visibility into historical rules. In exchange, we guarantee that the `standards/` folder is always the definitive "Current State of Truth." Historical context is preserved in Git, while structural pivots are managed via Immutable ADRs.
