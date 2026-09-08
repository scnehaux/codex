# Local GitHub App tooling

This is the versioned successor to the bootstrap `codex-app-local` ZIP. It is a
standalone operator integration, not the Codex governance evaluator or product
runtime. It has no `engine` imports and does not execute candidate code.

For initial App registration, installation, private-key generation, Windows ACLs,
Linux/macOS permissions, rotation and cleanup, see the
[full operator runbook](https://github.com/scnehaux/codex/blob/main/governance/github/README.md).
The instructions below add reproducible source acquisition and the Checks API
connectivity test. Keep the source revision you reviewed; a moving `main` branch
or a checksum bundled with code is not an independent trust decision.

## Files and local state

```text
integrations/github-app-local/
  github_app_preflight.py       GET-only preflight + optional connectivity probe
  config.json                   public App/Installation/Client IDs and repository
  requirements.txt              pinned direct runtime dependencies
  requirements-dev.txt          offline test/lint dependencies
  tests/test_preflight.py        synthetic-key, mocked-HTTP regression tests
  README.md                     this operational guide
  .gitignore                    excludes local credentials, environments and caches

Outside the checkout, on the operator workstation:
  codex-app-local/.venv/         existing Python environment, reusable
  codex-app-local-<revision>/    exported reviewed source, no .git directory
  .../secrets/github-app.pem    private key, separate from BOTH source directories
```

No private key, token, JWT, client secret or workstation `.venv` belongs in Git.
`config.json` is public configuration, not a secret store. The default IDs match
App `4864946`, installation `159870521`, and repository `scnehaux/codex`. They are
validated again on every authenticated run. Repository inclusion in the initial
GET-only preflight is not a complete inventory of every installed repository;
the write probe additionally verifies that its new token accesses exactly one.

Direct runtime pins are not a complete transitive hash lock. Install only from an
approved package index and review dependency upgrades before promoting a copy.

## Existing setup: no new key or secret folder

The earlier successful local preflight remains valid as evidence of that run.
Do not regenerate a key, recreate the secret folder, or loosen its ACL merely to
install this version. Reuse:

```text
Windows: %LOCALAPPDATA%\scnehaux-codex-authority\secrets\github-app.pem
POSIX:   ~/.local/share/scnehaux-codex-authority/secrets/github-app.pem
```

Windows ACLs still require operator verification with `icacls`: this Python tool
does not claim to validate Windows ACLs. POSIX file ownership and group/world
permissions are checked automatically. Folder separation, `-I`, and `.venv` are
not security sandboxes. A malicious program running as the same user may read the
key. Do not run untrusted candidate code on the credential-holding account.

## Export a reviewed revision: Windows / PowerShell

Use Git for Windows and Python 3.13. Run the following from a trusted Codex Git
checkout. Read the selected revision's source and review its CI results first.
This is source distribution, NOT promotion of a governance authority revision.

```powershell
$ErrorActionPreference = "Stop"
$revision = Read-Host "Paste the reviewed full 40-character helper commit SHA"
if ($revision -cnotmatch '^[0-9a-f]{40}$' -or $revision -eq ('0' * 40)) {
    throw "An exact reviewed commit SHA is required."
}

git fetch origin
if ($LASTEXITCODE -ne 0) { throw "Fetch failed." }
git cat-file -e "${revision}^{commit}"
if ($LASTEXITCODE -ne 0) { throw "Reviewed commit is not available locally." }

$runtime = Join-Path $env:USERPROFILE ("codex-app-local-" + $revision.Substring(0, 12))
$archive = "${runtime}.zip"
if ((Test-Path -LiteralPath $runtime) -or (Test-Path -LiteralPath $archive)) {
    throw "Destination exists. Inspect it instead of overwriting an active copy."
}

git archive --format=zip "--output=$archive" "${revision}:integrations/github-app-local"
if ($LASTEXITCODE -ne 0) { throw "Export failed; do not run a partial copy." }
Expand-Archive -LiteralPath $archive -DestinationPath $runtime
Set-Content -LiteralPath (Join-Path $runtime "SOURCE_REVISION.txt") -Value $revision -Encoding ascii
Get-ChildItem -LiteralPath $runtime
```

The export includes no Git checkout. It must also be outside any parent directory
containing `.git`. Authenticated execution refuses a helper inside a Git checkout
or worktree; offline preview and tests do not need credentials.

Reuse the original environment after confirming it is trusted:

```powershell
$python = Join-Path $env:USERPROFILE "codex-app-local\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Original environment not found; use the new-environment instructions below."
}
& $python -I -m pip install -r (Join-Path $runtime "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
& $python -I (Join-Path $runtime "github_app_preflight.py")
if ($LASTEXITCODE -ne 0) { throw "Preflight blocked. See the full runbook." }
```

For a new environment instead, run `py -3.13 -m venv "$runtime\.venv"`, check the
exit code, and set `$python = Join-Path $runtime ".venv\Scripts\python.exe"` before
installing requirements. No `Activate.ps1` or Execution Policy bypass is needed.

On a later PowerShell session, set `$runtime` to the versioned folder you selected
and `$python` to its trusted environment again. `SOURCE_REVISION.txt` records the
commit you exported; it is an operator note, not a cryptographic attestation.

## Export a reviewed revision: Linux / macOS

Run from a trusted Codex checkout. Set `revision` to the reviewed full commit SHA,
not a branch name. The example uses a fresh environment; an existing trusted
`$HOME/codex-app-local/.venv/bin/python` can also be reused.

```bash
set -eu
printf 'Reviewed full commit SHA: '
read -r revision
case "$revision" in *[!0-9a-f]*|'') echo 'Invalid SHA'; exit 1;; esac
if [ "${#revision}" -ne 40 ] || [ "$revision" = "0000000000000000000000000000000000000000" ]; then
    echo "An exact nonzero commit SHA is required."; exit 1
fi
git fetch origin
git cat-file -e "${revision}^{commit}"
runtime="$HOME/codex-app-local-$revision"
if [ -e "$runtime" ] || [ -e "$runtime.zip" ]; then
    echo "Destination exists; inspect it instead of overwriting."; exit 1
fi
git archive --format=zip --output="$runtime.zip" "${revision}:integrations/github-app-local"
python3.13 -m zipfile -e "$runtime.zip" "$runtime"
printf '%s\n' "$revision" > "$runtime/SOURCE_REVISION.txt"
python3.13 -m venv "$runtime/.venv"
python="$runtime/.venv/bin/python"
"$python" -I -m pip install -r "$runtime/requirements.txt"
"$python" -I "$runtime/github_app_preflight.py"
```

## Default: authentication preflight, GET only

The unchanged default invocation reads App and installation metadata using a
short-lived App JWT. It does not mint an installation token or write a check.
Expected successful output:

```text
[PASS] Authenticated App ID: 4864946
[PASS] Installation ID: 159870521
[PASS] Repository belongs to this installation: scnehaux/codex
[PASS] Installed permissions match the least-privilege setup.
[NOT RUN] Checks API write test and governance evaluation.
[NOT PROVEN] Effective merge enforcement. No checks or rulesets were written.
```

These are example lines, not evidence of a new authenticated run. The App needs
Contents: read, Pull requests: read, Checks: write, Metadata: read, and no other
active permissions. Webhooks may stay disabled: all network traffic is outbound.

## Preview first: no network, no PEM access

Choose a disposable test commit or an already-merged commit explicitly. Check Runs
attach to a commit, not an isolated local branch: the same SHA can appear in more
than one branch or PR. Do not choose a commit merely because a branch is named
"test". The helper never resolves a floating branch, tag, or PR number for you.

```powershell
$testSha = Read-Host "Full lowercase SHA of the explicitly selected test commit"
& $python -I (Join-Path $runtime "github_app_preflight.py") --probe-sha $testSha
```

With `--probe-sha` alone the output is `preview_only`, including the exact repo,
App ID, SHA, fixed check name, `neutral` conclusion and `remote_mutations: 0`.
It reads only public local configuration. This mode does not establish that the
commit exists on GitHub; that is checked immediately before a write.

## Explicit write: one connectivity check

Inspect the preview before running this separate command. This is a real remote
write: it creates a Check Run and uses token issuance/revocation endpoints. The
check remains visible after the helper exits; revoking the token does not remove
it. Never make this probe a required check in a ruleset or branch protection.

```powershell
& $python -I (Join-Path $runtime "github_app_preflight.py") `
    --probe-sha $testSha `
    --write `
    --confirm-repository "scnehaux/codex" `
    --confirm-sha $testSha
```

Equivalent POSIX command:

```bash
"$python" -I "$runtime/github_app_preflight.py" \
  --probe-sha "$testSha" --write \
  --confirm-repository scnehaux/codex --confirm-sha "$testSha"
```

Both confirmations must exactly match the configured repository and requested
SHA. Missing/mismatched confirmations fail before key access or API calls.
There is deliberately no option to change the check name or choose `success`.

The write path authenticates the App, verifies the installation, requests a token
restricted to the one target repository with Contents: read and Checks: write
(plus implicit Metadata: read), validates the returned permissions/lifetime,
verifies token repository scope and commit SHA, posts the probe, reads it back,
and attempts token revocation in `finally`, including after downstream failures.

A complete success reports `status: connectivity_verified`, the Check Run ID and
URL, `installation_token_revoked: true`, and `checks_write_tested: true`.
`governance_evaluated` and `effective_enforcement_proven` stay **false**.
`remote_mutations: 3` counts token issuance, check creation and token revocation;
it does not mean three check results.

The fixed name is **Codex App Connectivity Probe**, NOT **Codex Governance
Authority**. GitHub may accept a neutral result for a required check, so neutral
alone is not a safety boundary. The separate non-required name is essential.

## Failure and recovery

HTTP redirects are refused, the API host is fixed to `api.github.com`, TLS remains
enabled, bodies are bounded, and upstream bodies/tokens are not printed. No
network request is automatically retried.

For `runtime-checkout`, export the reviewed copy; never move the PEM into the
checkout. For `write-confirmation` or `probe-sha`, fix only the public arguments.
For 401, check App/key identity and the workstation clock. For 403, check approval
of installation permissions, organization restrictions and rate limits. For 404,
check repository/installation identity and the exact commit. Do not widen App
permissions or disable TLS just to clear an error.

A timeout, interruption, malformed response or read-back failure after POST does
not prove that no check was created. Inspect that commit's Checks page for the
fixed probe name and App before manually repeating a write. Repeated explicit
writes may create additional probe runs; this tool is not an idempotent job queue.

If issuance returns no usable token, the helper cannot revoke a token it never
received. If revocation fails or the process is forcibly terminated, a temporary
token may remain valid until expiry. Stop using the helper, resolve connectivity
and follow your incident procedure. The tool does not store the token for manual
recovery. GitHub installation tokens normally expire after one hour; deleting a
private key alone does not prove existing tokens were revoked. Suspend/uninstall
the installation through an authorized administrator when immediate containment
is required. Never paste a token into a ticket to troubleshoot cleanup.

For a suspected key leak, revoke the affected App key promptly, contain the
installation as appropriate, and establish a new trusted key/workstation. Normal
planned rotation can validate a new key first, then revoke the old one. Deleting a
local file is not remote revocation or guaranteed secure erasure on an SSD or in
backups. Follow the full runbook for storage, rotation, migration and cleanup.

## Update, rollback and tests

Export each reviewed helper revision to a new directory. Do not auto-update from
candidate PR code. Keep the previous reviewed copy and its environment for
rollback; do not change the PEM path or App identity during a code rollback.
Dependency environments must also be reviewed and recreated when incompatible.

The source includes offline tests with ephemeral synthetic keys and mocked HTTP.
Run them without a real App key, from the exported helper directory:

```powershell
& $python -I -m pip install -r (Join-Path $runtime "requirements-dev.txt")
if ($LASTEXITCODE -ne 0) { throw "Test dependencies failed to install." }
Push-Location $runtime
try {
    & $python -I -m unittest discover -s tests
    if ($LASTEXITCODE -ne 0) { throw "Offline tests failed." }
} finally { Pop-Location }
```

The independent `Local App Tooling` CI runs tests on Windows and Linux with a 95%
minimum coverage gate for the single runtime module, plus Ruff lint/format checks.
CI uses synthetic credentials only. It does not perform the live App write test,
deploy an evaluator, promote `authority_revision`, install a ruleset, or emit the
real authority check. Existing Governance Qualification remains separate.

## Upstream protocol references

- [App JWT authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app)
- [Scoped installation tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)
- [Check Run creation and read-back](https://docs.github.com/en/rest/checks/runs)
- [Installation token revocation](https://docs.github.com/en/rest/apps/installations#revoke-an-installation-access-token)
- [Required status checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)
