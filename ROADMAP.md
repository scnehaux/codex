# Scnehaux Codex Governance Roadmap

## 0. Document Purpose

This roadmap is the authoritative progress ledger for rebuilding the Scnehaux Architecture Governance Control Plane in `scnehaux/codex`

It exists to prevent the clean Codex repository from inheriting hidden defects from the legacy `anshacerbia2/scnehaux-architecture` estate

This document tracks:

- what is already complete
- what is only partially complete
- what has not started
- what is intentionally blocked
- what must be true before Genesis
- what must be true before architecture admission opens

This roadmap describes the state **before the previously generated Phase 5 script is executed**

The previous `phase5_semantic_foundation.py` is therefore **SUPERSEDED / DO NOT RUN** until a replacement implementation is generated from this roadmap

---

## 1. Status Legend

| Status        | Meaning                                                           |
| ------------- | ----------------------------------------------------------------- |
| `DONE`        | Implemented, tested, and currently proven by canonical gates      |
| `PARTIAL`     | Some controls exist, but the full invariant is not yet closed     |
| `NOT STARTED` | Identified but not implemented in Codex                           |
| `BLOCKED`     | Must wait for an earlier dependency or repository lifecycle event |
| `SUPERSEDED`  | Previous implementation plan or script must not be used           |

---

## 2. Current Verified Baseline

Current verified Codex state before Phase 5:

- Governance-only canonical repository exists
- Legacy provenance is pinned
- Architecture artifact admission is closed
- GDC baseline is `draft / 0.0.x`
- GDC drafts receive full validation
- Tech Radar usage is fail closed when technologies are declared
- Generic filename/suffix lint bypasses were removed
- Crawler ignore behavior is path aware
- Reserved `EXAMPLE` references no longer create lint noise
- `jsonschema.RefResolver` deprecation was removed
- Known dead `_resolve_base_ref` and unreachable CLI branch were deleted
- Per-file engine coverage hard gate is active
- Every currently governed `engine/**/*.py` file is at least 95% covered
- Aggregate engine coverage is above 95%
- Canonical linter produces zero warnings and zero failures
- Architecture artifact directories remain intentionally absent

Current repository authority state:

```text
Governance Control Plane lifecycle : draft / 0.0.x
Architecture admission             : CLOSED
Genesis commit                     : NOT YET CREATED
Stable governance baseline         : NOT YET REACHED
Architecture re-admission          : BLOCKED
```

---

# 3. P0 MASTER LEDGER

All P0 items below must be resolved or explicitly proven non-applicable before the Governance Control Plane can be considered trustworthy

## P0-A — Lifecycle, Validation, and Admission Semantics

| ID     | Defect / Risk                                                           | Target Invariant                                                        | Status | Current Evidence / Gap                                                                                                                   |
| ------ | ----------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| P0-A01 | Lifecycle state was used as validation policy                           | `Lifecycle State != Validation Profile != Admission Authority`          | `DONE` | GDC full-validation and architecture admission are separated, but ordinary artifact relaxation still derives from global exempt statuses |
| P0-A02 | `draft` can globally short-circuit validation                           | Relaxation must be artifact-aware and rule-aware                        | `DONE` | GDC draft is fixed; general model still needs replacement                                                                                |
| P0-A03 | `deprecated` is configured as exempt/relaxed                            | Retired artifacts remain full-validation baseline history               | `DONE` | Must remove `deprecated` from relaxed/exempt semantics                                                                                   |
| P0-A04 | ADR `accepted` is absent from generic baseline classifier               | Baseline classification must be artifact-type-aware                     | `DONE` | Current baseline helper is not complete                                                                                                  |
| P0-A05 | GDC draft could previously bypass governance                            | GDC draft always receives full validation                               | `DONE` | Phase 2 regression tests prove this                                                                                                      |
| P0-A06 | Architecture could be admitted before stable governance                 | Admission is closed until declared GDC baseline is approved and >=1.0.0 | `DONE` | `governance_auditor` + bootstrap manifest                                                                                                |
| P0-A07 | Genesis repository event was conflated with document approval           | Genesis admission and GDC approval are independent                      | `DONE` | Current bootstrap model uses draft/0.x GDCs                                                                                              |
| P0-A08 | Baseline authority is inferred from literal strings                     | Shared semantic states: pre-baseline, baseline-bearing, retired         | `DONE` | Needs Lifecycle Registry                                                                                                                 |
| P0-A09 | Validation relaxation can accidentally apply to baseline-bearing states | Only explicitly eligible pre-baseline states may relax                  | `DONE` | Needs explicit Validation Profile Registry                                                                                               |
| P0-A10 | Lifecycle age rules and validation strictness are coupled               | Age policy runs independently from validation profile                   | `DONE` | Current `exempt_statuses` mixes both concepts                                                                                            |

### P0-A Completion Evidence

Verified after Slice 5.1:

- 215/215 tests passed
- every currently governed `engine/**/*.py` file satisfied the >=95% per-file coverage gate
- aggregate engine coverage was 97.76%
- 12/12 GDC documents passed canonical lint
- warnings: 0
- failures: 0
- GDC draft uses full validation
- lifecycle age policy is artifact-aware
- ordinary architecture drafts retain the explicit 30-day WIP age policy
- GDC draft has no generic WIP TTL
- deprecated/superseded baseline history has no generic deletion TTL
- ADR accepted/superseded baseline semantics are artifact-aware
- architecture admission remains closed

### P0-A Exit Criteria

- Global `exempt_statuses` no longer determines validation strictness
- Artifact-specific literal states map into shared semantic lifecycle classes
- ADR `accepted` is baseline-bearing
- `deprecated` remains fully validated
- GDC draft remains fully validated
- Age/retirement policy remains enforceable without bypassing validation
- No duplicate baseline-status hardcoding remains

---

## P0-B — Normative Policy Coverage

