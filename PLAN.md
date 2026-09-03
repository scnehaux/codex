# Scnehaux Codex Execution Plan

<!-- REPOSITORY-BOUNDARY-REBASELINE:START -->

## Repository Boundary Rebaseline

Current execution authority:

- `scnehaux/codex` is the reusable governance framework and executable control plane
- Canonical architecture instances move to a separate architecture repository
- Codex framework roots are `governance/`, `schemas/`, `templates/`, `engine/`, `generators/`, `scripts/`, and `tests/`
- Architecture consumer roots are `enterprise/`, `standards/`, `domains/`, `systems/`, `designs/`, and `decisions/`
- Numeric directory prefixes are retired; semantic ordering and dependency come from metadata and graph contracts
- Framework resources resolve from Codex; organization architecture policy instances resolve from the consumer repository
- Immutable Genesis evidence is interpreted from the root commit's own historical manifest and layout
- External GitHub trust-boundary activation follows this repository-boundary rebaseline, not vice versa

<!-- REPOSITORY-BOUNDARY-REBASELINE:END -->

## 0. Current Authority State

This plan is the current execution contract for `scnehaux/codex`

Observed repository state:

```text
Canonical branch                  : main
Genesis root commit               : CREATED
Genesis SHA                       : 35ba5f427b8fcda41e8bb3a989cdf21cdf8e31cc
Active implementation branch      : phase10/github-enforcement
Observed branch HEAD              : ff32d981d1e4b302c6d6ac4ae3de606ec1a47a54
Architecture admission            : CLOSED
Governance lifecycle              : draft / 0.x
Live GitHub repository ruleset    : NOT INSTALLED
Open PR for active branch         : NONE
GitHub Actions evidence           : NONE
Governance 1.0 readiness          : NOT READY
```

Git history is the historical ledger

`normative-control-registry.yaml` is the control-level policy/evidence ledger

This document owns execution sequencing only

---

## 1. Operating Rules

Every implementation slice follows this sequence:

1. Define the invariant being closed
2. Inspect current implementation and tests
3. Identify the canonical semantic authority
4. Remove duplicate or stale authority before adding another one
5. Implement the smallest coherent production change
6. Add positive, negative, and failure-path tests
7. Run the narrowest relevant test set
8. Run canonical repository gates
9. Inspect generated-state drift
10. Inspect governed mutation/version impact
11. Inspect `git diff`
12. Update PLAN and ROADMAP only from observed evidence
13. Commit only when the slice acceptance criteria are satisfied

Never:

- lower a coverage or governance threshold to obtain green
- preserve dead compatibility APIs only to satisfy stale tests
- suppress linter findings instead of fixing the defect
- duplicate semantic rules across prose, schema, Python, and generators
- mark desired configuration as effective enforcement
- let the subject under governance become the sole authority that can weaken its own guardrail
- duplicate control-level status already owned by the normative control registry
- bulk-copy legacy architecture artifacts

---

## 2. Canonical Qualification Sequence

The active branch is not merge-ready until the following sequence is green from a clean checkout:

```bash
make github-policy-check
make lint-code
make lint-docs-format
make verify-generated
make check-waivers
make genesis-check
make mutation-check
SCNEHAUX_MUTATION_BASE_REF=35ba5f427b8fcda41e8bb3a989cdf21cdf8e31cc make mutation-ci-check
make governance-qualify
```

`make governance-qualify` is necessary but not sufficient for Phase 10 completion because committed-delta validation and effective external GitHub enforcement are separate controls

---

# 3. PHASE 10 — GITHUB ENFORCEMENT AND STABILIZATION

Phase 10 closes the active branch before any new architecture-semantic refactor begins

## Slice 10.1 — Cross-Platform Formatting Contract

### Problem

`prettier_runner.py`, its tests, and the Makefile currently expose inconsistent command/API contracts

### Target

One canonical formatter contract:

