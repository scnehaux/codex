---
doc_meta:
  id: GDC-008
  title: Product Architecture Document (PAD) Guideline
  owner: Architecture Authority
  version: 1.0.0
  status: approved
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
  last_reviewed: 2026-11-11
---

# Product Architecture Document (PAD) Guideline

## 1. Context & Scope

PADs represent the C1 System Context / Domain Architecture layer of the C4 metamodel, defining the logical domain capabilities, bounded contexts, trust boundaries, and strategic positioning of a business domain (e.g., `identity`, `ui-platform`, `hris`, `finance`).

PADs establish the "What". They serve as the design-time single source of truth (SSOT) for domain-level contracts. A single logical domain capability (PAD) governs one or more physical software containers (SADs) in a strict 1-to-N mapping. They establish conceptual integration rules (such as trust boundaries and SLA targets) _before_ physical systems are built. While concrete API specifications are delegated downstream via Web Developer Portals, the PAD remains the stable, logical anchor.

### 1.1 Philosophy & Decision Horizon

**Decision question:** _"What capability does this product or platform own, where are its boundaries, and what does it promise — independent of how any system builds it?"_ A PAD is the domain charter tier: the logical plan, not the solution.

**Every product AND platform has exactly one PAD.** A platform is simply a product whose consumers are internal; it is not a separate document type.

**Position on the three governing dimensions:**

- **Stability / half-life — 10+ years (one-way door).** It outlives the SADs and TDDs that realize it. To stay durable it must remain thin — capability, boundaries, contracts, NFR promises — and exclude implementation detail.
- **Abstraction — C1 logical.** Bounded contexts and contracts only; never physical containers, deployment, or technology choices (those are the SAD).
- **Ownership — one stream-aligned domain team.**

**Litmus test (PAD vs SAD):** _"Does this fact survive a complete technology rewrite?"_ If yes → PAD. If it would change when you swap technology or topology → SAD.

**Stability guardrail:** a PAD boundary is drawn by **bounded-context (capability) cohesion**, not by commercial or marketing packaging. Re-bundling products does not merge PADs — PADs follow domains, which keeps the 10-year horizon credible.

**Traceability:** a PAD realizes one or more EAD capabilities (upward, `realizes_capability`). Physical realization is recorded both ways: each SAD names its parent PAD in `parent_pad`, and the PAD lists its SADs in `fulfilled_by` (§2.2).

---

## 2. Policy Framework

### 2.1 Agnosticity & Stability

- **Agnosticity Policy**: PADs must remain technology-agnostic at the physical infrastructure level. They establish logical capabilities, trust boundaries, and conceptual integration policies (e.g., SLA targets). Concrete API specifications must be delegated to downstream Web Developer Portals, and physical container details belong in SADs.
- **Stability**: Because they govern logical rather than physical boundaries, PADs are designed to be highly stable. Future physical decompositions (e.g., splitting a monolithic HRIS backend into separate Payroll and Employee microservices) must require zero modification to the core domain contracts established within the PAD.

### 2.2 The Schema Architecture

