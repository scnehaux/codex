# Scnehaux Codex Execution Plan

## 0. Current Instruction

The previously generated `phase5_semantic_foundation.py` has **NOT been executed**

It is now **SUPERSEDED**

Do not execute it

The next implementation script must be regenerated from this plan after the P0 ledger is accepted

---

## 1. Operating Rules

Every implementation slice follows this sequence:

1. Define exact P0 IDs being closed
2. Inspect current implementation
3. Remove duplicate/dead semantic authority
4. Implement the smallest coherent production change
5. Add tests for reachable behavior
6. Run canonical tests
7. Run canonical governance lint
8. Verify per-file coverage
9. Verify aggregate coverage
10. Inspect dead/unreachable production paths
11. Inspect `git diff`
12. Update this plan and roadmap status
13. Do not commit until the slice acceptance criteria are met

Never:

- lower coverage threshold to get green
- test dead code instead of deleting it
- suppress warnings instead of fixing semantic defects
- add unwired registry/module code
- mark a P0 done because prose exists
- mark repository protection done because configuration was intended
- bulk-copy legacy architecture artifacts

---

# 2. PHASE 5 IMPLEMENTATION PLAN

## Slice 5.1 — Lifecycle and Validation Profile Refactor — DONE

### P0 IDs

- P0-A01
- P0-A02
- P0-A03
- P0-A04
- P0-A08
- P0-A09
- P0-A10

### Work

Create one artifact-aware Lifecycle Registry containing literal state → semantic class mapping

Target semantic classes:

```text
pre-baseline
baseline-bearing
retired
```

Create explicit Validation Profile semantics:

```text
full
relaxed
```

Rules:

- lifecycle class does not directly imply validation profile
- GDC draft = full
- approved = full
- ADR accepted = full
- deprecated = full
- only explicitly declared eligible pre-baseline states may be relaxed
- age/retirement checks execute independently from validation profile

Remove `deprecated` from global exemption behavior

Remove duplicate `_BASELINE_STATUSES` style hardcoding

### Tests

- GDC draft full
- ordinary eligible draft relaxed only when policy permits
- approved full
- ADR accepted full
- deprecated full
- retired age rule still runs
- unknown lifecycle literal fails registry integrity
- no status can silently acquire relaxed semantics

### Acceptance

- P0-A01/A02/A03/A04/A08/A09/A10 → `DONE`
- P0-A05/A06/A07 remain green
- every affected production file >=95%
- lint 0/0

---


### Completion Evidence

Slice 5.1 is proven complete:

- 215/215 tests passed
- per-file governed engine coverage >=95%
- aggregate engine coverage 97.76%
- canonical linter 12/12 PASS
- warnings 0
- failures 0
- no duplicate baseline-status authority remains
- lifecycle state, validation profile, lifecycle age, and admission authority are separate controls
- architecture admission remains closed

## Slice 5.2 — Temporal Integrity — DONE

### P0 IDs

- P0-D01 through P0-D08

### Work

Create one temporal validation authority

Enforce:

- valid ISO calendar dates
- no impossible dates
- no future created/updated/reviewed date
- `created_date <= last_updated`
- `created_date <= last_reviewed`
- bounded `review_cycle_days`
- deterministic evaluation date injection

Make JSON Schema format validation executable or move the responsibility entirely into the canonical temporal validator—do not maintain two inconsistent authorities

Replace ambient `datetime.date.today()` use in governance logic with injected/evaluation clock abstraction

### Tests

- leap-year valid/invalid dates
- invalid month/day
- future created date
- future reviewed date
- negative-age bypass impossible
- invalid review-cycle type
- review-cycle lower/upper bounds
- deterministic evaluation date
- ordering violations

### Acceptance

P0-D01…D08 all `DONE`

---


### Completion Evidence

Slice 5.2 is proven complete:

- 240/240 tests passed
- per-file governed engine coverage >=95%
- aggregate engine coverage 97.83%
- temporal governance module coverage 100%
- canonical linter 12/12 PASS
- warnings 0
- failures 0
- canonical date syntax is executable
- impossible calendar dates are rejected
- future dates and temporal ordering are blocking controls
- deterministic governance evaluation clock is installed
- review-cycle bounds are executable
- architecture admission remains closed

## Slice 5.3 — Public Classification Boundary — DONE

### P0 IDs

- P0-E01 through P0-E05

### Work

Declare canonical repository visibility policy

For public Codex:

```text
allowed governed classification = public
```

Audit every Genesis GDC

Normalize only if the content is genuinely safe/public

If a governance document contains non-public material, do not relabel it—move/rewrite/redact before Genesis

Define future private architecture estate contract for:

- internal
- restricted
- confidential

### Tests

- public repo + public artifact → pass
- public repo + internal → blocking
- public repo + restricted → blocking
- public repo + confidential → blocking
- classification absent where schema requires it → schema failure

### Acceptance

P0-E01…E05 all `DONE`

---


### Completion Evidence

Slice 5.3 is proven complete:

- 260/260 tests passed
- per-file governed engine coverage >=95%
- aggregate engine coverage 97.92%
- classification governance module coverage 100%
- canonical linter 12/12 PASS
- warnings 0
- failures 0
- repository visibility is an executable storage boundary
- public repository rejects non-public classifications
- false-security metadata is blocked
- observed/declared visibility drift is blocking
- architecture admission remains closed

## Slice 5.4 — Relationship Ontology Foundation — DONE

