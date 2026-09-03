---
doc_meta:
  id: GDC-010
  title: Architecture Decision Record (ADR) Guideline
  owner: Architecture Authority
  version: 0.1.0
  status: draft
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
---

# Architecture Decision Record (ADR) Guideline

## 1. Context & Scope

Architecture is rarely a straight line. As our systems evolve, we frequently encounter crossroads where we must introduce a new paradigm, deviate from the 'paved road' (established Engineering Standards / STD), or accept a critical trade-off to meet business demands.

An Architecture Decision Record (ADR) is how we capture the _why_ behind these pivotal moments. It ensures that every major architectural shift or deliberate tech-debt remains transparent, auditable, and easily understood by the engineers of tomorrow. This guideline applies to the Architecture Review Board (ARB), Domain Teams, System Teams, and all Software Engineers (SWEs) documenting decisions across both global and local repository contexts.

---

## 2. Policy Framework

### 2.1 ADR Taxonomy & Types

Every ADR must declare its `adr_type` to clarify the intent of the decision. The allowed types are:

| ADR Type                | Purpose                                                                               |
| ----------------------- | ------------------------------------------------------------------------------------- |
| **Foundational**        | Makes a core architectural decision for the first time when no prior decision exists. |
| **Implementation**      | Selects an implementation or option that is mandated/permitted by an STD.             |
| **Exception**           | Approves a deviation (waiver) against an active STD.                                  |
| **Conflict Resolution** | Resolves conflicting constraints between an STD, ADR, or business requirement.        |
| **Replacement**         | Replaces a pre-existing architectural decision.                                       |

### 2.2 The Schema Architecture

In addition to the global structural enforcement defined in **[GDC-001](GDC-001-fitness-functions.md)**, the ADR specification is strictly governed by the following domain-specific linter schemas:

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/adr.schema.json`). If you need to update a rule, modify the schema file and run: `python generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category      | Parameter                      | Enforcement / Value                                                                                                                                                             |
| :----------------- | :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Metadata Rules** | Metadata Rules                 | <ul><li>doc_meta</li></ul>                                                                                                                                                      |
| **Metadata Rules** | exception_info Required Fields | <ul><li>approved_by</li><li>expiry_date</li><li>risk_classification</li><li>exception_reason</li></ul>                                                                          |
| **Section Rules**  | Required Sections              | <ul><li>Title</li><li>Status</li><li>Context</li><li>Decision Drivers</li><li>Decision</li><li>Consequences</li><li>Compliance Impact</li><li>Alternatives Considered</li></ul> |
| **Section Rules**  | Recommended Sections           | <ul></ul>                                                                                                                                                                       |

<!-- AUTO-GENERATED-SCHEMA:END -->

| Linter Component  | File                                         | Enforcement Logic                                                                                                                                                                                                                                                                                              |
| :---------------- | :------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **JSON Schema**   | `schemas/adr.schema.json`                    | Enforces the `decision_record` properties and specific `allowed_statuses` for the ADR lifecycle.                                                                                                                                                                                                               |
| **Python Engine** | `engine/validators/domains/adr_validator.py` | **Taxonomy**: Validates `allowed_statuses` and `allowed_classifications`.<br>**Domain Validation**: Verifies immutability limits for `accepted` ADRs to prevent silent historical alterations.<br>**Temporal Enforcement**: Executes time-based checks against `expiry_date` to trigger expired waiver errors. |

**Engine Execution Mechanics**:

1. **Conditional Schema Validation**: The CI linter dynamically shifts its validation rules based on the `adr_type`. If `exception` is selected, the pipeline automatically enforces the presence and validity of the `exception_info` block.
2. **Automated Waiver Expiration (Hard Block)**: The CI pipeline performs temporal validation on Exception ADRs. If an active (`accepted`) waiver ADR reaches its `expiry_date`, the linter triggers a **Hard CI Block (Exit 1)** with an `exception_expired` error. To clear this block, the team must either resolve the technical debt or secure a waiver renewal. In either case, the expired ADR's `status` MUST be transitioned from `accepted` to either `deprecated` (if the debt is resolved and the waiver is no longer needed) or `superseded` (if a new Exception ADR is approved to extend the timeline). It cannot revert to `proposed` or be arbitrarily deleted.

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

