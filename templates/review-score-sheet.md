# Architecture Review Score Sheet

This score sheet is used by Reviewers and the Architecture Review Board (ARB) during the manual review phase of PAD, SAD, TDD, and ADR documents.

It supplements the automated `engine/cli.py` checks. While the linter ensures structural and policy-as-code compliance, this score sheet evaluates the qualitative engineering aspects based on the **10 Parameters of the Quality Rubric (GDC-002)**.

## Document Meta

- **Document ID**:
- **Reviewer**:
- **Date**:
- **Final Verdict**: APPROVED / REJECTED / REVISIONS REQUIRED

---

## Evaluation Rubric

| #   | Criterion                       | Result            | Reviewer Notes |
| --- | :------------------------------ | :---------------- | :------------- |
| 1   | **Clarity & Precision**         | Pass / Fail / N/A |                |
| 2   | **Living Scope Boundaries**     | Pass / Fail / N/A |                |
| 3   | **Traceability & Inheritance**  | Pass / Fail / N/A |                |
| 4   | **Architectural Drivers (COE)** | Pass / Fail / N/A |                |
| 5   | **Measurable NFRs**             | Pass / Fail / N/A |                |
| 6   | **Cross-Cutting (Zero-Trust)**  | Pass / Fail / N/A |                |
| 7   | **Trade-Offs**                  | Pass / Fail / N/A |                |
| 8   | **Risk & Graceful Degradation** | Pass / Fail / N/A |                |
| 9   | **TDD Lifecycle & Fates**       | Pass / Fail / N/A |                |
| 10  | **Governance Hygiene**          | Pass / Fail / N/A |                |

---

## ARB Strategic Dimensions (For High-Risk PRs Only)

_(Leave blank if this is a standard Peer Review)_

- **Enterprise Alignment**:
- **Blast Radius & Coupling**:
- **TCO & Tech Lifecycle**:
- **Enterprise Risk Posture**:
- **Reversibility (1-Way vs 2-Way)**:
- **Build vs Buy (Opportunity Cost)**:
- **Scalability Ceiling (10x Horizon)**:

---

## Summary and Action Items

**Key Strengths:**
-

**Critical Risks / Violations:**
-

**Required Revisions before Approval:** 1. 2.
