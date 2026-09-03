# Scnehaux Codex Governance Roadmap

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

## 0. Purpose and Authority

This roadmap is the workstream-level progress ledger for `scnehaux/codex`

Authority is intentionally separated:

```text
Git history                         : historical provenance
normative-control-registry.yaml     : control-level policy and evidence status
PLAN.md                             : current execution sequencing
ROADMAP.md                          : phase/workstream progress and dependencies
```

ROADMAP MUST NOT duplicate every normative control or independently redefine semantic policy

---

## 1. Current Observed State

```text
Canonical repository               : scnehaux/codex
Canonical branch                   : main
Genesis root commit                : 35ba5f427b8fcda41e8bb3a989cdf21cdf8e31cc
Active branch                      : phase10/github-enforcement
Observed branch HEAD               : ff32d981d1e4b302c6d6ac4ae3de606ec1a47a54
Architecture admission             : CLOSED
Governance baseline                : draft / 0.x
Live GitHub rulesets               : NONE
Active branch protected            : NO
Open PR for active branch          : NONE
GitHub Actions runs for branch     : NONE
Governance 1.0                     : NOT READY
```

The Genesis event already exists and MUST NOT be described as pending

---

## 2. Status Model

| Status    | Meaning                                                    |
| --------- | ---------------------------------------------------------- |
| `DONE`    | Implemented and proven by current evidence                 |
| `ACTIVE`  | Current execution workstream                               |
| `PARTIAL` | Some invariant exists but closure evidence is incomplete   |
| `PLANNED` | Sequenced future work                                      |
| `BLOCKED` | Cannot start or complete until an earlier invariant closes |

No item becomes `DONE` from prose or desired configuration alone

---

# 3. PHASE 10 — GITHUB ENFORCEMENT AND STABILIZATION

**Status: ACTIVE**

Goal:

> Make the active branch internally deterministic, then install and prove effective GitHub enforcement without allowing the governed change to self-authorize its own guardrails

## 3.1 Stabilization Ledger

| ID       | Invariant                                         | Status    | Current Gap                                                     |
| -------- | ------------------------------------------------- | --------- | --------------------------------------------------------------- |
| STAB-001 | One coherent Prettier runner contract             | `ACTIVE`  | production, tests, and Makefile disagree                        |
| STAB-002 | Python quality gate green                         | `ACTIVE`  | Ruff exposes unused imports/variables and baseline hygiene debt |
| STAB-003 | Generated projections reproducible                | `ACTIVE`  | branch must prove generate-then-format idempotence              |
| STAB-004 | Governed mutations satisfy current version policy | `ACTIVE`  | multiple changed GDCs retain unchanged versions                 |
| STAB-005 | Clean-checkout canonical qualification green      | `BLOCKED` | depends on STAB-001 through STAB-004                            |

### Phase 10 Stabilization Exit Evidence

```text
make github-policy-check   PASS
make lint-code             PASS
make lint-docs-format      PASS
make verify-generated      PASS
make check-waivers         PASS
make genesis-check         PASS
make mutation-check        PASS
make mutation-ci-check     PASS
make governance-qualify    PASS
```

---

## 3.2 Effective Enforcement Ledger

| ID      | Invariant                                                                      | Status    | Current Gap                                                                    |
| ------- | ------------------------------------------------------------------------------ | --------- | ------------------------------------------------------------------------------ |
| GHE-001 | PR cannot self-authorize weakening of its own governance guardrail             | `ACTIVE`  | ordinary PR workflow currently participates in defining its own required check |
| GHE-002 | Desired workflow/ruleset validation is semantic rather than text-fragment-only | `PARTIAL` | current checker mostly inspects strings and exact JSON fragments               |
| GHE-003 | Human review bootstrap exception is explicit and temporary                     | `PARTIAL` | normative >=1 approval conflicts with desired 0-approval bootstrap state       |
| GHE-004 | Effective GitHub state is observed independently from desired configuration    | `PLANNED` | no live-state observer/evidence model                                          |
| GHE-005 | Main ruleset is installed                                                      | `BLOCKED` | live repository currently has no ruleset                                       |
| GHE-006 | Negative enforcement evidence exists                                           | `BLOCKED` | requires installed effective controls                                          |
| GHE-007 | Desired/effective enforcement drift is zero                                    | `BLOCKED` | requires observer and installation                                             |

### Phase 10 Effective Enforcement Exit Evidence

Required negative proof:

1. direct push rejected
2. force push rejected
3. default branch deletion rejected
4. failing governance PR cannot merge
5. review behavior matches the active governed policy
6. unresolved required review thread blocks merge
7. stale approval handling matches policy
8. disallowed merge methods are rejected
9. observer reports desired/effective parity

Phase 10 is `DONE` only when both stabilization and effective enforcement are proven

---

# 4. PHASE 11 — EXECUTABLE FRAMEWORK & DECLARATIVE SEMANTIC AUTHORITY

Goal: compile governed declarative framework semantics into one immutable runtime authority and prevent unvalidated or revision-unbound repository state from entering canonical knowledge.

## 4.1 Phase 11 Dependency Chain

```text
Declarative Framework Contract
↓
Artifact Type / Layout / Lifecycle Contracts
+
Relationship Ontology
↓
FrameworkCompiler
↓
ExecutableFramework
↓
Schema Boundary + Validation Pipeline
↓
Provenance-Bound Repository Ingestion
↓
ValidatedRepositorySnapshot
↓
Canonical Knowledge
```

