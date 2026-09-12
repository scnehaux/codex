# GitHub governance evaluator activation evidence

This integration is now at the **evidence-bound provider-activation** stage.
The deterministic evaluator and read-only runtime are still the same reviewed,
immutable sources; this slice does not rewrite either executable.

## Pinned source identities

```text
evaluator revision: 23b05a855419b86b61b0c9266805bb66b143c366
evaluator blob:     ab2f152c21bd6d6f22df21172c4d027035ff8c11
runtime revision:   cbd64f78c8f72f28880d4673729a796b249d8eae
runtime blob:       c59911e9c0800c917fed21e6f33f3181c3a61e60
```

The evaluator stays offline. The runtime stays credential-free and performs only
fixed public GitHub reads for candidate identity, touched paths, and the exact
`Governance Qualification` check. Candidate code is never executed.

## Governed evidence chain

`governance/github/evidence/live-provenance-001.json` is the historical read-only
runtime proof. It deliberately preserves the pinned runtime's conservative
self-report (`publish_enabled: false`, `authority_binding_advanced: false`, and
`effective_enforcement_proven: false`). That evidence is not rewritten after the
fact.

`governance/github/evidence/publisher-live-001.json` records the separate external
publisher proof. The dedicated GitHub App `scnehaux-codex-authority` (integration
ID `4864946`) emitted `Codex Governance Authority` successfully for disposable
Codex PR #17 at exact head:

```text
a6ed1def64503ca57c647ce45937f887873aac6f
```

Provider check run:

```text
103547296485
```

The publisher proof is bound to exact candidate/source identity, isolated
credentials, no candidate code execution, and a revoked installation token. The
proof PR was closed without merge after evidence capture.

## Authority binding

`governance/github/authority-binding.yaml` now binds the independently reviewed
evaluator revision and both governed evidence records:

```text
authority_revision: 23b05a855419b86b61b0c9266805bb66b143c366
live_provenance_evidence: governance/github/evidence/live-provenance-001.json
publisher_evidence: governance/github/evidence/publisher-live-001.json
state: planned
effective_enforcement_claimed: false
```

This is a **privileged explicit promotion**. Candidate revisions still cannot
select the effective authority revision and cannot auto-deploy authority code.

With these bindings, `build_github_activation_plan(...)` may produce a provider
ruleset payload with no evidence blockers. Readiness of that plan is not the same
as effective enforcement: applying the provider ruleset and proving its negative
behavior are separate steps.

## Expected provider projection

The activation plan projects both required contexts:

```text
Governance Qualification
Codex Governance Authority  (integration_id: 4864946)
```

`activation.state` intentionally remains `planned`. The repository must not claim
effective enforcement until provider-side negative proof demonstrates that GitHub
actually blocks prohibited merge paths and missing/wrong-source authority checks.

## Runtime behavior remains read-only

The executable runtime entrypoint remains:

```text
runtime.py --pull-request <positive integer>
```

There is no token option, repository override, endpoint override, candidate facts
file, check-name override, or publish option. All requests remain fixed-host HTTPS
`GET` requests with redirects refused and bounded responses.

## Raw-byte verification on Windows

The promoted runtime/evaluator must be materialized outside every Git checkout and
verified using raw-object semantics:

```powershell
git hash-object --no-filters "$runtime\runtime.py"
git hash-object --no-filters "$runtime\evaluator.py"
```

Expected values:

```text
runtime.py   c59911e9c0800c917fed21e6f33f3181c3a61e60
evaluator.py ab2f152c21bd6d6f22df21172c4d027035ff8c11
```

If either differs, do not execute that copy.

## Next operational step

Render the privileged GitHub activation plan from the governed state, review the
exact ruleset payload, apply it through the privileged provider boundary, then run
negative enforcement proof. Until that last proof completes,
`effective_enforcement_proven` remains false.