### P0 IDs

- P0-C01
- P0-C02
- P0-C03
- P0-C04
- P0-C05
- P0-C07
- P0-C09

P0-C06 inverse reconciliation may complete in Slice 5.7 when RepositoryModel exists

### Work

Create one Relationship Registry

Each relation declares:

```text
name
source_types
target_types
cardinality
direction
dag_participation
authority_requirement
inverse_relation
```

Initial governed relations include at minimum:

- governed_by
- parent_pad
- parent_sad
- fulfilled_by
- realizes_capability if it is an architecture-ID edge
- any other current metadata cross-reference field

Refactor:

- metadata cross-reference validator
- graph auditor
- orphan logic
- hierarchy/traceability audit

to consume the same registry

No hardcoded secondary relationship tuple remains

### Tests

- wrong source type
- wrong target type
- missing target
- allowed target
- invalid cardinality
- example namespace
- retired/non-authoritative target where forbidden
- DAG participation generated from registry

### Acceptance

P0-C01/C02/C03/C04/C05/C07 → `DONE`

P0-C09 at least `PARTIAL` until generators migrate

---


### Completion Evidence

Slice 5.4 is proven complete:

- 296/296 tests passed
- per-file governed engine coverage >=95%
- aggregate engine coverage 98.08%
- graph auditor coverage 100%
- relationship registry coverage 99%
- canonical linter 12/12 PASS
- warnings 0
- failures 0
- Relationship Registry is the semantic authority for typed edges
- source/target type, cardinality, direction, DAG participation, and authority requirements are explicit
- downward inverse relations do not manufacture false DAG cycles
- legacy relationship hardcodes are removed
- inverse reconciliation remains deferred to Slice 5.7
- generator/auditor ontology reconciliation remains deferred to Slice 5.7
- architecture admission remains closed

- Slice 5.5 Normative Control Registry — DONE/CLOSED

### P0 IDs

- P0-B01 through P0-B07

### Work

Introduce stable Control IDs for root-of-trust normative rules

Initial registry must cover at minimum:

- GDC self-validation
- GDC draft full validation
- architecture admission closure
- lifecycle/baseline integrity
- temporal integrity
- public classification boundary
- relationship semantic integrity
- duplicate ID prevention
- cycle prevention
- technology-policy availability
- per-file coverage floor
- bootstrap/genesis constraints

Each control records:

```yaml
control_id:
source_gdc:
source_clause:
modality:
scope:
severity:
enforcement_mode:
implementation:
test_evidence:
```

Create an auditor that fails when:

- blocking MUST has no implementation
- blocking MUST has no test evidence
- implementation path does not exist
- referenced test evidence does not exist
- duplicate Control ID exists

### Acceptance

P0-B01…B07 all `DONE`

Policy coverage becomes a first-class measurable property

---

- Slice 5.6 Registry Integrity Auditor — CURRENT ACTIVE

### P0 IDs

- P0-F01 through P0-F09

### Work

At control-plane boot:

- enumerate governed artifact types
- parse every schema
- metaschema-validate every schema
- resolve every `$ref`
- verify `config.target_doc`
- verify validator registration
- detect orphan schema
- detect orphan validator
- detect duplicate registration
- validate lifecycle registry
- validate relationship registry
- validate severity/control registry reconciliation
- validate custom schema keyword registration

This must run even when there are zero EAD/STD/PAD/SAD/ADR/TDD instances

### Acceptance

P0-F01…F09 all `DONE`

A broken governance control plane fails before document lint begins

---

## Slice 5.7 — RepositoryModel and Zero-Corpus Execution

### P0 IDs

- P0-G01 through P0-G11
- finish P0-C06
- finish P0-C09

### Work

Create canonical repository loading pipeline:

```text
crawler
→ canonical Markdown/frontmatter parser
→ validated RepositoryModel
→ validators/auditors
→ generators/reports
```

Generators stop reparsing raw Markdown

Zero architecture estate must be valid

Generators must:

- no-op cleanly when relevant artifact set is empty
- never silently drop malformed artifact
- fail non-zero on governed input failure
- write to temporary output
- validate output
- atomically replace canonical derived file

Implement inverse relationship reconciliation on the RepositoryModel

### Acceptance

P0-G01…G11 all `DONE`

P0-C06/C09 → `DONE`

Governance-only repository is a supported first-class operating mode

---

## Slice 5.8 — Governance-Critical Coverage Expansion

### P0 IDs

- P0-H05
- P0-H06
- P0-H07
- P0-H09

### Work

Classify Python files:

```text
governance-critical production
test code
non-governance utility
```

Governance-critical production includes:

- engine
- canonical generators
- CI/governance scripts
- waiver/security/bootstrap enforcement code

Hard gate:

```text
each governance-critical file >=95%
aggregate governance-critical coverage >=95%
```

Add adversarial repository fixtures

### Acceptance

P0-H05/H06/H07/H09 all `DONE`

No reachable governance-critical file is hidden outside the coverage policy

---

# 3. PHASE 6 — GENESIS INTEGRITY

## Slice 6.1 — Static Genesis Auditor

### P0 IDs

- P0-J03
- P0-J08
- P0-J09

Validate before first commit:

- manifest syntax/schema
- repository identity
- canonical branch
- source repository
- source immutable SHA
- migration mode
- governance admission state
- required GDC baseline IDs
- allowed root paths
- forbidden architecture paths
- exact intended support metadata

