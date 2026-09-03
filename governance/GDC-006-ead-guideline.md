---
doc_meta:
  id: GDC-006
  title: Enterprise Architecture Document (EAD) Guideline
  owner: Architecture Authority
  version: 0.1.0
  status: draft
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
---

# Enterprise Architecture Document (EAD) Guideline

## 1. Context & Scope

EADs represent the C1 global context layer of the C4 metamodel, defining the global "City Map" and enterprise-wide directives.

EADs establish the "Why". They dictate the Business Drivers, Enterprise Principles, and the "North Star" cross-domain standardization principles that govern all downstream architecture artifacts, including Enterprise Standards (STD), Product Architecture Documents (PAD), System Architecture Documents (SAD), Architecture Decision Records (ADR), and Technical Design Documents (TDD).

### 1.1 Philosophy & Decision Horizon

**Decision question:** _"What must the enterprise become, and under what principles?"_ An EAD is the enterprise north-star (the central-planning tier): it sets direction, never a system design.

**Position on the three governing dimensions:**

- **Stability / half-life — Permanent (strategic horizon).** EADs change only when enterprise strategy itself shifts; they are the slowest-moving artifacts in the ecosystem. Volatile detail must not live here.
- **Abstraction — C1, enterprise-wide and implementation-agnostic.** Decomposed per the 6 modern Enterprise Domains (Capability, Landscape, Data, Integration, Platform, Security), one file each.
- **Ownership — Architecture Authority (enterprise).**

**Litmus test (EAD vs PAD/SAD):** _"Is this statement enterprise-wide AND independent of any specific system?"_ If it names a concrete system, API, or topology, it has leaked down into a PAD or SAD. `Data Flow Landscape` and `Application Interaction` stay at the macro (cross-domain) level.

**Boundary discipline:** an EAD states **principles and direction**; the enforceable **rules** that implement them live in the STD layer. The `Technology Standards` section therefore references the STD catalog instead of duplicating it (single source of truth), and `Organization Model` expresses durable team-topology principles rather than a volatile org chart.

**Traceability:** the `Business Capability Map` (EAD-EXAMPLE-001) is the root that every PAD capability traces upward to.

---

## 2. Policy Framework

### 2.1 Agnosticity Policies

EADs must remain conceptually agnostic (e.g., Capability, Data, Integration domains) and at a high level of abstraction. Strict SLA (Service Level Agreement) metrics (e.g., `P95 <= 200ms` or `>= 95%` availability) are mandated, but implementation-specific details are prohibited. The sole exception is the Platform & Cloud Strategy domain (`EAD-EXAMPLE-005`), which must explicitly define the enterprise technology portfolio and execution runtimes.

### 2.2 The Schema Architecture

In addition to the global structural enforcement defined in **[GDC-001](GDC-001-fitness-functions.md)**, the EAD specification is strictly governed by the following domain-specific linter schemas.

> [!WARNING]
>
> **DO NOT EDIT THIS TABLE MANUALLY.** This table is automatically generated from the JSON Schema (`schemas/ead.schema.json`). If you need to update a rule, modify the schema file and run: `python generators/generate_rules_doc.py`

<!-- AUTO-GENERATED-SCHEMA:START -->

| Rule Category      | Parameter            | Enforcement / Value                                                                                                                                                                                                                                                                                                  |
| :----------------- | :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Metadata Rules** | Metadata Rules       | <ul><li>doc_meta</li></ul>                                                                                                                                                                                                                                                                                           |
| **Section Rules**  | Required Sections    | <ul><li>Purpose</li><li>Scope</li><li>Enterprise Context</li><li>Architectural Drivers & Lessons</li><li>Architecture Model</li><li>Principles & Rules</li><li>Alternatives Considered</li><li>Single Points of Failure & Graceful Degradation</li><li>Ownership</li><li>Dependencies</li><li>Traceability</li></ul> |
| **Section Rules**  | Recommended Sections | <ul><li>Assumptions</li><li>Constraints</li><li>Risks</li><li>Future Direction</li><li>References</li></ul>                                                                                                                                                                                                          |

<!-- AUTO-GENERATED-SCHEMA:END -->

### 2.3 Semantic Definitions

#### 2.3.1 Naming Conventions

The filename must strictly adhere to the regex: `^EAD-\d{3}-[a-z0-9-]+\.md$`.

#### 2.3.2 Taxonomy

EADs do not follow a rigidly fixed taxonomy (like TOGAF). Instead, the taxonomy is determined by the Enterprise Architecture team based on current strategic needs, provided it strictly adheres to a **MECE (Mutually Exclusive, Collectively Exhaustive)** structure.

**Default Enterprise Taxonomy** The following taxonomy represents the default architectural decomposition adopted by Scnehaux Enterprise Architecture. The Enterprise Architecture Board may introduce, merge, split, or retire EAD artifacts when the enterprise architecture evolves, provided the resulting taxonomy remains MECE and preserves architectural lineage.

