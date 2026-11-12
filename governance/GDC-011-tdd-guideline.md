---
doc_meta:
  id: GDC-011
  title: Technical Design Document (TDD) Guideline
  owner: Architecture Authority
  version: 1.0.0
  status: approved
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
  last_reviewed: 2026-11-12
---

# Technical Design Document (TDD) Guideline

## 1. Context & Scope

TDDs represent the component-level (C3) blueprints, API contracts, ERDs, security boundaries, and failure handling mechanisms for specific implementations before code is written.

---

## 2. Policy Framework

### 2.1 Directory Taxonomy

- **Requirement**: TDDs are owned by the System/deployable they implement. A single-System repository uses `<repo>/designs/`; a repository containing multiple independently governed Systems uses `<system-root>/designs/`. A repository-level shared TDD folder MUST NOT mix designs from different parent SADs.

**Example Directory Structure:**

```text
notification-platform/               # Multi-System repository
├── runtime/                         # Parent SAD boundary
│   └── designs/
│       └── delivery-runtime/
│           └── TDD-notif-runtime-001-delivery-runtime.md
└── experience/                      # Separate parent SAD boundary
    └── designs/
        └── browser-boundary/
            └── TDD-notif-experience-001-browser-boundary.md
```

_Current automation_: the linter checks only that a TDD's path contains a `designs/` directory (`compliance_macro_directory`, ERROR). No rule checks which System owns a `designs/` folder or whether one folder holds designs for different parent SADs.

### 2.2 The Schema Architecture

In addition to the global structural enforcement defined in **[GDC-001](GDC-001-fitness-functions.md)**, the TDD specification is strictly governed by the following domain-specific linter schemas:

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/tdd.schema.json`). If you need to update a rule, modify the schema file and run: `python generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category      | Parameter            | Enforcement / Value                                                                                                                                                                                                                  |
| :----------------- | :------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Metadata Rules** | Metadata Rules       | <ul><li>doc_meta</li></ul>                                                                                                                                                                                                           |
| **Section Rules**  | Required Sections    | <ul><li>Purpose</li><li>Scope</li><li>Technical Context</li><li>Component Design</li><li>Data Model</li><li>API / Interface</li><li>Algorithms / Logic</li><li>Configuration</li><li>Testing Strategy</li><li>Traceability</li></ul> |
| **Section Rules**  | Recommended Sections | <ul><li>Performance Notes</li><li>Security Notes</li><li>Operational Notes</li></ul>                                                                                                                                                 |

<!-- AUTO-GENERATED-SCHEMA:END -->

| Linter Component          | File                                                 | Enforcement Logic                                                                                                                                                                                                                                                                                                                               |
| :------------------------ | :--------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **JSON Schema**           | `schemas/tdd.schema.json`                            | Requires `doc_meta` with `id`, `title`, `status`, `created_date`, `owner`, `version`, `classification`, `review_cycle_days`, `last_reviewed` and `parent_sad` (one SAD id or a list); limits `status` to `draft`, `approved` and `deprecated`; requires the ten sections of §2.3.5 and the filename pattern of §2.3.1. It has no content rules. |
| **Python Engine**         | `engine/control/validators/domains/tdd_validator.py` | Reports `traceability_violation` (ERROR) when `parent_sad` is missing or empty, or names a document that does not exist. It does not check the parent SAD's status or the content of any section.                                                                                                                                               |
| **Placement**             | `engine/control/validators/global_rules.py`          | The path has to contain a `designs/` directory (`compliance_macro_directory`, ERROR) and the filename has to start with the document `id` (`compliance_filename_match`, ERROR).                                                                                                                                                                 |
| **Technology Radar**      | `engine/control/validators/metadata_rules.py`        | Each `technologies` entry (`name` and `base`) has to be in the Tech Radar: a `hold` entry reports `technology_hold_violation` (CRITICAL); an unknown entry reports `unapproved_technology` (ERROR).                                                                                                                                             |
| **Relationship Contract** | `governance/framework/contracts/relationships.yaml`  | `tdd-parent-sad`: at least one target, each a SAD. A missing `parent_sad` reports `orphan_document` (ERROR); a target of another type, a duplicate or a self-reference reports `structural_integrity_violation` (CRITICAL). The parent SAD's status is not checked.                                                                             |

**Engine Execution Mechanics**:

1. **Hold Technology Enforcement**: a technology in the TDD's `technologies` metadata that the Tech Radar marks `hold` reports `technology_hold_violation` (CRITICAL, blocking). The linter reads only the `technologies` metadata, not technologies named in the text ([GDC-004 §3.1](GDC-004-tech-lifecycle.md)).
2. **Traceability**: `parent_sad` names at least one SAD, and each named SAD has to exist in the repository. Unlike the parent PAD of a SAD, the parent SAD's status is not checked.
3. **Remote Execution (Security Constraint)**: Downstream project repositories must not maintain local copies of the linter. Local CI/CD pipelines must invoke the central linter remotely. See **[GDC-001: Architecture Fitness Functions](GDC-001-fitness-functions.md)** for detailed setup instructions.
4. **Draft TDDs**: a `draft` TDD gets relaxed validation, which skips the schema, the placement and Tech Radar checks and the TDD validator. It fails with `lifecycle_age_violation` (ERROR) 30 days after `created_date`. The relationship contract audits (`orphan_document`, `structural_integrity_violation`) still apply.

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

The filename must strictly adhere to the regex: `^TDD-[a-z0-9-]+-[a-z0-9-]+-\d{3}[A-Z]*-[a-z0-9-]+\.md$`.

Example: `TDD-notif-runtime-001-delivery-runtime.md` with `id: TDD-notif-runtime-001`. The filename starts with the document `id` (§2.2, Placement).

#### 2.3.2 Taxonomy

TDDs are **single, cohesive documents** (`TDD-[repo]-[component]-[seq]-[slug].md`, §2.3.1). **The Cohesion Rule:** Splitting a TDD into separate micro-files (e.g., separating it into `schema.md` and `tests.md`) is strictly prohibited. All component design aspects must be fully encapsulated within the single canonical document's mandated sections to prevent drift.

#### 2.3.3 Directory Structure

Must reside in `designs/` adjacent to the owning System/deployable source root. Repository-root `designs/` is valid only when the repository represents one System/deployable. In multi-System repositories, each System/deployable owns its own `<system-root>/designs/` namespace.

_Current automation_: see §2.1. The control registry keeps this obligation pending until a repository topology check exists.

#### 2.3.4 Metadata Schema Properties

Every TDD must begin with a YAML frontmatter block containing these fields:

```yaml
doc_meta:
  id: TDD-notif-runtime-001 # TDD-[repo]-[component]-[seq]
  title: [Component Title] # Descriptive title of the component
  owner: [Engineer/Role] # Authoritative owner
  version: 1.0.0 # Semantic versioning format
  status: approved # draft | approved | deprecated
  classification: internal # public | internal | restricted | confidential
  parent_sad: SAD-001 # One SAD id, or a list of SAD ids
  review_cycle_days: 180 # Review cycle period
  created_date: YYYY-MM-DD # Creation date
  last_reviewed: YYYY-MM-DD # Last audit date
  technologies: # Optional; each name (and base) has to be in the Tech Radar
    - name: PostgreSQL
      type: database
```

| Metadata Field      | Type           | Description / Purpose                                                                                       |
| ------------------- | -------------- | ----------------------------------------------------------------------------------------------------------- |
| `id`                | String         | Unique identifier; the filename starts with it (e.g., `TDD-notif-runtime-001`).                             |
| `title`             | String         | Descriptive title of the document.                                                                          |
| `owner`             | String         | Lead Owner (e.g., Software Engineer).                                                                       |
| `version`           | String         | Must comply with Semantic Versioning (e.g., 1.0.0).                                                         |
| `status`            | Enum           | The current lifecycle state (must match Allowed Statuses below).                                            |
| `classification`    | Enum           | The data sensitivity (must match Allowed Classifications below).                                            |
| `parent_sad`        | String or List | The parent SAD id or ids this design implements (the SAD `id` values). At least one; each SAD has to exist. |
| `review_cycle_days` | Integer        | The frequency in days for required review.                                                                  |
| `last_reviewed`     | Date           | The date of the last formal review (YYYY-MM-DD).                                                            |
| `created_date`      | Date           | Creation date (YYYY-MM-DD). Starts the 30-day limit for a `draft` TDD.                                      |
| `technologies`      | List           | Optional. Technologies the design uses, checked against the Tech Radar (§2.2).                              |

##### Allowed Lifecycle Statuses

| Status       | Meaning / Lifecycle Stage                                                              |
| ------------ | -------------------------------------------------------------------------------------- |
| `draft`      | The design is under review. Relaxed validation; it fails 30 days after `created_date`. |
| `approved`   | The design is approved for implementation.                                             |
| `deprecated` | The implementation is being phased out or has been replaced.                           |

##### Allowed Classifications

| Classification | Meaning / Data Sensitivity             |
| -------------- | -------------------------------------- |
| `public`       | Available to anyone.                   |
| `internal`     | Restricted to company employees.       |
| `restricted`   | Restricted to specific teams or roles. |
| `confidential` | Restricted to named individuals.       |