### Acceptance

All pre-commit Genesis P0 become `DONE`

Then and only then is Genesis commit allowed

## Slice 6.2 — Post-Genesis Root Integrity

### P0 IDs

- P0-J04
- P0-J05
- P0-J06
- P0-J07

After first commit:

- exactly one root commit
- root contents obey manifest
- root contains no architecture estate
- manifest/provenance match expected root
- Genesis exception cannot be reused
- history rewrite policy prepared for GitHub enforcement

### Acceptance

P0-J complete

---

# 4. PHASE 7 — VERSION AND MUTATION

Close P0-K01 through P0-K06

Do not resurrect the commented legacy implementation

Build a new mutation model based on:

- artifact type
- semantic lifecycle
- pre-1.0 policy
- stable compatibility classification
- ADR immutability/supersession

Required before Governance Control Plane can become stable `1.0.0`

---

# 5. PHASE 8 — P1 REPRODUCIBILITY

Execute:

- P1-E dependency/build reproducibility
- P1-F CI/supply-chain immutability
- remaining P1-C metadata strictness
- P1-D waiver consolidation
- P1-G truthful generated telemetry/docs

No mutable downstream governance `main` consumption remains

---

# 6. PHASE 9 — EFFECTIVE GITHUB ENFORCEMENT

Close P0-L01 through P0-L09 and P1-H

Install actual controls, then prove them negatively

Required evidence:

1. direct push rejected
2. force push rejected
3. branch deletion rejected
4. failing governance PR cannot merge
5. missing CODEOWNER approval blocks
6. unresolved conversation blocks
7. stale approval handling works

Configuration screenshot/text is not sufficient evidence

---

# 7. PHASE 10 — GOVERNANCE 1.0 RELEASE

Prerequisites:

- all root-of-trust P0 closed
- required GDCs approved
- required GDCs >=1.0.0
- version mutation enforcement live
- reproducible dependency/toolchain contract
- effective GitHub enforcement evidence
- immutable governance release metadata

Release contains:

- governance version
- engine version
- schema version
- source commit SHA
- compatibility metadata
- provenance
- reproducible dependency resolution

---

# 8. PHASE 11 — ARCHITECTURE RE-ADMISSION

No legacy bulk migration

For every legacy artifact:

1. treat legacy version as provenance only
2. inspect semantic correctness
3. normalize against current Codex governance
4. validate abstraction boundary
5. validate lifecycle
6. validate relationships
7. validate technology policy
8. review architecture quality
9. admit via PR

Admission order:

```text
EAD
→ STD
→ PAD
→ SAD
→ ADR/TDD
```

---

# 9. CURRENT NEXT ACTION

Current next action is **NOT** to run the old Phase 5 script

Current next action after this roadmap/plan is accepted:

```text
Generate new Slice 5.1 implementation
→ run
→ validate
→ update ledger
→ continue Slice 5.2
```

No Genesis commit yet

<!-- PHASE5-STATUS:START -->
## Phase 5 Execution Status

- Slice 5.1 Lifecycle + Validation Profile — DONE/CLOSED
- Slice 5.2 Temporal Integrity — DONE/CLOSED
- Slice 5.3 Public Classification Boundary — DONE/CLOSED
- Slice 5.4 Relationship Ontology Foundation — DONE/CLOSED
- Slice 5.5 Normative Control Registry — DONE/CLOSED
- Slice 5.6 Registry Integrity Auditor — CURRENT ACTIVE
- Slice 5.7 RepositoryModel + Zero-Corpus — PLANNED
- Slice 5.8 Governance-Critical Coverage Expansion — PLANNED
<!-- PHASE5-STATUS:END -->

<!-- SLICE-5.5-CLOSEOUT:START -->
### Slice 5.5 Closeout Evidence

- Status: DONE/CLOSED
- Normative controls inventoried: 166
- Verified controls: 76
- Pending controls: 90
- Unowned governance gaps: 0
- Every pending control has explicit `control_owner` and `target_phase`
- Eight topology controls remain `automated + pending`
- Topology owner: `RepositoryModel / Topology Authority`
- Topology target: Slice 5.7 RepositoryModel + Zero-Corpus
- EAD agnosticity is machine-enforced with EAD-005 as the explicit technology-portfolio/runtime exception
- Registry self-controls `CTRL-GDC-000-038` through `CTRL-GDC-000-041` are automated and verified
- Automated verified controls require implementation mapping and test evidence
- Test proof before closeout: 323/323 passed
- Aggregate statement coverage before closeout: 98.24%
- Per-file production coverage gate: PASS, every governed production Python file >=95%
- `engine/governance/controls.py`: 100%
- Governance lint before closeout: 12/12 PASS, 0 warnings, 0 failures
- No architecture artifact directories admitted
- No commit created

Open follow-through:
- P0-B05 severity-to-effective-enforcement reconciliation → Slice 5.6
- P0-B07 full narrative-to-executable reconciliation remains PARTIAL while scheduled controls are pending
- Topology/directory/container controls → Slice 5.7
<!-- SLICE-5.5-CLOSEOUT:END -->

<!-- SCNEHAUX-AI-NATIVE-FRAMEWORK-REBASELINE -->

# AI-Native Scnehaux Framework Plan

## 1. Product Definition

Scnehaux is a reusable **AI-Native Architecture Knowledge & Control Plane**

Its purpose is not to maximize documentation

