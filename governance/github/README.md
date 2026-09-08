# GitHub Governance Authority

This directory contains the GitHub reference-provider projection and operator runbook for the Scnehaux Codex SCM governance trust boundary.

`README.md` is intentionally used for operator documentation because repository ingestion excludes support files named `README.md` from the governed architecture corpus. The runbook therefore remains colocated with the GitHub provider configuration without pretending to be a GDC architecture artifact.

## Files

- `authority-binding.yaml` — desired binding between the provider-neutral external governance authority and the GitHub App identity. This file is desired state only; it does not prove that the App is authenticated, running, or enforced.
- `main-ruleset.json` — desired GitHub ruleset projection for the default branch. Repository text alone is not evidence that the ruleset is installed or effective.
- `README.md` — this operator runbook for local GitHub App setup, authentication preflight, key storage, recovery, and evaluator activation.

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

---

# Local GitHub App / Governance Authority Runbook

This runbook documents the operator steps required to use the Scnehaux Codex GitHub App from a trusted local workstation.

It is intentionally written so the setup can be reconstructed later without relying on chat history.

## 1. Scope

This document covers:

- GitHub App registration and repository installation;
- least-privilege permissions;
- App ID and Installation ID discovery;
- local Python environment setup;
- private-key generation and safe local storage;
- Windows ACL hardening;
- Linux/macOS file-permission hardening;
- local GitHub App authentication preflight;
- expected output and troubleshooting;
- key rotation and workstation migration;
- local cleanup/uninstallation; and
- the boundary between preflight, evaluator execution, and effective merge enforcement.

This document does **not** claim that the external governance evaluator is already deployed or that GitHub rules are already enforcing merge policy.

## 2. Mental model

There are three separate components:

```text
Evaluator logic
    |
    | authenticates as
    v
GitHub App: scnehaux-codex-authority
    |
    | publishes check result
    v
Codex Governance Authority
    |
    | may later be required by
    v
GitHub ruleset / branch protection
```

The GitHub App is an identity and permission boundary. It is not the governance logic itself.

The local evaluator must use an approved evaluator revision and treat candidate pull-request content as untrusted input. A pull request must not be able to modify the evaluator that decides whether that same pull request is allowed to pass.

## 3. Security invariants

The following rules are mandatory:

1. Never commit a GitHub App private key, installation token, JWT, or client secret.
2. Never paste a private key, JWT, installation token, or Authorization header into chat, issue comments, logs, screenshots, or documentation.
3. Keep the private key outside every Git checkout and outside the helper/evaluator source directory.
4. Do not run untrusted pull-request code in a process that has access to the App private key or an installation token.
5. Keep App permissions least-privilege.
6. Do not make `Codex Governance Authority` a required check until the evaluator has produced a genuine result for a test candidate SHA.
7. Do not treat a successful authentication preflight as proof of governance compliance.
8. Do not treat repository configuration text as proof that a live GitHub ruleset is installed or effective.

## 4. GitHub App registration

The reference App name is:

```text
scnehaux-codex-authority
```

Create or manage it under the `scnehaux` organization:

```text
Organization settings
-> Developer settings
-> GitHub Apps
```

Recommended registration settings:

- Homepage URL: `https://github.com/scnehaux/codex`
- OAuth user authorization: disabled/not required
- Device Flow: disabled
- Webhook: may remain disabled for local/manual mode
- Installation scope: only on the owning account/organization

A webhook is not required for the current local/manual flow because the workstation initiates outbound requests to GitHub.

## 5. Required repository permissions

The dedicated App must use the minimum required repository permissions:

- Contents: read-only
- Pull requests: read-only
- Checks: read & write
- Metadata: read-only / implicit
- Administration: no access
- Repository contents write: no access

Additional permissions should remain `No access` unless a separately reviewed design explicitly requires them.

The local preflight is expected to reject unnecessary extra permissions.

## 6. Install the App only on `scnehaux/codex`

Install the App to the `scnehaux` organization using:

```text
Only select repositories
```

Select only:

```text
scnehaux/codex
```

Do not choose `All repositories` for this dedicated governance authority App.

After installation, verify in the organization GitHub Apps settings that exactly the intended repository is selected.

## 7. Public identifiers and secrets

### App ID

The App ID is shown in the GitHub App settings page.

The desired App binding is recorded in:

```text
governance/github/authority-binding.yaml
```

The `authority.integration_id` field is the GitHub App ID used to bind the required check to the intended App identity. It is **not** the Installation ID.

### Installation ID

The Installation ID identifies this App installation on the organization/repository.

A common way to find it is from the installation configuration URL:

```text
https://github.com/organizations/scnehaux/settings/installations/<INSTALLATION_ID>
```

The final numeric segment is the Installation ID.

### Client ID