| ID     | Defect / Risk                                                      | Target Invariant                                             | Status        | Current Evidence / Gap                                        |
| ------ | ------------------------------------------------------------------ | ------------------------------------------------------------ | ------------- | ------------------------------------------------------------- |
| P0-B01 | A GDC `MUST` can exist only as prose                               | Every critical normative rule has a stable Control ID        | `NOT STARTED` | No Normative Control Registry                                 |
| P0-B02 | Code coverage can be high while policy coverage is zero            | Policy coverage is measured independently from test coverage | `NOT STARTED` | No policy-to-control metric                                   |
| P0-B03 | EAD implementation-agnostic rule is documented but not executed    | EAD semantic boundary is machine-enforced                    | `NOT STARTED` | `EADValidator` remains effectively no-op                      |
| P0-B04 | Type-specific validator may exist but implement nothing            | Normative artifact validators cannot silently be no-op       | `NOT STARTED` | Needs registry/control audit                                  |
| P0-B05 | A severity entry can imply enforcement that does not exist         | Every blocking rule maps to executable implementation        | `NOT STARTED` | Severity integrity currently checks names, not implementation |
| P0-B06 | Tests can cover helpers without proving the documented rule        | Control Registry records direct test evidence                | `NOT STARTED` | Needs control → implementation → test mapping                 |
| P0-B07 | Governance prose can describe behavior the engine does not perform | Engine self-documentation must match executable behavior     | `NOT STARTED` | Needs control/evidence reconciliation                         |

### P0-B Exit Criteria

Every P0 `MUST` has:

```text
control_id
source_gdc
source_clause
modality
artifact_scope
enforcement_mode
severity
implementation
test_evidence
```

A blocking `MUST` without implementation or test evidence fails repository validation

---

## P0-C — Relationship and Graph Integrity

| ID     | Defect / Risk                                                               | Target Invariant                                                   | Status        | Current Evidence / Gap                                              |
| ------ | --------------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------- | ------------------------------------------------------------------- |
| P0-C01 | Relationship vocabulary is duplicated across validators/auditors/generators | One Relationship Registry is the SSOT                              | `DONE`        | `parent_pad`, `governed_by`, `fulfilled_by`, etc. remain duplicated |
| P0-C02 | Existing reference is validated mostly by ID existence                      | Relationship target type must also be valid                        | `DONE`        | `SAD.parent_pad -> PAD` not centrally enforced                      |
| P0-C03 | Relationship source type is not centrally enforced                          | Invalid relationship field on wrong artifact type fails            | `DONE`        | Needs registry                                                      |
| P0-C04 | Cardinality is spread across schemas                                        | Cardinality belongs to relationship ontology                       | `DONE`        | Needs registry                                                      |
| P0-C05 | DAG participation is hardcoded separately                                   | DAG semantics consume the same registry                            | `DONE`        | `graph_auditor` still has its own tuple                             |
| P0-C06 | Inverse relationships can drift                                             | Declared inverse edges reconcile                                   | `NOT STARTED` | Example: PAD `fulfilled_by` vs SAD `parent_pad`                     |
| P0-C07 | A referenced artifact may exist but be non-authoritative                    | Relationship policy can require authoritative target lifecycle     | `DONE`        | Needs lifecycle + relationship integration                          |
| P0-C08 | Example IDs can accidentally enter real graph semantics                     | Reserved `EXAMPLE` namespace never resolves as architecture estate | `DONE`        | Current lint is zero-noise                                          |
| P0-C09 | Graph generator and graph auditor can interpret different ontology          | Both must consume one registry/model                               | `NOT STARTED` | Requires RepositoryModel work                                       |

### P0-C Relationship Ontology Foundation Evidence

Verified after Slice 5.4:

- 296/296 tests passed
- every currently governed `engine/**/*.py` file satisfied the >=95% per-file coverage gate
- aggregate engine coverage was 98.08%
- `engine/auditors/graph_auditor.py` coverage was 100%
- `engine/governance/relationships.py` coverage was 99%
- 12/12 GDC documents passed canonical lint
- warnings: 0
- failures: 0
- one executable Relationship Registry owns typed relationship semantics
- source artifact types are explicit
- target artifact types are explicit
- cardinality is explicit
- direction and DAG participation are explicit
- target lifecycle authority is explicit
- `fulfilled_by` declares `parent_pad` as its inverse without participating in DAG cycle detection
- legacy `UPWARD_EDGE_FIELDS` and `cross_ref_fields` semantic hardcodes are removed
- `GDC-000` explicitly self-governs while preserving its existing governance authorities
- inverse reconciliation remains intentionally deferred to P0-C06 / Slice 5.7
- graph generator/auditor ontology reconciliation remains intentionally deferred to P0-C09 / Slice 5.7
- architecture admission remains closed

### P0-C Exit Criteria

- One declarative relationship authority
- Source type, target type, cardinality, direction, DAG participation, authority requirement, and inverse relation are declared once
- Metadata validator, graph auditor, orphan audit, traceability generator, and future indexes consume the same semantics

---

## P0-D — Temporal Integrity

| ID     | Defect / Risk                                                   | Target Invariant                                                   | Status | Current Evidence / Gap                                          |
| ------ | --------------------------------------------------------------- | ------------------------------------------------------------------ | ------ | --------------------------------------------------------------- |
| P0-D01 | JSON Schema `format: date` may be annotation-only               | ISO date validation is executable                                  | `DONE` | Current Phase 5 script was intended to fix this but has not run |
| P0-D02 | Invalid date can bypass age validation                          | Invalid governed date is a blocking finding                        | `DONE` | Needs explicit temporal validator                               |
| P0-D03 | Future `created_date` can produce negative age and pass         | Future governance dates fail                                       | `DONE` | No future-date guard                                            |
| P0-D04 | Future `last_reviewed` can appear fresh indefinitely            | Future review dates fail                                           | `DONE` | No future-date guard                                            |
| P0-D05 | Temporal ordering is not guaranteed                             | `created_date <= last_updated` and `created_date <= last_reviewed` | `DONE` | Needs explicit ordering                                         |
| P0-D06 | Governance uses ambient local clock                             | Evaluation date must be deterministic/injectable                   | `DONE` | Current `date.today()` remains                                  |
| P0-D07 | `review_cycle_days` lacks bounded governance semantics          | Review cycles have rational min/max bounds                         | `DONE` | Schema only checks integer today                                |
| P0-D08 | Age validation and date parsing have separate failure semantics | Temporal validation has one fail-closed authority                  | `DONE` | Needs consolidation                                             |