```text
CLI
→ run_prettier(mode)
→ resolve pinned npx
→ construct exact arguments
→ platform execution adapter
```

Supported modes:

```text
check
write
```

### Required Work

- reconcile `prettier_runner.py` with its tests and Makefile
- expose one production API rather than parallel stale contracts
- make `--check` and `--write` explicit and mutually exclusive
- preserve shell-free execution on POSIX
- make Windows command execution explicit and deterministic
- keep Prettier version pinned

### Acceptance

- formatter unit tests green
- `make lint-docs-format` green
- `make format-docs` green
- no stale formatter test contract remains

---

## Slice 10.2 — Python Quality Baseline

### Problem

The new quality gate exposes existing and newly introduced Ruff violations

### Required Work

- remove unused imports and variables
- fix formatting violations
- do not add blanket ignores for production code
- distinguish Phase 10 regressions from Genesis baseline debt, but close both when they are inside the governed gate

### Acceptance

```text
make lint-code = PASS
```

---

## Slice 10.3 — Generated-State Reconciliation

### Required Work

- run all canonical generators
- run canonical document formatting after generation
- commit only generate-then-format canonical output
- verify idempotence from a clean checkout

### Acceptance

```text
make verify-generated = PASS
second generate-then-format run = zero diff
```

---

## Slice 10.4 — Governed Mutation and Version Reconciliation

### Current Policy

Current governance treats editorial, typo, dead-link, and formatting changes as Patch mutations

This stabilization slice MUST NOT weaken the mutation authority merely to make the active branch pass

### Required Work

- enumerate every governed document changed relative to Genesis
- identify whether each change is textual, metadata, or semantic
- apply the version increase required by the current governance contract
- preserve immutable document identity
- do not introduce semantic-vs-textual version separation in this slice

### Acceptance

```text
make mutation-check = PASS
make mutation-ci-check = PASS
```

A future semantic-version model may separate Git textual revision from architecture semantic revision, but that is a governed design change and not a Phase 10 stabilization shortcut

---

## Slice 10.5 — Internal Governance Qualification

### Required Work

Run the complete canonical qualification sequence from a clean checkout

### Acceptance

- all unit and integration tests pass
- all governed coverage thresholds pass
- lint has zero blocking findings
- generated state is reproducible
- Genesis root remains immutable
- committed mutation delta is valid

Only after Slice 10.5 is green may effective GitHub enforcement be activated

---

## Slice 10.6 — Enforcement Trust Boundary

### Invariant

A pull request MUST NOT be able to become the sole authority that weakens the control used to qualify that same pull request

### Required Work

Introduce a trusted enforcement boundary for governance-critical paths, including at minimum:

```text
.github/workflows/**
.github/CODEOWNERS
governance/github/**
engine/control/governance/**
scripts/*governance*
```

The trusted boundary may use an independently anchored guardian workflow, external GitHub App/controller, repository ruleset policy, or equivalent mechanism

The ordinary PR workflow may validate candidate code, but it MUST NOT be the only authority protecting its own definition

### Acceptance

- enforcement architecture has an explicit authority boundary
- guardrail changes cannot self-authorize
- enforcement code has negative tests

---

## Slice 10.7 — GitHub Desired-State Semantic Validation

### Required Work

Replace text-fragment-only workflow checks with structured validation where practical

Validate at minimum:

- workflow trigger semantics
- permissions
- checkout safety properties
- exact required job/check identity
- required steps
- pinned action revisions
- ruleset semantics
- CODEOWNERS semantics
- repository settings required by governance

Desired-state validation remains separate from live-state observation

---

## Slice 10.8 — Review Bootstrap Exception

### Problem

Normative governance requires independent human approval while the current repository may not yet have a second independent qualified reviewer

### Required Work

Model the temporary exception explicitly:

```text
normative target        : >=1 independent governed approval
bootstrap exception     : 0 mandatory approvals
reason                  : no second independent reviewer available
exit condition          : second qualified reviewer becomes available
```