1. **Enterprise Capability & Domain Map (`EAD-EXAMPLE-001`)**: Establishes the macro business capabilities and maps them to strict Domain Ownership (Conway's Law).
2. **Enterprise System Landscape (`EAD-EXAMPLE-002`)**: The macro "City Map" of all physical products, systems, and their structural taxonomy.
3. **Enterprise Data Ownership & Topology (`EAD-EXAMPLE-003`)**: Governs data sovereignty, master data ownership, data residency, and analytical/transactional boundaries.
4. **Enterprise Integration Architecture (`EAD-EXAMPLE-004`)**: Defines macro integration patterns (Event-Driven vs REST), API strategies, and high-level context maps.
5. **Enterprise Platform Architecture (`EAD-EXAMPLE-005`)**: Defines the paved road for infrastructure, execution runtimes, and Operational Excellence.
6. **Enterprise Security Architecture (`EAD-EXAMPLE-006`)**: Defines global trust boundaries, zero-trust network policies, and IAM macro-strategies.

EAD artifacts must remain flat within the `enterprise/` directory.

#### 2.3.3 Directory Structure

**Example Directory Structure:**

```text
architecture/
└── enterprise/                                  # (Flat / MECE View)
    ├── EAD-EXAMPLE-0enterprise-capability-and-domain-map.md
    ├── EAD-EXAMPLE-002-system-landscape.md
    ├── EAD-EXAMPLE-003-enterprise-data-ownership-and-topology.md
    ├── EAD-EXAMPLE-004-enterprise-integration-architecture.md
    ├── EAD-EXAMPLE-005-enterprise-platform-architecture.md
    └── EAD-EXAMPLE-006-security-architecture.md
```

#### 2.3.4 Metadata Schema Properties

Every EAD artifact must include a YAML frontmatter block containing metadata such as `id`, `title`, `owner`, `version`, `status`, and `classification`.

##### Allowed Lifecycle Statuses

| Status       | Meaning / Lifecycle Stage            |
| ------------ | ------------------------------------ |
| `proposed`   | Under review or initial draft state. |
| `approved`   | Formalized and active.               |
| `deprecated` | Phased out and no longer applicable. |

##### Allowed Classifications

| Classification | Meaning / Data Sensitivity             |
| -------------- | -------------------------------------- |
| `public`       | Available to anyone.                   |
| `internal`     | Restricted to company employees.       |
| `restricted`   | Restricted to specific teams or roles. |

##### Semantic Versioning Classification

| Version           | Trigger / Architectural Change                                                        |
| ----------------- | ------------------------------------------------------------------------------------- |
| **Major (2.0.0)** | Splitting, merging, or fundamentally redefining core strategic business domains.      |
| **Minor (1.1.0)** | Adding a new enterprise capability or business domain without breaking existing ones. |
| **Patch (1.0.1)** | Editorial updates, typo fixes, formatting, fixing dead links.                         |

#### 2.3.5 Artifact Section

The linter enforces the presence of these sections. Their semantic purposes are:

| Section Name                                        | Objective                                                                         | Requirement                                                                                                     |
| --------------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Purpose**                                         | State the exact reason for the document's existence.                              | Required. Must explicitly outline what this specific EAD aims to govern.                                        |
| **Scope**                                           | Define the jurisdictional boundary.                                               | Required. Must define exactly who in the enterprise is bound by these rules.                                    |
| **Enterprise Context**                              | Explain how this fits into the broader company strategy.                          | Required. Must link to the overarching business goals or regulatory requirements.                               |
| **Architectural Drivers & Lessons**                 | Document business goals, value stream mapping, and COE-driven design responses.   | Required. Must explicitly list the business goals driving the architecture and any lessons from past incidents. |
| **Architecture Model**                              | Provide the visual mapping of the architecture.                                   | Required. Must include a Mermaid diagram (e.g. Capability Map, Context Map, Landscape).                         |
| **Principles & Rules**                              | Establish the non-negotiable, immutable rules with paired fitness functions.      | Required. Each principle must be paired with a machine-verifiable or audit-verifiable fitness function.         |
| **Alternatives Considered**                         | Document rejected architectural alternatives and consciously accepted trade-offs. | Required. Must list rejected alternatives with rationale and debt accepted.                                     |
| **Single Points of Failure & Graceful Degradation** | Map enterprise SPOFs and define degradation posture.                              | Required. Must identify universal dependencies and their blast radius with mitigation strategies.               |
| **Ownership**                                       | Explicitly define the Team Topology.                                              | Required. Must state exactly which organizational unit or collective owns the capability.                       |
| **Dependencies**                                    | List upstream/downstream integrations or constraints.                             | Required. Must map out external or internal dependencies required for this architecture.                        |
| **Traceability**                                    | Provide logical linkage to other artifacts.                                       | Required. Must reference associated EADs, ADRs, or downstream standards.                                        |
| **Assumptions** _(Optional)_                        | Document external dependencies or business assumptions.                           | Recommended. Must list business, external, or operational assumptions the design relies upon.                   |
| **Constraints** _(Optional)_                        | List hard structural constraints.                                                 | Recommended. Must list non-negotiable structural constraints.                                                   |
| **Risks** _(Optional)_                              | Risk matrix with likelihood, impact, and mitigation.                              | Recommended. Must document risks with likelihood, impact, and mitigation strategy.                              |
| **Future Direction** _(Optional)_                   | Anticipated evolution.                                                            | Recommended. Must describe how the architecture is expected to evolve.                                          |
| **References** _(Optional)_                         | Industry references and standards.                                                | Recommended. Must cite industry standards, books, or frameworks referenced.                                     |

### 2.4 Lifecycle & Audit

All EAD artifacts are subject to a maximum `review_cycle_days` to prevent staleness. Enterprise level directives typically carry a 180-day review cycle. When an EAD expires, the pipeline will flag it for architectural audit.

---

## 3. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs), the Architecture Authority explicitly documents the compromises of this EAD Guideline:

1. **Markdown Artifacts vs. Traditional EA Tools**
   - _Why rejected_: Traditional EA tools (e.g., Sparx Enterprise Architect) create a massive disconnect between Enterprise Architects and software engineers, locking capability models in proprietary formats.
   - _The Trade-Off_: We sacrifice strict formal modeling languages (like ArchiMate) and auto-generated dependency matrices. In exchange, we force Enterprise Architecture to live in the same Git repositories as the code, ensuring visibility, democratized access, and CI/CD validation.
