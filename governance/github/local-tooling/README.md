# Versioned local GitHub App tooling

The executable implementation of the authentication preflight and section 19's
Checks API connectivity test now lives in
[the standalone local integration](../../../integrations/github-app-local/README.md).
The [original operator runbook](../README.md) remains the initial registration,
private-key storage, ACL, recovery and governance-activation guide.

Use the integration guide to export an explicitly reviewed commit to a new local
folder, reuse the existing Python environment and PEM, preview without credentials,
and explicitly request one `Codex App Connectivity Probe`. Its tests and CI use
synthetic keys only. A live write still needs the operator's locally held key.

Never configure the connectivity probe as a required check. It does not evaluate
governance, and a neutral conclusion is not an independent safety boundary.
Nothing in this tooling promotes `authority_revision`, activates the desired
ruleset, or proves effective merge enforcement.
