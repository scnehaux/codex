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

# 4. PHASE 11 — DECLARATIVE SEMANTIC AUTHORITY

**Status: PLANNED**

Goal:

> Extract relationship ontology definitions from Python implementation into a declarative, versioned constitutional contract while retaining a single immutable typed runtime semantic model

## 4.1 Ontology Ledger

| ID      | Invariant                                                                          | Status    |
| ------- | ---------------------------------------------------------------------------------- | --------- |
| ONT-001 | Declarative relationship ontology owns authored vocabulary and rules               | `PLANNED` |
| ONT-002 | Ontology has identity, namespace, version, provenance, and compatibility semantics | `PLANNED` |
| ONT-003 | Ontology compiles once into immutable typed `RelationshipOntology`                 | `PLANNED` |
| ONT-004 | Parser contains no architecture relationship semantics                             | `PLANNED` |
| ONT-005 | Assembler orchestrates semantics but owns no duplicate semantic rules              | `PLANNED` |
| ONT-006 | Validator, graph, generators, and repository model consume one compiled ontology   | `PLANNED` |
| ONT-007 | JSON Schema remains structural or consumes generated ontology projections          | `PLANNED` |
| ONT-008 | Frontmatter stores relationship instances only                                     | `PLANNED` |
| ONT-009 | Core, profile, and company-extension layering is explicit                          | `PLANNED` |
| ONT-010 | Core semantic override is forbidden by default                                     | `PLANNED` |

Target semantic flow:

```text
relationship-ontology.yaml
→ Ontology Compiler
→ immutable typed RelationshipOntology
→ semantic validation / graph / repository compilation / projections
```

Target extension flow:

```text
Scnehaux Core Ontology
→ Framework Profile
→ Company Pack
→ Company Architecture
```

Phase 11 MUST NOT begin as part of a formatter/lint stabilization commit

---

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
- Phase 11 declarative semantic authority proven
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
→ Phase 11 Declarative Semantic Authority
→ Phase 12 Reproducibility
→ Phase 13 Governance 1.0
→ Phase 14 Architecture Re-Admission
```

This critical path is the authoritative sequencing until new observed evidence changes it

<!-- PHASE-STATUS:START -->

## Execution Status

- Genesis Integrity — DONE/CLOSED
- Phase 10 GitHub Enforcement and Stabilization — ACTIVE
- Phase 11 Declarative Semantic Authority — PLANNED
- Phase 12 Reproducibility and Supply-Chain Closure — PLANNED
- Phase 13 Governance 1.0 — BLOCKED
- Phase 14 Architecture Re-Admission — BLOCKED

<!-- PHASE-STATUS:END -->