Its purpose is to maintain a machine-readable, explainable, governable architecture model that can be consumed by humans, deterministic controls, graph retrieval, and AI systems

Primary outcome:

```text
Intent
+ Current Architecture
+ Organizational Context
+ Governance
+ Observed Reality
        ↓
Architecture Proposal
        ↓
Deterministic Proof
        ↓
Human Decision
        ↓
Git History
        ↓
Updated Architecture Knowledge
```

## 2. Core Design Principles

### 2.1 Architecture Model over Document Text

Markdown is a human-readable serialization and projection

Semantic authority lives in typed architecture state produced by the canonical parser and RepositoryModel

```text
Markdown
   ↓
Canonical Parser
   ↓
ArtifactModel
   ↓
RepositoryModel
```

### 2.2 Deterministic Control, Probabilistic Reasoning

```text
LLM       → reasoning / proposal
Graph     → relationships / retrieval
Parser    → structured interpretation
Linter    → deterministic invariants
Human     → decision authority
Git       → history / provenance
```

The linter remains mandatory but is not the architecture reasoning engine

### 2.3 Regex Boundary

Regex MAY be used for bounded lexical validation

Examples:

```text
identifier syntax
filename syntax
simple literal/token checks
```

Regex MUST NOT infer:

```text
frontmatter semantics
artifact lifecycle
relationships
graph state
architecture meaning
dependency semantics
structured sections
```

when a canonical parser or typed model can represent the same state

### 2.4 Git Is Canonical Authority

```text
Git-backed architecture repository
           ↓
RepositoryModel
           ↓
ArchitectureGraph
           ↓
Graph Store / Search / Vector Index
```

Graph stores and vector indexes are rebuildable materialized projections

LLMs are replaceable reasoning providers

### 2.5 AI Proposes, Control Plane Proves, Humans Decide

AI MUST NOT:

- silently approve architecture
- invent canonical relationships without explicit proposal state
- override deterministic controls
- mutate canonical architecture outside governed Git workflow

## 3. Framework Boundary

```text
┌──────────────────────────────────────────────────────────────┐
│                       SCNEHAUX FRAMEWORK                     │
│                                                              │
│  CORE                                                        │
│  Artifact Metamodel · Lifecycle · Relationship Ontology      │
│  RepositoryModel · ArchitectureGraph IR                      │
│                                                              │
│  CONTROL                                                     │
│  Parser · Validator · Linter · Auditor · Admission           │
│  Evidence · Versioning · Mutation Policy                     │
│                                                              │
│  KNOWLEDGE                                                   │
│  Graph Compiler · Retrieval · Search · Context Compiler      │
│                                                              │
│  AI                                                          │
│  Planner · Artifact Generator · Impact Analysis · Revision   │
│                                                              │
│  OBSERVATION                                                 │
│  Source · API · IaC · DB Schema · Runtime · Drift            │
│                                                              │
│  INTERFACES                                                  │
│  CLI · API · MCP/Tools · GitHub · Studio                     │
└──────────────────────────────────────────────────────────────┘

External commodity dependencies:

Git
LLM providers
Graph stores
Vector/search stores
CI systems
Cloud/runtime platforms
```

## 4. Scope Ownership

Scnehaux owns:

- architecture semantics
- artifact metamodel
- relationship ontology
- lifecycle semantics
- architecture governance
- repository compilation
- graph compilation
- architecture context construction
- structured artifact-generation contracts
- architecture reasoning workflow
- declared-vs-observed reconciliation contracts

Scnehaux does not own:

- foundation models
- graph database engines
- vector database engines
- Git implementation
- cloud platforms
- CI products
- business application runtime
- generic compiler ecosystems

## 5. Logical Module Boundaries

Logical modules are architectural boundaries, not mandatory services

```text
scnehaux-core
├── metamodel
├── lifecycle
├── relationships
├── provenance
└── repository

scnehaux-control
├── parser
├── validators
├── auditors
├── admission
├── evidence
└── mutation

scnehaux-knowledge
├── graph-ir
├── graph-compiler
├── retrieval
└── context-compiler

scnehaux-ai
├── intent-planner
├── architecture-planner
├── artifact-generator
├── impact-reasoning
└── revision-loop

scnehaux-observe
├── source-adapters
├── api-schema-adapters
├── iac-adapters
├── runtime-adapters
└── drift-reconciliation

scnehaux-interface
├── cli
├── api
├── mcp-tools
├── github
└── studio
```

Initial implementation SHOULD remain a modular monolith

Physical service decomposition requires demonstrated scaling or operational need

## 6. Framework vs Company Architecture

```text
┌──────────── SCNEHAUX CORE ────────────┐
│ Generic architecture semantics        │
│ Generic control plane                 │
│ Generic knowledge + AI contracts      │
└──────────────────┬────────────────────┘
                   │ configured by
                   ▼
┌──────────── COMPANY PACK ──────────────┐
│ Principles                            │
│ Policies                              │
│ Artifact profile                     │
│ Technology policy                    │
│ Regulatory context                   │
│ Organization context                 │
│ Optional ontology extensions         │
└──────────────────┬────────────────────┘
                   │ governs
                   ▼
┌──────── COMPANY ARCHITECTURE ──────────┐
│ EAD / STD / PAD / SAD / ADR / TDD      │
│ Capabilities / Systems / Platforms      │
│ Decisions / Constraints / Evidence      │
└─────────────────────────────────────────┘
```

