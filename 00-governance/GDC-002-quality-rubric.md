---
doc_meta:
  id: GDC-002
  title: Documentation Quality Framework
  owner: Architecture Authority
  version: 0.0.1
  status: draft
  classification: public
  governed_by: [GDC-000]
  review_cycle_days: 365
  created_date: 2026-01-01
---

# Documentation Quality Framework

## 1. Context & Scope

This document defines the **Qualitative Evaluation Criteria** for all architectural artifacts. While other documents in the `00-governance` suite define _what_ sections must exist or _how_ to audit them, this Framework defines _the rigorous benchmark_ the content must meet to pass the "Quality Gate" before entering the Scnehaux knowledge base.

### The `00-governance` Ecosystem (Separation of Concerns)

To prevent overlap and ensure a FAANG-grade modular governance model, the Governance Suite is divided into distinct operational boundaries:

1.  **Governance Policy (GDC-000)**: _The Law_. Defines the architectural metamodel (C4/DDD/AWS) and the structural Context-Aware Templates (PAD/SAD/TDD/EAD).
2.  **Compliance Engine / Linting Rules (GDC-001)**: _The Machine Police_. Automated CI/CD enforcement of the governance structure and semantic baseline (blocking prohibited words).
3.  **Quality Framework (GDC-002) - [THIS DOCUMENT]**: _The Qualitative Standard_. Defines the 10 deep architectural parameters (e.g., Trade-offs, Blast Radius, Quantification) that human reviewers must evaluate.
4.  **ARB Review Process (GDC-003)**: _The ARB Process_. Defines the formal procedure, risk registers, and macro-dimensions for Architecture Review Board (ARB) audits.
5.  **Architecture Review Score Sheet**: _The Execution Tool_. The physical markdown table filled out by the Certified Reviewer during a Pull Request, derived directly from the 10 Quality Framework criteria.

## 2. Policy Framework

All architecture documents are evaluated against 10 critical parameters. Each parameter is binary (Pass/Fail). The Score Sheet translates these parameters into actionable checks.

### 2.1 Scoring Criteria (The 10 Parameters)

| #      | Parameter                                         | Mandate                                           | Pass Condition                                                                                                                                                                           | Fail Condition                                                                                                                                                      |
| :----- | :------------------------------------------------ | :------------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1**  | **Clarity & Precision**                           | Eliminate "weasel words" and motivational filler. | Precise quantification (e.g., "System handles 5,000 RPS with < 200ms P99 latency").                                                                                                      | Using unquantified claims about availability, security, performance, or scalability without mathematical backing.                                                   |
| **2**  | **Defined Scope & Living Boundaries**             | Strict conceptual containment.                    | Strict C4 layer boundaries appropriate for the artifact type (e.g., C1 for EAD, C3 for TDD) that exclusively define inputs, outputs, and trust perimeters for that specific layer.       | A document that attempts to explain the entire enterprise, or a high-level SAD that leaks implementation details (e.g., embedding raw SQL queries or utility code). |
| **3**  | **Traceability & Federated Linkage**              | No orphan documents in the ecosystem.             | Explicit `governed_by` tags are present, and all hyperlink references resolve to valid, active documents.                                                                                | A SAD that does not map to a parent Platform (PAD), or an ADR/STD that lacks the context of what it governs.                                                        |
| **4**  | **Architectural Drivers & COE Integration**       | The concrete "Why" behind the design.             | Explicitly lists business goals, technical constraints, implicit assumptions, and directly integrates learnings from past Incident/COE reports.                                          | Designing a system solely driven by "Hype Driven Development" without acknowledging constraints, or ignoring past failures.                                         |
| **5**  | **Measurable NFRs (Non-Functional Requirements)** | The mathematics of the system's contract.         | Concrete targets established for Latency (P95/P99), Availability (e.g., 99.99%), Throughput (RPS), Data Freshness, and RTO/RPO limits.                                                   | Omitting SLAs, performance caps, or Error Budgets.                                                                                                                  |
| **6**  | **Cross-Cutting Concerns & Zero-Trust**           | Security and Observability by default.            | Defines explicit Zero-Trust cryptographic boundaries (mTLS, JWT validation at the edge), Data Classification (PII/PCI), and SLI/SLO tracing correlation.                                 | Assuming the internal VPC network is inherently safe, or lacking distributed tracing strategies.                                                                    |
| **7**  | **Trade-Offs & Alternatives**                     | Radical honesty in engineering.                   | A comprehensive "Alternatives Considered" section explaining exactly _why_ other patterns were rejected, and detailing the technical debt consciously accepted.                          | Proposing a "perfect" solution without acknowledging its inherent weaknesses, costs, or maintenance burden.                                                         |
| **8**  | **Risk & Graceful Degradation**                   | Chaos readiness and blast radius containment.     | Explicitly maps SPOFs (Single Points of Failure) and details the Graceful Degradation strategy (e.g., "If the caching layer dies, the service returns stale data rather than crashing"). | Designing under the assumption that dependencies (databases, 3rd party APIs, network) will never fail.                                                              |
| **9**  | **Lifecycle & Deprecation Strategy**              | Safe forward and backward evolution.              | Clear deprecation timelines are established. The _Ephemeral TDD Fate Matrix_ is executed (obsolete TDDs are actively archived).                                                          | Introducing a v2 API/Schema without a concrete timeline and automated strategy to sunset v1, or leaving stale TDDs rotting in the active directory.                 |
| **10** | **Governance & Namespace Hygiene**                | Structural integrity for automation.              | Files strictly conform to the scalable federated namespace (e.g., `ADR-IAM-000`) to prevent global namespace collisions and enable Policy-as-Code linter parsing.                        | Arbitrary file naming, missing YAML metadata headers, or bypassing structural templates.                                                                            |

