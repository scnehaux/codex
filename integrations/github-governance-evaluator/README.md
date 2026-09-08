# GitHub governance evaluator runtime source promotion

This directory is now **Stage 3e**. Stage 3b established deterministic offline
`pass`/`fail` semantics, Stage 3c pinned the reviewed evaluator source, and Stage 3d
added a read-only runtime that independently observes candidate identity, touched
paths, and `Governance Qualification` from GitHub. Stage 3e pins that reviewed
runtime source to an immutable commit and exact Git blob.

The promoted runtime source is the merged Stage 3d revision
`cbd64f78c8f72f28880d4673729a796b249d8eae`. Its exact `runtime.py` Git blob is
`c59911e9c0800c917fed21e6f33f3181c3a61e60`.

This slice still does **not** authenticate as the governance GitHub App, read a
private key, mint an installation token, publish a Check Run, advance the provider
binding, or prove merge enforcement.

## Promotion contracts

`promotion.json` continues to pin the deterministic evaluator source:

```text
evaluator revision: 23b05a855419b86b61b0c9266805bb66b143c366
evaluator blob:     ab2f152c21bd6d6f22df21172c4d027035ff8c11
```

`runtime-promotion.json` now pins the reviewed runtime source:

```text
runtime revision:   cbd64f78c8f72f28880d4673729a796b249d8eae
runtime path:       integrations/github-governance-evaluator/runtime.py
runtime blob:       c59911e9c0800c917fed21e6f33f3181c3a61e60
promotion mode:     privileged-explicit
promotion state:    runtime-source-pinned
```

The contract explicitly keeps candidate selection and candidate auto-deployment
forbidden. The effective runtime must be an exported copy administered outside
candidate control.

## Why `runtime.py` is intentionally unchanged in this slice

The source pin points to the already-reviewed Stage 3d runtime. This PR therefore
does not modify `runtime.py`. Changing the runtime while simultaneously claiming
that the previous blob is promoted would invalidate the pin.

The runtime also does not embed its own commit SHA. A Git commit SHA includes the
file content, so requiring the file to contain the SHA of the commit that contains
that same file would create a self-referential identity problem. Instead, the
promotion record binds the immutable commit and exact Git blob externally, and CI
verifies both against repository history.

For live use, the operator exports exactly the pinned runtime revision and verifies
the exported `runtime.py` blob before execution. This preserves a clean separation
between source identity and runtime behavior.

## Runtime behavior remains read-only

The executable entrypoint remains `runtime.py`, with only:

```text
--pull-request <positive integer>
```

There is no token option, endpoint override, repository override, check-name
override, candidate manifest option, facts-file option, or publish option.

The fixed flow remains:

```text
reviewed exported runtime copy
        |
        +--> verify promotion.json
        |
        +--> verify local evaluator.py == exact promoted evaluator blob
        |
        +--> GET exact open PR metadata from api.github.com
        |
        +--> GET bounded PR changed-file records
        |
        +--> GET latest Governance Qualification Check Run
        |
        +--> construct candidate manifest + evaluation facts in memory
        |
        +--> run the source-pinned deterministic evaluator
        |
        `--> emit evidence only; never publish authority
```

All GitHub requests remain fixed-host HTTPS `GET` requests. Redirects are refused,
responses and pagination are bounded, error bodies are suppressed, and no
`Authorization` header is sent.

## What is promoted now

After this PR is merged, the repository has an explicit reviewed source pin for
both layers:

- deterministic evaluator source is pinned;
- read-only runtime source is pinned;
- candidate state cannot choose either effective revision; and
- candidate changes cannot auto-deploy themselves into the future authority
  runtime.

That is still source promotion, not live runtime proof.

A completed Stage 3d runtime result still reports:

```text
runtime_source_promoted: false
facts_provenance_verified: false
publish_enabled: false
authority_binding_advanced: false
effective_enforcement_proven: false
```

Those fields are intentionally unchanged in the pinned Stage 3d runtime blob. A
source file cannot retroactively prove that an operator actually exported and ran
it. The next stage supplies that external execution evidence.

## Live proof still required

The next stage should create a controlled pull request and run an exported copy of
exactly the pinned runtime against that PR. The operator must verify the exported
runtime blob before execution and retain the resulting evidence bound to the exact
PR/base/head SHA.

Only after that live instance proof exists can a later privileged change consider:

```text
facts_provenance_verified: true
authority_revision: <eligible promoted authority revision>
publish_enabled: true
```

Even then, provider activation and merge enforcement remain separate operations and
must not be inferred from a successful runtime evaluation.

## Windows export procedure for the next stage

From a clean local repository, use the immutable runtime revision rather than
moving `main`:

```powershell
$revision = "cbd64f78c8f72f28880d4673729a796b249d8eae"
$runtime = "$env:USERPROFILE\codex-governance-runtime-cbd64f78c8f7"

git archive --format=zip "--output=$runtime.zip" "${revision}:integrations/github-governance-evaluator"
Expand-Archive -Path "$runtime.zip" -DestinationPath $runtime -Force

git hash-object "$runtime\runtime.py"
```

The final command must print:

```text
c59911e9c0800c917fed21e6f33f3181c3a61e60
```

Do not execute the runtime if that value differs. The exported directory must stay
outside every Git checkout because `runtime.py` fails closed when executed beneath a
`.git` directory.

The actual live command in the next stage is:

```powershell
py -3.13 -I "$runtime\runtime.py" --pull-request <CONTROLLED_PR_NUMBER>
```

No GitHub App private key is needed for this read-only proof stage.

## Protected mutations remain fail-closed

The pinned runtime still refuses to turn governance-critical changes into an
unearned success. The source-pinned evaluator protects workflow, ownership,
provider-policy, SCM-adapter, and governance-enforcement surfaces. The runtime adds
conservative fail-closed handling for additional critical paths such as:

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

A controlled live proof PR should therefore touch only a deliberately unprotected
fixture/document path. A later privileged-validation slice can address protected
mutation evidence separately.

## CI boundary

The `Governance Evaluator Runtime Source Promotion` workflow:

- checks out complete history without retained credentials;
- compiles the evaluator/runtime package and runs all regression tests;
- keeps the evaluator credential-free and the runtime read-only;
- verifies the evaluator source revision and exact blob;
- verifies the runtime source revision exists in reviewed history;
- verifies the runtime blob at that revision equals
  `c59911e9c0800c917fed21e6f33f3181c3a61e60`;
- verifies the current `runtime.py` remains exactly that promoted blob; and
- confirms `authority_revision` remains null, activation remains planned, and
  effective enforcement remains unclaimed.

CI validates the promotion record. It does not prove that an external operator has
executed the exported runtime. That live proof is intentionally the next stage.

The already-proven `Codex App Connectivity Probe` remains separate. It proves App
Checks API transport only and must never be configured as the required authority
context.