The Client ID is a public App identifier but is not used as a substitute for App ID or Installation ID.

### Secrets

The following are secrets and must not be stored in repository configuration:

- private key (`.pem`);
- installation access token;
- App JWT; and
- client secret.

## 8. Local helper/evaluator directory

For bootstrap and preflight, keep the local helper outside the Codex checkout.

Recommended Windows location:

```text
C:\Users\<USER>\codex-app-local
```

Recommended Linux/macOS location:

```text
$HOME/codex-app-local
```

The helper directory is not a security boundary. It is simply separated from the repository so local operator state is not confused with candidate source state.

A local preflight package may contain files such as:

```text
codex-app-local/
├── README.md
├── config.json
├── requirements.txt
├── github_app_preflight.py
├── test_preflight.py
├── TEST_RESULTS.txt
├── SHA256SUMS.txt
├── .gitignore
└── .venv/                 # created locally, not distributed as source
```

The files have the following roles:

- `github_app_preflight.py`: authenticates the App and verifies installation, repository inclusion, and permissions.
- `config.json`: contains public identifiers and the target repository only. Never place PEM/token/secret material here.
- `requirements.txt`: Python dependencies for the local helper.
- `test_preflight.py`: offline tests using synthetic keys and mocked GitHub responses.
- `TEST_RESULTS.txt`: evidence from helper tests; not evidence that the real App authenticated.
- `SHA256SUMS.txt`: optional integrity reference for distributed helper files.
- `.venv/`: locally created isolated Python environment. It is not a security sandbox.

Long-term evaluator tooling should be promoted and versioned through the governed repository process. A separately distributed bootstrap helper is not itself an approved evaluator revision.

## 9. Python setup

Use Python 3.13.

### Windows / PowerShell

From the helper directory:

```powershell
Set-Location "$env:USERPROFILE\codex-app-local"
py -3.13 --version
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -I -m pip install -r requirements.txt
```

Expected result:

```text
Python 3.13.x
...
Successfully installed ...
```

A notice that a newer `pip` version exists is not a failure and does not require an immediate upgrade.

You do not need to run `Activate.ps1` or change PowerShell Execution Policy because commands call the virtual-environment interpreter directly.

### Linux / macOS

```bash
cd "$HOME/codex-app-local"
python3.13 --version
python3.13 -m venv .venv
.venv/bin/python -I -m pip install -r requirements.txt
```

## 10. Generate/download the App private key

From the GitHub App settings page:

```text
Organization settings
-> Developer settings
-> GitHub Apps
-> scnehaux-codex-authority
-> Private keys
-> Generate a private key
```

GitHub downloads a `.pem` file.

If the previously generated private key file has been lost, it cannot be reconstructed from the App ID. Generate a new key and revoke the lost key when appropriate.

Do not leave the final operational private key in Downloads.

## 11. Windows secret storage

Recommended path:

```text
%LOCALAPPDATA%\scnehaux-codex-authority\secrets\github-app.pem
```

Equivalent per-user path:

```text
C:\Users\<USER>\AppData\Local\scnehaux-codex-authority\secrets\github-app.pem
```

### 11.1 Create the secret directory

Run in PowerShell:

```powershell
$secretDir = Join-Path $env:LOCALAPPDATA "scnehaux-codex-authority\secrets"
$who = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

New-Item -ItemType Directory -Path $secretDir -Force -ErrorAction Stop | Out-Null

icacls $secretDir /inheritance:r /grant:r "${who}:(OI)(CI)F"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to restrict the GitHub App secret directory. Stop here."
}

explorer.exe $secretDir
```

Expected `icacls` result includes:

```text
Successfully processed 1 files; Failed processing 0 files
```

### 11.2 Move and rename the PEM

Move the downloaded private-key file into the secret directory and rename it exactly:

```text
github-app.pem
```

Enable file-name extensions in File Explorer to avoid accidental names such as:

```text
github-app.pem.pem
github-app.pem.txt
```

### 11.3 Verify the file exists

```powershell
$key = Join-Path $env:LOCALAPPDATA "scnehaux-codex-authority\secrets\github-app.pem"
Test-Path -LiteralPath $key -PathType Leaf
```

Expected output:

```text
True
```

If it returns `False`, do not continue. Verify the location and exact filename.

### 11.4 Restrict the private key ACL

```powershell
$who = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

icacls $key /inheritance:r /grant:r "${who}:R"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to restrict the GitHub App private key. Stop here."
}

icacls $key
```

A healthy result should show the intended workstation account with read access, for example:

```text
C:\Users\<USER>\AppData\Local\scnehaux-codex-authority\secrets\github-app.pem DOMAIN\<USER>:(R)
```

Do not continue if broad/untrusted principals such as `Everyone` or unexpected user/group grants still have access.