### P0-D Completion Evidence

Verified after Slice 5.2:

- 240/240 tests passed
- every currently governed `engine/**/*.py` file satisfied the >=95% per-file coverage gate
- aggregate engine coverage was 97.83%
- `engine/governance/temporal.py` coverage was 100%
- 12/12 GDC documents passed canonical lint
- warnings: 0
- failures: 0
- governed date strings use canonical `YYYY-MM-DD`
- JSON Schema `format: date` is executable through `FormatChecker`
- invalid calendar dates fail validation
- future `created_date`, `last_updated`, and `last_reviewed` are blocking violations
- `created_date <= last_updated` is enforced when both are present
- `created_date <= last_reviewed` is enforced when both are present
- deterministic evaluation clock is available through `SCNEHAUX_EVALUATION_DATE`
- lifecycle-age and review-age calculations use the shared evaluation clock
- `review_cycle_days` is bounded to 1..3650
- architecture admission remains closed

### P0-D Exit Criteria

- Invalid dates fail closed
- Future dates fail closed
- Temporal ordering is enforced
- Evaluation date can be injected in tests/CI
- Review-cycle bounds are explicit
- No negative-age bypass remains

---

## P0-E — Classification and Repository Boundary

| ID     | Defect / Risk                                                | Target Invariant                                                      | Status | Current Evidence / Gap                      |
| ------ | ------------------------------------------------------------ | --------------------------------------------------------------------- | ------ | ------------------------------------------- |
| P0-E01 | `classification` is currently only metadata                  | Classification must correspond to actual repository confidentiality   | `DONE` | No repository visibility rule               |
| P0-E02 | Public repository may contain `classification: internal`     | Public Codex admits only public governed material                     | `DONE` | Current copied GDC metadata must be audited |
| P0-E03 | Schema allows `restricted` / `confidential` in a public repo | Non-public material must use a controlled private architecture estate | `DONE` | Boundary not modeled                        |
| P0-E04 | Classification can create false security confidence          | Metadata must never claim protection infrastructure does not provide  | `DONE` | Needs repository policy                     |
| P0-E05 | Future repository split may drift                            | Public/private estate policy must be explicit                         | `DONE` | Design required                             |

### P0-E Completion Evidence

Verified after Slice 5.3:

- 260/260 tests passed
- every currently governed `engine/**/*.py` file satisfied the >=95% per-file coverage gate
- aggregate engine coverage was 97.92%
- `engine/governance/classification.py` coverage was 100%
- 12/12 GDC documents passed canonical lint
- warnings: 0
- failures: 0
- canonical repository `scnehaux/codex` is declared `public`
- public repository storage permits only `classification: public`
- `internal`, `restricted`, and `confidential` artifacts require an approved non-public estate
- repository visibility mismatch is a CRITICAL governance violation
- classification metadata cannot imply confidentiality not provided by repository visibility
- all bootstrap GDCs are normalized to `classification: public`
- architecture admission remains closed

### P0-E Exit Criteria

Public Codex:

```text
repository visibility = public
governed artifact classification = public only
```

Non-public architecture requires a separate controlled estate

---

## P0-F — Schema, Validator, and Registry Integrity

| ID     | Defect / Risk                                                                | Target Invariant                                              | Status        | Current Evidence / Gap                                        |
| ------ | ---------------------------------------------------------------------------- | ------------------------------------------------------------- | ------------- | ------------------------------------------------------------- |
| P0-F01 | A schema may be broken but never loaded because no instance exists           | All schemas are validated at control-plane boot               | `NOT STARTED` | Zero-corpus schema audit absent                               |
| P0-F02 | `$ref` failure may remain latent                                             | Every `$ref` resolves before artifact lint                    | `NOT STARTED` | Registry audit absent                                         |
| P0-F03 | Schema and validator registries can drift                                    | One artifact type has exactly one schema + validator contract | `NOT STARTED` | Bijection audit absent                                        |
| P0-F04 | Orphan schema can silently exist                                             | Orphan schemas fail                                           | `NOT STARTED` | Not implemented                                               |
| P0-F05 | Orphan validator can silently exist                                          | Orphan validators fail                                        | `NOT STARTED` | Not implemented                                               |
| P0-F06 | Duplicate artifact registration can silently shadow behavior                 | Duplicate registrations fail                                  | `NOT STARTED` | Not implemented                                               |
| P0-F07 | `config.target_doc` may drift from guideline                                 | Schema → guideline mapping is validated                       | `PARTIAL`     | Phase 2 injected target docs, but no global integrity auditor |
| P0-F08 | Custom schema keywords can exist without registered handlers                 | Custom keyword registry is validated                          | `NOT STARTED` | Not implemented                                               |
| P0-F09 | Severity name integrity exists but control implementation integrity does not | Severity, control, schema, validator registries reconcile     | `PARTIAL`     | Severity schema checks already exist                          |

### P0-F Exit Criteria

Control-plane bootstrap validates every registry with zero architecture artifacts present

---

## P0-G — RepositoryModel, Generators, and Zero-Corpus Operation

