# Operator integrations

This directory contains separately distributable operator clients. They are not
part of the `engine` runtime or the framework's `scripts`/`generators` tooling.
Each integration owns its isolated dependencies and a package-local `tests/`
suite; framework regression tests remain under the repository-root `tests/`.

The first integration is [local GitHub App tooling](github-app-local/README.md).
It authenticates a GitHub App and can publish an explicitly requested connectivity
probe. It does not import Codex engine code or evaluate candidate governance.
Its source remains reviewable and versioned in this repository, while credentialed
execution uses an explicitly reviewed, exported copy on a trusted workstation.

`Local App Tooling` CI checks the standalone client on Windows and Linux with
Ruff and at least 95% runtime coverage. It has read-only repository permissions
and uses only synthetic keys and mocked API responses. The existing framework
qualification, generated projections and authority binding are unchanged.

Framework topography/function indexes describe their existing framework roots;
this independently distributed integration is documented here and in its package
README. Adding an integration does not promote a governance evaluator or exempt
actual governed artifacts from schema/frontmatter validation.