The core MUST NOT hard-code Scnehaux, ATI, aviation, banking, or any company-specific architecture

## 7. Knowledge Identity + Namespacing

Artifact display IDs may remain human-friendly:

```text
EAD-001
PAD-004
SAD-012
```

Canonical machine identity MUST support organization/repository namespace to avoid collision across adopters

Conceptual identity:

```text
organization_id
repository_id
artifact_id
```

Equivalent URI representation MAY be provided:

```text
scnehaux://acme/architecture/SAD-012
```

## 8. Knowledge States

Every knowledge assertion must be distinguishable as:

```text
DECLARED
OBSERVED
INFERRED
PROPOSED
```

Rules:

- DECLARED is canonical approved/intended architecture state
- OBSERVED comes from code/IaC/runtime/schema discovery
- INFERRED is machine or AI-derived and never silently promoted to DECLARED
- PROPOSED is pending architecture change

This distinction prevents deterministic graph traversal from being mistaken for guaranteed truth

## 9. Architecture Knowledge Flow

```text
Architecture Repository
          ↓
Canonical Parser
          ↓
RepositoryModel
          ↓
ArchitectureGraph IR
          ↓
     ┌────┼───────────────┐
     ▼    ▼               ▼
 Exact   Graph         Semantic
 Lookup  Traversal      Retrieval
     └────┼───────────────┘
          ↓
   Context Compiler
          ↓
    ContextPackage
          ↓
          AI
```

Retrieval MUST be hybrid

Graph traversal is preferred for relationship and impact questions

Exact-ID retrieval is preferred when an identifier is known

Semantic retrieval is supplementary, not authoritative

## 10. Hierarchical Context Model

Context is layered:

```text
GLOBAL
Scnehaux semantics

ORGANIZATION
Company architecture + policies

DOMAIN
Relevant business/domain architecture

PROJECT
Current product/system initiative

WORKING
Current branch / PR / conversation / task

OBSERVED
Code / IaC / schemas / runtime
```

The Context Compiler selects only relevant evidence within a bounded token budget

## 11. AI Architecture Generation

A user may provide high-level intent:

```text
Build a fraud-detection platform
50M transactions/day
multi-country
near-real-time
reuse existing architecture where possible
```

Scnehaux MUST first plan architecture change rather than blindly generate documents

```text
User Intent
    ↓
Intent Planner
    ↓
Architecture Planner
    ↓
Existing Architecture Retrieval
    ↓
Governance + Constraint Retrieval
    ↓
Observed Context Retrieval
    ↓
Determine Required Changes
    ↓
Determine Required Artifacts
    ↓
Structured ArtifactDraft
    ↓
Deterministic Validation
    ↓
Graph Simulation
    ↓
Deterministic Rendering
    ↓
Git PR Proposal
```

The planner may decide:

```text
EAD change   NO
PAD new      YES
SAD new      YES
ADR required YES
TDD now      NO
```

This prevents documentation bureaucracy from being automated rather than eliminated

## 12. ArtifactDraft Contract

AI MUST generate structured architecture state

Conceptual contract:

```text
ArtifactDraft<T>
├── identity
├── title
├── purpose
├── scope
├── lifecycle
├── relationships
├── architecture content
├── constraints
├── NFR
├── evidence
├── assumptions
├── unresolved questions
└── provenance
```

Free-form Markdown is not the canonical AI output contract

## 13. Deterministic Rendering + Round Trip

```text
ArtifactDraft
    ↓
Renderer
    ↓
Canonical Markdown
    ↓
Canonical Parser
    ↓
ArtifactModel
```

Required invariant:

```text
semantic_state(draft) == semantic_state(parsed artifact)
```

Formatting is therefore a projection concern rather than architecture semantics

## 14. Graph Simulation

Before admission, a PROPOSED artifact is overlaid onto the current ArchitectureGraph

Simulation checks include:

- illegal relationship type
- invalid source/target type
- prohibited cycles
- missing mandatory relationship
- deprecated/withdrawn target
- lifecycle incompatibility
- duplicate canonical identity
- policy conflict
- unresolved graph dependency

Only deterministic structural claims belong in this gate

Architecture quality and trade-off reasoning remain AI/human responsibilities

## 15. Declared vs Observed Architecture

Scnehaux will eventually ingest observed evidence:

```text
Source AST
OpenAPI / AsyncAPI / Protobuf
Terraform / CDK
Kubernetes
database schema
runtime topology
telemetry
```

Observed evidence is not allowed to silently rewrite DECLARED architecture

Instead:

```text
DECLARED != OBSERVED
        ↓
DRIFT
        ↓
AI explanation / recommendation
        ↓
human-governed resolution
```

## 16. Extensibility Contract

The reusable framework should expose logical extension points for:

```text
ArtifactType
Schema
Renderer
Validator
RelationshipType
ContextProvider
Retriever
ObservedSource
GraphStore
SemanticIndex
ModelProvider
```

Extensions MUST NOT require forking the core engine

Vendor-specific implementations stay behind adapters

## 17. Deployment Profiles

Scnehaux must scale by organizational maturity, not only data volume

### Minimal

```text
Git
Scnehaux Core
In-memory ArchitectureGraph
CLI
```

### Team

```text
Git
Core + Control + Knowledge
Search
CI
Optional LLM
```

### Enterprise

```text
Git
Core + Control + Knowledge + AI + Observe
Graph Store
Semantic Index
Model Gateway
API
GitHub integration
Observability
Studio
```

