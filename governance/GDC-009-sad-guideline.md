---
doc_meta:
  id: GDC-009
  title: System Architecture Document (SAD) Guideline
  owner: Architecture Authority
  version: 1.0.0
  status: approved
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
  last_reviewed: 2026-11-12
---

# System Architecture Document (SAD) Guideline

## 1. Context & Scope

SADs represent the C2 System/Software Architecture layer of the C4 metamodel, defining the physical execution containment, deployment topology, container boundaries, failure modes, and runtime observability (e.g., backend service monoliths, web SPAs, or mobile clients).

SADs establish the "How". They serve as the definitive physical blueprint for a specific deployable unit. A single logical domain capability (PAD) is physically fulfilled by one or more software containers (SADs) in a strict 1-to-N mapping. They establish the concrete technology stack, network isolation, and database engines required to execute the logical contracts defined by the PAD.

### 1.1 Philosophy & Decision Horizon

**Decision question:** _"How is one deployable system built to realize (part of) a PAD's capability?"_ A SAD is the solution-planning tier for a single deployable unit: the physical reality.

**Position on the three governing dimensions:**

- **Stability / half-life — 3–5 years (two-way door).** Expected to be refactored as technology and load evolve. Because it is replaceable, it may carry rich physical detail.
- **Abstraction — C2 physical (System Context + Container).** It stops at the container boundary; component- and class-level design (C3) belongs in the TDD.
- **Ownership — one system / service team.**

**Litmus test (SAD vs TDD):** _"Is this about how the system is composed and deployed (SAD), or how a unit is coded (TDD)?"_ Containers, deployment topology, and runtime flows → SAD. Classes, schemas / DDL, algorithms, and queries → TDD.

**Traceability:** every SAD declares its `parent_pad`; one PAD is realized by N SADs. A SAD never redefines a contract owned by its parent PAD — it implements it.

---

## 2. Policy Framework

### 2.1 Specificity & Containment

- **Specificity Rule**: Unlike PADs, SADs must completely drop agnosticity. They must explicitly specify the concrete physical deployment topology, technology stacks, cache stores, database engines, and physical container boundaries.
- **Containment Invariant**: SADs must explicitly document failure containment boundaries, specifically defining the Blast Radius for all major failure modes.
- **Physical Container Separation (Deployable Units Only)**: To prevent logical boundaries from being contaminated by deployment-specific execution mechanics, **every distinct deployable unit must have its own SAD**. Non-deployable components (e.g., shared UI libraries, internal SDKs) are strictly exempt from requiring a standalone SAD (see Section 2.1.1). For deployable systems, a single Identity PAD (`scnehaux-iam.pad.md`) might be fulfilled by:
  - **Backend API Service**: `scnehaux-iam.sad.md` (The core HTTP server).
  - **Frontend SPA**: `scnehaux-iam-web.sad.md` (The browser client).
  - **Async Worker**: `scnehaux-iam-worker.sad.md` (Kafka consumer handling background email dispatch).
  - **Data Pipeline/Cron**: `scnehaux-iam-archiver.sad.md` (Nightly job moving old sessions to cold storage).

#### 2.1.1 The Master SAD Federation (Multi-Repo & SDKs)

While microservices map neatly (one repo to one deployable unit), modern ecosystems often utilize **multi-repo libraries, SDKs, or Module Federation** where multiple repositories compile into a single deployable artifact. Forcing a SAD for every library repository creates excessive documentation noise and violates the physical deployment definition of a SAD.

To govern this, Scnehaux utilizes the **Aggregator-Component Pattern**:

1. **The Host Repository (The Master SAD)**: The primary repository responsible for compiling or deploying the final execution unit acts as the **Aggregator**. It must maintain the `Master SAD`. This artifact defines the aggregate physical topology, treating the remote SDKs and libraries as internal components within its container boundary.
2. **The Library/SDK Repositories (The Components)**: Repositories producing non-deployable libraries are **exempt** from requiring a SAD. They only require a **TDD** (Technical Design Document, `GDC-011`) to document their internal execution logic and API contracts.
3. **The Traceability Pointer**: To maintain the automated CI/CD Directed Acyclic Graph (DAG) and prevent the linter from flagging the library as an illegal orphan, the library repository must explicitly declare its governance inheritance in its linter configuration:
   ```yaml
   governance:
     master_sad: "SAD-001"
   ```
   _Current automation_: no engine module reads `master_sad`, and the linter has no repository-level SAD requirement to exempt a library from. The control registry keeps this obligation pending until a repository topology check exists.

