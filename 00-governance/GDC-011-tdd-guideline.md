---
doc_meta:
  id: GDC-011
  title: Technical Design Document (TDD) Guideline
  owner: Architecture Authority
  version: 0.0.1
  status: draft
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
---

# Technical Design Document (TDD) Guideline

## 1. Context & Scope

TDDs represent the component-level (C3) blueprints, API contracts, ERDs, security boundaries, and failure handling mechanisms for specific implementations before code is written.

---

## 2. Policy Framework

### 2.1 Directory Taxonomy

- **Requirement**: TDDs are owned by the System/deployable they implement. A single-System repository uses `<repo>/docs/02-designs/`; a repository containing multiple independently governed Systems uses `<system-root>/docs/02-designs/`. A repository-level shared TDD folder MUST NOT mix designs from different parent SADs.

**Example Directory Structure:**

```text
notification-platform/               # Multi-System repository
├── runtime/                         # Parent SAD boundary
│   └── docs/
│       └── 02-designs/
│           └── delivery-runtime/
│               └── TDD-notif-runtime-001-delivery-runtime.md
└── experience/                      # Separate parent SAD boundary
    └── docs/
        └── 02-designs/
            └── browser-boundary/
                └── TDD-notif-experience-001-browser-boundary.md
```

### 2.2 The Schema Architecture

In addition to the global structural enforcement defined in **[GDC-001](GDC-001-fitness-functions.md)**, the TDD specification is strictly governed by the following domain-specific linter schemas:

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/tdd.schema.json`). If you need to update a rule, modify the schema file and run: `python 06-fitness-function/generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category | Parameter | Enforcement / Value |
| :--- | :--- | :--- |
| **Metadata Rules** | Metadata Rules | <ul><li>doc_meta</li></ul> |
| **Section Rules** | Required Sections | <ul><li>Purpose</li><li>Scope</li><li>Technical Context</li><li>Component Design</li><li>Data Model</li><li>API / Interface</li><li>Algorithms / Logic</li><li>Configuration</li><li>Testing Strategy</li><li>Traceability</li></ul> |
| **Section Rules** | Recommended Sections | <ul><li>Performance Notes</li><li>Security Notes</li><li>Operational Notes</li></ul> |

<!-- AUTO-GENERATED-SCHEMA:END -->

| Linter Component  | File                                         | Enforcement Logic                                                                                                                                                                                              |
| :---------------- | :------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **JSON Schema**   | `schemas/tdd.schema.json`                    | Validates `parent_sad` attributes to prevent orphan designs.                                                                                                                                                   |
| **Python Engine** | `engine/validators/domains/tdd_validator.py` | **Taxonomy**: Validates `allowed_statuses` and `allowed_classifications`.<br>**Domain Validation**: Enforces exact structural mapping of nested Markdown sections (e.g., Sequence Diagrams, Payload examples). |

**Engine Execution Mechanics**:

1. **Hold Technology Enforcement**: The automated linter will execute a Hard Block (Exit 1) on any TDD document that implements a technology currently marked as `Hold` in its respective lifecycle phase.
2. **Traceability**: The linter ensures that a `parent_sad` attribute exists in the TDD metadata, preventing isolated or "orphan" components.
3. **Remote Execution (Security Constraint)**: Downstream project repositories must not maintain local copies of the linter. Local CI/CD pipelines must invoke the central linter remotely. See **[GDC-001: Architecture Fitness Functions](GDC-001-fitness-functions.md)** for detailed setup instructions.

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

The filename must strictly adhere to the regex: `^TDD-[a-z0-9-]+-[a-z0-9-]+-\d{3}[A-Z]*-[a-z0-9-]+\.md$`.

#### 2.3.2 Taxonomy

TDDs are **single, cohesive documents** (`TDD-[REPO]-[COMPONENT].md`). **The Cohesion Rule:** Splitting a TDD into separate micro-files (e.g., separating it into `schema.md` and `tests.md`) is strictly prohibited. All component design aspects must be fully encapsulated within the single canonical document's mandated sections to prevent drift.

#### 2.3.3 Directory Structure

Must reside in `docs/02-designs/` adjacent to the owning System/deployable source root. Repository-root `docs/02-designs/` is valid only when the repository represents one System/deployable. In multi-System repositories, each System/deployable owns its own `<system-root>/docs/02-designs/` namespace.

#### 2.3.4 Metadata Schema Properties

Every TDD must begin with a YAML frontmatter block containing these fields:

```yaml
doc_meta:
  id: TDD-[REPO]-[COMPONENT]-[Seq] # Unique system ID
  title: [Component Title] # Descriptive title of the component
  owner: [Engineer/Role] # Authoritative owner
  version: 1.0.0 # Semantic versioning format
  status: approved # proposed | approved | deprecated
  classification: internal # public | internal | restricted
  parent_sad: SAD-XXX # Referencing the Parent SAD ID
  review_cycle_days: 180 # Review cycle period
  last_reviewed: YYYY-MM-DD # Last audit date
```

