# GitHub Governance Authority

This directory contains the GitHub reference-provider projection for the Scnehaux Codex SCM governance trust boundary.

## Files

- `authority-binding.yaml` — desired binding between the provider-neutral external governance authority and the GitHub App identity. This file is desired state only; it does not prove that the App is authenticated, running, or enforced.
- `main-ruleset.json` — desired GitHub ruleset projection for the default branch. Repository text alone is not evidence that the ruleset is installed or effective.
- `LOCAL-EVALUATOR-SETUP.md` — operator runbook for using the GitHub App from a trusted local workstation, including private-key storage, Windows ACLs, Linux/macOS permissions, Python environment setup, preflight checks, troubleshooting, key rotation, and cleanup.

## Trust boundary

The candidate repository may define desired provider configuration, but it must not be the sole authority that decides whether its own governance guardrails are valid.

The intended flow is:

```text
candidate pull request
        |
        +--> Governance Qualification
        |      candidate-side deterministic validation
        |
        +--> Codex Governance Authority
               independently administered evaluator
               authenticated as the bound GitHub App
```

The external authority must evaluate a candidate as data. Untrusted pull-request code must never receive the GitHub App private key or an installation token.

## Current activation semantics

Do not infer provider activation from files in this directory. Effective enforcement is proven only after all of the following are true:

1. the GitHub App identity is bound and authenticated;
2. an immutable/trusted evaluator revision is explicitly promoted;
3. the evaluator can publish a genuine `Codex Governance Authority` check against the exact candidate SHA;
4. the provider ruleset is installed through a privileged boundary;
5. the live-state observer reports desired/effective parity; and
6. negative tests prove that forbidden operations are rejected by GitHub.

Until those conditions are met, `effective_enforcement_claimed` must remain false.