In addition to the global structural enforcement defined in **[GDC-001](GDC-001-fitness-functions.md)**, the PAD specification is strictly governed by the following domain-specific linter schemas:

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/pad.schema.json`). If you need to update a rule, modify the schema file and run: `python generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category             | Parameter                                   | Enforcement / Value                                                                                                                                                                                                                                                                                        |
| :------------------------ | :------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Metadata Rules**        | Metadata Rules                              | <ul><li>doc_meta</li></ul>                                                                                                                                                                                                                                                                                 |
| **Section Rules**         | Required Sections                           | <ul><li>Purpose & Scope</li><li>Enterprise Traceability</li><li>Domain & Context Model</li><li>Integration Contracts</li><li>Trust & Data Boundaries</li><li>Capability NFR</li><li>Ownership & Governance</li></ul>                                                                                       |
| **Section Rules**         | Recommended Sections                        | <ul><li>Assumptions & Constraints</li><li>Architectural Decisions</li><li>Evolution</li><li>References</li></ul>                                                                                                                                                                                           |
| **Content Quality Rules** | Purpose & Scope (Required Concepts)         | <ul><li>Out Of Scope</li></ul>                                                                                                                                                                                                                                                                             |
| **Content Quality Rules** | Enterprise Traceability (Required Concepts) | <ul><li>Realizes</li><li>Relationships</li><li>Consumed By</li></ul>                                                                                                                                                                                                                                       |
| **Content Quality Rules** | Domain & Context Model (Required Concepts)  | <ul><li>Bounded Context</li><li>Ubiquitous Language</li></ul>                                                                                                                                                                                                                                              |
| **Content Quality Rules** | Integration Contracts (Required Concepts)   | <ul><li>Integration Provided</li><li>Integration Consumed</li></ul>                                                                                                                                                                                                                                        |
| **Content Quality Rules** | Trust & Data Boundaries (Required Concepts) | <ul><li>Trust Boundary</li><li>Identity Access</li><li>Data Classification</li></ul>                                                                                                                                                                                                                       |
| **Content Quality Rules** | Capability NFR (Recommended Derivatives)    | <ul><li>SLA</li><li>SLO</li><li>RTO</li><li>RPO</li><li>Availability</li><li>Scalability</li><li>Peak Load</li><li>Concurrency</li><li>Compliance</li><li>Data Privacy</li><li>Data Residency</li><li>Audit</li><li>Usability</li><li>Accessibility</li><li>Interoperability</li><li>Cost Target</li></ul> |
| **Content Quality Rules** | Ownership & Governance (Required Concepts)  | <ul><li>Team Ownership</li><li>Realizing Systems</li></ul>                                                                                                                                                                                                                                                 |

<!-- AUTO-GENERATED-SCHEMA:END -->

| Linter Component  | File                                                 | Enforcement Logic                                                                                                                                                                                                                                                                                                                           |
| :---------------- | :--------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **JSON Schema**   | `schemas/pad.schema.json`                            | Requires the `doc_meta` fields of §2.3.4, the seven required sections of §2.3.5 with their required subsection terms, and the filename pattern of §2.3.1.                                                                                                                                                                                   |
| **Python Engine** | `engine/control/validators/domains/pad_validator.py` | **Upward**: `realizes_capability` must list at least one EAD id that exists, otherwise `traceability_violation` (ERROR).<br>**Downward**: every SAD in `fulfilled_by` must exist and must name this PAD in its `parent_pad`, otherwise `traceability_violation` (ERROR). An empty `fulfilled_by` reports `cross_reference_missing` (ERROR). |

**Engine Execution Mechanics**:

1. **Logical Boundary Isolation**: no linter rule reads PAD content for physical detail such as server names, deployment ports, database index structures or library versions, and the `technologies` whitelist applies only to SADs and TDDs. The ARB checks the Agnosticity Policy (§2.1) in review.
2. **Placeholder SADs**: `fulfilled_by` is required and an empty list is a blocking error, so a `chartered` or `approved` PAD lists at least one SAD. Before a system exists, list a `chartered` SAD placeholder (§2.3.6).
3. **Draft PADs**: a `draft` PAD gets relaxed validation, which skips the schema and the checks above (§2.4).

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

The filename must strictly adhere to the regex: `^[A-Za-z0-9-]+\.pad\.md$`.

Use the lowercase domain name, as in `ui-platform.pad.md`.

#### 2.3.2 Taxonomy

PADs are **single, cohesive artifacts** (`[domain].pad.md`). **The Cohesion Rule:** Splitting a PAD into separate micro-files (e.g., separating it into `security.md` and `operations.md`) is strictly prohibited. All domain aspects must be fully encapsulated within the single canonical artifact's mandated sections to prevent drift.

#### 2.3.3 Directory Structure

They must utilize **Asset Container Folders** (`domains/[domain]/`), which act as an isolation boundary for the `.pad.md` file and its supporting assets (e.g., architecture diagrams, PlantUML files).

**Example Directory Structure:**

```text
architecture/
└── domains/                     # (Asset Container Folders)
    └── ui-platform/
        ├── ui-platform.pad.md
        └── architecture-diagram.png
```

#### 2.3.4 Metadata Schema Properties

Every PAD must begin with a YAML frontmatter block containing these fields:

```yaml
doc_meta:
  id: PAD-001 # Domain capability ID
  title: [Capability Title] # Descriptive title of the Domain Capability
  owner: [Domain Team/Role] # Authoritative team owner (string or list)
  version: 1.0.0 # Semantic versioning format
  status: approved # chartered | draft | approved | deprecated
  classification: public # public | internal | restricted | confidential
  review_cycle_days: 180 # Review cycle period
  created_date: YYYY-MM-DD # Creation date
  last_reviewed: YYYY-MM-DD # Last audit date
  governed_by: [GDC-008] # At least one ADR, EAD or GDC id
  realizes_capability: [EAD-001] # At least one EAD id
  fulfilled_by: [SAD-001] # SAD ids; each SAD names this PAD in parent_pad
```

| Metadata Field        | Type            | Description / Purpose                                                                    |
| --------------------- | --------------- | ---------------------------------------------------------------------------------------- |
| `id`                  | String          | Unique identifier (e.g., `PAD-001`).                                                     |
| `title`               | String          | Descriptive title of the artifact.                                                       |
| `owner`               | String or array | Lead Owner (e.g., Domain Architect).                                                     |
| `version`             | String          | Must comply with Semantic Versioning (e.g., 1.0.0).                                      |
| `status`              | Enum            | The current lifecycle state (must match Allowed Statuses below).                         |
| `classification`      | Enum            | The data sensitivity (must match Allowed Classifications below).                         |
| `review_cycle_days`   | Integer         | The frequency in days for required review.                                               |
| `last_reviewed`       | Date            | The date of the last formal review (YYYY-MM-DD).                                         |
| `created_date`        | Date            | The date the artifact was created (YYYY-MM-DD).                                          |
| `governed_by`         | Array           | At least one ADR, EAD or GDC id (`relationships.yaml`).                                  |
| `realizes_capability` | Array           | At least one EAD id that exists.                                                         |
| `fulfilled_by`        | Array           | SAD ids matching `^SAD-\d{3}(?:-[A-Z0-9-]+)?$`; each SAD names this PAD in `parent_pad`. |

##### Allowed Lifecycle Statuses

| Status       | Meaning / Lifecycle Stage                                                                                                                |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `chartered`  | The logical capability boundary is recognized as a valid candidate, but no shared Product/Platform implementation commitment exists yet. |
| `draft`      | The PAD is under active architecture design or Architecture Authority review; draft-age pressure applies.                                |
| `approved`   | The domain architecture is formalized and acts as the official contract.                                                                 |
| `deprecated` | The domain capability is being phased out or has been replaced.                                                                          |

##### Allowed Classifications

| Classification | Meaning / Data Sensitivity             |
| -------------- | -------------------------------------- |
| `public`       | Available to anyone.                   |
| `internal`     | Restricted to company employees.       |
| `restricted`   | Restricted to specific teams or roles. |
| `confidential` | Need-to-know access only.              |

##### Semantic Versioning Classification

| Version           | Trigger / Architectural Change                                                                                                                     |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Major (2.0.0)** | Redesigning the boundary, shifting significant logical responsibilities to another domain, or breaking integration contracts (e.g., API rewrites). |
| **Minor (1.1.0)** | Adding a new subsystem or capability without breaking existing integrations.                                                                       |
| **Patch (1.0.1)** | Editorial updates, formatting, fixing dead links.                                                                                                  |

#### 2.3.5 Artifact Section

The linter enforces the presence of these sections. Their semantic purposes are:

| Section Name                               | Objective                                                                     | Requirement                                                                                                                                                            |
| ------------------------------------------ | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose & Scope**                        | Define the boundaries, goals, and non-goals of this capability.               | Must explicitly outline what is **Out of Scope** to prevent feature creep.                                                                                             |
| **Enterprise Traceability**                | Map the logical capability to the Enterprise Architecture Document (EAD).     | Must contain **Realizes**, **Relationships** and **Consumed By**.                                                                                                      |
| **Domain & Context Model**                 | Establish the bounded contexts, conceptual models, and business logic.        | Must define the **Bounded Context** and **Ubiquitous Language**. _Domain Policies_ (e.g. Retry Policy, MFA Policy) are highly recommended here.                        |
| **Integration Contracts**                  | Specify strict logical API boundaries and event publishing.                   | Must contain **Integration Provided** and **Integration Consumed**.                                                                                                    |
| **Trust & Data Boundaries**                | Map the isolation levels, identity propagation, and tenant separation models. | Must contain **Trust Boundary**, **Identity Access** and **Data Classification**.                                                                                      |
| **Capability NFR**                         | Explicit, quantifiable Non-Functional Requirements (NFR) targets.             | Must quantify metrics focusing on business SLAs, RTO, RPO, and Auditability (Operational Excellence belongs in SAD). The linter does not check this section's content. |
| **Ownership & Governance**                 | Map the logical capability to the physical systems (SADs) that fulfill it.    | Must explicitly document **Team Ownership** and list the **Realizing Systems**.                                                                                        |
| **Assumptions & Constraints _(Optional)_** | Document any external dependencies or business assumptions.                   | Must list business, external, or operational constraints the design relies upon.                                                                                       |
| **Architectural Decisions _(Optional)_**   | Document architectural decisions made within the domain.                      | Can summarize local decisions or link out to full ADRs for complex cross-domain decisions.                                                                             |
| **Evolution _(Optional)_**                 | Describe the future architectural trajectory (not a timeline roadmap).        | Explains how the architecture intends to evolve long-term (e.g., migrating from REST to Event-Driven).                                                                 |
| **References _(Optional)_**                | Additional context or external documents.                                     | List any relevant documentation, standard guidelines, or upstream mandates.                                                                                            |

The linter matches each required subsection term case-insensitively at the start of a line: plain text, a bold term, a bold list item, or a `###` to `#####` heading. Use the exact words: a heading `Identity & Access` does not match the term `Identity Access`.

#### 2.3.6 Platform Commitment & Approval Gate

PAD lifecycle status expresses **enterprise commitment**, not document completeness.

- `chartered` means the logical boundary is recognized and may be matured in detail, but it is not yet an active shared Product/Platform implementation commitment
- `draft` means the PAD is under active design/review; the global draft-age rule applies
- `approved` means the PAD is the authoritative logical contract and downstream physical design may proceed
- `deprecated` means the logical capability is being retired or replaced

A PAD may be promoted to `approved` only when at least one of these drivers exists:

1. **Constitutional / authority need** — central authority is required to preserve enterprise trust, control, evidence, or singular ownership
2. **Mandatory dependency** — an already approved Product/Platform requires the capability and local duplication would violate an authority boundary or create unacceptable systemic risk
3. **Demonstrated consumer/runtime evidence** — repeated concrete consumers, operational friction, lifecycle independence, or runtime economics show that shared ownership reduces total-system complexity

Approval also requires:

- explicit accountable ownership
- concrete consumers or governed authority obligations
- stable authority and data boundaries
- provided/consumed logical contracts
- capability NFR and degradation posture
- an adoption, support, and operational intent appropriate to the capability

Architecture completeness, taxonomy symmetry, hypothetical reuse, or a mature-looking document **do not by themselves justify `approved` status**.

A `chartered` PAD may have a `chartered` SAD placeholder for traceability. A SAD may enter `draft` or `approved` only after its parent PAD is `approved`; this is enforced by the SAD validator.

### 2.4 Lifecycle & Audit

As the Single Source of Truth (SSOT) for Product Architecture Documents (PAD), the PAD represents highly stable domain capabilities. They must undergo a periodic review every `review_cycle_days` (default 180 days) to ensure structural integrity and relevance against the enterprise capability map.

_Current automation_: a `last_reviewed` date older than `review_cycle_days` reports `review_age_violation` (WARNING, not blocking). `governance/framework/contracts/lifecycle.yaml` gives `chartered`, `approved` and `deprecated` PADs full validation. A `draft` PAD gets relaxed validation and fails with `lifecycle_age_violation` (ERROR) 30 days after `created_date`.

---

## 3. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the Architecture Authority explicitly documents the compromises of this PAD Guideline:

1. **C1/C2 Separation (PAD vs. SAD) vs. Unified Architecture Artifacts**
   - _Why rejected_: A unified artifact containing both logical capabilities and physical servers rapidly decays. When physical servers scale or database engines change, the logical boundary artifact requires constant, unnecessary updates.
   - _The Trade-Off_: We accept the cognitive overhead of maintaining two separate but linked artifacts (PAD for logical, SAD for physical). In exchange, we gain highly stable logical contracts (PADs) that do not break when physical infrastructure topologies mutate.
