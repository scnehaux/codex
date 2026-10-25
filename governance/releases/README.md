# Governance release metadata

This directory documents the Slice 13.4 release protocol. No Governance 1.0 release
or GDC approval is declared by adding the verifier.

The canonical JSON manifest lives in the independent `scnehaux/codex-authority`
repository at `governance/releases/governance-MAJOR.MINOR.PATCH.json`. A Codex
commit cannot contain a manifest that names its own final commit SHA. Authority
retains the manifest after publication and governed merge, with its own immutable
revision. Its SHA-256 is published with the release. The manifest is unsigned;
integrity relies on protected repository history and Authority review. Manifest and publication-record revisions must both be reachable from fetched
Authority main. It does
not establish hosted signed provenance or independent human review.

## Bound source and publication

The release source is the exact PR head that received the dedicated Authority
App's successful check. The release tag `governance-vMAJOR.MINOR.PATCH` points at
that same commit. Squash merge produces a different SHA: the verifier also checks
that the PR is merged into `scnehaux/codex` main, its squash commit has exactly the
source tree, and that merge is an ancestor of the fetched `origin/main`. This
preserves the exact published commit identity without treating two SHAs as equal.

Authority first retains the publisher's actual successful outcome at
`governance/publications/HEAD_SHA.json` through its normal reviewed PR path. The
outcome is the existing `codex-publication-outcome` wire record, including the exact
candidate, check run id, permit and activation digests, and token revocation.
Copying a local journal is evidence preparation, not an approval. The verifier
reads immutable Git blobs from the independently committed record, recomputes its
binding, then reads back the actual GitHub App check and merged PR. It does not
execute Authority code or load publisher credentials. It derives the publisher
identity from Authority's pinned `governance/authority.json`, and check contexts
from their canonical declarations.
Core release binding is provider-neutral. The GitHub adapter at
`engine/adapters/scm/github_release.py` owns API transport, App identity matching
and provider response interpretation; the command-line entrypoint composes it
with the core verifier.

The manifest binds all required GDC ids, paths, statuses, versions and Git blob
ids; the source commit and tree; package version; compiled framework version,
ontology version and semantic/authority/contract digests; every schema JSON blob;
the raw reproducibility policy digest and complete toolchain pins; control registry
blob and pending root ids; and the retained Authority record and identity blobs.
Compilation uses an exact Git blob snapshot, excluding local overlays and line-ending
conversion. Duplicate JSON keys, extra fields, noncanonical bytes and any field
drift fail verification.

## Preparation and verification

From a clean checkout of the exact release source, with both repositories' Git
objects available, prepare metadata outside both repositories:

```sh
python scripts/governance_release.py build \
  --authority-root ../codex-authority \
  --authority-revision FULL_PUBLICATION_RECORD_COMMIT \
  --release-version 1.0.0 \
  --output ../governance-1.0.0.json
```

The builder reports `release_metadata_bound` and `release_declared: false`.
It never overwrites an output, publishes a check, approves a GDC, or creates a tag.
It can expose pending readiness in metadata; building metadata does not satisfy
release criteria. Review and commit the canonical bytes in Authority, preserving
the file bytes rather than formatting the compact JSON.

Verify the committed manifest with its independently recorded digest:

```sh
python scripts/governance_release.py verify \
  --authority-root ../codex-authority \
  --manifest-revision FULL_MANIFEST_COMMIT \
  --manifest-sha256 MANIFEST_SHA256 \
  --release-version 1.0.0
```

Verification rejects pending root controls, unapproved or unstable required GDCs,
missing qualification, the wrong App, unsuccessful or mismatched checks, unmerged
PRs, and divergent or noncanonical main history. `GITHUB_TOKEN` may supply a read
token for API quota; redirects are refused. The verifier only uses GET requests.
Candidate CI grants only `contents: read`, `checks: read`, and `pull-requests: read`,
matching the [check readback](https://docs.github.com/en/rest/checks/runs#get-a-check-run)
and [PR readback](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request) endpoints.
For final release verification, append `--tag governance-v1.0.0`; a different
tag name or commit fails. Canonical full qualification on the source remains a
separate mandatory gate.

## Declaring a release candidate in CI

Dispatch **Governance Release Candidate** with four explicit fields:
`source_commit`, `authority_commit`, `release_version`, and `manifest_sha256`.
This dispatch is the release-candidate declaration. It checks out both exact
commits without persisted credentials, verifies the independently stored manifest
and provider readback, then runs canonical full governance qualification on that
source with the pinned toolchain. Merely opening an implementation PR does not
declare a release candidate. This workflow creates no release or tag and leaves
architecture admission closed. Slice 13.6 owns the final release act after the
individual GDC approvals and all root obligations have actually closed.
