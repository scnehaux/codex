---
doc_meta:
  id: GDC-004
  title: Technology Lifecycle & Standards Governance
  owner: Architecture Authority
  version: 1.0.0
  status: approved
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 180
  created_date: 2026-01-01
  last_reviewed: 2026-11-04
---

# Technology Lifecycle & Standards Governance

## 1. Context & Scope

This policy establishes the standard maturity phases, sunset procedures, rule conflict resolution priorities, and applicability criteria governing all technology choices and engineering standards across the Scnehaux enterprise.

It ensures that technology standards evolve dynamically to avoid technological debt and vendor lock-in.

GDC-004 owns these policies. [GDC-001 §3](./GDC-001-fitness-functions.md#3-technology-lifecycle-governance) documents the automated checks that enforce them, [GDC-003](./GDC-003-review-process.md) the review that decides transitions and waivers, and [GDC-010](./GDC-010-adr-guideline.md) the Exception ADR format.

---

## 2. Policy Framework

### 2.1 Standards Maturity Model

To prevent rigid compliance grids, every enterprise standard must declare one of four maturity phases:

1. **Assessed (Evaluation)**: The standard is experimental or undergoing evaluation. Teams are encouraged to run pilots, but adoption is optional. No waivers are required to deviate.
2. **Trial (Limited Adoption)**: The standard is verified in pilot programs. It is recommended for new services, but existing services are exempt.
3. **Adopted (Default Mandate)**: The standard is the default mandatory baseline. Deviations require an approved exception waiver.
4. **Hold (Retirement)**: The standard is deprecated. New implementations are prohibited from adopting it. Existing implementations must schedule a migration path to replacement systems.

The enterprise Technology Radar (`enterprise/tech-radar.yaml` in the validated architecture repository, checked against `schemas/tech-radar.schema.json`) records the same four phases for technologies as the rings `assess`, `trial`, `adopt` and `hold`.

---

### 2.2 Technology Sunset & Deprecation Strategy

When a standard technology, framework, or library decays (due to security concerns, obsolescence, or vendor deprecation), the system must execute this 3-Stage Sunset Strategy:

1. **Sunset Recommendation (Stage 1)**:
   - The Architecture Review Board (ARB) transitions the standard's state to `Hold`, or moves the technology to the `hold` ring of the Technology Radar with its `sunset_date` and `successor`.
   - The ARB must publish a companion migration guide or successor standard within `30 days`.
2. **Phase-Out Grace Window (Stage 2)**:
   - Existing active systems enter a grace window of maximum `180 days` to migrate off the legacy technology.
   - During this phase, compile checks emit warnings but do not fail the build.
3. **Hard Enforcement Block (Stage 3)**:
   - Upon expiration of the grace window, warnings escalate to hard errors. The CI compliance engine blocks any new pull requests containing references to the deprecated technology.

_Current automation_: the linter does not read `sunset_date` yet, so Stage 2 has no automated warning. A technology in the `hold` ring is blocked from the day it enters the ring (§3.1). Until the grace check exists, the ARB keeps a technology in its current ring during the grace window and moves it to `hold` when the window ends.

---

## 3. Enforcement Mechanism

### 3.1 Automated Enforcement

The CI compliance engine enforces the technology lifecycle through structured metadata, not free-text scanning ([GDC-001 §3](./GDC-001-fitness-functions.md#3-technology-lifecycle-governance)):

1. **Hold Blocks** (`engine/control/validators/metadata_rules.py`): Each `technologies` entry (and its `base`) in the front matter of a SAD or TDD is checked against the Technology Radar. A technology in the `hold` ring raises `technology_hold_violation` at `CRITICAL` severity (hard CI block). A technology missing from the radar raises `unapproved_technology` at `ERROR`. When technologies are declared, a missing or unreadable radar raises `technology_policy_unavailable` at `CRITICAL`.
2. **Waiver Expiry** (`engine/control/auditors/waiver_auditor.py`): An `accepted` Exception ADR past its `expiry_date` raises `exception_expired` at `ERROR`; one expiring within 30 days raises a warning.

### 3.2 Qualitative Enforcement (ARB Audit)

The Architecture Review Board (ARB) is responsible for human-driven governance:

1. **Maturity Transitions**: The ARB manually evaluates and votes to transition standards between the `Assessed`, `Trial`, `Adopted` and `Hold` phases, and technologies between the `assess`, `trial`, `adopt` and `hold` rings.
2. **Conflict & Applicability**: The ARB evaluates if a team's implementation correctly justifies the `Applicability Criteria` (e.g., Team Size Metric) when adopting specific tooling.

### 3.3 Rule Conflict Resolution Matrix

When multiple mandatory standards collide during implementation, the following priority tree governs the outcome (highest priority wins):

1. **Security & Data Compliance** (e.g., encryption-at-rest, PII isolation, RLS rules).
2. **System Resilience & Stability** (e.g., circuit breakers, load shedding limits).
3. **Observability & Auditability** (e.g., audit trail logs, telemetry trace injection).
4. **Operational Performance** (e.g., frame rate rendering target, latency budgets).
5. **Developer Experience & Scaffolding** (e.g., directory styles, compiler version selection).

_Exception Rule_: Performance must not override Security on public network boundaries. Performance is permitted to override Audit tracing only for isolated, local high-frequency loop executions (e.g., local state evaluation).

---

## 4. Severity & Exceptions

### 4.1 Applicability Criteria Framework

To prevent excessive exception waivers, standards must not apply absolute mandates unconditionally. Standards must declare an **Applicability Criteria Matrix**:

- **Team Size Metric**: Tooling frameworks (e.g., Module Federation) are `Adopted` only if the team count is greater than `3` and independent deployments are required. Otherwise, a standalone monolithic deployment is the default.
- **System Scale Metric**: Advanced scaling patterns (e.g., read replicas, microservices partition keys) are `Trial` by default and become `Adopted` only when query throughput exceeds the threshold the standard declares (e.g., >5000 read QPS).

### 4.2 Exception Waiver Procedure

When a team must deviate from a mandatory engineering standard or architectural constraint (e.g. using an uncertified database engine or violating a frontend layer limit):

- **Waiver Request Initiation**: The requesting team must draft a dedicated local project Exception ADR detailing the deviation, the specific standard rule being bypassed, and the mitigation strategies implemented.
- **Exception ADR Format**: The waiver is an ADR with `adr_type: exception` and an `exception_info` block (`approved_by`, `expiry_date`, `risk_classification`, `exception_reason`), as defined in [GDC-010](./GDC-010-adr-guideline.md).
- **Approval Authority Matrix**:
  - _Tier 1 Deviation (High Impact - Database, Core Security)_: Requires unanimous sign-off from the Architecture Review Board (ARB).
  - _Tier 2 Deviation (Medium Impact - Frontend Stack, Observability)_: Requires approval from the Domain Lead.
  - _Tier 3 Deviation (Low Impact - Custom Helpers, Internal Tooling)_: Requires approval from the Lead System Engineer.
- **Time-Bound Review Commitments**: The reviewing authority must issue an official decision (Approved, Rejected, or Request Info) within `5 business days` of the waiver ADR submission.
- **Auditing and Expiration**: Approved waivers must carry an expiration date not exceeding `365 days` from approval. The team must re-submit the waiver for review annually or execute the migration path back to standard compliance.
- **Resolving Expired Waivers**: [GDC-010 §2.4.3](./GDC-010-adr-guideline.md#243-resolving-expired-waivers-exception-adrs) defines the three resolution paths: resolve the debt, evolve the standard, or renew the waiver.

---

## 5. Appendix: Architectural Trade-Offs

In accordance with the Quality Rubric (Trade-Offs parameter), the ARB explicitly documents the compromises within this Tech Lifecycle policy:

1. **180-Day Sunset Grace Period vs. Immediate Deprecation**
   - _Why rejected_: Immediate deprecation halts all product delivery, forcing teams into unplanned emergency migrations and jeopardizing business roadmaps.
   - _The Trade-Off_: We consciously accept the security and maintenance risk of running obsolete technology for up to 180 days. In exchange, we provide engineering teams a predictable, humane runway to schedule their technical debt payoff without halting feature velocity.