| Metadata Field      | Type    | Description / Purpose                                            |
| ------------------- | ------- | ---------------------------------------------------------------- |
| `id`                | String  | Unique identifier (e.g., `STD-EXAMPLE-008`).                      |
| `title`             | String  | Descriptive title of the document.                               |
| `owner`             | String  | Lead Owner (e.g., Software Engineer).                            |
| `version`           | String  | Must comply with Semantic Versioning (e.g., 1.0.0).              |
| `status`            | Enum    | The current lifecycle state (must match Allowed Statuses below). |
| `classification`    | Enum    | The data sensitivity (must match Allowed Classifications below). |
| `parent_sad`        | String  | The parent SAD ID this design implements (e.g., `SAD-EXAMPLE-001`).      |
| `review_cycle_days` | Integer | The frequency in days for required review.                       |
| `last_reviewed`     | Date    | The date of the last formal review (YYYY-MM-DD).                 |

##### Allowed Lifecycle Statuses

| Status       | Meaning / Lifecycle Stage                                    |
| ------------ | ------------------------------------------------------------ |
| `proposed`   | The design is under review.                                  |
| `approved`   | The design is approved for implementation.                   |
| `deprecated` | The implementation is being phased out or has been replaced. |

##### Allowed Classifications

| Classification | Meaning / Data Sensitivity             |
| -------------- | -------------------------------------- |
| `public`       | Available to anyone.                   |
| `internal`     | Restricted to company employees.       |
| `restricted`   | Restricted to specific teams or roles. |

##### Semantic Versioning Classification

| Version           | Trigger / Architectural Change                                                                                                        |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Major (2.0.0)** | Breaking API contract changes (e.g., removing a required field, changing an endpoint path, fundamentally altering a database schema). |
| **Minor (1.1.0)** | Adding an optional field to an API response, adding a new non-breaking endpoint.                                                      |
| **Patch (1.0.1)** | Editorial updates, typo fixes, formatting, fixing dead links.                                                                         |

#### 2.3.5 Artifact Section

The linter enforces the presence of these sections. Their semantic purposes are:

| Section Name                             | Objective                                                                                                                  | Requirement                                                                      |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Context & Requirements**               | Define the upstream and downstream context, what the feature accomplishes, and the specific functional requirements.       | Must link to the Parent SAD.                                                     |
| **Design Details**                       | Provide the C3 component blueprints. Include sequence diagrams, internal interactions, and structural class/module design. | Must be technology-specific.                                                     |
| **API / Schema Contracts**               | Outline the exact payloads, database schemas (ERD), API endpoints, or event formats.                                       | Must define validation rules.                                                    |
| **Security & Privacy**                   | Detail how PII is handled, what specific RBAC or RLS policies apply, and encryption requirements.                          | Must detail specific RBAC policies, encryption keys, and PII handling routines.  |
| **Failure Handling**                     | Describe component-level retries, circuit breakers, degradation, and edge case mitigation.                                 | Must be mapped to the SAD Blast Radius.                                          |
| **Observability**                        | Document exact metric names, log formats, and distributed tracing spans that will be emitted.                              | Must define specific SLI/SLO metrics, tracing spans, and alert thresholds.       |
| **Testing Strategy**                     | Outline unit, integration, and E2E testing approaches.                                                                     | Must mention edge cases and security testing.                                    |
| **Rollout Strategy**                     | Document feature flags, rollout phases, schema migration steps, and backward compatibility.                                | Must detail rollback procedures.                                                 |
| **Alternatives Considered _(Optional)_** | Analysis of alternate paths rejected during review.                                                                        | Must list rejected technologies/designs and the rationale for rejection.         |
| **Compatibility Strategy _(Optional)_**  | Detailed backward compatibility plans for API changes.                                                                     | Must outline API versioning or schema migration paths to avoid breaking changes. |

### 2.4 Lifecycle & Audit

#### 2.4.1 TDD Fate Matrix

TDDs are ephemeral. Their lifecycle must follow the **Ephemeral TDD Matrix**:

- **Class A (Strategic Transition)**: Designs governing core architectural shifts, major security FSMs, or schema migrations. Once fully implemented in production, their metadata `status` is transitioned to `deprecated` and the physical file is moved to `docs/02-designs/historical/` to serve as a permanent forensic audit trail.
- **Class B (Component & Feature Detail)**: Standard feature implementation layouts. The final API contract is moved to the Source Code (e.g., OpenAPI/Swagger) and the physical TDD file is deleted once verified in production. They must **never** be folded into the SAD to prevent C3 detail pollution in C2 documents.
- **Class C (Exploratory & Spike)**: Prototype or exploratory designs. Deleted immediately after the Pull Request merges.

---

## 3. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the ARB explicitly documents the compromises of this TDD Guideline:

1. **The Ephemeral TDD Matrix vs. Permanent TDD Archives**
   - _Why rejected_: Archiving every component-level design forever leads to thousands of obsolete files. When a new engineer joins, they cannot distinguish between active architecture and legacy spikes.
   - _The Trade-Off_: We intentionally destroy (delete) historical design context for Class B/C implementations once they merge to main. In exchange, we radically reduce search latency and ensure that only high-level abstractions (PADs/SADs) and foundational shifts (Class A TDDs) are permanently maintained.