| ID     | Defect / Risk                                                           | Target Invariant                                     | Status        | Current Evidence / Gap                     |
| ------ | ----------------------------------------------------------------------- | ---------------------------------------------------- | ------------- | ------------------------------------------ |
| P0-G01 | Generators parse Markdown independently                                 | One canonical parser feeds one RepositoryModel       | `NOT STARTED` | Legacy parser duplication still copied     |
| P0-G02 | Generator can swallow malformed frontmatter                             | Malformed governed input fails generation            | `NOT STARTED` | Fail-open generator paths remain           |
| P0-G03 | Generator can catch exception, print, and continue                      | Governance-critical generation error exits non-zero  | `NOT STARTED` | Not fixed                                  |
| P0-G04 | `verify-generated` can trust failed generation                          | Reconciliation only runs after successful generation | `NOT STARTED` | Not fixed                                  |
| P0-G05 | ADR index assumes `05-decisions` exists                                 | Zero architecture corpus is valid                    | `NOT STARTED` | Generator not bootstrap-safe               |
| P0-G06 | PAD/SAD index assumes `03/04` exists                                    | Zero architecture corpus is valid                    | `NOT STARTED` | Generator not bootstrap-safe               |
| P0-G07 | Traceability generator assumes architecture layer exists                | Zero architecture corpus is valid                    | `NOT STARTED` | Generator not bootstrap-safe               |
| P0-G08 | Generated state can be partially written                                | Generate → validate → atomic replace                 | `NOT STARTED` | Transactional generation absent            |
| P0-G09 | Maturity dashboard can hardcode healthy status                          | Derived telemetry must be evidence-based             | `NOT STARTED` | MATURITY intentionally not copied          |
| P0-G10 | Ambient Git index can affect generator output                           | Generator tests are deterministic                    | `DONE`        | Engine topography determinism was fixed    |
| P0-G11 | Architecture admission closed but generators assume architecture estate | All governance tools support governance-only mode    | `NOT STARTED` | Full zero-corpus integration suite missing |

### P0-G Exit Criteria

`make`/canonical equivalent can operate safely before any `01–05` architecture estate exists

---

## P0-H — Governance-Critical Test Integrity

| ID     | Defect / Risk                                                    | Target Invariant                                     | Status                  | Current Evidence / Gap                               |
| ------ | ---------------------------------------------------------------- | ---------------------------------------------------- | ----------------------- | ---------------------------------------------------- |
| P0-H01 | Aggregate coverage can hide weak critical files                  | >=95% per governed production file                   | `DONE`                  | Hard pytest gate active for `engine/**/*.py`         |
| P0-H02 | Test environment previously masked broken production imports     | Test import topology must match production           | `DONE`                  | Current Python path matches package root             |
| P0-H03 | Coverage-only tests can exercise dead code                       | Dead code is deleted instead                         | `DONE`                  | `_resolve_base_ref` test/code removed                |
| P0-H04 | Unreachable defensive branches can remain to inflate denominator | Proven unreachable code is deleted/refactored        | `DONE` for known branch | CLI dead relpath branch removed                      |
| P0-H05 | Coverage scope only includes `engine/`                           | All governance-critical Python code is governed      | `PARTIAL`               | Generators/scripts are outside current per-file gate |
| P0-H06 | Governance-critical generators are ungoverned by coverage        | Canonical generators >=95% each                      | `NOT STARTED`           | Coverage expansion required                          |
| P0-H07 | Governance-critical scripts are ungoverned by coverage           | CI/security/waiver/bootstrap scripts >=95% each      | `NOT STARTED`           | Coverage expansion required                          |
| P0-H08 | Collection failure produced misleading coverage output           | Primary collection failure must remain authoritative | `DONE`                  | Collection-safe coverage hook fixed                  |
| P0-H09 | No adversarial malformed-repository integration corpus           | Critical fail-closed paths need hostile fixtures     | `NOT STARTED`           | Add in Phase 5/6                                     |

### P0-H Exit Criteria

All governance-critical Python production paths—not only `engine/`—have honest per-file coverage >=95%

---

## P0-I — Technology Policy Availability

| ID     | Defect / Risk                                                                | Target Invariant                                         | Status        | Current Evidence / Gap                   |
| ------ | ---------------------------------------------------------------------------- | -------------------------------------------------------- | ------------- | ---------------------------------------- |
| P0-I01 | Missing Tech Radar previously allowed technology validation to silently pass | Technologies declared + radar missing = blocking failure | `DONE`        | Phase 4 predecessor hardening            |
| P0-I02 | Malformed Tech Radar previously silently passed                              | Malformed/unreadable radar = blocking failure            | `DONE`        | Regression tests exist                   |
| P0-I03 | No technology declared should not require radar                              | Zero-technology governance bootstrap remains valid       | `DONE`        | Current behavior                         |
| P0-I04 | Tech Radar lifecycle vocabulary can drift                                    | Machine lifecycle vocabulary has one authority           | `NOT STARTED` | P1 semantic normalization still required |

---

## P0-J — Genesis Integrity and Root of Trust

| ID     | Defect / Risk                                             | Target Invariant                                                | Status        | Current Evidence / Gap                                                   |
| ------ | --------------------------------------------------------- | --------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------ |
| P0-J01 | Genesis provenance could be informal                      | Source repository + immutable source SHA are declared           | `DONE`        | Bootstrap manifest contains legacy SHA                                   |
| P0-J02 | Genesis allowed/forbidden paths could be informal         | Manifest explicitly declares both                               | `DONE`        | Bootstrap manifest exists                                                |
| P0-J03 | Static manifest can drift or become malformed             | Manifest integrity is executable                                | `PARTIAL`     | Architecture admission consumes manifest; full genesis validation absent |
| P0-J04 | First root commit can contain forbidden paths             | Root commit contents must be audited                            | `NOT STARTED` | No root integrity auditor                                                |
| P0-J05 | Repository could accidentally gain multiple roots         | Exactly one root commit                                         | `BLOCKED`     | Requires Genesis commit to exist                                         |
| P0-J06 | Genesis exception could be reused later                   | Genesis exception expires permanently after root commit         | `BLOCKED`     | Requires post-Genesis audit                                              |
| P0-J07 | Root manifest could mutate after Genesis                  | Genesis provenance must remain immutable or explicitly migrated | `BLOCKED`     | Requires committed root                                                  |
| P0-J08 | Architecture directories could enter Genesis              | `01–05` forbidden in root                                       | `PARTIAL`     | Manifest forbids them but root history not yet testable                  |
| P0-J09 | Support metadata could fall outside allowed root contract | All intended root support files must be explicit                | `PARTIAL`     | ROADMAP/PLAN not yet in repo because new script not run                  |

