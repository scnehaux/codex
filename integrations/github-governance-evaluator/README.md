# GitHub governance evaluator skeleton

This directory is **Stage 3a only**: a plan-only skeleton for the future external
`Codex Governance Authority` evaluator. It does not authenticate to GitHub, use a
private key, mint installation tokens, run candidate code, publish a Check Run, or
claim a governance decision.

The purpose of this slice is to make the trust boundary executable before adding
credentials or live authority behavior. A candidate manifest is treated as
untrusted data. The evaluator requires an explicit full source revision for the
trusted evaluator copy and refuses to treat the candidate SHA itself as that
authority revision.

## Input contract

`--candidate-manifest` is UTF-8 JSON with exactly:

```json
{
  "schema_version": 1,
  "repository": "scnehaux/codex",
  "pull_request": 7,
  "base_sha": "<40 lowercase hex>",
  "head_sha": "<40 lowercase hex>",
  "changed_files": ["sorted/repository-relative/path"]
}
```

Changed paths are bounded, unique, sorted, repository-relative POSIX paths. The
skeleton rejects traversal, absolute/Windows paths, control characters, malformed
SHAs, wrong repository identity, unknown fields, and candidate-as-authority use.

The current protected-path classifier is intentionally conservative around the
trust-boundary concerns already declared by repository governance: workflow and
ownership definitions, provider policy projection, SCM enforcement code, and the
governance entrypoint. A protected mutation is **not** automatically a failure;
it means later trusted evaluation must validate it through the privileged path.

## Run locally without credentials

From the repository root:

```powershell
py -3.13 -I integrations/github-governance-evaluator/evaluator.py `
  --candidate-manifest integrations/github-governance-evaluator/examples/candidate-manifest.json `
  --authority-source-revision cccccccccccccccccccccccccccccccccccccccc
```

Expected output includes:

```text
status: evaluation_plan_ready
governance_decision: not_evaluated
publish_enabled: false
authority_promoted: false
candidate_code_executed: false
credentials_used: false
effective_enforcement_proven: false
```

The example SHA is synthetic. It is not a promoted evaluator revision.

## Trust and promotion boundary

Source living in this repository does not make a candidate branch an authority.
A later phase must explicitly review and promote an immutable evaluator revision,
export/run that trusted revision outside candidate control, fetch candidate state
as data, perform deterministic governance evaluation, and only then authenticate
as the bound GitHub App to publish the real `Codex Governance Authority` result.

This skeleton deliberately has no GitHub API client and no option to publish a
check. `governance/github/authority-binding.yaml` therefore remains unchanged:
`authority_revision` is still null and activation remains planned.

The already-proven `Codex App Connectivity Probe` is separate. It proves App
Checks API transport only and must never be configured as the required authority
context.
