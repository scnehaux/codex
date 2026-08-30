---
doc_meta:
  id: GDC-008
  title: Product Architecture Document (PAD) Guideline
  owner: Architecture Authority
  version: 0.0.1
  status: draft
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
---

# Product Architecture Document (PAD) Guideline

## 1. Context & Scope

PADs represent the C1 System Context / Domain Architecture layer of the C4 metamodel, defining the logical domain capabilities, bounded contexts, trust boundaries, and strategic positioning of a business domain (e.g., `identity`, `ui-platform`, `hris`, `finance`).

PADs establish the "What". They serve as the design-time single source of truth (SSOT) for domain-level contracts. A single logical domain capability (PAD) governs one or more physical software containers (SADs) in a strict 1-to-N mapping. They establish conceptual integration rules (such as trust boundaries and SLA targets) _before_ physical systems are built. While concrete API specifications are delegated downstream via Web Developer Portals, the PAD remains the stable, logical anchor.

### 1.1 Philosophy & Decision Horizon

**Decision question:** _"What capability does this product or platform own, where are its boundaries, and what does it promise — independent of how any system builds it?"_ A PAD is the domain charter tier: the logical plan, not the solution.

**Every product AND platform has exactly one PAD.** A platform is simply a product whose consumers are internal; it is not a separate document type.

**Position on the three governing dimensions:**

- **Stability / half-life — 10+ years (one-way door).** The longest-lived C2 artifact. To stay durable it must remain thin — capability, boundaries, contracts, NFR promises — and exclude implementation detail.
- **Abstraction — C1 logical.** Bounded contexts and contracts only; never physical containers, deployment, or technology choices (those are the SAD).
- **Ownership — one stream-aligned domain team.**

**Litmus test (PAD vs SAD):** _"Does this fact survive a complete technology rewrite?"_ If yes → PAD. If it would change when you swap technology or topology → SAD.

**Stability guardrail:** a PAD boundary is drawn by **bounded-context (capability) cohesion**, not by commercial or marketing packaging. Re-bundling products does not merge PADs — PADs follow domains, which keeps the 10-year horizon credible.

**Traceability:** a PAD fulfills one or more EAD capabilities (upward). Physical realization is mapped bottom-up, where SADs declare their parent PAD, preventing the PAD from needing constant updates.

---

## 2. Policy Framework

### 2.1 Agnosticity & Stability

- **Agnosticity Policy**: PADs must remain technology-agnostic at the physical infrastructure level. They establish logical capabilities, trust boundaries, and conceptual integration policies (e.g., SLA targets). Concrete API specifications must be delegated to downstream Web Developer Portals, and physical container details belong in SADs.
- **Stability**: Because they govern logical rather than physical boundaries, PADs are designed to be highly stable. Future physical decompositions (e.g., splitting a monolithic HRIS backend into separate Payroll and Employee microservices) must require zero modification to the core domain contracts established within the PAD.

### 2.2 The Schema Architecture

In addition to the global structural enforcement defined in **[GDC-001](GDC-001-fitness-functions.md)**, the PAD specification is strictly governed by the following domain-specific linter schemas:

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/pad.schema.json`). If you need to update a rule, modify the schema file and run: `python 06-fitness-function/generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category | Parameter | Enforcement / Value |
| :--- | :--- | :--- |
| **Metadata Rules** | Metadata Rules | <ul><li>doc_meta</li></ul> |
| **Section Rules** | Required Sections | <ul><li>Purpose & Scope</li><li>Enterprise Traceability</li><li>Domain & Context Model</li><li>Integration Contracts</li><li>Trust & Data Boundaries</li><li>Capability NFR</li><li>Ownership & Governance</li></ul> |
| **Section Rules** | Recommended Sections | <ul><li>Assumptions & Constraints</li><li>Architectural Decisions</li><li>Evolution</li><li>References</li></ul> |
| **Content Quality Rules** | Purpose & Scope (Required Concepts) | <ul><li>Out Of Scope</li></ul> |
| **Content Quality Rules** | Enterprise Traceability (Required Concepts) | <ul><li>Realizes</li><li>Relationships</li><li>Consumed By</li></ul> |
| **Content Quality Rules** | Domain & Context Model (Required Concepts) | <ul><li>Bounded Context</li><li>Ubiquitous Language</li></ul> |
| **Content Quality Rules** | Integration Contracts (Required Concepts) | <ul><li>Integration Provided</li><li>Integration Consumed</li></ul> |
| **Content Quality Rules** | Trust & Data Boundaries (Required Concepts) | <ul><li>Trust Boundary</li><li>Identity Access</li><li>Data Classification</li></ul> |
| **Content Quality Rules** | Capability NFR (Recommended Derivatives) | <ul><li>SLA</li><li>SLO</li><li>RTO</li><li>RPO</li><li>Availability</li><li>Scalability</li><li>Peak Load</li><li>Concurrency</li><li>Compliance</li><li>Data Privacy</li><li>Data Residency</li><li>Audit</li><li>Usability</li><li>Accessibility</li><li>Interoperability</li><li>Cost Target</li></ul> |
| **Content Quality Rules** | Ownership & Governance (Required Concepts) | <ul><li>Team Ownership</li><li>Realizing Systems</li></ul> |