### 2.2 The Schema Architecture

In addition to the global structural enforcement defined in **[GDC-001](GDC-001-fitness-functions.md)**, the SAD specification is strictly governed by the following domain-specific linter schemas:

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/sad.schema.json`). If you need to update a rule, modify the schema file and run: `python generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category             | Parameter                                        | Enforcement / Value                                                                                                                                                                                                                                                                            |
| :------------------------ | :----------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Metadata Rules**        | Metadata Rules                                   | <ul><li>doc_meta</li></ul>                                                                                                                                                                                                                                                                     |
| **Section Rules**         | Required Sections                                | <ul><li>Purpose & Scope</li><li>Enterprise Traceability</li><li>Solution Context</li><li>Architecture Model</li><li>State & Data Architecture</li><li>Integration Contracts</li><li>Security & Trust Boundary</li><li>NFR</li><li>Deployment Strategy</li><li>Architecture Decisions</li></ul> |
| **Section Rules**         | Recommended Sections                             | <ul><li>Assumptions</li><li>Compatibility Strategy</li><li>Migration Strategy</li><li>Alternatives</li></ul>                                                                                                                                                                                   |
| **Content Quality Rules** | Context & Scope (Required)                       | <ul><li>Objective</li><li>Constraint</li><li>Capability</li></ul>                                                                                                                                                                                                                              |
| **Content Quality Rules** | Context & Scope (Recommended)                    | <ul><li>Requirement</li><li>Assumption</li></ul>                                                                                                                                                                                                                                               |
| **Content Quality Rules** | Solution Context (Recommended)                   | <ul><li>System Context</li><li>External</li><li>Internal</li></ul>                                                                                                                                                                                                                             |
| **Content Quality Rules** | Architecture Model (Recommended Concepts)        | <ul><li>Container</li><li>Component</li><li>Sequence</li><li>Runtime Flow</li><li>Event Flow</li></ul>                                                                                                                                                                                         |
| **Content Quality Rules** | State & Data Architecture (Recommended Concepts) | <ul><li>Storage</li><li>Cache</li><li>Schema</li><li>Stateless</li></ul>                                                                                                                                                                                                                       |
| **Content Quality Rules** | Integration Contracts (Recommended Concepts)     | <ul><li>API</li><li>Event</li><li>Consumed</li><li>Published</li></ul>                                                                                                                                                                                                                         |
| **Content Quality Rules** | Security & Trust Boundary (Recommended Concepts) | <ul><li>Authentication</li><li>Authorization</li><li>Encryption</li><li>Secrets</li><li>Audit</li></ul>                                                                                                                                                                                        |
| **Content Quality Rules** | Deployment Strategy (Required)                   | <ul><li>CI/CD</li></ul>                                                                                                                                                                                                                                                                        |
| **Content Quality Rules** | Deployment Strategy (Recommended Concepts)       | <ul><li>Environment</li><li>Infrastructure</li></ul>                                                                                                                                                                                                                                           |
| **Content Quality Rules** | Architecture Decisions (Required)                | <ul><li>Rejected</li></ul>                                                                                                                                                                                                                                                                     |
| **Content Quality Rules** | NFR (Required)                                   | <ul><li>Blast Radius</li></ul>                                                                                                                                                                                                                                                                 |
| **Content Quality Rules** | NFR Derivatives (Recommended)                    | <ul><li>Latency</li><li>Throughput</li><li>RPS</li><li>Scalability</li><li>Caching</li><li>Observability</li><li>Telemetry</li><li>Alerting</li><li>Runbook</li><li>Circuit Breaker</li><li>Retry</li><li>Timeout</li><li>Failover</li></ul>                                                   |

