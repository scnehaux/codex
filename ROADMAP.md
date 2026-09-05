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
- External SCM trust-boundary activation follows this repository-boundary rebaseline, not vice versa
- GitHub is the first reference SCM provider; provider-specific enforcement remains an adapter concern rather than core governance semantics

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

# 3. PHASE 10 — SCM ENFORCEMENT AND STABILIZATION

**Status: ACTIVE**

Goal:

> Make the active branch internally deterministic, define a provider-neutral SCM enforcement contract, then install and prove one reference-provider implementation without allowing the governed change to self-authorize its own guardrails

## 3.1 Stabilization Ledger

| ID       | Invariant                                         | Status | Current Gap                        |
| -------- | ------------------------------------------------- | ------ | ---------------------------------- |
| STAB-001 | One coherent Prettier runner contract             | `DONE` | closed by current qualification    |
| STAB-002 | Python quality gate green                         | `DONE` | closed by current qualification    |
| STAB-003 | Generated projections reproducible                | `DONE` | closed by reproducibility evidence |
| STAB-004 | Governed mutations satisfy current version policy | `DONE` | closed by mutation qualification   |
| STAB-005 | Clean-checkout canonical qualification green      | `DONE` | closed by governance qualification |

### Phase 10 Stabilization Exit Evidence

Current reference-provider gate remains GitHub-specific until Slice 10.7 extracts the provider adapter contract:

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

## 3.2 SCM Enforcement Architecture

Canonical direction:

```text
Codex Core Governance
        ↓
SCM Enforcement Contract
        ↓
Provider Adapter
        ↓
Provider Control Plane
```

Provider model:

```text
GitHub   : reference adapter / current implementation
GitLab   : future adapter
Others   : extension point when justified
```

Hard boundaries:

- Codex core governance MUST NOT depend on GitHub-, GitLab-, or vendor-specific policy semantics
- provider adapters MAY translate canonical SCM enforcement policy into native controls but MUST NOT redefine governance meaning
- repository boundaries and trust boundaries are separate concerns; moving governance into another repository does not by itself solve self-authorization
- no third repository is required merely to support multiple SCM providers
- the authority that prevents a candidate change from weakening its own guardrail MUST exist outside that candidate change
- GitHub Free reference binding uses a dedicated GitHub App identity and external evaluator runtime
- GitLab remains a provider adapter target over the same provider-neutral trust semantics

## 3.3 Effective Enforcement Ledger

| ID      | Invariant                                                                              | Status    | Current Gap                                                                                           |
| ------- | -------------------------------------------------------------------------------------- | --------- | ----------------------------------------------------------------------------------------------------- |
| SCM-001 | Trust model rejects candidate-local state as sufficient governance guardrail authority | `ACTIVE`  | trust contract and negative proof qualified; external authority identity/runtime not yet bound        |
| SCM-002 | Provider-neutral enforcement policy is distinct from provider-native configuration     | `DONE`    | authored SCM policy is semantic authority; GitHub configuration is a provider projection              |
| SCM-003 | Desired provider state is validated semantically rather than by text fragments only    | `DONE`    | structured fail-closed semantic and GitHub projection validation are qualified                        |
| SCM-004 | Human review bootstrap exception is explicit and temporary                             | `DONE`    | provider-neutral bootstrap exception, deterministic exit condition, and provider projection qualified |
| SCM-005 | Effective provider state is observed independently from desired configuration          | `PLANNED` | no provider-neutral live-state observer/evidence model                                                |
| SCM-006 | Reference-provider controls are installed and proven                                   | `BLOCKED` | GitHub has no effective ruleset and the external trust boundary is not yet closed                     |
| SCM-007 | Desired/effective enforcement drift is zero                                            | `BLOCKED` | requires observer, provider activation, and negative enforcement evidence                             |

### Phase 10 Effective Enforcement Exit Evidence

Required negative proof against the activated reference provider:

1. direct push rejected
2. force push rejected
3. default branch deletion rejected
4. failing governance PR cannot merge
5. review behavior matches the active governed policy
6. unresolved required review thread blocks merge
7. stale approval handling matches policy
8. disallowed merge methods are rejected
9. observer reports desired/effective parity
10. provider-native configuration cannot redefine provider-neutral governance semantics

Phase 10 is `DONE` only when both stabilization and effective reference-provider enforcement are proven through the provider-neutral contract.

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

Phase 11 MUST NOT begin as part of Phase 10 enforcement stabilization. It starts only after Phase 10 external SCM enforcement trust-boundary evidence is complete.

# 5. PHASE 12 — REPRODUCIBILITY AND SUPPLY-CHAIN CLOSURE

**Status: PLANNED**

Goal:

> Make governance qualification reproducible enough for a stable root-of-trust release

| ID      | Invariant                                                            | Status    |
| ------- | -------------------------------------------------------------------- | --------- |
| REP-001 | Python build backend deterministic                                   | `PLANNED` |
| REP-002 | Governance Python dependency resolution has no floating ranges       | `PLANNED` |
| REP-003 | Lock/hash policy defined                                             | `PLANNED` |
| REP-004 | Node/Prettier resolution reproducible                                | `PLANNED` |
| REP-005 | Runtime/runner version policy explicit                               | `PLANNED` |
| REP-006 | Provider CI/action dependencies are immutably pinned where supported | `PARTIAL` |
| REP-007 | Dependency update process governed and tested                        | `PLANNED` |

---

# 6. PHASE 13 — GOVERNANCE 1.0

**Status: BLOCKED**

Governance 1.0 requires:

- all root-of-trust P0 controls closed in `normative-control-registry.yaml`
- Phase 10 effective SCM enforcement proven on the reference provider
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
STAB-001..005 Internal Stabilization                         DONE
→ SCM-001 Trust Boundary                                    ACTIVE
→ SCM-002 Provider-Neutral Enforcement Contract             DONE
→ SCM-003 Desired-State Semantic Validation                  DONE
→ SCM-004 Review Bootstrap Exception                         DONE
→ SCM-005 Live-State Observer                               PLANNED
→ SCM-006 Reference-Provider Activation + Negative Evidence BLOCKED
→ SCM-007 Drift Closure                                     BLOCKED
→ Phase 11 Executable Framework & Declarative Semantic Authority
→ Phase 12 Reproducibility
→ Phase 13 Governance 1.0
→ Phase 14 Architecture Re-Admission
```

This critical path is the authoritative sequencing until new observed evidence changes it

<!-- PHASE-STATUS:START -->

## Execution Status

- Genesis Integrity — DONE/CLOSED
- Phase 10 SCM Enforcement and Stabilization — ACTIVE
- Phase 11 Executable Framework & Declarative Semantic Authority — PLANNED
- Phase 12 Reproducibility and Supply-Chain Closure — PLANNED
- Phase 13 Governance 1.0 — BLOCKED
- Phase 14 Architecture Re-Admission — BLOCKED

<!-- PHASE-STATUS:END -->