Graph/vector/LLM infrastructure is therefore optional to the core framework

## 18. Self-Hosting / Dogfooding

Scnehaux itself will become the first architecture corpus governed by Scnehaux

However, while architecture admission is CLOSED:

- no official Scnehaux EAD/PAD/SAD/TDD/ADR is admitted
- this plan acts only as a pre-admission framework design contract
- official artifacts are generated/admitted only after governance permits architecture admission

Future Scnehaux architecture is expected to describe at least:

```text
Enterprise/Framework capability view
Platform/domain boundaries
Core Engine
Control Plane
Knowledge Runtime
AI Harness
Observation Engine
Interfaces
Key irreversible decisions
```

## 19. Phase 6 Implementation Order

```text
6.1 Framework Product Boundary
6.2 Capability + Logical Module Map
6.3 Artifact Metamodel
6.4 Semantic Parsing Boundary
6.5 ArchitectureGraph IR
6.6 Deterministic Graph Compiler
6.7 Knowledge Provenance
6.8 ContextPackage + ArtifactDraft
6.9 Deterministic Renderer + Round Trip + Graph Simulation
6.10 Temporary Tool Reconciliation
```

Phase 6 is semantic-foundation work

It MUST NOT introduce a mandatory Neo4j, vector database, LLM vendor, agent framework, or microservice topology

## 20. Phase 6 Definition of Done

- framework/product boundary is explicit
- framework/company boundary is explicit
- logical modules are explicit
- canonical ArtifactModel exists
- architecture semantics are parser/model-driven
- semantic regex pseudo-parsing is removed
- ArchitectureGraph IR exists
- graph compilation is deterministic
- knowledge provenance states are explicit
- ContextPackage exists
- ArtifactDraft exists
- deterministic rendering exists
- round-trip semantic equivalence is proven
- graph simulation contract exists
- temporary migration tooling is reconciled
- tests remain >=95% per governed production Python file
- governance lint remains green
- architecture admission remains CLOSED
- architecture artifact directories remain absent

<!-- SCNEHAUX-AI-NATIVE-COMPATIBILITY-RECONCILIATION -->

## AI-Native Compatibility Reconciliation

Before ContextPackage, ArtifactDraft, Graph RAG, or AI Harness work continues, the existing governance implementation MUST be reconciled with the reusable AI-native framework target.

This reconciliation exists to prevent AI-native capabilities from being built on top of legacy documentation-centric assumptions.

### Canonical Authority Chain

The target authority model is:

```text
Markdown / Structured Source
        ↓
Canonical Parser
        ↓
ArtifactModel
        ↓
RepositoryModel
        ↓
KnowledgeGraph IR
```

Rules:

- `ArtifactModel` is the canonical semantic representation of an architecture artifact
- `RepositoryModel` is an immutable repository snapshot/collection of canonical artifact models
- `RepositoryModel` MUST NOT independently redefine artifact semantics already represented by `ArtifactModel`
- derived graph, indexes, dashboards, and AI context MUST consume canonical model state rather than reparsing Markdown independently

### Knowledge Graph Generalization

The graph abstraction MUST NOT assume that every node is an architecture artifact.

Target graph model:

```text
KnowledgeNode
├── key
├── node_type
├── knowledge_state
├── properties
└── provenance

KnowledgeEdge
├── source
├── target
├── relationship_type
├── knowledge_state
└── provenance
```

Expected node types may include:

```text
artifact
capability
platform
system
component
technology
control
standard
decision
team
data-domain
interface
nfr
deployment
observed-resource
```

Artifact lifecycle and artifact type belong in artifact-node properties rather than being mandatory fields for every knowledge node.

### Reference Resolution

The graph compiler MUST evolve from a same-repository closed-world model into an explicit resolvable-reference model.

Supported conceptual references:

```text
LocalRef
ExternalRef
ObservedRef
```

Rules:

- unresolved references fail closed
- explicitly external references are permitted when a resolver/profile authorizes them
- cross-repository and cross-organization identities MUST remain namespaced
- external references MUST preserve provenance and authority boundaries

### Framework Profile Separation

Scnehaux-specific bootstrap assumptions MUST NOT become framework-core semantics.

Examples that belong in profiles/configuration:

```text
required GDC baseline IDs
governance admission prerequisites
default artifact folders
default artifact families
default relationship policies
default maturity controls
```

Conceptual split:

```text
Scnehaux Core
      +
Governance / Artifact Profile
      +
Company Pack
      +
Company Architecture
```

The Codex repository MAY use the strict Scnehaux default profile, while another adopter MAY choose a lighter or regulated profile without forking the engine.

### Relationship Hierarchy Reconciliation

The framework MUST preserve:

```text
valid source/target type
relationship semantics
cardinality
lifecycle compatibility
cycle constraints
required relationships where justified
```

The framework MUST NOT enforce an artificial universal documentation chain such as:

```text
TDD → SAD → PAD → EAD
```

when the architecture change does not require every artifact layer.

The Architecture Planner may legitimately decide:

```text
EAD change   NO
PAD change   NO
SAD new      YES
ADR required YES
TDD now      NO
```

Artifact necessity is policy- and context-driven, not ritual-driven.

### Semantic Validation Reconciliation

The following patterns MUST be removed or demoted from hard architecture governance when they infer semantic meaning from text:

```text
semantic regex parsing
keyword-based architecture inference
prose-pattern compliance
technology inference from free text
NFR completeness inferred from keyword presence
```

Regex remains permitted only for bounded lexical validation such as:

```text
identifier syntax
filename syntax
date syntax
URI syntax
simple literal/token constraints
```

Structured architecture semantics MUST come from typed state, registries, relationships, or canonical parsers.

### Generator Reconciliation

All architecture-derived outputs MUST converge on one authority chain:

```text
ArtifactModel
    ↓
RepositoryModel
    ↓
KnowledgeGraph IR
    ↓
derived views
```

Generators MUST NOT each implement their own Markdown parser or architecture inference logic.

Examples of derived views:

```text
traceability graph
ADR index
PAD/SAD index
maturity dashboard
architecture overview
knowledge graph projection
AI context package
```

### Artifact Type Extensibility

Base `ArtifactModel` remains generic.

Artifact-specific structure MUST be supplied through artifact-type definitions/registries:

```text
ArtifactTypeDefinition
├── schema
├── renderer
├── validator
├── relationship policy
├── lifecycle policy
└── AI generation contract
```

This enables organizations to add or remove artifact families without forking core engine behavior.

### Development Governance vs Product Governance

Repository engineering policies such as:

```text
>=95% per-production-file Python coverage
Genesis bootstrap restrictions
Codex-specific branch policy
```

remain valid for development of Scnehaux itself.

They MUST NOT automatically become mandatory architecture policies for every framework adopter.

### Phase 6.6A Definition of Done

Phase 6.6A closes only when:

- RepositoryModel authority is reconciled with ArtifactModel
- graph IR supports non-artifact knowledge nodes
- local/external/observed reference semantics are defined
- Scnehaux-specific baseline assumptions are profile-driven
- universal mandatory artifact-chain assumptions are removed or policy-scoped
- semantic regex/prose-pattern governance is inventoried and removed/demoted
- architecture generators consume canonical model/graph state
- artifact-type behavior is registry/profile extensible
- no new AI/RAG layer depends on unreconciled legacy semantics

<!-- SCNEHAUX-CODEX-CAPABILITY-ARCHITECTURE-FREEZE -->

## Scnehaux Codex Capability Architecture Freeze

Scnehaux Codex is designed around stable capabilities and contracts, not a fixed number of AI agents.

Agent topology is a runtime concern.

The framework MUST remain valid whether an adopter uses:

```text
one general-purpose agent
manager + specialist agents
deterministic workflow with selected AI stages
multi-model regulated review
human-heavy approval workflow
```

### Stable Capability Set

The canonical capability architecture contains twelve primary capabilities.

```text
1. Intent Analysis
2. Architecture Planning
3. Knowledge Compilation
4. Context Compilation
5. Research
6. Architecture Synthesis
7. Deterministic Validation
8. AI Architecture Review
9. Simulation / Impact Analysis
10. Drift Reconciliation
11. Approval Orchestration
12. Evaluation
```

These capabilities MAY be implemented by one or many runtime agents.

They MUST NOT be coupled to a specific model vendor, agent framework, graph database, or orchestration topology.

### 1. Intent Analysis

Transforms human/business intent into a structured `IntentSpec`.

Conceptual contract:

```text
IntentSpec
├── business_goal
├── scope
├── actors
├── scale
├── latency
├── availability
├── security
├── geography
├── compliance
├── constraints
├── cost_posture
├── time_horizon
├── reuse_preference
├── assumptions
└── unknowns
```

Inferred requirements remain explicitly `INFERRED` until promoted by policy or human decision.

### 2. Architecture Planning

Produces `ArchitecturePlan`.

The planner determines:

```text
what architecture already exists
what must change
what should be reused
what must be researched
which artifacts are required
which reviews are required
which approval path applies
```

Artifact creation is therefore an output of planning rather than a ritual prerequisite.

### 3. Knowledge Compilation

Maintains the reusable architecture knowledge substrate.

Responsibilities include:

```text
typed ingestion
namespacing
deduplication
provenance preservation
reference resolution
graph compilation
index projection
freshness/revision tracking
```

Researchers consume knowledge.

Knowledge Compilation maintains knowledge.

### 4. Context Compilation

Produces a bounded `ContextPackage` for reasoning tasks.

The compiler may combine:

```text
exact identifier lookup
knowledge graph traversal
full-text retrieval
semantic retrieval
organization context
domain context
project context
working context
observed architecture
research evidence
```

Individual agents MUST NOT become independent sources of retrieval semantics.

### 5. Research

Produces a structured `ResearchPackage`.

Research may use:

```text
Scnehaux Codex knowledge
source code
IaC
runtime evidence
internal connected sources
external standards
vendor documentation
web research
academic literature
```

Every material finding MUST preserve evidence and provenance.

### 6. Architecture Synthesis

Produces an `ArchitectureProposal`.

Synthesis operates on:

```text
IntentSpec
ArchitecturePlan
ContextPackage
ResearchPackage
governing controls
observed reality
```

The proposal is then projected into one or more typed `ArtifactDraft<T>` objects.

Architecture reasoning MUST NOT be constrained by Markdown layout.

### 7. Deterministic Validation

Produces `ValidationReport`.

Deterministic validation owns machine-verifiable facts such as:

```text
schema
identity
relationship legality
cardinality
lifecycle
registry integrity
graph invariants
version/mutation rules
admission policy
```

