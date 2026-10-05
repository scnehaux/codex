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

Historical reference-provider acceptance baseline (Phase 10 status closure):

```text
Canonical branch                  : main
Genesis root commit               : CREATED
Genesis SHA                       : 35ba5f427b8fcda41e8bb3a989cdf21cdf8e31cc
Observed Codex baseline            : 107f0dc53e873ef6d24a9f12cd28da7348f79331
Authority acceptance revision      : 360d9729310bf2903f4456f5b4464aaac17f873a
Architecture admission            : CLOSED
Governance lifecycle              : draft / 0.x
Live GitHub repository ruleset     : INSTALLED / ACTIVE (23193929)
Desired/effective drift            : ALIGNED at acceptance preflight
Phase 10 acceptance                : accepted scoped reference-provider evidence
Review bootstrap                   : active / 0 mandatory approvals
Privileged maintenance bootstrap   : disabled / permanent reader promoted
Governance 1.0 readiness            : NOT READY (later phases remain)
```

This snapshot is source-bound historical evidence, not an automatically refreshed
current-state feed. Phase 10 is closed for the accepted reference-provider scope;
the Phase 11 ledger and Current Next Action below own implementation sequencing.
Slice 11.6 is complete through Authority publication and governed merge. Slice 11.7 is active. This status grants no standing publication.

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
make scm-trust-boundary-check
make github-policy-check
make framework-contract-check
make lint-code
make lint-docs-format
make verify-generated
make check-waivers
make genesis-check
make mutation-check
SCNEHAUX_MUTATION_BASE_REF=35ba5f427b8fcda41e8bb3a989cdf21cdf8e31cc make mutation-ci-check
make governance-qualify
```

`make governance-qualify` is necessary but not sufficient for merge readiness because committed-delta validation and effective external SCM enforcement are separate controls. `make github-policy-check` remains the GitHub reference-provider projection gate alongside the implemented provider-neutral SCM contract.

---

# 3. PHASE 10 — SCM ENFORCEMENT AND STABILIZATION

**Status: DONE - scoped GitHub reference-provider acceptance under REC-D-018.**

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

GitHub Free reference strategy:

```text
Repository ruleset
→ required check: Codex Governance Authority
→ expected source: dedicated GitHub App integration_id
→ external evaluator from pinned trusted revision
→ privileged explicit promotion
```

`Governance Qualification` remains candidate validation only. The candidate workflow MUST NOT emit `Codex Governance Authority`.

The provider-neutral contract remains reusable by GitLab. A future GitLab adapter binds the same external-authority semantics to a GitLab-native mechanism (for example a Self-Managed server-side receive hook or another independently administered provider control) without changing SCM core meaning.

### Acceptance

- enforcement architecture has an explicit authority boundary
- trust model rejects candidate-local repository state as sufficient guardrail authority
- provider-specific controls are outside core semantic authority
- enforcement boundary has negative tests
- GitHub can act as the first reference provider without becoming a Codex core dependency
- design-time trust validation MUST NOT be reported as proof of effective provider enforcement; activation evidence remains Slice 10.10

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

Implementation boundary for this slice:

- `governance/scm/enforcement-policy.yaml` is the authored provider-neutral semantic authority
- `engine/control/governance/scm_policy.py` loads an immutable typed contract and validates shape/types without independently choosing policy values
- `engine/adapters/scm/github.py` validates GitHub native desired state as a projection of the authored SCM policy
- GitHub workflow semantics are parsed structurally; unscoped text-fragment matching is not semantic authority
- GitLab remains a first-class `scm-provider` extension point and must consume the same policy contract when implemented
- live/effective provider state remains Slice 10.9/10.10 and is not inferred from repository desired state

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

`make github-policy-check` remains the GitHub reference-provider projection gate for the implemented provider-neutral SCM contract. Adapter extraction does not remove reference-provider validation.

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

### Historical activation observation - 2026-09-18

The reference-provider ruleset is active on GitHub with no bypass actors and the
external `Codex Governance Authority` check source-bound to App integration
`4864946`. Missing-authority and wrong-source checks are provider-blocked; a real
direct Contents API write to `main` was rejected with repository-rule violations;
PR #22 completed the bootstrap installation through the required App check; and
PR #23 subsequently proved protected maintenance through the promoted permanent
reader with bootstrap disabled.

The live observer reports the desired ruleset as installed, provider enforcement
`ACTIVE`, and desired/effective drift `ALIGNED` at main
`362d5c072fe407c915e2307bc455720739b20154`.

At that historical checkpoint Phase 10 remained active. The later observations,
owner method decision and final preflight below close the scoped reference-provider
acceptance without rewriting those earlier evidence records.

### Scoped acceptance and governed status closure - 2026-09-21

The owner accepted REC-D-018: compose actual production qualification/Authority
paths, causally controlled disposable mechanisms, and current production state,
without widening the dedicated App installation. Authority PR #31 recorded the
assessment at `360d9729310bf2903f4456f5b4464aaac17f873a`:

- [Ten-row acceptance and scope limits](https://github.com/scnehaux/codex-authority/blob/360d9729310bf2903f4456f5b4464aaac17f873a/governance/evidence/phase10-acceptance-001.json).
- [Fresh effective/inherited/legacy preflight](https://github.com/scnehaux/codex-authority/blob/360d9729310bf2903f4456f5b4464aaac17f873a/governance/evidence/phase10-final-preflight-001.json).
- [Decision and claim ownership](https://github.com/scnehaux/codex-authority/blob/360d9729310bf2903f4456f5b4464aaac17f873a/docs/implementation-notes/0019-phase10-scoped-acceptance.md).

All ten obligations are accepted for the declared GitHub reference-provider scope.
The active named and effective rules match the tested controls; inherited rules add
no extra ruleset. An authorized admin read confirms no legacy protection layer.
The public observer reports installed / active / aligned. Fixtures remain archived
with zero open PRs and temporary reviewer access restored to Read.

This is not a successful full-mirror installation, independent human approval,
new native-Git default-deletion proof, or a guarantee of future provider state.
UNKNOWN and unsent operations retain zero proof credit. The visible zero-approval
review exception remains active; the separate privileged bootstrap is disabled.
Historical runtime and component false self-reports remain local to their original
scope. The new Authority acceptance record owns the system-level scoped assessment.

The status-closure PR must independently pass the current clean-checkout gates,
promoted runtime, durable permit boundary and dedicated-App source-bound check.
Its normal merge completes this status transition; the operational completion
record must retain that merge and subsequent publication disarm. Phase 11.1 is the
next planned slice, not implemented by closing this phase.

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

**Status: ACTIVE - Slices 11.1-11.6 complete; Slice 11.7 ValidatedRepositorySnapshot active.**

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

### Slice 11.1 implementation evidence

Status: **DONE on governed merge of this slice.**

The authored entrypoint is `governance/framework/contract-set.yaml`, with nine
versioned family contracts under `governance/framework/contracts/`. The strict
loader rejects ambiguous YAML, unsafe family paths, conflicting ownership and
unsupported versions. `scripts/framework_contract_check.py` proves a lossless
mirror against the current artifact vocabulary, repository layout, lifecycle,
relationship, schema, validator, governance-reference and extension semantics.

Runtime authority intentionally remains with the legacy Python registries until
Slices 11.2 and 11.3 migrate those families. The equivalence gate is part of
canonical governance qualification, so the staged declarative mirror and runtime
cannot drift independently. This avoids both a flag-day cutover and a permanent
dual-authority model.

Implementation recommendations and trade-offs are recorded in
`governance/framework/README.md` as REC-11-001 through REC-11-003. Slice 11.4
remains the compiler/immutable `ExecutableFramework` boundary; Slice 11.1 does
not claim provenance-bound loading or runtime activation.

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

### Slice 11.2 implementation evidence

Status: **DONE on governed merge of this slice.**

`engine/control/framework/artifacts.py` compiles the governed artifact vocabulary,
lossless family identity, canonical roots, lifecycle policies, schema bindings and
validator bindings into one immutable runtime view. Repository discovery, metadata
type detection, lifecycle helpers, validator lookup, relationship artifact-type
recognition and maturity inventory now consume that view rather than independently
authored Python/schema lists.

`LIFECYCLE_REGISTRY` and hard-coded governed corpus roots are removed. JSON
Schema's artifact-directory mapping remains a checked projection for compatibility;
it cannot redefine runtime topology. TDD is explicitly and fail-closed bound to
`designs`. Because no prior cross-type family taxonomy existed, the Slice 11.2
contract records a lossless one-type/one-family identity and rejects reclassification
until a separately governed semantic decision exists.

Relationship rules themselves remain Python-authored only until Slice 11.3; the
full compiler and immutable `ExecutableFramework` remain Slice 11.4. REC-11-004
records why this bounded typed subset view is preferable to prematurely creating a
second full runtime registry.

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

### Slice 11.3 implementation evidence

Status: **DONE on governed merge of this slice.**

`engine/control/framework/relationships.py` compiles the governed relationship
ontology into immutable typed specs and rejects ambiguous source/field pairs,
unknown artifact types, invalid cardinalities/directions, inconsistent inverse
relations, and lifecycle/status constraints that are not valid for their source
or target artifact types.

`engine/control/governance/relationships.py` is now a compatibility/behavior
facade. Its `RELATIONSHIP_REGISTRY` is only a projection of compiled ontology;
the file no longer authors `RelationshipSpec(...)` declarations. Graph auditing,
repository assembly, rendering and metadata validation therefore consume the
declarative ontology without moving semantic authority into JSON Schema.

The pre-cutover relationship meaning is locked by ontology semantic digest
`7fa6c8a1114986f6a3d2095933b0f3cd8536f3012bedeb751438bf4ed4189e07`
and existing behavioral regression tests. REC-11-005 records why this dedicated
typed projection was temporary; Slice 11.4 now subsumes it into `ExecutableFramework`.

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

### Slice 11.4 implementation evidence

Status: **DONE on governed merge of this slice.**

`engine/control/framework/executable.py` is the composition root for all nine
framework contract families. `FrameworkCompiler` produces one frozen
`ExecutableFramework` exposing artifact vocabulary/families/layout/lifecycle,
schema and validator bindings, relationship ontology, governance/severity policy,
extension declarations, contract identity, and deterministic semantic identity.

Runtime artifact and relationship accessors now delegate to the singleton
`ExecutableFramework`; production lifecycle, relationship, parser, repository,
validator and generator consumers resolve migrated semantics through that root.
Fragment compilers remain internal migration/building blocks and test seams, not
independent runtime authorities.

The compiled semantic SHA-256 is
`6f7e79c82aea1342d7f8eed9d2181383bb52b349f30af3cdf7ea3c609cf14980`.
It normalizes semantically unordered relation/extension declarations, so equivalent
representations compile to the same identity while semantic changes change the
digest. REC-11-006 records the compiler composition and digest boundary.

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

### Slice 11.5 implementation evidence

Status: **DONE on governed merge of this slice.**

`base.schema.json` is structural-only. Repository discovery policy, content rules,
severity mapping, blocking severities and the previously hard-coded NFR taxonomy are
owned by `governance/framework/contracts/governance-policy.yaml` and exposed through
`ExecutableFramework`. The CLI, validators, test support and generated governance
documentation consume that compiled policy rather than `x-global-config`.

`engine/control/validation/pipeline.py` establishes immutable `SourceDocument`,
`ParsedArtifact` and `ArtifactCandidate` states, deterministic `ValidationReport`
production and a fail-closed promotion boundary. Existing structural/domain
validators are reused rather than reimplemented. Malformed or invalid candidates
remain inspectable with deterministic findings but cannot be promoted; candidate
sets additionally fail promotion when relationship DAG validation fails.

This slice deliberately does not claim revision-bound provenance or a canonical
repository snapshot. Those trust boundaries remain Slices 11.6 and 11.7.
REC-11-007 records the schema/config authority and promotion-boundary decision.

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

### Slice 11.6 local implementation evidence

Status: **LOCALLY QUALIFIED — governed merge pending.**

`engine/control/repository/git_ingestion.py` introduces immutable
`GitRepositoryContext`, `GitSourceProvenance`, `GitIngestedCandidate` and
`GitCandidateBatch` contracts plus `GitRepositoryReader` and the
`ingest_git_governed_corpus` entrypoint. The reader obtains regular-file blobs from
an exact full commit SHA and binds their raw-byte SHA-256 to repository identity,
architecture namespace and repository-relative path. Discovery uses compiled
framework layout and ignore policy. Unsafe or ambiguous paths, non-regular files,
invalid UTF-8 and mismatched content/provenance fail closed.

`SourceReference.content_digest` stays optional and provider-independent. The
assembler preserves supplied provenance on artifacts and relationships;
`SourceDocument` and the candidate identity preserve source namespace and digest.
Git provenance records and deterministic identities can be reconstructed without
reading mutable working-tree content. Repository identity and namespace are explicit
caller bindings; this does not authenticate a remote repository or grant approval.

Regression evidence is maintained in
`tests/control/repository/test_git_ingestion.py` and
`tests/control/repository/test_git_ingestion_regressions.py`, with supporting core,
assembler and pipeline tests. Local qualification passed: **1075 tests**,
**98.59% total coverage**, the **95% per-file coverage gate**, Ruff, Prettier,
generated-state reproducibility, framework/SCM checks, waiver checks, Genesis and
mutation/version integrity. GDC-001 is bumped to 0.1.10 for generated topography.
These results do not authorize external publication. Each submitted revision must
complete clean-checkout and committed-delta qualification against its actual base,
followed by exact-candidate Authority evidence and governed merge.

REC-11-008 records the proposed design recommendation; it does not claim owner
approval. No `ValidatedRepositorySnapshot`, canonical knowledge admission or
architecture admission is claimed; those boundaries remain later slices.

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

Implementation candidate:

- `load_framework_contract_set` composes the governed core contract, exact framework profile, and explicitly declared company packs into one deterministic contract set.
- company packs declare typed operations; additive artifact types and relationship types are supported without core Python edits.
- governed restriction and compatibility-preserving override modes are distinct policy classes and default-denied until explicitly enabled by governed policy.
- forbidden core semantic overrides fail closed even when named explicitly.
- `ExecutableFramework.provenance` records core, profile, and company-pack layer identity/version/path plus immutable authored-layer SHA-256 evidence.
- semantic identity includes contributing layer identity/version/path while remaining insensitive to semantically unordered authored declaration ordering.
- validator plugins for company artifact types are isolated under the `company_packs.*` namespace; arbitrary import paths remain rejected.
- current core semantics remain unchanged when `company_packs` is empty.

Governed merge and exact-candidate Authority evidence completed for Slice 11.8. The company-pack composition boundary is now DONE.

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

Implementation candidate:

- framework semantic authority advances from `0.1.0` to `0.2.0`; relationship ontology is independently versioned as `1.0.0`.
- `extensions.yaml`, which already owns `compatibility-metadata`, declares same-major backward compatibility, explicit-only migration, the historical authority origin, migration rules, and deprecation/removal policy.
- company packs must declare half-open framework and ontology compatibility ranges; incompatible packs fail before extension operations are composed.
- `ExecutableFramework.semantic_sha256` identifies normalized semantic meaning, while `authority_sha256` additionally binds the exact authored contract hash and all contributing core/profile/company-pack layer SHA-256 identities.
- semantically unordered declaration reordering may preserve semantic identity while changing exact authored authority identity.
- `ValidatedRepositorySnapshot` records framework version, ontology version, semantic SHA, contract SHA, authority SHA, and exact contributing layer identities/hashes so historical repository state remains bound to the authority that interpreted it.
- migration is never inferred: a path from the declared historical origin to the current framework/ontology pair must exist explicitly.
- deprecation declarations are explicit and removal requires a later major-version boundary.

Governed merge and exact-candidate Authority evidence completed for Slice 11.9. Compatibility and versioning are now DONE.

### Phase 11 Exit

**Status: DONE.** All Slice 11.1-11.9 acceptance boundaries have completed governed merge. The closure is scoped to the executable framework and canonical repository trust boundary; Governance 1.0 remains not ready and architecture admission remains CLOSED.

Phase 11 exit criteria:

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

Those concerns begin only after the canonical repository trust boundary is established. Phase 12 has now completed reproducibility and supply-chain closure; Phase 13 Governance 1.0 is the active next phase.

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

### Slice 12.1 — Deterministic Toolchain & Dependency Declarations

Pin the governance qualification environment before adding artifact hash locks:

- exact build backend version
- exact direct and observed transitive Python package declarations
- exact Python and Node versions in CI
- immutable full-SHA GitHub Action references
- machine-checkable rejection of floating dependency/tool declarations

This slice does not claim package artifact hash locking or npm lockfile closure; those remain Phase 12.2. Dependency update workflow and policy closure remain Phase 12.3.

### Slice 12.2 — Artifact Hash Locks & Locked Document Toolchain

Close artifact-integrity gaps for qualification installs:

- hash-lock the Python qualification artifact set for supported CI platforms
- require `pip --require-hashes` for governance qualification dependencies
- commit npm package metadata and lock Prettier with registry integrity
- replace network-resolving `npx --yes` execution with the local `npm ci` installed binary
- fail closed when either lock or local toolchain is missing/drifted

Dependency update workflow/policy closure remains Phase 12.3.

### Slice 12.3 — Governed Dependency Update Procedure

Make dependency changes reviewable as atomic governed mutations rather than independent file edits:

- Python declaration, constraints, hash lock, and reproducibility policy move together
- npm declaration, lockfile, and reproducibility policy move together
- committed-delta CI rejects partial or lock-only updates
- the permanent readiness graph records policy, implementation, and test evidence

Governed merge completed via Codex PR #40 after exact-candidate Authority publication. All Phase 12 reproducibility invariants are now closed.

---

# 6. PHASE 13 — GOVERNANCE 1.0

**Status: ACTIVE — NOT READY FOR RELEASE.**

Governance 1.0 may be released only when:

- all root-of-trust P0 controls are closed in the normative control registry
- current canonical qualification is green
- effective SCM enforcement is proven on the activated reference provider
- executable framework and declarative semantic authority are installed and validated
- ontology compatibility contract exists
- reproducible dependency/toolchain contract is closed
- required GDCs are approved and versioned for stable baseline
- release metadata binds governance, engine, ontology/schema, and source commit versions

## 6.1 Phase 13 Entry Observations

Observed at Codex `main` `6d08b695556f19ceff78e50996fa027cb95e862b` before any Phase 13 slice:

- the normative control registry holds 166 controls: 79 `verified`, 87 `pending`, 0 `gap`
- the registry has no field that identifies a root-of-trust P0 control; "root-of-trust P0" appears only in this plan and ROADMAP, so the first release criterion has no machine-checkable closure condition
- 37 pending controls still target retired phase labels (`Phase 6 Genesis Integrity`, `Phase 7 Version + Mutation`, `Phase 8 ...`, `Phase 9 Effective GitHub Enforcement`, `Slice 5.7 RepositoryModel + Zero-Corpus`) although Genesis and Phase 10 are closed; 50 pending controls target `Phase 10 Governance 1.0 Review`, which is now Phase 13
- all 41 GDC-000 controls record `source_file: GDC-0governance-policy.md`; the extractor fingerprints the real file name `GDC-000-governance-policy.md`, so the field is a descriptive artifact of numeric-prefix retirement, not a fingerprint defect
- all twelve required baseline GDCs are `draft` at `0.x.y`; GDC-000 §2.6 item 6 makes approval and promotion to `1.0.0` one act
- `ValidatedRepositorySnapshot`, repository graph compilation and graph simulation are exercised by tests but are not called by the CLI, scripts or integrations; `make lint` is not part of `Scnehaux Governance` CI
- `engine/control/framework/artifacts.py` rejects any layout where `TDD` is not `designs`, which is a semantic rule authored in Python
- `governance/github/authority-binding.yaml` is `desired_state_only: true` and still declares `activation.state: planned` and evaluator revision `23b05a8...`, while Authority `governance/attested-handover.json` promotes runtime package source `d835991...`
- no release metadata artifact, release verifier or release tag exists

These observations are inputs for the slices below, not completion claims.

## 6.2 Phase 13 Slice Ledger

Every slice follows the §1 operating rules, its own canonical qualification, exact-candidate Authority publication and governed merge.

### Slice 13.1 — Root-of-Trust Release Classification

Invariant: the first Governance 1.0 criterion becomes machine-checkable.

- add an explicit release classification to every control record, as selected by REC-13-001
- registry structure checks fail closed on a missing or unknown classification
- governance readiness reports the pending root-of-trust set by control id
- no control changes evidence status in this slice

### Slice 13.2 — Registry Evidence Reconciliation

Invariant: no pending control targets a retired or closed phase without a recorded reason.

Status: ACTIVE; this evidence reconciliation is locally prepared and still requires exact-candidate Authority publication and governed merge. The target-phase vocabulary and descriptive source-file correction merged in Codex PR #43. This candidate maps three controls to retained evidence, producing 82 `verified` / 84 `pending` without changing normative statements:

- `CTRL-GDC-000-027`: current bootstrap provenance matches the immutable Genesis manifest; the real Genesis gate and its malformed-provenance tests supply deterministic evidence, replacing the generic human-review placeholder
- `CTRL-GDC-000-028`: owner-accepted REC-D-018 rows 2-3 and effective production rules support history protection within that historical reference-provider scope; native Git default deletion remains unobserved
- `CTRL-GDC-003-003`: the immutable root exists, and owner-accepted direct-push refusal plus production PR-only/no-bypass rules support expiry of the Genesis exception

The offline source-bound assessment is `governance/github/evidence/registry-reconciliation-001.json`. Historical Authority records are preserved with revision/blob pins and canonical content digests; scoped acceptance is not a fresh provider observation or standing publication capability. Four controls remain pending in this slice:

- `CTRL-GDC-000-026`: later qualification cannot reconstruct the missing pre-root full qualification record
- `CTRL-GDC-003-004`: PR-only controls and feature-branch examples do not establish the complete short-lived-branch obligation
- `CTRL-GDC-003-010`: automatic source-branch deletion remains unevidenced and was previously observed disabled; squash-method evidence does not close the cleanup requirement
- `CTRL-GDC-003-011`: strict-check configuration does not substitute for observed rejection of a behind-main PR

The desired-only Authority binding remains explicitly justified in `governance/github/README.md`: evaluator, promoted runtime package and publisher identities are separate; historical system acceptance does not activate publication or change component proof flags.

- each of the 37 retired-phase controls becomes `verified` with implementation and test or Authority evidence references, or is re-targeted to a current Phase 13 or Phase 14 slice with the reason recorded
- `Phase 10 Governance 1.0 Review` targets are renamed to the current Phase 13 slice that owns them
- `target_phase` values are validated against the governed phase/slice vocabulary
- `source_file` records the real GDC file name
- `governance/github/authority-binding.yaml` is reconciled with Authority promotion evidence, or its desired-state-only `planned` value is explicitly justified; effective enforcement remains an observed-evidence claim only

### Slice 13.3 — Runtime Authority Closure

Invariant: canonical qualification validates the governed corpus through the executable framework path that Phase 11 declared authoritative.

- governance qualification builds a `ValidatedRepositorySnapshot` of the current GDC corpus and fails closed on any rejected candidate
- framework-injected validation no longer falls back to module-level validator, lifecycle or relationship state
- the `TDD == designs` Python rule moves into the declarative layout or lifecycle contract
- raw-artifact graph compilation is either removed from the public surface or restricted to snapshot input
- the canonical CI path runs the repository lint/audit entrypoint, or its retirement is recorded with the replacing gate

### Slice 13.4 — Release Metadata Binding

Invariant: a Governance release is identified by one deterministic, verifiable manifest.

- implement the release manifest selected by REC-13-002
- a release verifier recomputes every bound identity from the exact source commit and fails closed on drift
- CI verifies the manifest whenever a release candidate is declared

### Slice 13.5 — Stable GDC Baseline

Invariant: every GDC in `required_baseline_ids` is `approved` at `>=1.0.0` through the review evidence selected by REC-13-003.

- GDC-000 is promoted first, because every other GDC is `governed_by` GDC-000
- each candidate carries a GDC-002 quality rubric score sheet with at least 9 passes and its normative-control delta
- approval and the `1.0.0` version change happen in the same governed change, per GDC-000 §2.6 item 6
- the ARB approval is an owner act; preparation of a candidate does not approve it

### Slice 13.6 — Governance 1.0 Release

Invariant: Governance 1.0 is declared only from observed evidence.

- every root-of-trust control is `verified`
- canonical qualification and the release verifier pass on the exact release commit
- the release manifest, Authority publication evidence and release tag bind the same commit
- PLAN and ROADMAP record the release; opening architecture admission is the first Phase 14 act, not part of this slice

## 6.3 Phase 13 Recommendations

These are recommendations for owner decision. None is accepted until the owner decision is recorded; until then the affected slice does not start implementation.

### REC-13-001 — Define root-of-trust by integrity of the authority chain

**Status: recommended; awaiting owner decision.**

Recommendation: a control is root-of-trust when its failure would let an unauthorized, unverified or unreproducible change become canonical governance authority. In practice this covers controls that protect:

1. who may change the governed source and how (change restriction, PR-only path, no history rewrite)
2. separation between the candidate change and the authority that approves it
3. integrity verification of governed source, runtime and toolchain
4. provenance and archival of each governance release

Content-quality, authoring-style and consumer-artifact rules remain release obligations of their own phase, but they are not root-of-trust. Every control records exactly one class; root-of-trust controls must be `verified` before Governance 1.0, while other pending controls must name their owning later slice.

Alternatives considered:

- treat every `CRITICAL` control as P0: rejected, because severity measures lint blocking strength, not trust impact; for example the PAD and SAD cohesion rules are `CRITICAL` content rules with no artifacts to evaluate while admission is closed
- require all 166 controls verified: rejected, because the registry also holds consumer-artifact rules, for example EAD flatness (`CTRL-GDC-006-005`) and PAD/SAD asset containers (`CTRL-GDC-008-006`, `CTRL-GDC-009-009`), that cannot be exercised before Phase 14 admits artifacts

Trade-off and residual risk: classification is itself a judgment applied per control; Slice 13.1 must show the per-control class in its diff so the classification is reviewable, and changing a control's class later is a governed mutation.

References:

1. NIST SP 800-218, SSDF v1.1, PS.1: "Help prevent unauthorized changes to code, both inadvertent and intentional, which could circumvent or negate the intended security characteristics of the software." <https://doi.org/10.6028/NIST.SP.800-218>
2. NIST SP 800-218, PS.2: "Help software acquirers ensure that the software they acquire is legitimate and has not been tampered with."
3. NIST SP 800-218, PS.3.1: "Securely archive the necessary files and supporting data (e.g., integrity verification information, provenance data) to be retained for each software release."
4. NIST SP 800-53 Rev. 5, CM-5: "Define, document, approve, and enforce physical and logical access restrictions associated with changes to the system."
5. NIST SP 800-53 Rev. 5, SI-7: "Employ integrity verification tools to detect unauthorized changes to the following software, firmware, and information: [Assignment: organization-defined software, firmware, and information] ..."
6. NIST SP 800-53 Rev. 5, AC-5 discussion: "Separation of duties addresses the potential for abuse of authorized privileges and helps to reduce the risk of malevolent activity without collusion."

### REC-13-002 — Bind each release with a deterministic release manifest

**Status: recommended; awaiting owner decision.**

Recommendation: a committed, canonical JSON release manifest per Governance release binds:

- release version `MAJOR.MINOR.PATCH` (Semantic Versioning 2.0.0)
- exact source commit SHA
- every required baseline GDC id, version and Git blob SHA
- engine package version from `pyproject.toml`
- framework semantic version, ontology version, `semantic_sha256` and `authority_sha256` from `ExecutableFramework`
- schema file Git blob SHAs
- reproducibility policy digest and qualification toolchain pins
- the Authority publication evidence for the release commit

A verifier recomputes every field from the exact commit; the release tag points at that commit, and the manifest SHA-256 is published with the release.

Alternatives considered:

- Git tag only: rejected, because a tag identifies a commit but does not state which governance, framework and schema identities a consumer should verify
- signed SLSA provenance now: deferred, because Build L2 requires a hosted build platform with signed provenance, which Codex does not yet operate; the manifest fields are chosen to map onto SLSA `buildDefinition`/`resolvedDependencies` later

Trade-off and residual risk: the manifest is unsigned, so its integrity rests on the protected `main` ruleset and the Authority check; this corresponds to SLSA Build L1 ("can be used to prevent mistakes but is trivial to bypass or forge") and must be stated in the release notes.

References:

1. Semantic Versioning 2.0.0, item 5: "Version 1.0.0 defines the public API. The way in which the version number is incremented after this release is dependent on this public API and how it changes." <https://semver.org/spec/v2.0.0.html>
2. Semantic Versioning 2.0.0, item 4: "Major version zero (0.y.z) is for initial development. Anything MAY change at any time. The public API SHOULD NOT be considered stable."
3. SLSA v1.0 Provenance: provenance exists to "Describe how an artifact or set of artifacts was produced so that: Consumers of the provenance can verify that the artifact was built according to expectations." <https://slsa.dev/spec/v1.0/provenance>
4. SLSA v1.0 Levels, Build L1: "Package has provenance showing how it was built. Can be used to prevent mistakes but is trivial to bypass or forge."; Build L2: "Forging the provenance or evading verification requires an explicit 'attack', though this may be easy to perform." <https://slsa.dev/spec/v1.0/levels>
5. NIST SP 800-218, PS.2.1: "Make software integrity verification information available to software acquirers."; PS.3.2: "Collect, safeguard, maintain, and share provenance data for all components of each software release (e.g., in a software bill of materials [SBOM])."

### REC-13-003 — Record GDC approval explicitly while the review bootstrap exception is active

**Status: recommended; awaiting owner decision.**

Context: GDC-003 §3.2 names the ARB as the required approver for GDCs, and its bootstrap exception allows the SCM projection of 0 mandatory approvals while fewer than 2 independent qualified reviewers exist. A merge therefore does not by itself prove an ARB approval.

Recommendation: each Slice 13.5 GDC promotion carries an explicit, PR-bound approval record that names the approver acting as ARB, the exact candidate head, the GDC-002 score sheet result and the review-exception status. The record is created by the approver, never by the change author or an automated agent, and it lives on the PR as a provider review or in the independently administered Authority repository.

Alternatives considered:

- wait for 2 independent qualified reviewers before Governance 1.0: strongest separation, but it blocks the release on staffing rather than on evidence; acceptable if the owner prefers it
- treat merge as approval: rejected, because under the bootstrap exception it cannot distinguish approval from authorship

Trade-off and residual risk: with one administrator, author and approver may be the same person; the record makes this visible instead of preventing it. The bootstrap exception and this residual risk must be stated in the Governance 1.0 release notes and reassessed when the reviewer count reaches 2.

References:

1. NIST SP 800-53 Rev. 5, AC-5: "Identify and document [Assignment: organization-defined duties of individuals]; and Define system access authorizations to support separation of duties."
2. NIST SP 800-53 Rev. 5, CM-5 discussion: "Therefore, organizations permit only qualified and authorized individuals to access systems for purposes of initiating changes."
3. GDC-003 §3.2, bootstrap exception: "The exception MUST be explicit, retain the Pull Request path and all machine gates, and expire when the independent qualified reviewer count reaches 2."

---

# 7. PHASE 14 — ARCHITECTURE RE-ADMISSION

Admitted architecture instances live in the consumer repository `scnehaux/codex-architecture`; Codex framework roots never receive them.

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
Phase 12 Reproducibility and Supply-Chain Closure: DONE
-> Phase 13 Governance 1.0: ACTIVE / NOT READY
-> Owner decisions on REC-13-001 through REC-13-003
-> Slice 13.1 Root-of-Trust Release Classification
```

Phase 10 reference-provider acceptance, Phase 11 executable-framework closure, and Phase 12 reproducibility closure are complete. Phase 13 is now the active workstream, but Governance 1.0 is not released and architecture admission remains closed.

<!-- PHASE-STATUS:START -->

## Execution Status

- Genesis Integrity — DONE/CLOSED
- Version and Mutation Authority — IMPLEMENTED; candidate delta qualification required per slice
- Phase 10 SCM Enforcement and Stabilization — DONE, scoped reference-provider acceptance
- Phase 11 Executable Framework & Declarative Semantic Authority — DONE, Slices 11.1-11.9 governed and merged
- Phase 12 Reproducibility and Supply-Chain Closure — DONE
- Phase 13 Governance 1.0 — ACTIVE / NOT READY
- Phase 14 Architecture Re-Admission — BLOCKED

<!-- PHASE-STATUS:END -->
