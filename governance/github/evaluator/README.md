# Governance evaluator staging

Stage 3 begins with a deliberately non-authoritative evaluator skeleton at
`integrations/github-governance-evaluator/`.

The skeleton converts a bounded candidate manifest into an evaluation plan while
keeping `governance_decision: not_evaluated`, `publish_enabled: false`, and
`authority_promoted: false`. It identifies governance-sensitive mutations but
does not declare those changes valid or invalid.

This preserves the SCM trust boundary: source in a candidate-controlled repository
may describe desired evaluator behavior, but candidate state cannot become the
sole authority, cannot select the effective identity, and cannot auto-deploy an
authority revision.

Do not update `authority_revision`, require `Codex Governance Authority`, or
activate the desired ruleset based on this skeleton. Those actions belong after an
immutable revision is explicitly promoted and both positive and negative evaluator
evidence exist.