ADR filenames must adhere to the pattern `^ADR-[A-Z]{2,4}(?:-[A-Z]{2,4})?-\d{3}-[a-z0-9-]+\.md$`. Example: `ADR-EXAMPLE-001-api-design.md` or `ADR-EXAMPLE-002-color-palette.md`.

#### 2.3.2 Taxonomy

ADRs are organized by their scope (Global vs Domain/System context).

- **Global ADRs**: Decisions that affect the entire organization or cross-cutting boundaries.
- **Domain/System ADRs**: Decisions contained within a specific bounded context (Domain) or a single application (System). Note: Physically, all ADRs are strictly centralized in the root architecture repository; there are no "local" project-level ADR folders.

#### 2.3.3 Directory Structure

**Architecture Repository (Architecture Repo)**

```text
architecture/
└── decisions/
    ├── _global/
    │   └── ADR-EXAMPLE-001-api-design.md
    └── ui-platform/
        └── ADR-UIP-001-react-framework.md
```

#### 2.3.4 Metadata Schema Properties

| Metadata Field | Type         | Description / Purpose                                                                                         |
| -------------- | ------------ | ------------------------------------------------------------------------------------------------------------- |
| `id`           | String       | Unique identifier (e.g., `ADR-IAM-000`).                                                                      |
| `title`        | String       | Descriptive title of the document.                                                                            |
| `adr_type`     | Enum         | The intent of the decision (must match Allowed Types in §2.1).                                                |
| `status`       | Enum         | The current lifecycle state (must match Allowed Statuses below).                                              |
| `created`      | Date         | The creation date (YYYY-MM-DD).                                                                               |
| `created_by`   | String       | The author of the ADR.                                                                                        |
| `governed_by`  | List[String] | **Required**: Must point to EAD, PAD, SAD, or GDC-000 (if purely technical/global). Links the ADR to the DAG. |

**Exception Info Required Fields (Conditional)** _Required only if `adr_type` is `exception`._

| Metadata Field        | Type   | Description / Purpose                                   |
| --------------------- | ------ | ------------------------------------------------------- |
| `approved_by`         | String | The Sponsor, Approver Name, or ARB granting the waiver. |
| `expiry_date`         | Date   | Waiver validity cap (max 365 days).                     |
| `risk_classification` | Enum   | The evaluated risk (`low`, `medium`, `high`).           |
| `exception_reason`    | String | Brief rationale explaining the standard deviation.      |

##### Allowed Lifecycle Statuses

| Status       | Meaning / Lifecycle Stage            |
| ------------ | ------------------------------------ |
| `proposed`   | Under review or initial draft state. |
| `accepted`   | Formalized and active.               |
| `rejected`   | The proposed decision was rejected.  |
| `superseded` | Replaced by a newer ADR.             |
| `deprecated` | Phased out and no longer applicable. |

##### Allowed Classifications

_N/A for Architecture Decision Records (ADRs). ADRs are inherently technical decisions and inherit the classification of their parent repositories or systems._

##### Semantic Versioning Classification

_N/A for Architecture Decision Records (ADRs). ADRs are immutable historical records. If an ADR changes, it must be superseded by a new ADR rather than versioned._

#### 2.3.5 Artifact Section

The linter enforces the presence of these sections. Their semantic purposes are:

| Section Name                | Objective                                                                                                                                         | Requirement                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Title**                   | The ADR ID and a descriptive title header.                                                                                                        | Must follow the naming convention and clearly state the architecture decision.    |
| **Status**                  | Chronological table tracking state transitions (`Date`, `Status`), the `ADR Type`, the `Reviewers` (or SMEs) consulted, and the final `Approver`. | Must track the chronological state transitions, reviewers, and approvers.         |
| **Context**                 | The technical problem, constraints, and business requirements driving the decision.                                                               | Must objectively describe the problem space and constraints driving the decision. |
| **Decision Drivers**        | The core technical and business factors forcing the decision.                                                                                     | Must list the critical technical and business factors forcing the choice.         |
| **Decision**                | The chosen course of action with concrete, binding statements.                                                                                    | Must explicitly define the chosen course of action in binding terms.              |
| **Consequences**            | The results (Positive, Negative, Operational) of the decision.                                                                                    | Must analyze the positive, negative, and operational impacts of the decision.     |
| **Compliance Impact**       | Defines related standards, compliance status, and required waivers.                                                                               | Must list any standards violated and link to the required waivers.                |
| **Alternatives Considered** | Analysis of alternate paths rejected during review.                                                                                               | Must provide a comparative analysis of rejected options.                          |