Notes:

- `/inheritance:r` removes inherited ACL entries.
- `/grant:r` replaces grants for the named principal; it is not a universal purge of every possible explicit ACL entry.
- Local administrators may still be able to take ownership on a managed Windows workstation.

## 12. Linux/macOS secret storage

Recommended location:

```text
$HOME/.local/share/scnehaux-codex-authority/secrets/github-app.pem
```

Create the directory:

```bash
mkdir -p "$HOME/.local/share/scnehaux-codex-authority/secrets"
chmod 700 "$HOME/.local/share/scnehaux-codex-authority/secrets"
```

Move or rename the downloaded key to:

```text
~/.local/share/scnehaux-codex-authority/secrets/github-app.pem
```

Restrict permissions:

```bash
chmod 600 "$HOME/.local/share/scnehaux-codex-authority/secrets/github-app.pem"
```

Verify:

```bash
ls -l "$HOME/.local/share/scnehaux-codex-authority/secrets/github-app.pem"
```

The key must not be group/world-readable.

## 13. Local authentication preflight

The preflight is designed to prove only identity, installation, repository inclusion, and least-privilege permissions.

It must not publish a governance-success check.

### Windows

```powershell
Set-Location "$env:USERPROFILE\codex-app-local"
.\.venv\Scripts\python.exe -I github_app_preflight.py
```

### Linux / macOS

```bash
cd "$HOME/codex-app-local"
.venv/bin/python -I github_app_preflight.py
```

### Expected success output

```text
[PASS] Authenticated App ID: <EXPECTED_APP_ID>
[PASS] Installation ID: <EXPECTED_INSTALLATION_ID>
[PASS] Repository belongs to this installation: scnehaux/codex
[PASS] Installed permissions match the least-privilege setup.
[NOT RUN] Checks API write test and governance evaluation.
[NOT PROVEN] Effective merge enforcement. No checks or rulesets were written.
```

The final two lines are intentional.

A successful preflight means:

```text
App authentication             PASS
Installation binding           PASS
Repository inclusion           PASS
Least-privilege permissions    PASS
```

It does **not** mean:

```text
Checks API write               proven
Governance evaluator           executed
Candidate governance           passed
GitHub ruleset                 installed
Effective merge enforcement    proven
```

## 14. What the preflight should verify

A robust preflight should perform read-only validation equivalent to:

1. authenticate as the expected GitHub App using a short-lived App JWT;
2. retrieve the expected App installation;
3. verify the installation is not suspended;
4. verify the installation uses selected repositories;
5. verify `scnehaux/codex` belongs to that installation; and
6. verify installed repository permissions are exactly the expected least-privilege set.

It should never print:

- PEM content;
- JWT;
- installation access token;
- client secret; or
- Authorization headers.

## 15. Common troubleshooting

### Private key not found

If this returns `False`:

```powershell
$key = Join-Path $env:LOCALAPPDATA "scnehaux-codex-authority\secrets\github-app.pem"
Test-Path -LiteralPath $key -PathType Leaf
```

verify the key location and exact filename.

### `key-invalid`

Confirm the file is the RSA private key generated for this GitHub App, not a token, client secret, or public key.

### HTTP 401

Check:

- private key/App identity match;
- JWT construction; and
- local workstation clock synchronization.

### HTTP 403

Check whether installation permission changes are pending approval or whether the installed permission set differs from the intended least-privilege contract.

### HTTP 404

Confirm the App is installed on the expected organization and repository.

### Permission mismatch

Correct App permissions. Do not broaden permissions merely to silence the preflight.

### Repository selection mismatch

Use `Only select repositories` and include only `scnehaux/codex`.

### TLS/network error

Check internet access, proxy, DNS, and workstation clock. Do not disable TLS certificate verification.

### Windows ACL check

Display only the current key ACL:

```powershell
$key = Join-Path $env:LOCALAPPDATA "scnehaux-codex-authority\secrets\github-app.pem"
icacls $key
```

Do not paste the key file contents into a troubleshooting ticket.

## 16. Key rotation

Rotate the App private key when:

- the workstation is lost or compromised;
- the key was accidentally exposed;
- operator ownership changes;
- security policy requires periodic rotation; or
- a bootstrap key is being replaced with a production key.

Recommended rotation sequence:

1. Generate a new GitHub App private key.
2. Store it in the protected local secret directory.
3. Run authentication preflight with the new key.
4. Verify the correct App and installation.
5. Update the evaluator process to use the new key.
6. Confirm the evaluator can authenticate using the new key.
7. Revoke or delete the old key in GitHub App settings.
8. Securely delete the old local file.

Do not delete the old key before confirming the new key works unless the old key is known compromised.

## 17. Moving to a new workstation

Do not copy an unprotected private key through chat or email.