<!-- AUTO-GENERATED-SCHEMA:END -->

| Linter Component     | File                                                 | Enforcement Logic                                                                                                                                                                                                                                        |
| :------------------- | :--------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **JSON Schema**      | `schemas/sad.schema.json`                            | Requires the `doc_meta` fields of §2.3.4 (including `governed_by` and `parent_pad`), the ten required sections of §2.3.5 with their required subsection terms, and the filename pattern of §2.3.1. Checks the shape of the optional `technologies` list. |
| **Python Engine**    | `engine/control/validators/domains/sad_validator.py` | `parent_pad` must name a PAD that exists and lists this SAD in its `fulfilled_by`; a `draft` or `approved` SAD needs an `approved` parent PAD (§2.3.6). Each failure reports `traceability_violation` (ERROR).                                           |
| **Technology Radar** | `engine/control/validators/metadata_rules.py`        | Each `technologies` entry (`name` and `base`) must be in the Tech Radar: a `hold` entry reports `technology_hold_violation` (CRITICAL); an unknown entry reports `unapproved_technology` (ERROR).                                                        |

**Engine Execution Mechanics**:

1. **Physical Containment Audit**: Unlike PADs, SADs must specify the concrete database engines, cache stores, and container topologies. No linter rule checks that a SAD contains this information; the ARB checks it in review.
2. **Hold Technology Enforcement**: a technology in the SAD's `technologies` metadata that the Tech Radar marks `hold` reports `technology_hold_violation` (CRITICAL, blocking). The linter reads only the `technologies` metadata, not technologies named in the text ([GDC-004 §3.1](GDC-004-tech-lifecycle.md)).
3. **Draft SADs**: a `draft` SAD gets relaxed validation, which skips the schema and the checks above. The parent PAD gate of §2.3.6 still applies (§2.4).

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

`schemas/sad.schema.json` checks filenames against `^[a-z0-9-]+\.sad\.md$`: lowercase letters, digits and hyphens only.

- **Naming Convention**:
  - `[system-name].sad.md` (no suffix): Represents the **primary/core application** of the system.
  - `[system-name]-[suffix].sad.md`: Represents **specific applications, clients, or workers** (e.g., `iam-web`, `iam-worker`).
- **Ambiguity Rule**: If a system contains multiple SADs, **avoid using a suffix-less name**. It is highly recommended to use explicit suffixes for all containers (e.g., `iam-api.sad.md` and `iam-web.sad.md`) to prevent ambiguity.

#### 2.3.2 Taxonomy

SADs are **single, cohesive artifacts** (`[system-name].sad.md` or `[system-name]-[suffix].sad.md`). **The Cohesion Rule:** Splitting a SAD into separate micro-files (e.g., separating it into `security.md` and `operations.md`) is strictly prohibited. All system aspects must be fully encapsulated within the single canonical artifact's mandated sections to prevent drift.

- **Grouping Rule**: The implementation of a single logical PAD will often result in multiple physical SADs. To maintain cohesion, **all SADs fulfilling the same domain must be grouped together** within a single `[system-name]` directory. Do not create separate root folders for each container. _(Reminder: While they share a folder, each physical container must still be documented by exactly **one** SAD)._

#### 2.3.3 Directory Structure

They must utilize **Asset Container Folders** (`systems/[system-name]/`), which act as an isolation boundary for the system's `.sad.md` files and supporting assets (e.g., deployment topology diagrams).

**Example Directory Structure:**

```text
architecture/
└── systems/                  # (Asset Container Folders)
    └── iam/                         # (System grouping folder)
        ├── iam-api.sad.md           # (Backend API SAD, explicit suffix)
        ├── iam-web.sad.md           # (Client application SAD)
        └── deployment-topology.png
```

#### 2.3.4 Metadata Schema Properties

Every SAD must begin with a YAML frontmatter block containing these fields:

```yaml
doc_meta:
  id: SAD-001 # Unique software system ID
  title: [Application Title] # Descriptive title of the application
  owner: [System Team/Role] # Authoritative system owner (string or list)
  version: 1.0.0 # Semantic versioning format
  status: chartered # chartered | draft | approved | deprecated
  classification: internal # public | internal | restricted | confidential
  parent_pad: PAD-001 # Exactly one parent PAD; that PAD lists this SAD in fulfilled_by
  governed_by: [GDC-009] # At least one ADR, EAD, GDC or STD id
  review_cycle_days: 180 # Review cycle period
  created_date: YYYY-MM-DD # Creation date
  last_reviewed: YYYY-MM-DD # Last audit date
  technologies: # Optional; each name (and base) must be in the Tech Radar
    - name: PostgreSQL
      type: database
```

| Metadata Field      | Type            | Description / Purpose                                                                   |
| ------------------- | --------------- | --------------------------------------------------------------------------------------- |
| `id`                | String          | Unique identifier matching `^SAD-\d{3}(?:-[A-Z0-9-]+)?$` (e.g., `SAD-001`).             |
| `title`             | String          | Descriptive title of the artifact.                                                      |
| `owner`             | String or array | Lead Owner (e.g., System Architect).                                                    |
| `version`           | String          | Must comply with Semantic Versioning (e.g., 1.0.0).                                     |
| `status`            | Enum            | The current lifecycle state (must match Allowed Statuses below).                        |
| `classification`    | Enum            | The data sensitivity (must match Allowed Classifications below).                        |
| `parent_pad`        | String          | Exactly one parent PAD id (e.g., `PAD-001`); that PAD lists this SAD in `fulfilled_by`. |
| `governed_by`       | String or array | At least one ADR, EAD, GDC or STD id (`relationships.yaml`).                            |
| `review_cycle_days` | Integer         | The frequency in days for required review.                                              |
| `last_reviewed`     | Date            | The date of the last formal review (YYYY-MM-DD).                                        |
| `created_date`      | Date            | The date the artifact was created (YYYY-MM-DD).                                         |
| `technologies`      | Array           | Optional. Each entry has `name`, `type` and an optional `base`; see §2.2.               |

##### Allowed Lifecycle Statuses

| Status       | Meaning / Lifecycle Stage                                                                           |
| ------------ | --------------------------------------------------------------------------------------------------- |
| `chartered`  | A physical realization is recognized for traceability, but no system is in active design/build yet. |
| `draft`      | The physical system architecture is under active design/review; draft-age pressure applies.         |
| `approved`   | The software architecture is formalized and acts as the official design blueprint.                  |
| `deprecated` | The system is being phased out or has been replaced.                                                |

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
| **Major (2.0.0)** | Overhauling the core framework, splitting the monolith, changing the persistence layer, or altering physical deployment topologies (e.g., VM to Kubernetes). |
| **Minor (1.1.0)** | Adding a new bounded context, exposing a new major API version, or integrating a new managed service (e.g., adding an S3 bucket or a Redis cache).           |
| **Patch (1.0.1)** | Editorial updates, formatting, updating the `parent_pad` reference, fixing dead links.                                                                       |

#### 2.3.5 Artifact Section

The linter enforces the presence of these sections. Their semantic purposes are:

| Section Name                          | Objective                                                                                                 | Requirement                                                                                             |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Purpose & Scope**                   | Explain the technical "Why" behind the system boundary.                                                   | Must contain **Objective**, **Constraint** and **Capability**.                                          |
| **Enterprise Traceability**           | Link the system to its parent PAD and its governing documents.                                            | Must name the parent PAD and the documents in `governed_by`.                                            |
| **Solution Context**                  | Show the system among its users and its external and internal systems.                                    | Recommended terms: System Context, External, Internal.                                                  |
| **Architecture Model**                | Concrete C2 container diagrams, request lifecycles, asynchronous event publishing, and degradation paths. | Must illustrate all physical containers and boundaries, with sequence diagrams for critical operations. |
| **State & Data Architecture**         | Document data classification, persistence layers, and caching strategies.                                 | Must detail database engines, storage, and data sensitivity (PII/PHI).                                  |
| **Integration Contracts**             | Specify API endpoints, consumed services, and published events.                                           | Must detail external/internal integrations and data contracts.                                          |
| **Security & Trust Boundary**         | Detail system-level threat mitigations, input validation, and secrets management.                         | Must address threat models, data encryption at rest/transit, and IAM boundaries.                        |
| **NFR**                               | Quantified targets, SPOFs, fallback strategies, monitoring, and the exact **Blast Radius**.               | Must contain **Blast Radius** (§2.4).                                                                   |
| **Deployment Strategy**               | Document CI/CD pipelines, release environments, and scaling triggers.                                     | Must contain **CI/CD**.                                                                                 |
| **Architecture Decisions**            | Document the decisions taken, the alternatives evaluated, and their trade-offs.                           | Must contain **Rejected**, listing rejected technologies or designs with the rationale.                 |
| **Assumptions (Optional)**            | Document external operational assumptions.                                                                | Lists business, external, or operational assumptions the design relies upon.                            |
| **Compatibility Strategy (Optional)** | Detail schema migration or API versioning compatibility rules.                                            | Outlines API versioning or schema migration paths to avoid breaking changes.                            |
| **Migration Strategy (Optional)**     | Describe how the system moves from its current to its target state.                                       | Lists the migration steps and their rollback.                                                           |
| **Alternatives (Optional)**           | Record alternatives in more depth than Architecture Decisions.                                            | Lists each alternative and why it was not chosen.                                                       |

The linter matches each required subsection term case-insensitively at the start of a line: plain text, a bold term, a bold list item, or a `###` to `#####` heading. It does not check the recommended terms or the content of the other cells.

#### 2.3.6 Parent PAD Activation Gate

SAD lifecycle is subordinate to the parent PAD commitment state.

- a `chartered` SAD is permitted under a `chartered`, `draft`, or `approved` PAD as a non-build placeholder
- a SAD SHALL NOT enter `draft` while its parent PAD is not `approved`
- a SAD SHALL NOT enter `approved` while its parent PAD is not `approved`
- promotion of the parent PAD does not automatically approve the SAD; physical design still follows the SAD review lifecycle

The relationship contract `sad-parent-pad` enforces this rule for `draft` and `approved` SADs (`structural_integrity_violation`, CRITICAL). The SAD validator reports it as well (`traceability_violation`, ERROR) for SADs that get full validation.

### 2.4 Lifecycle & Audit

All SAD artifacts must undergo a periodic review every `review_cycle_days` (default 180 days) to ensure structural integrity and relevance against the enterprise capability map.

_Current automation_: a `last_reviewed` date older than `review_cycle_days` reports `review_age_violation` (WARNING, not blocking). `governance/framework/contracts/lifecycle.yaml` gives `chartered`, `approved` and `deprecated` SADs full validation. A `draft` SAD gets relaxed validation and fails with `lifecycle_age_violation` (ERROR) 30 days after `created_date`. The schema requires the term `Blast Radius` in the NFR section; it does not check each failure mode.

**Qualitative Enforcement (Architecture Authority Audit)** _Note: Qualitative scoring is inherited from **[GDC-002 §2 — Scoring Criteria](GDC-002-quality-rubric.md)**._

SADs have the following custom overriding audit metric:

1. **Blast Radius Analysis**: Under the NFR section, every major failure mode must specify the _Blast Radius_ (e.g., "Single User Session", "Full Tenant Isolation", "Entire Platform Outage") to pass the review gate.

---

## 3. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the Architecture Authority explicitly documents the compromises of this SAD Guideline:

1. **Manual Blast Radius Enforcement vs. Automated Chaos Engineering**
   - _Why rejected_: Fully automated Chaos Engineering requires significant infrastructure maturity and cannot run effectively during the design phase before code is written.
   - _The Trade-Off_: We rely on the architect's manual, theoretical calculation of the "Blast Radius" during the design phase. In exchange, we force engineers to confront and document failure boundaries proactively, preventing SPOFs from entering the codebase in the first place.
