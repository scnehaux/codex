# Permanent attestation reader candidate

## Status and decision scope

Recorded on 2026-09-16. This is implementation-local documentation, not a normative architecture artifact. The project owner's instruction to proceed authorizes preparation of this candidate and review of the documentation PR; it does not activate a privileged bootstrap, approve an attestation, promote source, or enable publication.

The documentation ledger was merged in Authority PR #13 at `62ef870399e295bfba70fa5b73b54261a6828a79`. This candidate starts from Codex `0f9dab0091746ac1232174c75ed6330b53dff750` and implements the reader capability requested by Authority PR #12. It is not the completion of Stage D or effective enforcement.

Read the [recommendation ledger][ledger] and [maintenance lifecycle][lifecycle] alongside this record. Decisions below select an implementation for review within this candidate. They do not retroactively mark every recommendation accepted or operationally proven.

## Selected migration and alternatives

For REC-D-001, this candidate adds `attested_runtime.py` rather than changing the historically promoted `runtime.py`. The new entrypoint verifies and reuses the exact historical collector, evaluator, and promotion-file bytes. The old source, source pins, CI checks, and historical evidence stay unchanged.

The same-path alternative is valid in principle, but the current CI checks the working-tree source against the historical blob. Reconciling that contract in the installing PR would enlarge the change. The additive option avoids that coupling at the cost of one extra entrypoint and later package/retirement work. It is the selected candidate migration, not a universal architecture rule.

The loader compiles the verified dependency bytes directly. It does not re-import those files through a search path or use their cached bytecode. This applies the source-identity invariant to the bytes executed; it does not remove the need for an independently controlled deployment host and complete package pinning.

The new entrypoint uses the existing collector's PR identity, changed-path and qualification collectors and the existing evaluator's decision function. Reusable semantics stay in Codex. Authority must not acquire a second permanent governance engine.

## Authority read boundary

REC-D-002 and REC-D-003 are implemented using a fixed Git-object read chain:

```text
Authority refs/heads/main
  -> exact Authority commit
  -> root tree
  -> governance tree
  -> privileged-validations tree
  -> exact candidate-head.json blob
  -> bounded bytes + strict attestation validation
```

This deliberately refines the earlier Contents API proposal. GitHub documents that the Contents API can dereference a symlink to a normal file [contents]. Walking non-recursive trees permits explicit rejection of symlinks, submodules, executable approval files, duplicate names, and truncated trees. A matching content digest alone is not evidence that a file exists at the authorized path.

The successful path takes six Authority GET requests, resolves `main` once, and follows only immutable object identities after that. Each request is restricted to `https://api.github.com/repos/scnehaux/codex-authority/git/`, the exact main ref or commit/tree/blob object families, with no arbitrary queries, redirects, credentials, automatic retry, or ambient proxy routing.

Each Authority response is bounded to 1,000,000 bytes; each tree to 10,000 entries; the decoded attestation to 128,000 bytes; each request to a 10-second timeout. These are conservative implementation limits, not performance guarantees. A future Authority adapter must apply a compatible whole-process timeout and output limit. No current limit is silently raised by this candidate.

An absent exact path in a complete tree means no approval. A failed HTTP request, including 404 for an expected object, is a boundary failure, not evidence of absence. Unknown JSON fields in the attestation, duplicate keys, non-finite constants, malformed UTF-8, non-boolean claims, wrong scope/decision, and mismatched candidate identity fail closed. Renamed paths must include their previous names in the complete sorted touched-path set.

Unprotected candidates make no Authority read. Failed qualification or an unknown non-privilege blocker does not cause an attestation lookup or become a PASS. Only the existing two privilege blockers are eligible to be satisfied. Candidate identity and qualification are collected again before returning, detecting drift during collection. This does not eliminate every race; the publisher still needs a fresh exact-candidate check before any write.

## Result contract and retained evidence

REC-D-004 and REC-D-005 require an explicit boundary rather than pretending this is the historical output. The new result has `schema_version: 2`, kind `codex-attested-runtime-result`, and status `attested_runtime_evaluation_complete`.

The result includes the original unprivileged evaluator result and runtime blockers, the final evaluator result, the candidate observation, qualification evidence, historical dependency identities, and privileged-validation evidence. Verified approval evidence includes Authority revision, path, tree chain, blob SHA, raw-byte SHA-256, canonical attestation digest, and the validated approval record. The canonical digest serialization matches the version-1 Authority attestation convention.

The original FAIL is preserved even when a separately verified approval satisfies privilege. This output is not durable storage and is not a publication permit. A later Authority adapter/evidence change must retain this chain before issuing capability. Failure to persist it must remain a blocker.