### 2.2 Document-Specific Quality Focus & Lifespan Expectancy

Architectural quality is heavily judged based on its target resilience and expected half-life. Over-engineering a tactical, short-term feature is penalized exactly as severely as under-engineering a core infrastructure platform.

| Artifact                               | Target Lifespan                                                                                      | Quality Focus (Must Define)                                                                                                                                 |
| :------------------------------------- | :--------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **EAD** (Enterprise Architecture)      | **Permanent (Strategic Horizon)**                                                                    | Organizational macro-capabilities, value streams, and enterprise-wide technical vectors.                                                                    |
| **PAD** (Platform Architecture)        | **10+ Years (One-Way Doors)**. Migrating off a core physical layer incurs massive liabilities.       | Explicit Trust Boundaries (IAM/VPC), high-level API integration contracts, and multi-region/multi-AZ failure propagation models.                            |
| **SAD** (Software Architecture)        | **3-5 Years (Two-Way Doors)**. Expected to be refactored/rewritten as business domain models evolve. | C2 Container Topology, strict network perimeters, and runtime Graceful Degradation matrices. Optimize heavily for component decoupling and observability.   |
| **TDD** (Technical Design)             | **Ephemeral (Tied exclusively to codebase)**. Expected to become obsolete rapidly.                   | Strict API/Event Contracts, internal Data Models (ERDs), and code-level fault tolerance (retries/circuit breakers). Documentation overhead must be minimal. |
| **STD** (Standard Document)            | **Living Document (Strictly Versioned)**                                                             | Universally applicable within its blast radius and completely deterministic (verifiable via CI linters or Policy-as-Code).                                  |
| **ADR** (Architecture Decision Record) | **Permanent Record of Point-in-Time Context**                                                        | Exact business constraints at the time of decision, explicitly rejected alternatives, and consciously accepted technical debt.                              |

## 3. Enforcement Mechanism (The Governance Layers)

In a mature architecture ecosystem, manual checklists are not the primary enforcement engine. We rely on **Policy-as-Code** for absolute consistency, reserving human intellect for strategic judgment.

| Governance Layer           | Role                        | Enforcement                                                                                                            |
| :------------------------- | :-------------------------- | :--------------------------------------------------------------------------------------------------------------------- |
| **Linter / Policy Engine** | Primary Enforcement         | Blocks non-compliant docs at the CI/CD level (Semantic/Prohibited Words).                                              |
| **Metadata Validation**    | Structural Governance       | Enforces Context-Aware Templates (PAD/SAD/TDD) based on ID prefix.                                                     |
| **CI/CD Gates**            | Mandatory Automation        | Prevents PR merges if the Policy Engine throws an `ERROR` or `CRITICAL`.                                               |
| **Manual Score Sheet**     | Human Fallback & Exceptions | Used by reviewers to evaluate semantic _quality_, business logic, or manual exceptions (`lint_disable` justification). |
| **ARB Review**             | Strategic Oversight         | Required for high-risk approvals, strategic EAD/PAD pivots, or formal waiver requests.                                 |

### 3.1 Audit Trail (No Backdoor Approvals)

An architecture document is only considered 'Approved' or 'Accepted' when it is formally reviewed and merged via a Git Pull Request. You must not manually change the document's status without a PR, nor use external tools (like Jira or Confluence) as proof of approval. The Git commit history is the only recognized proof.

## 4. Severity & Exceptions

### Score Classification

The final score is the sum of passes across the 10 parameters (Maximum Score: 10).

- **0-5 Passes**: Draft / Incomplete -> **Reject** (Rewrite required)
- **6-8 Passes**: Needs Work -> **Revision Required**
- **9 Passes**: Enterprise-Ready -> **Approve** (Standard passing grade)
- **10 Passes**: Governance-Grade -> **Gold Standard**

**Enforcement Rule**: Documents failing to meet the minimum score of **9 Passes** must not be marked as Approved, must not be referenced as authoritative, and must not guide production implementation.

**Exceptions**: Temporary scratchpads or documents clearly marked as `status: draft` are exempt from scoring until they are submitted for approval.

## 5. Appendix: Architectural Trade-Offs

In accordance with the 10th parameter (Trade-Offs), the ARB explicitly documents the compromises of this Quality Rubric:

1. **10 Binary (Pass/Fail) Checks vs. Weighted Individual Scoring (1-5)**
   - _Why rejected_: Grading _individual_ parameters on a subjective 1-5 scale introduces negotiation between reviewer and author. Instead, we strictly enforce 10 binary (Pass/Fail) checks, which objectively sum up to a Total Score of 0-10.