### P0-J Exit Criteria

Before Genesis:

- manifest statically valid
- intended root contents exactly match allowed contract
- architecture estate absent

After Genesis:

- exactly one root commit
- root contents verified
- root provenance verified
- Genesis exception structurally exhausted

---

## P0-K — Version and Mutation Enforcement

| ID     | Defect / Risk                                                       | Target Invariant                                                  | Status        | Current Evidence / Gap              |
| ------ | ------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------- | ----------------------------------- |
| P0-K01 | `audit_version_bump()` is intentionally no-op                       | Version mutation policy becomes executable before stable baseline | `NOT STARTED` | Live seam exists, no implementation |
| P0-K02 | Old implementation assumed `approved` only                          | Mutation policy must be artifact/lifecycle aware                  | `NOT STARTED` | ADR `accepted` etc. not covered     |
| P0-K03 | Any modification was treated similarly                              | Mutation classifier distinguishes patch/minor/major semantics     | `NOT STARTED` | Design required                     |
| P0-K04 | Pre-1.0 version semantics are not explicit enough                   | Scnehaux 0.x policy is normative and executable                   | `NOT STARTED` | Design required                     |
| P0-K05 | Stable baseline can be changed without compatibility classification | >=1.0 mutation requires compatibility-aware version bump          | `NOT STARTED` | Design required                     |
| P0-K06 | ADR immutability differs from versioned artifacts                   | ADR mutation/supersession policy is type-aware                    | `NOT STARTED` | Design required                     |

### P0-K Exit Criteria

No stable baseline artifact can change without the required mutation/version contract

---

## P0-L — Effective GitHub Enforcement

These items cannot be completed before a Genesis root exists, but the design must be prepared before architecture admission

| ID     | Defect / Risk                                           | Target Invariant                      | Status    | Current Evidence / Gap         |
| ------ | ------------------------------------------------------- | ------------------------------------- | --------- | ------------------------------ |
| P0-L01 | Governance may claim protection not actually configured | Effective GitHub state is evidence    | `BLOCKED` | Genesis not committed          |
| P0-L02 | Main direct push may remain possible                    | Direct push rejected                  | `BLOCKED` | Ruleset not installed          |
| P0-L03 | Force push may remain possible                          | Force push rejected                   | `BLOCKED` | Ruleset not installed          |
| P0-L04 | Main deletion may remain possible                       | Branch deletion rejected              | `BLOCKED` | Ruleset not installed          |
| P0-L05 | CI may not be required                                  | Governance status checks required     | `BLOCKED` | Workflow/ruleset not installed |
| P0-L06 | CODEOWNERS may be decorative                            | Required CODEOWNER approval           | `BLOCKED` | Teams/owners need verification |
| P0-L07 | Unresolved review conversations may not block           | Conversation resolution required      | `BLOCKED` | Ruleset not installed          |
| P0-L08 | Approval may remain stale after material change         | Stale approval policy verified        | `BLOCKED` | Ruleset not installed          |
| P0-L09 | Configuration can be mistaken for enforcement           | Negative tests are mandatory evidence | `BLOCKED` | Requires live GitHub controls  |

---

# 4. P0 COMPLETION SUMMARY

Current status before Phase 5 implementation:

| Domain                             | Done | Partial | Not Started | Blocked |
| ---------------------------------- | ---: | ------: | ----------: | ------: |
| Lifecycle / validation / admission |   10 |       0 |           0 |       0 |
| Normative policy coverage          |    0 |       0 |           7 |       0 |
| Relationship / graph               |    1 |       0 |           8 |       0 |
| Temporal integrity                 |    8 |       0 |           0 |       0 |
| Classification boundary            |    5 |       0 |           0 |       0 |
| Registry integrity                 |    0 |       2 |           7 |       0 |
| RepositoryModel / generators       |    1 |       0 |          10 |       0 |
| Test integrity                     |    5 |       1 |           3 |       0 |
| Technology availability            |    3 |       0 |           1 |       0 |
| Genesis integrity                  |    2 |       4 |           1 |       2 |
| Version / mutation                 |    0 |       0 |           6 |       0 |
| GitHub enforcement                 |    0 |       0 |           0 |       9 |

The table is a planning ledger, not a maturity score

A high count of `DONE` does not compensate for any unresolved root-of-trust P0

---

# 5. P1 MASTER WORKSTREAMS

P1 begins only where it does not undermine unresolved P0 work

## P1-A — Artifact Metamodel Consistency

- Resolve EAD C0 vs C1 contradiction
- Replace EAD numeric-ID semantic special cases with explicit archetype semantics
- Reconcile GDC lifecycle prose with schema vocabulary
- Remove lifecycle-specific impossible requirements such as mandatory `last_reviewed` on pre-baseline states
- Reconcile PAD `chartered` with `fulfilled_by`
- Reconcile SAD `chartered` with full design requirements
- Normalize technology lifecycle vocabulary
- Establish shared semantic classes while preserving artifact-specific literal statuses

Status: `NOT STARTED`

## P1-B — Review and Approval Model

- Separate non-waivable critical gates from quality scoring
- Replace universal rubric with common rubric + artifact overlays
- Remove `N/A = Pass`
- Recalculate denominator when a criterion is not applicable
- Prevent 9/10 scoring from masking critical security/lineage failure
- Separate quality score from approval authority

Status: `NOT STARTED`

## P1-C — Metadata Strictness

- Reject unknown governed metadata keys
- Introduce explicit extension namespaces if needed
- Prevent optional-field typos from silently becoming pseudo-metadata
- Move relationship cardinality out of duplicated schema definitions
- Use canonical SemVer parser rather than hand-maintained regex where appropriate

Status: `NOT STARTED`

## P1-D — Waiver / Exception Governance

