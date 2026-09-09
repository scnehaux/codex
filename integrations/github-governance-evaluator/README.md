# GitHub governance evaluator live-proof attestation

This directory is now **Stage 3f**. Stage 3b established deterministic offline
`pass`/`fail` semantics, Stage 3c pinned the reviewed evaluator source, Stage 3d
added a read-only runtime that independently observes candidate identity, touched
paths, and `Governance Qualification`, and Stage 3e pinned that reviewed runtime
source to an immutable commit and exact Git blob. Stage 3f records the first
successful external live observation and hardens provider activation so source
pinning alone can never make the GitHub ruleset ready.

The source identities remain unchanged:

```text
evaluator revision: 23b05a855419b86b61b0c9266805bb66b143c366
evaluator blob:     ab2f152c21bd6d6f22df21172c4d027035ff8c11
runtime revision:   cbd64f78c8f72f28880d4673729a796b249d8eae
runtime blob:       c59911e9c0800c917fed21e6f33f3181c3a61e60
```

`runtime.py` and `evaluator.py` are intentionally unchanged in this slice.

## First live provenance evidence

`governance/github/evidence/live-provenance-001.json` records the controlled live
execution against PR `#15` while that PR was still open. The exported runtime read
GitHub directly and observed:

```text
repository:             scnehaux/codex
pull request:           15
base SHA:               ed893641a9c96a6cb4c8a590f2757e32116721f6
candidate SHA:          968e496ff6de16b223bd9a15122ee81ed4ee1e5a
changed path:           .gitignore
candidate qualification: pass
qualification check id: 102414770301
governance decision:    pass
```

The live runtime also established that candidate identity and changed files were
read independently from GitHub, the exact `Governance Qualification` check was
bound to the candidate SHA and GitHub Actions source, candidate code was not
executed, credentials were not used, and no runtime failure reason or protected
mutation was present.

The evidence record deliberately distinguishes **observed external evidence** from
the immutable Stage 3d runtime's own conservative self-report. The pinned runtime
still emits:

```text
runtime_source_promoted: false
facts_provenance_verified: false
publish_enabled: false
authority_binding_advanced: false
effective_enforcement_proven: false
```

Those fields are retained verbatim in the governed evidence. Stage 3f does not
rewrite them. Instead, the higher-level attestation records:

```text
live_instance_proven: true
facts_provenance_evidenced: true
publisher_proven: false
authority_binding_advanced: false
effective_enforcement_proven: false
```

This is evidence that the promoted read-only design works in a real external
execution. It is **not** evidence that the GitHub App publisher or merge enforcement
is operational.

## Activation gate is now evidence-aware

`governance/github/authority-binding.yaml` now points to the governed live proof and
keeps publisher evidence unbound:

```text
live_provenance_evidence: governance/github/evidence/live-provenance-001.json
publisher_evidence: null
authority_revision: null
state: planned
effective_enforcement_claimed: false
```

`engine/adapters/scm/github_activation.py` fails closed unless all provider
activation prerequisites are satisfied. A future ready plan must have:

- a positive configured GitHub App `integration_id`;
- an immutable `authority_revision`;
- valid governed live-provenance evidence under `governance/github/evidence/`;
- `authority_revision` equal to the evaluator revision bound by that live evidence;
- valid governed publisher evidence proving the configured App emitted the exact
  `Codex Governance Authority` check for a candidate SHA;
- activation state still `planned`; and
- `effective_enforcement_claimed: false` until provider-side negative proof exists.

Consequently, merely filling `authority_revision` can no longer make the activation
plan ready. The current expected blockers are still at least:

```text
authority-revision-unbound
authority-publisher-evidence-unbound
```

The publisher evidence schema is intentionally validated before activation even
though no real publisher evidence exists yet. The next slice must produce that
evidence from the external GitHub App publisher rather than weakening this gate.

## Runtime behavior remains read-only

The executable entrypoint remains:

```text
runtime.py --pull-request <positive integer>
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

## Correct raw-byte export and verification on Windows

The first live proof exposed an important operator detail. With the repository's
text normalization, a normal archive/extraction path on Windows can materialize
CRLF bytes even though a plain `git hash-object` may normalize them back to the
expected Git object identity. The runtime correctly rejected that materialization
because it hashes the **raw bytes it actually executes**.

Therefore verification must use raw-object semantics:

```powershell
$runtime = "$env:USERPROFILE\codex-governance-runtime-cbd64f78c8f7"

git hash-object --no-filters "$runtime\runtime.py"
git hash-object --no-filters "$runtime\evaluator.py"
```

Expected values are:

```text
runtime.py   c59911e9c0800c917fed21e6f33f3181c3a61e60
evaluator.py ab2f152c21bd6d6f22df21172c4d027035ff8c11
```

If either value differs, do not execute that copy. Re-materialize the exact raw Git
objects without working-tree filters:

```powershell
py -3.13 -c "import subprocess,pathlib; pathlib.Path(r'$runtime\runtime.py').write_bytes(subprocess.check_output(['git','cat-file','blob','c59911e9c0800c917fed21e6f33f3181c3a61e60']))"
py -3.13 -c "import subprocess,pathlib; pathlib.Path(r'$runtime\evaluator.py').write_bytes(subprocess.check_output(['git','cat-file','blob','ab2f152c21bd6d6f22df21172c4d027035ff8c11']))"
```

Then repeat `git hash-object --no-filters`. This verifies the actual bytes that the
isolated Python process will load, not a filtered Git interpretation.

The exported directory must remain outside every Git checkout because `runtime.py`
fails closed when executed beneath a `.git` directory. Local branch and current
working directory are otherwise irrelevant because the runtime uses its explicit
external path and reads candidate facts from GitHub.

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

Stage 3f itself changes protected authority material and therefore does not claim
that the Stage 3d runtime has solved privileged validation. That remains a separate
trust concern.

## What remains before provider enforcement

The next operational slice is the external publisher. It must take a trusted
runtime decision and use the already-bound GitHub App identity to create an exact
`Codex Governance Authority` Check Run on the candidate SHA. Publisher credentials
must remain outside candidate control, and the publisher must not execute candidate
code.

Only after a controlled publisher proof exists should a later privileged change:

1. record governed publisher evidence;
2. bind `authority_revision` to the evaluator revision already proven by live
   evidence;
3. produce an activation plan with no evidence blockers;
4. apply the provider ruleset; and
5. perform negative enforcement tests that demonstrate GitHub actually blocks
   prohibited merges, force-pushes, deletion, and missing authority checks.

Until step 5 completes, `effective_enforcement_proven` remains false.

## CI boundary

The `Governance Evaluator Runtime Source Promotion` workflow now also validates the
Stage 3f evidence boundary. It still verifies immutable evaluator/runtime revisions
and blobs, runs all evaluator/runtime/evidence regression tests, preserves the
runtime promotion contract's conservative false claims, checks that the live proof
is exactly bound to those source identities, and asserts that publisher/provider
activation remains unadvanced.

The already-proven `Codex App Connectivity Probe` remains separate. It proved App
Checks API transport only and must never be configured as the required authority
context.
