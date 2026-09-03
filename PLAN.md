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
- External SCM trust-boundary activation follows this repository-boundary rebaseline, not vice versa
- GitHub is the first reference SCM provider; provider-specific enforcement remains an adapter concern rather than core governance semantics

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

`make governance-qualify` is necessary but not sufficient for Phase 10 completion because committed-delta validation and effective external SCM enforcement are separate controls. `make github-policy-check` remains the current reference-provider gate until Slice 10.7 extracts the provider adapter contract

---

# 3. PHASE 10 — SCM ENFORCEMENT AND STABILIZATION

Phase 10 closes the active branch before any new architecture-semantic refactor begins.

GitHub is the first reference SCM provider. The core enforcement architecture MUST remain provider-neutral so GitHub, GitLab, or a future SCM provider can be supported through adapters without redefining governance semantics.

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

Only after Slice 10.5 is green may SCM enforcement work proceed to the external trust boundary.

---

## Slice 10.6 — SCM Enforcement Trust Boundary

### Invariants

A candidate change MUST NOT be able to become the sole authority that weakens the control used to qualify that same candidate change.

Repository boundary is not trust boundary.

The enforcement authority that prevents self-authorization MUST exist outside the candidate mutation being evaluated.

### Required Work

Define the provider-neutral trust model:

```text
Codex Core Governance
        ↓
SCM Enforcement Contract
        ↓
Provider Adapter
        ↓
External Provider / Server Authority
```

Current GitHub governance-critical paths include at minimum:

```text
.github/workflows/**
.github/CODEOWNERS
governance/github/**
engine/control/governance/**
scripts/*governance*
```

Future provider adapters MAY use different native paths and mechanisms. Those provider details MUST NOT become core governance semantics.

Acceptable trust anchors include provider organization/enterprise controls, independently anchored required workflows, server-side receive hooks, external controllers, or equivalent mechanisms whose authority cannot be weakened by the candidate change.

A third repository is NOT required merely to support multiple SCM providers. Splitting repositories MUST NOT be used as a substitute for a real trust boundary.

### Acceptance

- enforcement architecture has an explicit authority boundary
- candidate guardrail changes cannot self-authorize
- provider-specific controls are outside core semantic authority
- enforcement boundary has negative tests
- GitHub can act as the first reference provider without becoming a Codex core dependency

---

## Slice 10.7 — SCM Desired-State Semantic Validation

### Required Work

Introduce a provider-neutral SCM enforcement contract and keep provider-native configuration as an adapter projection.

Canonical direction:

```text
SCMEnforcementPolicy
        ↓
Provider Adapter
        ├─ GitHub ruleset / Actions / CODEOWNERS
        └─ GitLab protected branch / CI / approval controls
```

GitLab support is an extension point in this phase, not an implementation requirement.

Refactor current GitHub desired-state validation so semantic meaning is not owned by text fragments or GitHub-native JSON.

Validate at minimum:

- protected/default branch intent
- change-through-review requirement
- force-push and deletion policy
- required qualification intent
- review and thread-resolution policy
- allowed merge strategy
- provider workflow trigger semantics
- provider permissions
- checkout/source safety properties
- required check/job mapping
- pinned provider action/runtime dependencies where supported
- provider-native ruleset/branch-policy semantics
- ownership semantics
- repository settings required by governance

The existing `make github-policy-check` remains the current reference-provider gate until adapter extraction is implemented. It MUST NOT be renamed ahead of implementation.

### Acceptance

- one provider-neutral authored enforcement contract exists
- GitHub configuration is a provider projection, not the semantic authority
- provider adapters cannot redefine canonical governance meaning
- desired-state validation is structured and fail-closed
- provider-neutral policy validation remains separate from live-state observation

---

## Slice 10.8 — Review Bootstrap Exception

### Problem

Normative governance requires independent human approval while the current repository may not yet have a second independent qualified reviewer

### Required Work

Model the temporary exception in provider-neutral policy:

```text
normative target        : >=1 independent governed approval
bootstrap exception     : 0 mandatory approvals
reason                  : no second independent reviewer available
exit condition          : second qualified reviewer becomes available
```

Provider adapters translate that policy into their native review/approval controls.

The exception MUST be visible in governance policy and MUST have a deterministic exit condition.

Existing provider-specific normative wording in review governance MUST be reconciled through a separately governed GDC mutation rather than silently changed as roadmap prose.

---

## Slice 10.9 — SCM Live-State Observer

### Required Work

Observe actual provider state independently from repository desired configuration.

Model:

```text
Policy
→ Desired State
→ Provider Adapter
→ Privileged Reconciler / Admin Boundary
→ SCM Provider
→ Observer
→ Effective State
→ Evidence
```

The observer contract MUST be provider-neutral. Provider adapters supply native observation details.

### Acceptance

The system can distinguish:

```text
desired
installed
effective
drifted
```

And evidence identifies:

```text
provider
repository
observed_revision
observation_time
effective_policy
drift
```

---

## Slice 10.10 — Provider Activation and Negative Enforcement Evidence

Activate effective controls only after Slices 10.1–10.9 are ready.

GitHub is the first reference-provider activation. GitLab support does not block Phase 10 completion.

Required evidence against the activated reference provider:

1. direct push to `main` rejected
2. force push rejected
3. default branch deletion rejected
4. failing governance qualification cannot merge
5. required review behavior matches the active bootstrap policy
6. unresolved review thread blocks merge when required
7. stale review handling matches policy
8. only allowed merge method is accepted
9. post-install observer reports no desired/effective drift
10. provider-native configuration cannot redefine provider-neutral governance semantics

Configuration text alone is not evidence.

### Phase 10 Exit

- clean-checkout internal qualification green
- provider-neutral SCM enforcement contract exists
- reference-provider adapter is installed and effective
- external trust boundary prevents self-authorization
- negative enforcement evidence is captured
- desired/effective drift is zero
- core governance does not depend on GitHub- or GitLab-specific semantics
- branch is merge-ready through the governed path

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
- pin provider CI/action dependencies immutably where supported; keep current GitHub Actions on full commit SHAs
- document and test dependency update procedure

---

# 6. PHASE 13 — GOVERNANCE 1.0

Governance 1.0 may be released only when:

- all root-of-trust P0 controls are closed in the normative control registry
- current canonical qualification is green
- effective SCM enforcement is proven on the activated reference provider
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

Do not activate reference-provider enforcement before the SCM trust boundary and desired-state contract are ready

Do not begin ontology extraction as part of a formatter/lint repair commit

<!-- PHASE-STATUS:START -->

## Execution Status

- Genesis Integrity — DONE/CLOSED
- Version and Mutation Authority — IMPLEMENTED, ACTIVE BRANCH RECONCILIATION REQUIRED
- Phase 10 SCM Enforcement and Stabilization — CURRENT ACTIVE
- Phase 11 Executable Framework & Declarative Semantic Authority — PLANNED
- Phase 12 Reproducibility and Supply-Chain Closure — PLANNED
- Phase 13 Governance 1.0 — BLOCKED
- Phase 14 Architecture Re-Admission — BLOCKED

<!-- PHASE-STATUS:END -->