- Collapse waiver logic into one canonical implementation
- Make scripts wrappers over the same implementation
- Fail malformed waiver frontmatter closed
- Inject deterministic evaluation time
- Model waiver renewal/supersession lineage
- Make dependent exception impact explicit

Status: `NOT STARTED`

## P1-E — Dependency and Build Reproducibility

- `pyproject.toml` becomes human-maintained dependency declaration SSOT
- Remove or generate redundant `requirements.txt`
- Generate deterministic constraints/lock artifact
- Pin build backend
- Pin governance-critical dependencies
- Remove runtime `npx --yes` dependency resolution
- Define reproducible container from current architecture

Status: `NOT STARTED`

## P1-F — CI and Supply Chain

- Pin GitHub Actions to immutable SHAs
- Replace mutable governance `main` consumption with immutable release/SHA
- Define governance release provenance
- Define compatibility metadata
- Document runner/container contract
- Ensure same policy + input + toolchain = same result

Status: `NOT STARTED`

## P1-G — Derived Telemetry and Documentation Truthfulness

- Rebuild MATURITY only from actual evidence
- Remove hardcoded PASSING/SYNCHRONIZED telemetry
- Make governance documentation describe actual engine behavior
- Reconcile generated docs against implementation
- Eliminate duplicated parser/semantic descriptions

Status: `NOT STARTED`

## P1-H — CODEOWNERS and Ownership Validity

- Verify referenced teams exist
- Verify owners have required repository permissions
- Verify team eligibility for CODEOWNERS enforcement
- Validate ownership before making it a required merge control

Status: `BLOCKED` until GitHub enforcement phase

---

# 6. EXECUTION ROADMAP

## Phase 5 — Close Semantic Root-of-Trust P0

Order:

1. P0-A Lifecycle / Validation Profile Registry
2. P0-D Temporal Integrity
3. P0-E Classification Boundary
4. P0-C Relationship Registry foundation
5. P0-B Normative Control Registry
6. P0-F Registry Integrity Auditor
7. P0-G Zero-Corpus RepositoryModel
8. P0-H Governance-Critical Coverage Expansion

Genesis remains NO-GO throughout Phase 5

## Phase 6 — Genesis Integrity

Close P0-J pre-Genesis requirements

Only after static Genesis acceptance is clean may the root commit be created

## Phase 7 — Version and Mutation Governance

Close P0-K before any stable governance release

## Phase 8 — Reproducibility and Supply Chain

Close P1-E, P1-F, remaining zero-corpus generator concerns

## Phase 9 — GitHub Enforcement

Close P0-L and P1-H immediately after Genesis root exists

## Phase 10 — Governance Stable Release

Required GDC baseline:

```text
status = approved
version >= 1.0.0
```

Only after:

- all root-of-trust P0 are closed
- required repository controls have effective evidence
- reproducible governance release exists
- version mutation enforcement is live

## Phase 11 — Architecture Re-Admission

No bulk copy from legacy

Re-admission order:

1. EAD
2. STD
3. PAD
4. SAD
5. ADR / TDD according to truthful lineage

---

# 7. GENESIS GO / NO-GO

## Genesis NO-GO while any of these remain

- Lifecycle/validation/admission semantics unresolved
- Policy coverage absent for root-of-trust MUST controls
- Temporal integrity fail-open
- Public classification boundary unenforced
- Schema/validator registry integrity unaudited
- Zero-corpus governance execution unsupported
- Bootstrap manifest statically unaudited
- Governance-critical coverage below policy
- Known dead governance-critical production code exists
- Canonical lint has warning/failure
- Architecture artifact estate is present

## Genesis may proceed only when

- All **pre-Genesis P0** items are `DONE`
- Items inherently requiring a committed root are explicitly `BLOCKED POST-GENESIS`, not silently ignored
- Canonical tests pass
- Per-file coverage gate passes
- Aggregate coverage gate passes
- Canonical linter reports 0 warning / 0 failure
- `git diff` contains only intended Genesis root-of-trust assets

---

# 8. ARCHITECTURE ADMISSION GO / NO-GO

Architecture admission remains closed until:

- Required GDC baseline IDs are approved
- Required GDC baseline versions are >=1.0.0
- Version mutation control is live
- Genesis integrity is proven
- GitHub protection is proven by negative tests
- Governance release is immutable and reproducible
- Policy coverage has no unresolved P0
- Waiver path is fail closed

Only then:

`architecture_admission: closed -> open`

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

<!-- P0-B-STATUS:START -->

### P0-B — Normative Policy Coverage

- B01 stable Control IDs for GDC MUST — DONE
- B02 policy coverage independent from code coverage — DONE
- B03 EAD implementation-agnostic machine-enforced — DONE
- B04 no silent no-op normative validators — DONE
- B05 severity implies real enforcement — OPEN, owned by Slice 5.6 Registry Integrity Auditor
- B06 control → test evidence — DONE for automated verified controls; unresolved controls remain explicitly pending
- B07 docs vs executable behavior reconciliation — PARTIAL, pending controls continue in their owning phases

<!-- P0-B-STATUS:END -->

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

<!-- SCNEHAUX-AI-NATIVE-ROADMAP-REBASELINE -->

# AI-Native Framework Roadmap Rebaseline

> This section supersedes the forward roadmap from Phase 6 onward
> Earlier completed phases remain historical fact and are not rewritten

## Product Direction

Scnehaux is no longer framed as a documentation-governance framework

Scnehaux is an **AI-Native Architecture Knowledge & Control Plane** that transforms:

```text
business/product intent
+ organization architecture knowledge
+ governing constraints
+ observed technology state
```

into:

```text
structured architecture proposals
+ deterministic validation
+ graph-aware impact analysis
+ governed architecture artifacts
+ explainable Git history
```

The canonical authority remains Git-backed structured architecture knowledge

Graph stores, vector stores, and LLM providers are replaceable projections or reasoning substrates

## Roadmap Status