<!-- AUTO-GENERATED-SCHEMA:END -->

| Linter Component  | File                                         | Enforcement Logic                                                                                                                                                                                                       |
| :---------------- | :------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **JSON Schema**   | `schemas/pad.schema.json`                    | Enforces C1/C2 macro-topology boundaries and integration contracts.                                                                                                                                                     |
| **Python Engine** | `engine/validators/domains/pad_validator.py` | **Taxonomy**: Validates `allowed_statuses` and `allowed_classifications`.<br>**Domain Validation**: Enforces that `fulfilled_by` exists and is a populated list of SAD IDs, guaranteeing C1 to C2 boundary composition. |

**Engine Execution Mechanics**:

1. **Logical Boundary Isolation**: The linter will flag any PAD that hardcodes physical server names, specific deployment ports, database index structures, or specific library versions.

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

The filename must strictly adhere to the regex: `^[a-z0-9-]+\.pad\.md$`.

#### 2.3.2 Taxonomy

PADs are **single, cohesive artifacts** (`[domain].pad.md`). **The Cohesion Rule:** Splitting a PAD into separate micro-files (e.g., separating it into `security.md` and `operations.md`) is strictly prohibited. All domain aspects must be fully encapsulated within the single canonical artifact's mandated sections to prevent drift.

#### 2.3.3 Directory Structure

They must utilize **Asset Container Folders** (`03-domain/[domain]/`), which act as an isolation boundary for the `.pad.md` file and its supporting assets (e.g., architecture diagrams, PlantUML files).

**Example Directory Structure:**

```text
codex/
└── 03-domain/                     # (Asset Container Folders)
    └── ui-platform/
        ├── ui-platform.pad.md
        └── architecture-diagram.png
```

#### 2.3.4 Metadata Schema Properties

Every PAD must begin with a YAML frontmatter block containing these fields:

```yaml
doc_meta:
  id: PAD-PLT-XXX # Domain capability ID
  title: [Capability Title] # Descriptive title of the Domain Capability
  owner: [Domain Team/Role] # Authoritative team owner
  version: 1.0.0 # Semantic versioning format
  status: approved # chartered | draft | approved | deprecated
  classification: public # public | internal | restricted
  review_cycle_days: 180 # Review cycle period
  last_reviewed: YYYY-MM-DD # Last audit date
```

| Metadata Field      | Type    | Description / Purpose                                            |
| ------------------- | ------- | ---------------------------------------------------------------- |
| `id`                | String  | Unique identifier (e.g., `PAD-EXAMPLE-001`).                         |
| `title`             | String  | Descriptive title of the artifact.                               |
| `owner`             | String  | Lead Owner (e.g., Domain Architect).                             |
| `version`           | String  | Must comply with Semantic Versioning (e.g., 1.0.0).              |
| `status`            | Enum    | The current lifecycle state (must match Allowed Statuses below). |
| `classification`    | Enum    | The data sensitivity (must match Allowed Classifications below). |
| `review_cycle_days` | Integer | The frequency in days for required review.                       |
| `last_reviewed`     | Date    | The date of the last formal review (YYYY-MM-DD).                 |

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

##### Semantic Versioning Classification