### 2.4 Lifecycle & Audit

#### 2.4.1 Document Lifecycle & Statuses

Every architectural decision must progress through a managed, auditable lifecycle. An ADR must exist in one of five explicit states:

```
    [Proposed] ──► [Accepted] ──► [Superseded]
         │              │
         ▼              ▼
    [Rejected]     [Deprecated]
```

- **Proposed**: The decision is drafted and undergoing active peer review. It carries no authority.
- **Accepted**: The decision has been reviewed, approved by the designated authority, and is active.
- **Rejected**: The decision has been evaluated and declined. The record remains as historical context.
- **Superseded**: The decision has been replaced by a newer ADR. The newer ADR must explicitly reference the superseded record by ID.
- **Deprecated**: The decision is no longer recommended or valid, but has not been directly replaced.

#### 2.4.2 The Immutability Principle

An ADR is a strict historical record. Once an ADR reaches the **Accepted** or **Rejected** state, its core substantive content (Context, Decision Drivers, Decision, Consequences) **MUST NEVER BE MODIFIED**.

- If a decision needs to be reversed or fundamentally changed, you must create a **new ADR** (using the `replacement` type) and update the old ADR's status to `Superseded`.
- **Administrative Exemption (Decoupled Execution)**: Strategic decisions (ADRs) are decoupled from tactical execution (STDs). An ADR may be approved before its corresponding Standard document is finalized. Appending hyperlinks to newly drafted Standards (STDs) or cross-referencing newer ADRs in the "Related Standards" section is classified as a metadata update and is explicitly permitted.
- Other permissible edits to an existing Accepted ADR include: updating the Status table to reflect a lifecycle transition, or fixing minor typographical errors that do not alter the technical context.

> [!IMPORTANT]
>
> **Semantic Versioning DOES NOT apply to ADRs.**
>
> Unlike living documents (EAD, PAD, SAD, TDD), ADRs do not use `Major.Minor.Patch` versioning. ADRs are immutable, point-in-time decision records. Once an ADR is accepted, its architectural content must never be modified. If the architectural decision changes in the future, a **NEW** ADR must be authored which explicitly supersedes the old one.

#### 2.4.3 Resolving Expired Waivers (Exception ADRs)

When an Exception ADR reaches its `expiry_date`, the CI pipeline will block the repository. To clear the block, the team must execute one of the following three scenarios:

1. **Scenario A: Resolving Temporary Tech Debt**
   - _Context_: The deviation was a temporary hack (e.g., using an unapproved library to hit a deadline).
   - _Action_: The team refactors the codebase to comply with the global STD.
   - _ADR Update_: The expired Exception ADR's status is changed to `deprecated`.

2. **Scenario B: Paved Road Evolution (Permanent Necessity)**
   - _Context_: The deviation proved to be a permanent necessity and a better architectural choice for the enterprise.
   - _Action_: The organization must update the Global STD to officially permit the new technology or pattern.
   - _ADR Update_: The old Exception ADR is changed to `deprecated` (the waiver is no longer needed), and a new `Implementation` ADR is created under the newly revised STD.

3. **Scenario C: Niche Permanence (Waiver Renewal)**
   - _Context_: The deviation is permanent for this specific team, but the ARB refuses to make it a global standard to prevent widespread adoption.
   - _Action_: The team must submit a new Exception ADR to the ARB, requesting an extension of the waiver for another cycle (paying the "bureaucracy tax").
   - _ADR Update_: The old Exception ADR's status is changed to `superseded`, replaced by the newly approved Exception ADR.

---

## 3. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the ARB explicitly documents the compromises of this ADR Guideline:

1. **Centralized Markdown ADRs vs. Local Codebase Co-location**
   - _Why rejected_: Distributing ADRs into local project repositories (`docs/adr/`) makes it impossible for the Architecture Review Board (ARB) to have a real-time, global view of all architectural decisions across the enterprise. It also enables teams to secretly bypass governance.
   - _The Trade-Off_: We lose the "Git Time-Travel" benefit (where checking out an old branch in a product repo inherently brings the old ADR). In exchange, we gain Absolute Visibility and strict ARB control by forcing all ADRs into the centralized Root Architecture Repository.