Preferred approaches:

- generate a fresh private key on or for the new trusted workstation, validate it, then revoke the previous key; or
- use an approved enterprise secret-transfer mechanism.

On the new workstation, repeat:

```text
Python environment setup
-> protected secret directory
-> private-key placement
-> ACL/file-permission verification
-> authentication preflight
```

The App ID and repository binding remain repository/public configuration; the private key remains workstation/operator secret state.

## 18. Local cleanup

### Remove only the Python helper environment

Windows:

```powershell
Remove-Item -LiteralPath "$env:USERPROFILE\codex-app-local\.venv" -Recurse -Force
```

Linux/macOS:

```bash
rm -rf "$HOME/codex-app-local/.venv"
```

This does not revoke the GitHub App private key.

### Remove local private-key material

Only after the key is no longer needed or has been revoked or rotated.

Windows:

```powershell
Remove-Item -LiteralPath "$env:LOCALAPPDATA\scnehaux-codex-authority\secrets\github-app.pem" -Force
```

Linux/macOS:

```bash
rm -f "$HOME/.local/share/scnehaux-codex-authority/secrets/github-app.pem"
```

If decommissioning the App entirely, also uninstall or revoke it through GitHub organization settings.

## 19. Checks API write test

After authentication preflight succeeds, the next safe milestone is a controlled connectivity test for the GitHub Checks API.

That test must:

- obtain a short-lived installation token;
- target an explicitly selected test commit SHA;
- publish a clearly labeled connectivity/test Check Run;
- avoid claiming governance compliance;
- avoid making the check required before the path is proven; and
- verify that the check source is the intended GitHub App.

Do **not** publish a fake `success` result against an active candidate and treat that as evaluator evidence.

## 20. Local governance evaluator

A production-quality local evaluator must have a stronger boundary than the preflight helper.

Required properties include:

1. an explicitly approved evaluator revision;
2. no automatic deployment of evaluator logic from the candidate branch;
3. candidate source treated as input data;
4. no execution of untrusted candidate code with App credentials present;
5. exact binding of the result to the candidate commit SHA;
6. deterministic failure behavior;
7. preserved evidence explaining pass/fail;
8. explicit operator/promotion process for new evaluator revisions; and
9. test coverage for both success and failure paths.

Only after these properties are proven should the evaluator emit the real:

```text
Codex Governance Authority
```

check as governance evidence.

## 21. Effective enforcement activation

The GitHub App/evaluator and GitHub ruleset are different concerns.

Do not enable required enforcement until:

- the App identity is bound;
- the evaluator revision is promoted;
- a genuine evaluator check has been observed on a controlled test candidate;
- ruleset payload generation is ready;
- an administrator installs the live ruleset; and
- post-install observation reports expected effective state.

Phase 10 negative enforcement evidence must ultimately prove GitHub rejects prohibited operations such as:

- direct push to the default branch;
- force push;
- default-branch deletion;
- merging with failing required governance checks;
- merging with unresolved required review threads;
- violating active review policy; and
- using disallowed merge methods.

Configuration files alone are not sufficient evidence.

## 22. Recovery checklist

If you return to this setup months later, use this checklist:

```text
[ ] Confirm App still exists: scnehaux-codex-authority
[ ] Confirm App is installed only on scnehaux/codex
[ ] Confirm Contents=read, Pull requests=read, Checks=write
[ ] Confirm authority-binding.yaml contains the intended App ID
[ ] Confirm private key exists only in protected local secret storage
[ ] Confirm Windows ACL / POSIX permissions are restricted
[ ] Recreate Python .venv if necessary
[ ] Run local authentication preflight
[ ] Do not assume evaluator/ruleset enforcement from preflight alone
[ ] Confirm approved evaluator revision before publishing real governance checks
[ ] Confirm live-state observer reports expected provider state after activation
```

## 23. Operator handoff information

Safe information to share in normal project discussion:

- GitHub App name;
- App ID;
- Installation ID;
- Client ID;
- repository name;
- sanitized preflight output;
- evaluator revision SHA; and
- non-secret ruleset/evidence metadata.

Never share:

- `.pem` content/file;
- App JWT;
- installation token;
- client secret;
- Authorization header; or
- secret-store export.

## 24. Source of truth

Repository semantics are split intentionally:

```text
governance/scm/enforcement-policy.yaml
    provider-neutral policy

governance/scm/trust-boundary.yaml
    external-authority security invariants

governance/github/authority-binding.yaml
    GitHub App desired binding

governance/github/main-ruleset.json
    GitHub provider projection

governance/github/README.md
    operator runbook (this document)
```

Operator documentation must not redefine normative governance semantics. If this runbook conflicts with governed policy/contracts, the governed policy/contracts take precedence and the documentation must be corrected.