LLMs MUST NOT replace deterministic proof where deterministic proof is available.

### 8. AI Architecture Review

Produces one or more `ArchitectureReview` objects.

AI review challenges:

```text
architectural quality
trade-offs
reuse opportunities
overengineering
underengineering
failure modes
NFR alignment
coupling
operability
security reasoning
cost reasoning
migration risk
evidence quality
```

Generation and review SHOULD be independently executed where risk justifies it.

### 9. Simulation / Impact Analysis

Produces `SimulationReport`.

Initial scope is graph simulation.

The contract MUST remain extensible to:

```text
dependency impact
blast radius
cycle detection
migration impact
capacity simulation
failure simulation
cost simulation
```

Simulation operates on `CURRENT + PROPOSED` state without mutating canonical architecture.

### 10. Drift Reconciliation

Produces `DriftReport`.

```text
DECLARED
    vs
OBSERVED
    ↓
DriftReport
```

Observed implementation MUST NOT silently rewrite declared architecture.

Resolution may be:

```text
change implementation
change architecture
accept governed exception
research further
```

### 11. Approval Orchestration

Produces `ApprovalPackage` and applies organization policy.

Approval policy may consider:

```text
artifact type
risk classification
affected scope
validation result
review result
simulation result
required approvers
segregation of duties
auto-approval policy
```

Human approval remains the default authority for consequential architecture decisions.

Auto-approval is an adopter policy, not a Scnehaux Codex core assumption.

### 12. Evaluation

Provides continuous architecture-AI evaluation.

Evaluation dimensions include:

```text
context precision
context recall
constraint adherence
evidence grounding
hallucination rate
architecture quality
reuse accuracy
review quality
validator agreement
latency
cost
```

Model upgrades and prompt/runtime changes MUST be evaluated against reproducible architecture scenarios rather than subjective impressions.

## Cross-Cutting Runtime Substrates

The capability architecture depends on reusable cross-cutting substrates.

```text
Evidence + Provenance
Model Gateway
Tool / Capability Registry
Guardrails
Trace / Run Provenance
Identity + Authorization
Budget / Cost Control
```

### Evidence + Provenance

Material claims MUST be traceable:

```text
Claim
 ↓
Evidence
 ↓
Source
 ↓
Authority
 ↓
Revision
```

Evidence is a first-class data primitive, not merely a citation string.

### Model Gateway

The framework requests model capabilities rather than specific vendors.

Examples:

```text
structured_output
reasoning
tool_calling
vision
large_context
cost_class
latency_class
```

### Tool / Capability Registry

Tools are registered independently from agents.

Conceptual capabilities include:

```text
architecture.lookup
architecture.graph.query
architecture.search
architecture.artifact.read
source.inspect
iac.inspect
runtime.query
web.search
standard.lookup
```

### Guardrails

Guardrails apply at multiple boundaries:

```text
input
tool invocation
output
mutation
authorization scope
```

### Trace / Run Provenance

Every architecture AI run MUST be reconstructable from:

```text
run_id
model/provider/version
instruction version
tool calls
knowledge revision
retrieved evidence
IntentSpec
ArchitecturePlan
ResearchPackage
ContextPackage
ArchitectureProposal
ArtifactDraft
ValidationReport
SimulationReport
ArchitectureReview
ApprovalPackage
final decision
```

### Budget / Cost Control

Execution policy may select different depth profiles without changing architecture semantics.

Examples:

```text
fast
balanced
deep
regulated
```

The profile may vary:

```text
number of researchers
number of independent reviewers
model class
external research
simulation depth
human approval requirements
```

## Canonical Architecture Workflow

```text
User Intent
    ↓
IntentSpec
    ↓
ArchitecturePlan
    ↓
ResearchPlan
    ↓
ResearchPackage
    ↓
ContextPackage
    ↓
ArchitectureProposal
    ↓
ArtifactDraft[]
    ↓
ValidationReport
    ↓
SimulationReport
    ↓
ArchitectureReview[]
    ↓
Revision Loop
    ↓
ApprovalPackage
    ↓
Decision
    ↓
Git
    ↓
Knowledge Graph
    ↓
Observed / Drift Reconciliation Loop
```

The contracts are stable.

The agent topology is replaceable.

## Five Stable Planes

```text
KNOWLEDGE PLANE
ArtifactModel
RepositoryModel
KnowledgeGraph
Search / Index
Observed Architecture

INTELLIGENCE PLANE
Intent Analysis
Architecture Planning
Context Compilation
Research
Architecture Synthesis
AI Architecture Review

CONTROL PLANE
Parser
Deterministic Validator / Linter
Policy
Simulation
Admission

GOVERNANCE PLANE
Evidence
Provenance
Approval
Audit
Identity / Authorization

RUNTIME PLANE
Model Gateway
Tool Registry
Agent Orchestration
Guardrails
Tracing
Evaluation
Budget / Cost
```

These are logical responsibility planes.

They do not imply independent services or repositories.

The default implementation remains modular-monolith compatible.

## Capability Architecture Invariants

- no capability requires a specific agent topology
- no agent is itself an authority boundary
- AI reasoning never replaces available deterministic validation
- claims used for architecture decisions are provenance-aware
- generation and review are separable capabilities
- observed state never silently overwrites declared state
- approval policy is organization-configurable
- retrieval semantics are centralized through Context Compilation
- model/provider replacement does not change architecture semantics
- evaluation is required before material AI-runtime upgrades
