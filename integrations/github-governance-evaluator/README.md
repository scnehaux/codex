# GitHub governance evaluator runtime boundary

This directory is now **Stage 3d**. Stage 3b established deterministic offline
`pass`/`fail` semantics, and Stage 3c pinned the reviewed evaluator source revision.
Stage 3d adds a read-only runtime collector that obtains candidate identity,
touched paths, and the candidate-side `Governance Qualification` result directly
from GitHub instead of trusting caller-supplied candidate/facts JSON.

The collector still does **not** authenticate as the governance GitHub App, read a
private key, mint an installation token, execute candidate code, publish a Check
Run, advance the provider binding, or prove merge enforcement.

## Source promotion remains unchanged

`promotion.json` still pins the deterministic evaluator to merged Stage 3b commit
`23b05a855419b86b61b0c9266805bb66b143c366`. The runtime verifies that its local
`evaluator.py` has the exact Git blob from that promoted commit before importing
and executing it.

The runtime source added in this slice is **not itself promoted yet**. Therefore a
completed runtime result still reports:

```text
runtime_source_promoted: false
facts_provenance_verified: false
publish_enabled: false
authority_binding_advanced: false
effective_enforcement_proven: false
```

Independent collection is necessary but not sufficient for provider authority.
The next privileged slice must pin the runtime revision after this code is merged
and reviewed.

## Read-only collection flow

The executable entrypoint is `runtime.py`. It exposes only one operator input:

```text
--pull-request <positive integer>
```

There is no token option, endpoint override, repository override, check-name
override, candidate manifest option, facts-file option, or publish option.

The fixed flow is:

```text
reviewed exported runtime copy
        |
        +--> verify promotion.json
        |
        +--> verify local evaluator.py == exact promoted Git blob
        |
        +--> GET exact open PR metadata from api.github.com
        |
        +--> GET bounded PR changed-file records
        |
        +--> GET latest Governance Qualification Check Run
        |       exact candidate SHA
        |       GitHub Actions App ID 15368
        |       app slug github-actions
        |
        +--> construct candidate manifest + evaluation facts in memory
        |
        +--> run the source-pinned deterministic evaluator
        |
        `--> emit evidence only; never publish authority
```

All GitHub requests are fixed-host HTTPS `GET` requests. Redirects are refused,
responses and pagination are bounded, error bodies are not rendered, and no
`Authorization` header is sent. The current repository is public, so this slice
uses GitHub's public read API only.

## Candidate identity binding

The collector requires all of the following before evaluation:

- the requested pull request is still open;
- both base and head repositories are exactly `scnehaux/codex`;
- the base branch is exactly `main`;
- base and candidate SHAs are exact nonzero lowercase 40-character SHAs;
- base and candidate SHAs differ;
- the changed-file count is positive and no greater than 2,000;
- every changed-file record is obtained through bounded pagination; and
- renamed files include both the new and previous path so a rename cannot hide a
  protected mutation.

The runtime never resolves a floating candidate branch into authority. GitHub's
exact PR metadata is treated as the provider observation and the candidate SHA is
bound through every subsequent step.

## Candidate qualification source binding

The collector requests only the latest check named `Governance Qualification` for
the exact candidate SHA. Exactly one latest result must exist. Its source must be:

```text
GitHub App ID: 15368
App slug: github-actions
App owner: github
Details URL: https://github.com/scnehaux/codex/actions/runs/...
```

A completed `success` maps to candidate qualification `pass`. Any other completed
conclusion maps to `fail`. A missing, ambiguous, wrong-source, wrong-SHA, or
incomplete check blocks runtime evaluation instead of guessing.

This is still candidate-side qualification evidence. It becomes useful to the
external authority because the future runtime observes it independently rather
than accepting a caller-authored facts file.

## Protected mutations remain fail-closed

The source-pinned Stage 3b evaluator already protects workflow, ownership,
provider-policy, SCM-adapter, and governance-enforcement surfaces. The Stage 3d
runtime adds a conservative fail-closed layer for critical paths not yet present in
that pinned classifier, including:

```text
Makefile
constraints.txt
conftest.py
pyproject.toml
engine/control/
generators/
integrations/github-governance-evaluator/
scripts/
```

A runtime-only critical mutation cannot receive a Stage 3d `pass`. It fails with
`runtime-critical-mutation-requires-privileged-validation` until a later reviewed
evaluator revision incorporates the expanded classifier and is explicitly
re-promoted.

For mutations already recognized by the pinned evaluator, privileged validation is
still unavailable in Stage 3d. Those candidates fail deterministically with the
existing `privileged-validation-missing` behavior. No caller can supply a fake
privileged `pass` to this runtime.

## Why facts provenance is still false

The collector can now prove that candidate identity, changed paths, and candidate
qualification were read directly from fixed GitHub endpoints. However, the
collector source itself was introduced after the currently promoted evaluator
revision and has not yet received its own immutable runtime pin.

Accordingly:

```text
facts_collected_independently: true
facts_provenance_verified: false
runtime_source_promoted: false
```

This distinction prevents candidate-controlled source from declaring itself a
trusted runtime merely because it can read GitHub correctly.

## Local operator use

Do not run `runtime.py` from a Git checkout. Authenticated execution is not involved
in this stage, but authority evidence must still come from a reviewed exported
copy. The CLI deliberately rejects any source beneath a `.git` directory.

After a future PR pins the runtime source revision, the operator will export that
exact reviewed revision outside Git and run approximately:

```powershell
py -3.13 -I runtime.py --pull-request 123
```

Do not use the current branch or moving `main` as an authority runtime. This PR is
for implementation and offline verification only.

## CI boundary

The `Governance Evaluator Facts Provenance` workflow:

- checks out complete history without retained credentials;
- compiles the evaluator/runtime package;
- runs deterministic decision, promotion, and runtime regression tests;
- keeps the promoted evaluator offline and credential-free;
- verifies the current evaluator blob is exactly the one stored in the pinned
  Stage 3b commit;
- verifies runtime code has no credential, process, or alternate HTTP-client
  dependencies; and
- confirms `authority_revision` remains null, activation remains planned, and
  effective enforcement remains unclaimed.

CI does not perform a live authority evaluation and does not hold the GitHub App
private key. It is validation of the implementation, not the independent authority
itself.

The already-proven `Codex App Connectivity Probe` remains separate. It proves App
Checks API transport only and must never be configured as the required authority
context.