The exception MUST be visible in governance policy and MUST have a deterministic exit condition

---

## Slice 10.9 — Live-State Observer

### Required Work

Observe actual GitHub state independently from repository desired configuration

Model:

```text
Policy
→ Desired State
→ Privileged Reconciler / Admin Boundary
→ GitHub
→ Observer
→ Effective State
→ Evidence
```

### Acceptance

The system can distinguish:

```text
desired
installed
effective
drifted
```

---

## Slice 10.10 — Activation and Negative Enforcement Evidence

Install the effective controls only after Slices 10.1–10.9 are ready

Required evidence:

1. direct push to `main` rejected
2. force push rejected
3. default branch deletion rejected
4. failing governance qualification cannot merge
5. required review behavior matches the active bootstrap policy
6. unresolved review thread blocks merge when required
7. stale review handling matches policy
8. only allowed merge method is accepted
9. post-install observer reports no desired/effective drift

Configuration text alone is not evidence

### Phase 10 Exit

- clean-checkout internal qualification green
- effective GitHub controls installed
- negative enforcement evidence captured
- desired/effective drift is zero
- branch merge-ready through the governed path

---

# 4. PHASE 11 — EXECUTABLE FRAMEWORK & DECLARATIVE SEMANTIC AUTHORITY

Phase 11 separates authored framework semantics from Python implementation and establishes the first canonical repository trust boundary.

Core invariants:

- Runtime behavior MUST derive from an immutable `ExecutableFramework` deterministically compiled from governed declarative framework contracts
- Python implementation MUST NOT independently redefine framework semantics
- JSON Schema owns structural validation only; runtime governance configuration and semantic policy MUST live outside schemas
- No parsed, unvalidated, or revision-unbound artifact state may enter canonical knowledge compilation
- `ValidatedRepositorySnapshot` is the first canonical authority permitted to feed knowledge compilation
- Existing Scnehaux semantics are extracted, normalized, and formalized; Phase 11 MUST NOT silently redefine established governance meaning

## Slice 11.1 — Declarative Framework Contract

### Target

Define the governed authored inputs that describe a Scnehaux framework without requiring Python edits for ordinary semantic evolution.

Required contract families:

- framework identity and version
- artifact type declarations
- repository layout policy
- lifecycle policy
- relationship ontology
- schema bindings
- validator bindings
- governance and severity policy references
- extension declarations and compatibility metadata

### Acceptance

- declarative contracts have explicit schema/version identity
- contract loading is deterministic and fail-closed
- duplicate or conflicting semantic ownership is rejected
- existing runtime semantics can be represented without loss

## Slice 11.2 — Artifact Type / Layout / Lifecycle Contracts

### Target

Remove independent runtime ownership of artifact vocabulary, repository topology, and lifecycle semantics from Python registries.

The declarative model MUST define:

- artifact type identity and family
- canonical repository location
- schema binding
- validator capability binding
- allowed lifecycle states
- semantic lifecycle class
- validation profile
- lifecycle age policy when applicable

### Acceptance

- `ARTIFACT_TYPES`, governed corpus roots, and lifecycle mappings no longer act as independent semantic authorities
- TDD has one explicit topology contract
- artifact discovery and type detection derive from compiled framework state
- semantic layout is not inferred from numbered directory names

## Slice 11.3 — Relationship Ontology

### Target

Extract relationship semantics from Python into a versioned machine-readable ontology.

The ontology MUST define:

- relationship identity
- metadata field
- allowed source and target artifact types
- cardinality
- direction
- DAG participation
- inverse relation when applicable
- authority constraints
- lifecycle/status constraints where semantically required

### Acceptance

- `RELATIONSHIP_REGISTRY` is no longer authored in Python
- parser/frontmatter stores relationship instances only
- prose may explain ontology rules but cannot redefine them
- schema validation does not become the semantic relationship authority
- current Scnehaux relationship meaning is preserved unless changed by a separately governed decision