## 4.2 Phase 11 Ledger

| Slice | Capability                                   | Status  | Exit Evidence                                                                |
| ----- | -------------------------------------------- | ------- | ---------------------------------------------------------------------------- |
| 11.1  | Declarative Framework Contract               | PLANNED | Governed, versioned contract model exists and fails closed                   |
| 11.2  | Artifact Type / Layout / Lifecycle Contracts | PLANNED | Runtime type/layout/lifecycle semantics derive from declarative contracts    |
| 11.3  | Relationship Ontology                        | PLANNED | Relationship semantics are machine-readable and no longer authored in Python |
| 11.4  | FrameworkCompiler + ExecutableFramework      | PLANNED | Deterministic immutable compiled runtime authority exists                    |
| 11.5  | Schema Boundary & Validation Pipeline        | PLANNED | JSON Schema is structural-only and invalid candidates cannot be promoted     |
| 11.6  | Provenance-Bound Repository Ingestion        | PLANNED | Canonical Git ingestion is repository/namespace/revision/path/digest bound   |
| 11.7  | ValidatedRepositorySnapshot                  | PLANNED | Only validated revision-bound snapshots can feed canonical knowledge         |
| 11.8  | Framework Extension / Company Pack Model     | PLANNED | Company semantics extend core without Python/core fork                       |
| 11.9  | Compatibility & Versioning                   | PLANNED | Framework/ontology/extensions have enforceable compatibility contracts       |

## 4.3 Phase 11 Hard Invariants

- Runtime behavior MUST derive from an immutable `ExecutableFramework` deterministically compiled from governed declarative contracts
- Python implementation MUST NOT independently redefine framework semantics
- JSON Schema MUST NOT remain the authority for runtime repository/governance semantics
- No parsed, unvalidated, or revision-unbound artifact state may enter canonical knowledge compilation
- `ValidatedRepositorySnapshot` is the first canonical repository trust boundary
- Existing Scnehaux semantics are extracted and formalized, not silently reinvented

## 4.4 Explicitly Deferred Beyond Phase 11

- deterministic Artifact → Claim/Evidence projection
- ContextScope / KnowledgeState / working-revision axis cleanup
- IntentSpec and capability-registry redesign
- AI routing, model-provider, MCP, agent, studio, or chatbot runtime

Phase 11 MUST NOT begin as part of Phase 10 enforcement stabilization. It starts only after Phase 10 external enforcement trust-boundary evidence is complete.

# 5. PHASE 12 — REPRODUCIBILITY AND SUPPLY-CHAIN CLOSURE

**Status: PLANNED**

Goal:

> Make governance qualification reproducible enough for a stable root-of-trust release

| ID      | Invariant                                                      | Status    |
| ------- | -------------------------------------------------------------- | --------- |
| REP-001 | Python build backend deterministic                             | `PLANNED` |
| REP-002 | Governance Python dependency resolution has no floating ranges | `PLANNED` |
| REP-003 | Lock/hash policy defined                                       | `PLANNED` |
| REP-004 | Node/Prettier resolution reproducible                          | `PLANNED` |
| REP-005 | Runtime/runner version policy explicit                         | `PLANNED` |
| REP-006 | GitHub Actions remain immutable full-SHA references            | `PARTIAL` |
| REP-007 | Dependency update process governed and tested                  | `PLANNED` |

---

# 6. PHASE 13 — GOVERNANCE 1.0

**Status: BLOCKED**

Governance 1.0 requires:

- all root-of-trust P0 controls closed in `normative-control-registry.yaml`
- Phase 10 effective enforcement proven
- Phase 11 executable framework and declarative semantic authority proven
- Phase 12 reproducibility closure proven
- required GDCs approved at stable versions
- release metadata binds governance, engine, ontology/schema, and source commit versions

No architecture admission opens merely because the engine tests are green

---

# 7. PHASE 14 — ARCHITECTURE RE-ADMISSION

**Status: BLOCKED**

Blocked by Governance 1.0

No legacy bulk migration

Admission order:

```text
EAD
→ STD
→ PAD
→ SAD
→ ADR / TDD
```

Every admitted artifact must be evaluated as current architecture, with legacy content retained as provenance rather than authority

---

# 8. Current Critical Path

```text
STAB-001 Formatter Contract
→ STAB-002 Python Quality
→ STAB-003 Generated State
→ STAB-004 Mutation/Version Reconciliation
→ STAB-005 Internal Qualification
→ GHE-001 Trust Boundary
→ GHE-002/GHE-003 Desired-State Governance
→ GHE-004 Live Observer
→ GHE-005 Install Ruleset
→ GHE-006 Negative Evidence
→ GHE-007 Drift Closure
→ Phase 11 Executable Framework & Declarative Semantic Authority
→ Phase 12 Reproducibility
→ Phase 13 Governance 1.0
→ Phase 14 Architecture Re-Admission
```

This critical path is the authoritative sequencing until new observed evidence changes it

<!-- PHASE-STATUS:START -->

## Execution Status

- Genesis Integrity — DONE/CLOSED
- Phase 10 GitHub Enforcement and Stabilization — ACTIVE
- Phase 11 Executable Framework & Declarative Semantic Authority — PLANNED
- Phase 12 Reproducibility and Supply-Chain Closure — PLANNED
- Phase 13 Governance 1.0 — BLOCKED
- Phase 14 Architecture Re-Admission — BLOCKED

<!-- PHASE-STATUS:END -->