##### Semantic Versioning Classification

| Version           | Trigger / Architectural Change                                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Major (2.0.0)** | Breaking API contract changes (e.g., removing a required field, changing an endpoint path, fundamentally altering a database schema). |
| **Minor (1.1.0)** | Adding an optional field to an API response, adding a new non-breaking endpoint.                                                      |
| **Patch (1.0.1)** | Editorial updates, typo fixes, formatting, fixing dead links.                                                                         |

#### 2.3.5 Artifact Section

The linter requires each of these sections as a `##` heading with exactly that name (a leading number such as `3.` is allowed; case matters). The schema has no content rules, so the Requirement column is checked in review. Their semantic purposes are:

| Section Name                        | Objective                                                                                                                              | Requirement                                                                             |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| **Purpose**                         | State what the component or feature accomplishes and why.                                                                              | Names the functional requirements it meets.                                             |
| **Scope**                           | Bound the design: what it covers and what it leaves to other TDDs or to the SAD.                                                       | Lists the in-scope and out-of-scope items.                                              |
| **Technical Context**               | Place the component among its upstream and downstream dependencies inside the parent SAD.                                              | Links to the parent SAD.                                                                |
| **Component Design**                | Provide the C3 component blueprint: internal modules, interactions and sequence diagrams.                                              | Technology-specific.                                                                    |
| **Data Model**                      | Define the persistent and in-flight data: schemas, ERDs, migrations.                                                                   | Defines field types and validation rules.                                               |
| **API / Interface**                 | Define the exact payloads, endpoints, events and error contracts.                                                                      | Defines validation rules and the versioning or compatibility path for breaking changes. |
| **Algorithms / Logic**              | Describe the core logic, state machines and the component-level failure handling (retries, circuit breakers, degradation, edge cases). | Failure handling maps to the parent SAD's Blast Radius.                                 |
| **Configuration**                   | List configuration, feature flags and rollout settings.                                                                                | Gives defaults and the rollback setting for each flag.                                  |
| **Testing Strategy**                | Outline unit, integration and E2E testing.                                                                                             | Covers edge cases and security testing.                                                 |
| **Traceability**                    | Link the design to its parent SAD, the ADRs it follows and the requirements it meets.                                                  | Names the parent SAD id from `parent_sad`.                                              |
| **Performance Notes (Recommended)** | Record latency, throughput and resource budgets.                                                                                       | Gives measurable targets.                                                               |
| **Security Notes (Recommended)**    | Detail PII handling, RBAC or RLS policies and encryption.                                                                              | Names the policies, keys and PII handling routines.                                     |
| **Operational Notes (Recommended)** | Document metrics, log formats, tracing spans, alerts, rollout phases and rollback.                                                     | Defines SLI/SLO metrics and the rollback procedure.                                     |

Teams can add further sections, such as Alternatives Considered or Compatibility Strategy.

### 2.4 Lifecycle & Audit

#### 2.4.1 TDD Fate Matrix

TDDs are ephemeral. Their lifecycle must follow the **Ephemeral TDD Matrix**:

- **Class A (Strategic Transition)**: Designs governing core architectural shifts, major security FSMs, or schema migrations. Once fully implemented in production, their metadata `status` is transitioned to `deprecated` and the physical file is moved to `designs/historical/` to serve as a permanent forensic audit trail.
- **Class B (Component & Feature Detail)**: Standard feature implementation layouts. The final API contract is moved to the Source Code (e.g., OpenAPI/Swagger) and the physical TDD file is deleted once verified in production. They must **never** be folded into the SAD to prevent C3 detail pollution in C2 documents.
- **Class C (Exploratory & Spike)**: Prototype or exploratory designs. Deleted immediately after the Pull Request merges.

_Current automation_: no rule checks a TDD's class, its deletion or the move to `designs/historical/`; the Fate Matrix is a review obligation. A `last_reviewed` date older than `review_cycle_days` reports `review_age_violation` (WARNING, not blocking). `governance/framework/contracts/lifecycle.yaml` gives `approved` and `deprecated` TDDs full validation.

---

## 3. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the ARB explicitly documents the compromises of this TDD Guideline:

1. **The Ephemeral TDD Matrix vs. Permanent TDD Archives**
   - _Why rejected_: Archiving every component-level design forever leads to thousands of obsolete files. When a new engineer joins, they cannot distinguish between active architecture and legacy spikes.
   - _The Trade-Off_: We intentionally destroy (delete) historical design context for Class B/C implementations once they merge to main. In exchange, we radically reduce search latency and ensure that only high-level abstractions (PADs/SADs) and foundational shifts (Class A TDDs) are permanently maintained.