## Slice 11.4 — FrameworkCompiler + ExecutableFramework

### Target

Introduce a deterministic compilation boundary from declarative contracts to immutable runtime authority.

```text
Declarative Framework Contracts
        ↓
FrameworkCompiler
        ↓
ExecutableFramework
```

`ExecutableFramework` MUST expose typed immutable runtime registries/policies for:

- artifact types
- repository layout
- lifecycle
- relationship ontology
- schema bindings
- validator bindings
- governance/severity policy

### Acceptance

- equivalent declarative input always compiles to equivalent semantic state
- ambiguous, incomplete, or conflicting contracts fail compilation
- runtime consumers receive `ExecutableFramework` rather than loading semantic fragments independently
- compiled semantic state has a deterministic digest or equivalent identity

## Slice 11.5 — Schema Boundary & Validation Pipeline

### Target

Restore the boundary:

```text
JSON Schema
= structural shape

ExecutableFramework
= runtime framework semantics

RelationshipOntology
= relationship semantics

Governance controls
= enforcement policy
```

Move non-structural runtime configuration out of `base.schema.json`, including repository layout and enforcement configuration that is not JSON-document shape.

Establish:

```text
SourceDocument
↓
ParsedArtifact
↓
ArtifactCandidate
↓
Deterministic Validation
↓
ValidationReport
```

### Acceptance

- JSON Schema no longer acts as repository/governance configuration storage
- document type detection derives from `ExecutableFramework`
- full structural, lifecycle, relationship, and governance validation occurs before canonical promotion
- invalid candidates remain available for diagnostics but cannot become canonical repository knowledge

## Slice 11.6 — Provenance-Bound Repository Ingestion

### Target

Bind canonical Git-backed architecture ingestion to immutable repository provenance without making generic `SourceReference` Git-specific.

Git-backed canonical ingestion MUST establish at minimum:

- repository identity
- architecture namespace
- immutable revision / commit SHA
- repository-relative source path
- source content digest

Generic source contracts remain provider-independent so future observed sources do not inherit Git-specific assumptions.

### Acceptance

- canonical Git ingestion cannot silently omit repository identity or revision
- artifact provenance can distinguish identical artifact IDs across repositories and revisions
- source content can be integrity-checked against its recorded digest
- provenance identity is deterministic and reconstructable

## Slice 11.7 — ValidatedRepositorySnapshot

### Target

Create the first canonical repository trust boundary.

```text
ArtifactCandidate
↓
Deterministic Validation
↓
Revision-Bound Provenance
↓
ValidatedRepositorySnapshot
↓
Canonical Knowledge Compilation
```

The existing `RepositoryModel` compatibility surface may remain temporarily, but canonical knowledge compilation MUST consume only validated snapshot state.

### Acceptance

- malformed or semantically invalid artifacts cannot enter a validated snapshot
- unresolved required relationships cannot enter canonical knowledge
- snapshot identity includes framework identity and repository provenance
- KnowledgeGraph compilation rejects unvalidated repository state
- snapshot construction is deterministic for the same framework + repository revision

## Slice 11.8 — Framework Extension / Company Pack Model

### Target

Allow organization-specific semantics without core forks.

Layering:

```text
Scnehaux Core Framework
        ↓
Framework Profile
        ↓
Company Pack
        ↓
Governed Extensions
        ↓
FrameworkCompiler
```

Extension policy MUST distinguish:

- additive extension
- governed restriction
- compatibility-preserving override where explicitly allowed
- forbidden core semantic override

### Acceptance

- company-specific artifact types or relationship extensions do not require editing core Python
- extension conflicts fail closed
- core semantic replacement is forbidden by default
- compiled framework provenance identifies all contributing contract layers

## Slice 11.9 — Compatibility & Versioning

### Target

Make framework evolution explicit and reproducible.