All promotion/publication/effective-enforcement claims remain false. The existing Authority adapter must reject this unfamiliar result; acceptance requires an explicitly reviewed version-aware adapter, package source binding, evidence handling, and publisher source compatibility. No old adapter is widened in this candidate.

## Cross-repository completion checklist

The following work remains before live bootstrap activation or permanent handover. These are implementation-review requirements, not newly installed provider rules.

1. Review this reader candidate and its exact changed-file set. Preserve old-runtime evaluation of the installing PR. Candidate qualification and the source-promotion workflow must pass independently.
2. Review the Authority bootstrap evidence chain, permit issuer, version-aware consumer, publisher source bindings, and candidate-proof lifecycle together. The existing historical publisher-proof verifier is not a generic activation interface; new activation records must not overwrite old evidence.
3. Record exact candidate attestation and controlled activation only after that review. Serialize the operator run and reconcile ambiguous remote writes rather than blindly retrying. Exact candidate scope does not imply exactly-once publication (REC-D-007).
4. Preserve the active provider rules. Merge the Codex candidate only through the legitimate attestation/evidence/permit/App check path. No required check, proof flag, or threshold is bypassed.
5. Separately promote the reviewed complete permanent package from Authority, record abort/recovery behavior, and disarm the candidate-scoped bootstrap (REC-D-006). Merging source is not promotion.
6. Prove a subsequent authorized protected candidate can use the permanent path with the bootstrap disabled, while invalid candidates remain blocked (REC-D-008). Map all applicable Phase 10 exit obligations; do not equate this reader or two destructive-rule tests with full completion.

REC-D-009 status reconciliation is deliberately not bundled into this source candidate. REC-D-010 excludes new hosting, queues, databases, and multi-repository machinery here. REC-D-011 remains a pre-activation review of actual administrator/deployment/credential control: repository separation and hashes do not establish independent human administration or protect against compromise of the trusted operator/provider.

If collection, qualification, source verification, or evidence handling fails, stop. Recovery may restore a previously reviewed fail-closed package; that can preserve safety without restoring maintenance availability. It must not weaken rules or create a permanent bootstrap bypass.

## Tests and evidence limits

`tests/test_attested_runtime.py` includes parser, transport, Git-path binding, source-loader, and orchestration tests, plus integration tests against the actual historical collector/evaluator and existing fake GitHub fixtures. These tests use synthetic inputs and no publisher credentials or live writes.

Local verification on Python 3.13.5: 29 unit tests passed using the command below, and both new Python files compiled. The local environment could not clone GitHub, so this subset mocks the historical dependency boundary for orchestration. Do not report it as a local full-repository or historical-runtime integration pass.

```bash
python -I -m unittest discover -s integrations/github-governance-evaluator/tests -p test_attested_runtime.py -k Unit -v
```

In a complete checkout, run the complete existing integration suite, including the new actual-dependency tests:

```bash
python -I -m unittest discover -s integrations/github-governance-evaluator/tests -v
```

The existing source-promotion workflow already discovers this test directory. No workflow is weakened or skipped. Required GitHub CI outcomes and exact final head must be recorded on the candidate PR after observation. CI success is not proof of independent promotion, durability, provider enforcement, post-disarm liveness, or battle-tested operation.

## Decision history and references

On 2026-09-16, following the instruction to proceed: merged Authority's documentation-only PR #13; selected the additive entrypoint for this candidate; refined snapshot reads to inspect Git file modes; retained original and final verdicts separately; selected an explicit new result contract. Source implementation and tests are submitted for review, not effective deployment. No attestation or activation decision is made here.

The change applies the small-mechanism, fail-safe-default and complete-mediation reasoning described by Saltzer and Schroeder [principles]. GitHub's primary documentation defines the relevant object and symlink behaviors [contents], [trees], [blobs], [commits]. Python's JSON documentation describes default duplicate-name/non-finite-number handling [json]; this reader deliberately rejects both. These references justify design choices, not a security certification of this implementation.

[ledger]: https://github.com/scnehaux/codex-authority/blob/62ef870399e295bfba70fa5b73b54261a6828a79/docs/implementation-notes/0002-stage-d-recommendation-ledger.md
[lifecycle]: https://github.com/scnehaux/codex-authority/blob/62ef870399e295bfba70fa5b73b54261a6828a79/docs/privileged-maintenance.md
[contents]: https://docs.github.com/en/rest/repos/contents#get-repository-content
[trees]: https://docs.github.com/en/rest/git/trees#get-a-tree
[blobs]: https://docs.github.com/en/rest/git/blobs#get-a-blob
[commits]: https://docs.github.com/en/rest/git/commits#get-a-commit
[json]: https://docs.python.org/3.13/library/json.html#standard-compliance-and-interoperability
[principles]: https://web.mit.edu/saltzer/www/publications/protection/Basic.html