```text
PHASE 1   Genesis Contract                         CLOSED
PHASE 2   Lifecycle + Admission                    CLOSED
PHASE 3   Namespace / Validation Foundation        CLOSED
PHASE 4   Governance Hardening                     CLOSED
PHASE 5   Executable Governance Control Plane      CLOSED

PHASE 6   Architecture Knowledge Model Rebaseline  CURRENT
PHASE 7   Genesis Integrity
PHASE 8   Version + Mutation
PHASE 9   Governance P1 Hardening

--------- GENESIS ROOT COMMIT ---------

PHASE 10  Effective GitHub Enforcement
PHASE 11  Governance 1.0

PHASE 12  Architecture Knowledge Runtime
PHASE 13  AI Architecture Harness
PHASE 14  Observed Architecture + Drift
PHASE 15  AI-Assisted Architecture Re-admission
```

## Phase 6 — Architecture Knowledge Model Rebaseline

Purpose:

> Define the stable semantic contracts required for Scnehaux to become a reusable,
> AI-native architecture framework without coupling Genesis to any graph database,
> vector database, model provider, or agent framework

### 6.1 Framework Product Boundary

Define:

- what Scnehaux owns
- what Scnehaux integrates with
- what remains commodity infrastructure
- framework vs company-specific responsibility
- canonical authority boundaries

### 6.2 Capability + Logical Module Map

Define logical modules without forcing service decomposition:

```text
scnehaux-core
scnehaux-control
scnehaux-knowledge
scnehaux-ai
scnehaux-observe
scnehaux-interface
```

Default implementation remains modular-monolith compatible

### 6.3 Artifact Metamodel

Introduce canonical typed representations for:

```text
Artifact
ArtifactIdentity
ArtifactType
ArtifactLifecycle
ArtifactRelationship
ArtifactSection
ArtifactEvidence
ArtifactSource
ArtifactProvenance
```

Artifact semantics MUST NOT be inferred from prose when structured state exists

### 6.4 Semantic Parsing Boundary

Audit production regex/text inference

Rule:

> Regex MUST NOT infer structured or semantic architecture state when a canonical parser/model exists

Regex remains valid only for bounded lexical concerns such as identifier and filename syntax

### 6.5 ArchitectureGraph IR

Define vendor-neutral graph representation:

```text
ArchitectureNode
ArchitectureEdge
NodeType
RelationshipType
Provenance
KnowledgeState
```

Required knowledge states:

```text
DECLARED
OBSERVED
INFERRED
PROPOSED
```

### 6.6 Deterministic Graph Compiler

```text
RepositoryModel
      ↓
ArchitectureGraph
```

Same canonical repository state MUST produce the same graph

LLMs MUST NOT invent canonical graph edges

### 6.7 ContextPackage Contract

Define the model-independent AI context payload:

```text
Task
OrganizationContext
TargetArchitecture
RelevantArtifacts
GraphNeighborhood
GoverningControls
ObservedContext
Conflicts
Assumptions
Sources
TokenBudget
```

### 6.8 ArtifactDraft + Deterministic Renderer

AI authoring MUST target a typed structured draft rather than free-form Markdown

```text
AI
 ↓
ArtifactDraft<T>
 ↓
deterministic validation
 ↓
deterministic renderer
 ↓
Markdown projection
```

### 6.9 Round-Trip + Graph Simulation

Required invariant:

```text
ArtifactDraft
    ↓ render
Markdown
    ↓ parse
ArtifactModel

semantic_state(ArtifactDraft) == semantic_state(ArtifactModel)
```

Proposed artifacts MUST be graph-simulated before admission for invalid relationships,
cycles where prohibited, lifecycle violations, missing mandatory edges, and conflicts

### 6.10 Temporary Tool Reconciliation

Every temporary migration/probe script MUST be classified:

```text
ongoing invariant
    → permanent implementation + permanent test/gate

migration-only / discovery-only
    → delete before Genesis
```

## Phase 6 Exit Criteria

Phase 6 closes only when:

- Scnehaux framework boundary is explicit
- logical module boundaries are explicit
- artifact metamodel is canonical
- semantic parsing no longer depends on regex pseudo-parsing
- ArchitectureGraph IR exists
- deterministic graph compilation is proven
- knowledge provenance states exist
- ContextPackage contract exists
- ArtifactDraft contract exists
- deterministic rendering contract exists
- round-trip semantic equivalence is proven
- graph simulation contract exists
- temporary tooling has been reconciled
- no official EAD/PAD/SAD/TDD/ADR artifact is admitted while architecture admission is CLOSED

## Later Runtime Phases

### Phase 12 — Architecture Knowledge Runtime

Add replaceable runtime adapters:

- exact identifier lookup
- graph traversal
- full-text retrieval
- semantic/vector retrieval
- hybrid retrieval router
- context assembler
- graph-store adapter
- semantic-index adapter

### Phase 13 — AI Architecture Harness

Add:

- intent planner
- architecture planner
- artifact planning
- architecture Q&A
- impact analysis
- structured artifact generation
- validation/revision loop
- graph simulation
- PR proposal generation
- replaceable model gateway

### Phase 14 — Observed Architecture + Drift

Add observed-state adapters for:

- source AST
- OpenAPI / AsyncAPI / Protobuf
- IaC
- deployment descriptors
- database schemas
- runtime topology
- telemetry

Reconcile:

```text
DECLARED architecture
        vs
OBSERVED implementation
        ↓
architecture drift
```

### Phase 15 — AI-Assisted Architecture Re-admission

Use the mature framework to re-admit Scnehaux architecture itself and later organization architecture

Scnehaux becomes its own first reference implementation

<!-- SCNEHAUX-AI-NATIVE-COMPATIBILITY-RECONCILIATION -->

## Phase 6 Roadmap Correction

Phase 6.4–6.6 established semantic parsing and initial graph foundations.

Before Phase 6.7 begins, an explicit compatibility reconciliation is inserted.

