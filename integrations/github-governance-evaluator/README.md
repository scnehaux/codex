# GitHub governance evaluator source promotion

This directory is **Stage 3c**. Stage 3b established deterministic offline
`pass`/`fail` semantics. Stage 3c now pins the reviewed evaluator source revision
that an operator may export into the future independently administered runtime.
It still does not authenticate to GitHub, use a private key, mint installation
tokens, execute candidate code, publish a Check Run, advance the provider binding,
or prove merge enforcement.

The pinned source is recorded in `promotion.json`. The current pin is the merged
Stage 3b revision `23b05a855419b86b61b0c9266805bb66b143c366`. That revision is an
immutable Git commit containing the deterministic decision engine. Pinning it does
**not** make the repository itself the effective authority and does not prove that
an external runtime is running that revision.

## Promotion contract

`promotion.json` is intentionally narrow:

```json
{
  "schema_version": 1,
  "repository": "scnehaux/codex",
  "authority_source_revision": "23b05a855419b86b61b0c9266805bb66b143c366",
  "promotion": {
    "mode": "privileged-explicit",
    "state": "source-pinned",
    "candidate_may_select_effective_revision": false
  },
  "runtime": {
    "execution_location": "external",
    "exported_copy_required": true,
    "facts_provenance_verified": false,
    "publish_enabled": false,
    "authority_binding_advanced": false,
    "effective_enforcement_proven": false
  }
}
```

The contract expresses a reviewed source pin only. The effective evaluator must be
an exported copy administered outside candidate control. Candidate state may not
select the effective revision, and no candidate update may auto-deploy itself into
the credential-holding runtime.

## Why `authority_revision` is still null

`governance/github/authority-binding.yaml` remains desired provider state and still
contains `authority_revision: null`. This is deliberate. The Stage 3b engine still
accepts a caller-supplied facts file whose provenance is not independently proven.
Advancing the provider binding now would let a source pin look more authoritative
than the evidence supports.

The next slice must create the independently collected facts boundary and prove
that the exported runtime is actually running the pinned revision. Only after that
runtime evidence exists should a separate privileged change advance
`authority_revision` in the provider binding and enable publication of the real
`Codex Governance Authority` context.

## Candidate and facts inputs

The decision engine still consumes two bounded JSON inputs. Candidate state is
untrusted data. `evaluation-facts` binds repository, PR, base SHA, candidate SHA,
authority source revision, candidate qualification and privileged validation. The
engine rejects identity mismatches, malformed paths/SHAs, candidate-as-authority
use and contradictory privileged claims.

A deterministic Stage 3b result remains one of:

- exit `0`: governance decision `pass`;
- exit `2`: deterministic governance decision `fail`;
- exit `1`: invalid or unbound input.

Every completed result still reports `facts_provenance_verified: false`,
`publish_enabled: false`, `authority_promoted: false`, `candidate_code_executed:
false`, `credentials_used: false`, and `effective_enforcement_proven: false`.

## CI and operator boundary

The `Governance Evaluator Source Promotion` workflow checks out complete history,
runs the positive/negative decision tests and promotion tests, rejects network,
credential and process-client imports in the evaluator, proves that the pinned
commit exists in repository history, and verifies that provider activation remains
unadvanced.

CI is still candidate-side evidence. It does not hold the GitHub App private key
and does not become the external authority merely because these checks pass.

For the next runtime slice, the operator should export exactly the pinned commit
outside any candidate checkout, independently collect facts for an exact candidate
SHA, run the deterministic engine from the pinned source, and keep App credentials
unavailable to candidate code. Only that trusted runtime may later publish the real
`Codex Governance Authority` check.

The already-proven `Codex App Connectivity Probe` remains separate. It proves App
Checks API transport only and must never be configured as the required authority
context.