Define:

- framework semantic version
- ontology version
- extension compatibility range
- migration rules
- deprecation policy
- compiled framework identity
- backward-compatibility expectations

### Acceptance

- incompatible framework changes are detectable before repository compilation
- framework/profile/company-pack combinations are reproducible
- semantic migrations are explicit rather than inferred
- historical repository revisions can be interpreted against the framework authority that governed them

### Phase 11 Exit

Phase 11 is complete only when:

- declarative framework contracts are the authored semantic authority
- `FrameworkCompiler` deterministically produces immutable `ExecutableFramework`
- artifact type, layout, lifecycle, relationship, schema-binding, validator-binding, and governance policy consumers derive from that runtime authority
- JSON Schema is restricted to structural validation responsibilities
- canonical Git ingestion is repository-, namespace-, revision-, path-, and digest-bound
- only `ValidatedRepositorySnapshot` may feed canonical knowledge compilation
- extension/company-pack semantics work without a core fork
- framework compatibility and semantic versioning are enforced

Phase 11 explicitly does NOT include:

- Artifact → Claim/Evidence projection
- ContextScope redesign
- IntentSpec/capability routing redesign
- model-provider, MCP, agent, or studio implementation

Those concerns begin only after the canonical repository trust boundary is established.

# 5. PHASE 12 — REPRODUCIBILITY AND SUPPLY-CHAIN CLOSURE

Close remaining dependency and build reproducibility gaps before Governance 1.0

Required work includes:

- pin build backend deterministically
- eliminate floating Python dependency ranges in governance qualification
- define lock/hash policy
- make Node/Prettier resolution reproducible
- define runner/runtime version policy
- retain full-SHA GitHub Action pinning
- document and test dependency update procedure

---

# 6. PHASE 13 — GOVERNANCE 1.0

Governance 1.0 may be released only when:

- all root-of-trust P0 controls are closed in the normative control registry
- current canonical qualification is green
- effective GitHub enforcement is proven
- executable framework and declarative semantic authority are installed and validated
- ontology compatibility contract exists
- reproducible dependency/toolchain contract is closed
- required GDCs are approved and versioned for stable baseline
- release metadata binds governance, engine, ontology/schema, and source commit versions

---

# 7. PHASE 14 — ARCHITECTURE RE-ADMISSION

No legacy bulk migration

Every legacy artifact is re-admitted as a new governed decision under current Codex semantics

For each artifact:

1. preserve legacy source as provenance
2. inspect current semantic correctness
3. normalize to current artifact model
4. validate abstraction boundary
5. validate lifecycle and classification
6. validate ontology relationships
7. validate technology policy
8. review architecture quality
9. admit through effective governed PR path

Admission order:

```text
EAD
→ STD
→ PAD
→ SAD
→ ADR / TDD
```

---

# 8. Current Next Action

The current next action is:

```text
Slice 10.1 Cross-Platform Formatting Contract
→ Slice 10.2 Python Quality Baseline
→ Slice 10.3 Generated-State Reconciliation
→ Slice 10.4 Mutation/Version Reconciliation
→ Slice 10.5 Internal Qualification
```

Do not activate the live GitHub ruleset before the stabilization wave is green

Do not begin ontology extraction as part of a formatter/lint repair commit

<!-- PHASE-STATUS:START -->

## Execution Status

- Genesis Integrity — DONE/CLOSED
- Version and Mutation Authority — IMPLEMENTED, ACTIVE BRANCH RECONCILIATION REQUIRED
- Phase 10 GitHub Enforcement and Stabilization — CURRENT ACTIVE
- Phase 11 Executable Framework & Declarative Semantic Authority — PLANNED
- Phase 12 Reproducibility and Supply-Chain Closure — PLANNED
- Phase 13 Governance 1.0 — BLOCKED
- Phase 14 Architecture Re-Admission — BLOCKED

<!-- PHASE-STATUS:END -->
