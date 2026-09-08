# GitHub governance evaluator decision engine

This directory is **Stage 3b**: a deterministic, offline decision engine for the
future external `Codex Governance Authority`. It now produces staging `pass` or
`fail` decisions, but it still does not authenticate to GitHub, use a private key,
mint installation tokens, execute candidate code, publish a Check Run, promote an
authority revision, or prove merge enforcement.

The trust boundary remains explicit: candidate state is untrusted data. A second
bounded `evaluation-facts` input supplies qualification facts to the engine. The
engine validates exact repository/PR/base/head/authority binding and applies the
same decision every time for the same validated inputs. **This stage does not
verify the provenance of that facts file.** A future promoted runtime must collect
those facts independently before any result is eligible for publication.

## Candidate input

`--candidate-manifest` remains schema version 1:

```json
{
  "schema_version": 1,
  "repository": "scnehaux/codex",
  "pull_request": 8,
  "base_sha": "<40 lowercase hex>",
  "head_sha": "<40 lowercase hex>",
  "changed_files": ["sorted/repository-relative/path"]
}
```

Changed paths are bounded, unique, sorted, repository-relative POSIX paths. The
engine rejects traversal, absolute/Windows paths, control characters, malformed
SHAs, wrong repository identity, unknown fields, and candidate-as-authority use.

## Evaluation facts input

`--evaluation-facts` is a separate schema version 1 object:

```json
{
  "schema_version": 1,
  "repository": "scnehaux/codex",
  "pull_request": 8,
  "base_sha": "<same exact base SHA>",
  "head_sha": "<same exact candidate SHA>",
  "authority_source_revision": "<same explicit evaluator revision>",
  "candidate_qualification": "pass",
  "privileged_validation": "not_required"
}
```

`candidate_qualification` is exactly `pass` or `fail`. `privileged_validation` is
exactly `pass`, `fail`, or `not_required`. The facts file is data only; merely
writing `pass` into it is **not** authority evidence. The current offline engine
sets `facts_provenance_verified: false` in every completed result.

## Deterministic policy

The engine applies these rules in fixed order:

1. Repository, PR, base SHA, candidate SHA, and authority revision must bind exactly.
2. The candidate SHA cannot equal the authority source revision.
3. Candidate qualification must be `pass`; otherwise the decision is `fail`.
4. Mutations to protected governance/SCM/workflow/ownership surfaces require
   `privileged_validation: pass`.
5. A protected mutation with `fail` or `not_required` fails. An unprotected
   candidate must use `not_required`; a contradictory privileged claim is blocked
   as invalid input rather than silently accepted.

A completed result has `governance_decision: pass` or `fail`. A pass exits `0`, a
deterministic governance failure exits `2`, and invalid/unbound input exits `1`.
The output always keeps `publish_enabled: false`, `authority_promoted: false`,
`candidate_code_executed: false`, `credentials_used: false`, and
`effective_enforcement_proven: false`.

## Run locally without credentials

Create candidate and facts JSON files matching the contracts, then run:

```powershell
py -3.13 -I integrations/github-governance-evaluator/evaluator.py `
  --candidate-manifest candidate.json `
  --evaluation-facts facts.json `
  --authority-source-revision cccccccccccccccccccccccccccccccccccccccc
```

Do not interpret a local `pass` as a real GitHub authority result. The caller can
still fabricate the facts file in this stage. The purpose of Stage 3b is to lock
down deterministic decision semantics and negative behavior before credentials or
provider writes are introduced.

## Trust and promotion boundary

Source living in the candidate repository does not make it the effective authority.
A later slice must explicitly review and promote an immutable evaluator revision,
export/run that trusted revision outside candidate control, independently collect
candidate state and qualification facts, bind them to the exact candidate SHA, and
only then authenticate as the already-bound GitHub App to publish the real
`Codex Governance Authority` result.

`governance/github/authority-binding.yaml` intentionally remains unchanged in this
slice: `authority_revision` is still null and activation remains planned. The
already-proven `Codex App Connectivity Probe` remains separate and must never be
configured as the required authority context.