```text
6.1  Framework Product Boundary                 DONE
6.2  Capability + Logical Module Map            DONE
6.3  Artifact Metamodel                         DONE
6.4  Semantic Parsing Boundary                  DONE
6.5  Initial Architecture Graph IR              DONE
6.6  Deterministic Graph Compiler               DONE

6.6A AI-Native Compatibility Reconciliation     CURRENT

6.7  Knowledge Provenance + ContextPackage
6.8  ArtifactDraft Contract
6.9  Deterministic Renderer + Graph Simulation
6.10 Temporary Tool Reconciliation
```

### Phase 6.6A Scope

#### A. Canonical model authority

Reconcile:

```text
ArtifactModel
RepositoryModel
```

Target:

```text
ArtifactModel = artifact semantic authority
RepositoryModel = immutable repository snapshot of ArtifactModel
```

No split-brain semantic model is permitted.

#### B. Graph generalization

Replace artifact-only graph assumptions with a vendor-neutral knowledge graph IR.

Target node categories include both architecture artifacts and domain knowledge such as capabilities, platforms, systems, technologies, controls, teams, and observed resources.

#### C. External reference contract

Introduce explicit resolvable reference semantics for:

```text
local repository references
cross-repository references
cross-organization references
observed-source references
```

Unresolved references remain fail-closed.

#### D. Profile-driven governance

Move repository-specific assumptions out of framework-core semantics, including:

```text
required baseline GDC IDs
default artifact directories
artifact-family requirements
admission prerequisites
strictness profiles
```

The Codex repository remains free to use the strict default Scnehaux profile.

#### E. Ontology-driven relationships

Preserve relationship safety without requiring every change to traverse an absolute EAD→PAD→SAD→TDD hierarchy.

Artifact creation is determined by architecture context and policy.

#### F. Semantic regex/prose-pattern retirement

Inventory production semantic inference.

Classify:

```text
lexical regex
    → KEEP

structured/semantic regex
    → REMOVE / REPLACE

prose keyword governance
    → DEMOTE / REPLACE WITH STRUCTURED STATE
```

#### G. Generator convergence

Derived architecture outputs MUST consume canonical model/graph state.

Independent parser/inference implementations in generators are not allowed.

### Phase 6.6A Exit Gate

Phase 6.7 MUST NOT begin until the compatibility reconciliation is green.

The gate proves that:

- AI context will consume one canonical semantic model
- Graph RAG will operate on a general knowledge graph rather than a document-only graph
- company adopters can customize profiles without forking Scnehaux Core
- external architecture knowledge can be referenced safely
- deterministic governance remains model-driven
- legacy docs-centric semantic inference does not leak into the AI-native layer

<!-- SCNEHAUX-CODEX-CAPABILITY-ARCHITECTURE-FREEZE -->

## AI Capability Architecture Roadmap Freeze

The AI-native roadmap is now capability-driven rather than agent-count-driven.

Phase 6.6A MUST reconcile legacy implementation against the following stable capability architecture before downstream AI contracts are implemented.

### Phase 6.6A Additional Reconciliation Targets

Add to the existing Phase 6.6A gate:

```text
capability architecture is explicit
agent topology is runtime-configurable
retrieval semantics are centralized
evidence/provenance is first-class
generation and review are separable
approval is policy-driven
evaluation is first-class
runtime tracing is reconstructable
budget/depth profiles are configurable
```

### Phase 6.7 — Knowledge Provenance + Context Foundation

Deliver:

```text
Evidence
Claim
SourceAuthority
KnowledgeRevision
ContextPackage
ContextCompiler contract
retrieval strategy contract
```

### Phase 6.8 — Intent, Planning, Research, and Artifact Contracts

Deliver:

```text
IntentSpec
ArchitecturePlan
ResearchPlan
ResearchPackage
ArchitectureProposal
ArtifactDraft<T>
```

No mandatory agent topology is introduced.

### Phase 6.9 — Validation, Simulation, Review, and Approval Contracts

Deliver:

```text
ValidationReport
SimulationReport
ArchitectureReview
ApprovalPackage
deterministic renderer
round-trip equivalence
graph simulation
```

### Phase 6.10 — Temporary Tool Reconciliation

Retire migration/probe tooling only after every ongoing invariant is mapped to permanent capability, implementation, test, and gate.

## Phase 12 — Architecture Knowledge Runtime

Deliver runtime implementations for:

```text
Knowledge Compilation
exact retrieval
graph retrieval
full-text retrieval
semantic retrieval
hybrid retrieval
Context Compilation
knowledge revision tracking
graph-store adapters
semantic-index adapters
```

## Phase 13 — AI Architecture Runtime

Phase 13 is refined into capability-runtime work.

```text
13.1  Model Gateway
13.2  Tool / Capability Registry
13.3  Intent Analysis Runtime
13.4  Architecture Planning Runtime
13.5  Research Runtime
13.6  Architecture Synthesis Runtime
13.7  AI Architecture Review Runtime
13.8  Specialized Review Routing
13.9  Evidence / Citation Enforcement
13.10 Independent Generation / Review Policy
13.11 Revision Loop
13.12 Guardrails
13.13 Trace / Run Provenance
13.14 Budget / Depth Profiles
13.15 Human / Policy Approval Integration
13.16 Architecture AI Evaluation Harness
```

The implementation MAY use:

```text
single-agent orchestration
manager-worker orchestration
multi-agent orchestration
deterministic workflow orchestration
multi-model review
```

without changing core contracts.

## Phase 14 — Observed Architecture + Reconciliation Runtime

Deliver:

```text
ObservedSource adapters
source AST inspection
API/schema inspection
IaC inspection
runtime inspection
DriftReport
declared-observed reconciliation workflow
```

## Phase 15 — AI-Assisted Architecture Re-admission

Scnehaux Codex becomes its own first full reference implementation.

The framework uses its own:

```text
Intent Analysis
Planning
Research
Context Compilation
Synthesis
Validation
Simulation
Review
Approval
Git admission
knowledge compilation
```

to create and evolve its official architecture corpus after architecture admission is legally open.