| Version           | Trigger / Architectural Change                                                                                                                     |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Major (2.0.0)** | Redesigning the boundary, shifting significant logical responsibilities to another domain, or breaking integration contracts (e.g., API rewrites). |
| **Minor (1.1.0)** | Adding a new subsystem or capability without breaking existing integrations.                                                                       |
| **Patch (1.0.1)** | Editorial updates, formatting, fixing dead links.                                                                                                  |

#### 2.3.5 Artifact Section

The linter enforces the presence of these sections. Their semantic purposes are:

| Section Name                               | Objective                                                                     | Requirement                                                                                                                                     |
| ------------------------------------------ | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose & Scope**                        | Define the boundaries, goals, and non-goals of this capability.               | Must explicitly outline what is **Out of Scope** to prevent feature creep.                                                                      |
| **Enterprise Traceability**                | Map the logical capability to the Enterprise Architecture Document (EAD).     | Must declare what it **Realizes**, what it **Depends On**, and what is **Referenced By** it.                                                    |
| **Domain & Context Model**                 | Establish the bounded contexts, conceptual models, and business logic.        | Must define the **Bounded Context** and **Ubiquitous Language**. _Domain Policies_ (e.g. Retry Policy, MFA Policy) are highly recommended here. |
| **Integration Contracts**                  | Specify strict logical API boundaries and event publishing.                   | Must define the capabilities that are **Provided** and **Consumed**.                                                                            |
| **Trust & Data Boundaries**                | Map the isolation levels, identity propagation, and tenant separation models. | Must detail the **Trust Boundary**, **Identity & Access** logic, and **Data Classification**.                                                   |
| **Capability NFR**                         | Explicit, quantifiable Non-Functional Requirements (NFR) targets.             | Must quantify metrics focusing on business SLAs, RTO, RPO, and Auditability (Operational Excellence belongs in SAD).                            |
| **Ownership & Governance**                 | Map the logical capability to the physical systems (SADs) that fulfill it.    | Must explicitly document **Team Ownership** and list the **Realizing Systems**.                                                                 |
| **Assumptions & Constraints _(Optional)_** | Document any external dependencies or business assumptions.                   | Must list business, external, or operational constraints the design relies upon.                                                                |
| **Architectural Decisions _(Optional)_**   | Document architectural decisions made within the domain.                      | Can summarize local decisions or link out to full ADRs for complex cross-domain decisions.                                                      |
| **Evolution _(Optional)_**                 | Describe the future architectural trajectory (not a timeline roadmap).        | Explains how the architecture intends to evolve long-term (e.g., migrating from REST to Event-Driven).                                          |
| **References _(Optional)_**                | Additional context or external documents.                                     | List any relevant documentation, standard guidelines, or upstream mandates.                                                                     |

#### 2.3.6 Platform Commitment & Approval Gate

PAD lifecycle status expresses **enterprise commitment**, not document completeness.

- `chartered` means the logical boundary is recognized and may be matured in detail, but it is not yet an active shared Product/Platform implementation commitment
- `draft` means the PAD is under active design/review; the global draft-age rule applies
- `approved` means the PAD is the authoritative logical contract and downstream physical design may proceed
- `deprecated` means the logical capability is being retired or replaced

A PAD may be promoted to `approved` only when at least one of these drivers exists:

1. **Constitutional / authority need** â€” central authority is required to preserve enterprise trust, control, evidence, or singular ownership
2. **Mandatory dependency** â€” an already approved Product/Platform requires the capability and local duplication would violate an authority boundary or create unacceptable systemic risk
3. **Demonstrated consumer/runtime evidence** â€” repeated concrete consumers, operational friction, lifecycle independence, or runtime economics show that shared ownership reduces total-system complexity

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

---

## 3. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the Architecture Authority explicitly documents the compromises of this PAD Guideline:

1. **C1/C2 Separation (PAD vs. SAD) vs. Unified Architecture Artifacts**
   - _Why rejected_: A unified artifact containing both logical capabilities and physical servers rapidly decays. When physical servers scale or database engines change, the logical boundary artifact requires constant, unnecessary updates.
   - _The Trade-Off_: We accept the cognitive overhead of maintaining two separate but linked artifacts (PAD for logical, SAD for physical). In exchange, we gain highly stable logical contracts (PADs) that do not break when physical infrastructure topologies mutate.
