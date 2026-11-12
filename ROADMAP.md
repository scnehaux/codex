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
Observed pre-closure baseline       : 107f0dc53e873ef6d24a9f12cd28da7348f79331
Authority acceptance revision       : 360d9729310bf2903f4456f5b4464aaac17f873a
Architecture admission              : CLOSED
Governance baseline                 : draft / 0.x
Live GitHub ruleset                  : INSTALLED / ACTIVE (23193929)
Default branch protected by ruleset : YES / no bypass actors
Desired/effective drift             : ALIGNED at acceptance preflight
Phase 10                            : DONE in scoped reference-provider acceptance
Phase 11                            : DONE; Slices 11.1-11.9 complete
Active local phase                  : Phase 13; Governance 1.0
Governance 1.0                       : NOT READY
```

The Genesis event already exists and MUST NOT be described as pending. Provider
state above is historical evidence from the Phase 10 acceptance preflight, not a
fresh live observation. Implementation sequencing follows the Phase 11 ledger.

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

**Status: DONE - scoped GitHub reference-provider acceptance under REC-D-018.**

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

The GitHub reference-provider projection gate remains alongside the implemented provider-neutral SCM contract. Historical Phase 10 qualification evidence:

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

| ID      | Invariant                                                                              | Status | Current Gap                                                                                                                 |
| ------- | -------------------------------------------------------------------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------- |
| SCM-001 | Trust model rejects candidate-local state as sufficient governance guardrail authority | `DONE` | dedicated App source binding, independently promoted runtime, bootstrap disarm, and post-disarm maintenance path are proven |
| SCM-002 | Provider-neutral enforcement policy is distinct from provider-native configuration     | `DONE` | authored SCM policy is semantic authority; GitHub configuration is a provider projection                                    |
| SCM-003 | Desired provider state is validated semantically rather than by text fragments only    | `DONE` | structured fail-closed semantic and GitHub projection validation are qualified                                              |
| SCM-004 | Human review bootstrap exception is explicit and temporary                             | `DONE` | provider-neutral bootstrap exception, deterministic exit condition, and provider projection qualified                       |
| SCM-005 | Effective provider state is observed independently from desired configuration          | `DONE` | provider-neutral live-state observer and evidence model qualified; reference-provider state observed independently          |
| SCM-006 | Reference-provider controls are installed and proven                                   | `DONE` | all ten obligations accepted under REC-D-018; immutable evidence and current preflight recorded in Authority PR #31         |
| SCM-007 | Desired/effective enforcement drift is zero                                            | `DONE` | fresh observer ALIGNED at acceptance baseline `107f0dc...`; effective/inherited/legacy checks agree                         |

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

That exit is accepted for the current GitHub reference-provider scope, with the
owner's explicit REC-D-018 evidence-method decision and
[Authority acceptance record](https://github.com/scnehaux/codex-authority/blob/360d9729310bf2903f4456f5b4464aaac17f873a/governance/evidence/phase10-acceptance-001.json).
This status transition must itself merge through the ordinary qualification,
promoted runtime, evidence/permit and App-bound check path. Its operational merge
and publication disarm are recorded separately, not guessed in advance.

The full-mirror fixture remains BLOCKED; composed evidence does not imply all
interactions were exercised in one identical deployment. No independent human
review or native-Git default-deletion result is invented. The review exception
remains active, while privileged bootstrap and standing publication remain disabled.
Historical false component flags are not overwritten. Relevant provider/policy,
App/runtime or review-exception changes require reassessment. Phase 11 and later
phases retain their own acceptance boundaries; Phase 11 progress is recorded below.
Governance 1.0 is not declared ready.

---

# 4. PHASE 11 — EXECUTABLE FRAMEWORK & DECLARATIVE SEMANTIC AUTHORITY

**Status: DONE**

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

| Slice | Capability                                   | Status | Exit Evidence                                                                              |
| ----- | -------------------------------------------- | ------ | ------------------------------------------------------------------------------------------ |
| 11.1  | Declarative Framework Contract               | DONE   | Versioned nine-family contract set, strict loader, lossless equivalence gate               |
| 11.2  | Artifact Type / Layout / Lifecycle Contracts | DONE   | Immutable runtime view derives type/family/layout/lifecycle/bindings from contracts        |
| 11.3  | Relationship Ontology                        | DONE   | Typed ontology runtime derives all relationship semantics from declarative contracts       |
| 11.4  | FrameworkCompiler + ExecutableFramework      | DONE   | One deterministic immutable compiled runtime authority and semantic digest exist           |
| 11.5  | Schema Boundary & Validation Pipeline        | DONE   | Schema is structural-only; deterministic reports gate candidate promotion                  |
| 11.6  | Provenance-Bound Repository Ingestion        | DONE   | Exact Git provenance candidate received Authority publication and governed merge           |
| 11.7  | ValidatedRepositorySnapshot                  | DONE   | Exact snapshot candidate received Authority publication and governed merge                 |
| 11.8  | Framework Extension / Company Pack Model     | DONE   | Exact company-pack candidate received Authority publication and governed merge             |
| 11.9  | Compatibility & Versioning                   | DONE   | Exact compatibility/versioning candidate received Authority publication and governed merge |

Slice 11.1 began as a staged mirror. Slice 11.2 made artifact vocabulary,
lossless family identity, canonical roots, lifecycle, schema bindings and validator
bindings declarative runtime authority. Slice 11.3 made relationship ontology
declarative. Slice 11.4 composed those semantics plus governance/severity and
extension declarations into one immutable `ExecutableFramework`. Slice 11.5 now
restores JSON Schema to structural shape only, moves runtime governance policy into
the executable framework contract, and gates repository promotion behind
deterministic validation reports. Slice 11.6 binds exact commit blobs to repository,
namespace, source path and raw-byte digest and is complete through exact-candidate
Authority publication and governed merge. Slice 11.7 completed the canonical validated repository snapshot boundary through
exact-candidate Authority publication and governed merge. Slice 11.8 completed
layer-aware framework/profile/company-pack composition through exact-candidate
Authority publication and governed merge. Slice 11.9 completed framework/ontology compatibility, migration, deprecation and historical authority identity through exact-candidate Authority publication and governed merge.
REC-11-001 through REC-11-011 in `governance/framework/README.md` record the staged
migration decisions.

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

Phase 11 follows the accepted Phase 10 reference-provider trust-boundary evidence.
Each new slice still requires its own canonical qualification and governed merge.

# 5. PHASE 12 — REPRODUCIBILITY AND SUPPLY-CHAIN CLOSURE

**Status: DONE**

Goal:

> Make governance qualification reproducible enough for a stable root-of-trust release

| ID      | Invariant                                                            | Status |
| ------- | -------------------------------------------------------------------- | ------ |
| REP-001 | Python build backend deterministic                                   | `DONE` |
| REP-002 | Governance Python dependency resolution has no floating ranges       | `DONE` |
| REP-003 | Lock/hash policy defined                                             | `DONE` |
| REP-004 | Node/Prettier resolution reproducible                                | `DONE` |
| REP-005 | Runtime/runner version policy explicit                               | `DONE` |
| REP-006 | Provider CI/action dependencies are immutably pinned where supported | `DONE` |
| REP-007 | Dependency update process governed and tested                        | `DONE` |

### Phase 12.1 — Deterministic Toolchain & Dependency Declarations

**Status: DONE.**

- qualification Python is pinned to `3.13.15`
- qualification Node is pinned to `24.21.0`
- Python build backend is pinned to `setuptools==84.0.0`
- governed Python dependencies and observed CI transitives use exact pins
- GitHub Actions references remain full commit SHAs
- `scripts/reproducibility_check.py` is a permanent fail-closed qualification gate
- Prettier remains version-pinned at `3.9.6`; npm lock/integrity closure is intentionally Phase 12.2
- hash-locked Python artifact installation and governed dependency update procedure remain later Phase 12 slices

### Phase 12.2 — Artifact Hash Locks & Locked Document Toolchain

**Status: DONE.**

- `requirements-lock.txt` binds the Python qualification artifact set to SHA-256 hashes for Python 3.13 Windows x64 and manylinux x86_64 wheels
- governance CI installs the Python qualification environment with `pip --require-hashes`
- `package-lock.json` binds Prettier `3.9.6` to npm integrity metadata
- document formatting uses the locally installed locked Prettier binary; `npx --yes` resolution is removed
- `npm ci --ignore-scripts` is the only supported document-toolchain installation path
- dependency update procedure remains Phase 12.3

### Phase 12.3 — Governed Dependency Update Procedure

**Status: ACTIVE.**

- Python dependency/lock mutations are an atomic four-file bundle: `pyproject.toml`, `constraints.txt`, `requirements-lock.txt`, and `governance/reproducibility-policy.json`
- npm dependency/lock mutations are an atomic three-file bundle: `package.json`, `package-lock.json`, and `governance/reproducibility-policy.json`
- lock-only and declaration-only mutations fail closed in committed-delta CI
- the policy is a permanent governance readiness control with implementation and test evidence
- governed merge completed via Codex PR #40 after exact-candidate Authority publication; controlled publication was subsequently disarmed

### Phase 12 Exit

**Status: DONE.** All REP-001 through REP-007 invariants are implemented and qualified. Codex PR #40 merged as `6d08b695556f19ceff78e50996fa027cb95e862b` after `Governance Qualification` and dedicated-App `Codex Governance Authority` check `109587442778` succeeded on exact candidate `b0e2fb076a19d456d18e487657b0cd99ab1a1ddc`. Authority subsequently recorded Slice 12.3 completion and disarmed controlled publication.

This closure establishes the reproducibility/supply-chain prerequisite for Phase 13. It does not declare Governance 1.0 released, approve draft GDCs at stable versions, or open architecture admission.

---

# 6. PHASE 13 — GOVERNANCE 1.0

**Status: ACTIVE — Governance 1.0 NOT READY.**

Governance 1.0 requires:

- all root-of-trust P0 controls closed in `normative-control-registry.yaml`
- Phase 10 effective SCM enforcement proven on the reference provider
- Phase 11 executable framework and declarative semantic authority proven
- Phase 12 reproducibility closure proven
- required GDCs approved at stable versions
- release metadata binds governance, engine, ontology/schema, and source commit versions

No architecture admission opens merely because the engine tests are green

## 6.1 Phase 13 Ledger

| Slice | Capability                           | Status  | Exit Evidence                                                                                            |
| ----- | ------------------------------------ | ------- | -------------------------------------------------------------------------------------------------------- |
| 13.1  | Root-of-Trust Release Classification | DONE    | Every control carries one release class; readiness reports pending root-of-trust ids                     |
| 13.2  | Registry Evidence Reconciliation     | ACTIVE  | No pending control targets a retired phase; phase targets are validated                                  |
| 13.3  | Runtime Authority Closure            | DONE    | PR #45 merged after exact-head Authority check `111729656469`; PR #110 disarmed publication              |
| 13.4  | Release Metadata Binding             | DONE    | PR #47 merged after exact-head Authority check `121288035795`; PR #118 disarmed publication              |
| 13.5  | Stable GDC Baseline                  | ACTIVE  | GDC-000 to GDC-009 `approved` / `1.0.0` (PRs #48, #50 to #58); GDC-010 candidate awaits owner ARB record |
| 13.6  | Governance 1.0 Release               | PLANNED | Release manifest, Authority evidence and tag bind one qualified commit                                   |

Slice 13.2's retained-evidence reconciliation merged in Codex PR #44 after Authority check `111666125699` succeeded on the exact head; Authority PR #107 disarmed publication. Bootstrap provenance and two history/PR-path controls map to immutable Genesis and owner-accepted Phase 10 evidence, with its original reference-provider limits preserved. Registry counts are 82 verified / 84 pending. Four obligations remain pending: historical pre-root qualification, complete short-lived-branch evidence, automatic branch cleanup, and actual behind-main refusal. Slice 13.2 is not complete.

Slice 13.3 merged in Codex PR #45 at `db18d03440afa2097f926314df53749a5d2bd7aa`, after Authority check `111729656469` succeeded on exact head `8e2b8c088e484c0acc75255e2ebf95011b0fded4`. Authority PR #110 disarmed publication. Commit-bound GDC qualification, framework injection, snapshot-only public graph compilation and repository lint in CI are effective implementation behavior. Local qualification passed 1168 tests with 98.54% coverage and the per-file floor intact.

The owner accepted REC-13-001, REC-13-002 and REC-13-003 on 2026-10-05 by replying "oke gas" to their explicit selection. PLAN section 6.3 records the decision; individual GDC approval remains a separate owner ARB act.

Slice 13.1 merged in Codex PR #46 at `86545a1324388fcc0777f7ca1f6ab1bcd2ab5def`, after exact-head Authority check `120984021092`; Authority PR #114 disarmed publication. The 166 controls retain 82 verified / 84 pending, including 29 pending roots. Local qualification passed 1184 tests with 98.55% aggregate coverage and the per-file floor intact.

Slice 13.4 merged in Codex PR #47 at `0582d15b4c77dbc3c7eab8314a22c4db6a1c6c49`, after exact-head Authority check `121288035795` on `f8a145d00a885d8c4d606550d4efa05b19c10846`. The canonical squash tree equals the published candidate tree. Authority PR #118 retained the actual outcome and restored disabled state with null activation. Local clean-checkout qualification passed 1266 tests with 98.59% aggregate coverage; all candidate CI checks passed. The manifest/verifier and explicit release-candidate workflow are implemented. No Governance 1.0 manifest, tag or admission is declared.

Slice 13.5 promoted GDC-000 to `approved` / `1.0.0` in Codex PR #48, merged at `a8ea1e313000883a5186db8d7e0675c6e2ce00f5` after exact-head Authority check `124511720935` on `f01908ef03e361b60b5b298c75378d5ee60c53b3`. Authority PRs #119, #122 and #123 attested, activated and disarmed the publication; #120 merged an unedited earlier activation that was never usable and #121 disarmed it. The owner's REC-13-003 ARB approval record (score 10/10, review date 2026-10-29, bootstrap exception active) was created after the merge, in Authority PR #124, which states the deviation. Authority PR #126 now blocks permits for GDC promotions without a valid exact-head record. GDC-001 followed in Codex PR #50, merged at `785977e8afc4e2596a2d82c9e0aaf2bdb18e1be1` after exact-head Authority check `124666189317` on `de7defe07c6aa0c7648e00c2fdcb129d4ecc5d5a`. This time the owner's ARB record (score 10/10, review date 2026-10-31) was merged first, in Authority PR #133; #134, #135 and #136 then attested, activated and disarmed the publication. Eleven GDC-001 controls kept their ids, mappings, classes and evidence states with rebound fingerprints. GDC-002 followed in Codex PR #51, merged at `7ead894fc19fdf72c0160e0cc2bf87420d63966e` after exact-head Authority check `125863102419` on `19988ad917a07f19aba9d19c41ee0ec5d64e4c63`; the owner's ARB record (score 9/10, review date 2026-11-03) was merged first in Authority PR #139, then #140, #141 and #142 attested, activated and disarmed the publication. GDC-003 followed in Codex PR #52, merged at `6e016957eb4ce5d883940d787952a234ff2189cc` after exact-head Authority check `126605602188` on `0c992ccdd9a961082d0ff87e4b5635a1a45ce7a0`; the owner's ARB record (score 9/10, review date 2026-11-04) was merged first in Authority PR #143, then #144, #145 and #146 attested, activated and disarmed the publication; all 19 GDC-003 control fingerprints were unchanged. GDC-004 followed in Codex PR #53, merged at `7ab674aff330eefb3f74e835f966440f8da1153a` after exact-head Authority check `129695436778` on `3e10ea381becb55b7d581a8da14872a98ec94fb0`; the owner's ARB record (score 9/10, review date 2026-11-04) was merged first in Authority PR #147, then #148, #149 and #150 attested, activated and disarmed the publication; all 10 GDC-004 control fingerprints were unchanged. GDC-005 followed in Codex PR #54, merged at `fda84648ac11937f72487c8afbd6fcc7789b5b26` after exact-head Authority check `129759956098` on `bf684b4783bf07c51bd1beacc589add94bc69883`; the owner's ARB record (score 9/10, review date 2026-11-10) was merged first in Authority PR #151, then #152, #153 and #154 attested, activated and disarmed the publication; `CTRL-GDC-005-004` and `CTRL-GDC-005-011` were rebound. GDC-006 followed in Codex PR #55, merged at `6e8236b8e715dc3296f86831644c50932b33539d` after exact-head Authority check `130464125887` on `9b5876dc90fe15173e63835b6e0a0ccfeb6b8b05`; the owner's ARB record (score 9/10, review date 2026-11-10) was merged first in Authority PR #155, then #156, #157 and #158 attested, activated and disarmed the publication; `CTRL-GDC-006-003` was rebound. GDC-007 followed in Codex PR #56, merged at `9c5f45dc218cf8ab8b96db95d42ba62eb688858a` after exact-head Authority check `130486999326` on `ab724e243dbc2c4e91729a15384c985a269f07e7`; the owner's ARB record (score 9/10, review date 2026-11-11) was merged first in Authority PR #159, then #160, #161 and #162 attested, activated and disarmed the publication; `CTRL-GDC-007-010` was rebound. GDC-008 followed in Codex PR #57, merged at `879dffb7f64c4e088c06a9da0043562105d23692` after exact-head Authority check `130581070166` on `2d3b1a5f8cc2db9012db3b9be938cd543898a73b`; the owner's ARB record (score 9/10, review date 2026-11-11) was merged first in Authority PR #163, then #164, #165 and #166 attested, activated and disarmed the publication; `CTRL-GDC-008-001` and `CTRL-GDC-008-004` were rebound. GDC-009 followed in Codex PR #58, merged at `75da9af4415ef9b4f930995e1047a241d32fc952` after exact-head Authority check `131046587442` on `229289b07077dfa4a60049e17e4da3fc2d4253e2`; the owner's ARB record (score 9/10, review date 2026-11-12) was merged first in Authority PR #167, then #168, #169 and #170 attested, activated and disarmed the publication; five GDC-009 controls were rebound. The other two required GDCs and all 29 pending roots remain separate obligations.

The unmerged GDC-010 candidate proposes `approved` / `1.0.0` and corrects the document to the ADR schema, the ADR validator, the waiver audit and the relationship and lifecycle contracts: the real validator path and checks, no automated immutability check, the waiver audit and its expiry timing, filename examples that match the schema, the metadata table, and a "Current automation" note. `CTRL-GDC-010-003`, `-004` and `-011` keep their ids, classes and evidence states with rebound statements and fingerprints. The author-proposed score sheet is not approval evidence: the owner's exact-head ARB record must be merged in Authority before the permit.

---

# 7. PHASE 14 — ARCHITECTURE RE-ADMISSION

**Status: BLOCKED**

Consumer repository: `scnehaux/codex-architecture`

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
Phase 10 Stabilization + scoped reference-provider acceptance  DONE
→ Phase 11 Slices 11.1-11.5                                    DONE
-> Slice 11.6 Provenance-Bound Repository Ingestion             DONE
-> Slice 11.7 ValidatedRepositorySnapshot                      DONE
-> Slice 11.8 Framework Extension / Company Pack Model          DONE
-> Slice 11.9 Compatibility & Versioning                       DONE
→ Phase 12 Reproducibility                                    DONE
→ Phase 13 Governance 1.0                                     ACTIVE
-> REC-13-001..003 owner decisions                             ACCEPTED (2026-10-05)
-> Slice 13.1 Root-of-Trust Release Classification            DONE (#46)
-> Slice 13.4 Release Metadata Binding                         DONE (#47)
-> Slice 13.5 Stable GDC Baseline: GDC-000                     DONE (#48)
-> Slice 13.5 Stable GDC Baseline: GDC-001                     DONE (#50)
-> Slice 13.5 Stable GDC Baseline: GDC-002                     DONE (#51)
-> Slice 13.5 Stable GDC Baseline: GDC-003                     DONE (#52)
-> Slice 13.5 Stable GDC Baseline: GDC-004                     DONE (#53)
-> Slice 13.5 Stable GDC Baseline: GDC-005                     DONE (#54)
-> Slice 13.5 Stable GDC Baseline: GDC-006                     DONE (#55)
-> Slice 13.5 Stable GDC Baseline: GDC-007                     DONE (#56)
-> Slice 13.5 Stable GDC Baseline: GDC-008                     DONE (#57)
-> Slice 13.5 Stable GDC Baseline: GDC-009                     DONE (#58)
-> Slice 13.5 Stable GDC Baseline: GDC-010 owner ARB review     NEXT
→ Phase 14 Architecture Re-Admission                          BLOCKED
```

This critical path is the authoritative sequencing until new observed evidence changes it

<!-- PHASE-STATUS:START -->

## Execution Status

- Genesis Integrity — DONE/CLOSED
- Phase 10 SCM Enforcement and Stabilization — DONE, scoped reference-provider acceptance
- Phase 11 Executable Framework & Declarative Semantic Authority — DONE, Slices 11.1-11.9 governed and merged
- Phase 12 Reproducibility and Supply-Chain Closure — DONE
- Phase 13 Governance 1.0 — ACTIVE / NOT READY
- Phase 14 Architecture Re-Admission — BLOCKED

<!-- PHASE-STATUS:END -->
