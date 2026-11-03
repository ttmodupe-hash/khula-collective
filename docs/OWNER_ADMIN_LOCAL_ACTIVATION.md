# Khula Collective — private owner administration setup
**3 November 2026 · Owner-only operating instructions · No secrets stored here**

## What has been verified

- Production: https://khula-collective-production.up.railway.app
- Private setup page: https://khula-collective-production.up.railway.app/?owner_setup=1
- Railway production source: `feature/khula-parity-savings-intelligence-20261026`
- The current owner activation/recovery logic has passed unit and integration tests.
- The previous private code emailed on 2 November expired; an attempted new
  private code delivery was blocked, so the undisclosed challenge was disabled.
- **No owner login is claimed to have been activated or recovered.**
- The connected Railway project owner must complete the private challenge
  locally; never email it, give it to ChatGPT, or commit it to GitHub.

## Route A: Owner's own local Python terminal

Use Python 3.11+ on the **owner's private computer**. From a trusted copy of
the repository run:

```bash
python scripts/generate_owner_challenge.py --owner-email YOUR_RAILWAY_OWNER_EMAIL --hours 6
```

The script uses `secrets.token_urlsafe(32)`, hashes the token with SHA-256,
generates a short UTC expiry and writes **nothing to disk**. It refuses to
print a privileged code in a noninteractive terminal (CI, redirection, logs).

## Route B: Windows PowerShell (no Python installation)

Use a private PowerShell terminal on your own Windows computer. Copy the
following commands directly; **do not run them in a shared/remote terminal**.

```powershell
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$rng.Dispose()
$oneUseCode = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$hasher = [System.Security.Cryptography.SHA256]::Create()
$hashBytes = $hasher.ComputeHash([System.Text.Encoding]::ASCII.GetBytes($oneUseCode))
$hasher.Dispose()
$digest = ([BitConverter]::ToString($hashBytes)).Replace('-', '').ToLowerInvariant()
$expiresUTC = [DateTime]::UtcNow.AddHours(6).ToString("yyyy-MM-ddTHH:mm:ssZ")
Write-Host "Railway KHULA_OWNER_SETUP_TOKEN_SHA256 = $digest"
Write-Host "Railway KHULA_OWNER_SETUP_EXPIRES_UTC = $expiresUTC"
Write-Host "Private ONE-USE code for the Khula app form only: $oneUseCode"
```

The code is a locally generated 256-bit secret. Do not copy it into the
Railway SHA256 variable: **only the digest** goes into Railway.

## In Railway's authenticated production Variables screen

Verify the correct project **mellow-patience** / service
**khula-collective** / environment **production**. Configure these four
variables as an atomic operational change where possible:

| Variable | Value |
|---|---|
| `KHULA_OWNER_SETUP_EMAIL` | Exact email verified by the Railway owner's own account |
| `KHULA_OWNER_SETUP_TOKEN_SHA256` | Only the 64-character lowercase SHA-256 digest generated locally |
| `KHULA_OWNER_SETUP_EXPIRES_UTC` | Generated UTC expiry, no more than 12 hours ahead |
| `KHULA_OWNER_SETUP_DISABLED` | `0` to make this specific challenge temporarily usable |

Leave all other member, bank and privacy settings **unchanged**. Railway may
redeploy the service after the variable update; confirm the deployment status
is **SUCCESS** and the mounted member-ledger volume is still `/data`.

## Claim access yourself, without sharing the private code

1. Open `https://khula-collective-production.up.railway.app/?owner_setup=1`.
2. Type your exact Railway owner email and private locally generated code.
3. Create and confirm a **strong original administrator password**.
4. Confirm the owner account/overseas-hosting statement.
5. Submit once. The original code is stored only as a digest and can be
   consumed once; existing owner recovery invalidates earlier sessions.
6. Sign in using the confirmed owner username and new password.
7. Open **Membership Approvals**; independently verify identity and club
   eligibility before approving any pending applicant.

**Do not set a new admin role from an ordinary member account.**
Creating owner access does not certify Khula's POPIA or constitution review,
and the member registration gate intentionally remains closed until proper
legal and operational sign-off.

## After your owner sign-in succeeds

- Set `KHULA_OWNER_SETUP_DISABLED=1` to close the public owner challenge
  capability, then clear the temporary digest/expiry in Railway through its
  private Variables screen after confirming that you can still sign in.
- Rotate/remove the separate `KHULA_BOOTSTRAP_ADMIN_PASSWORD` secret after
  verifying no ordinary bootstrap recovery is needed.
- Apply administrator MFA and a backup/isolated restore test in a separate
  reviewed release before real financial onboarding.
- Never send your owner password or original activation code to support;
  use a fresh challenge for subsequent owner recovery.

## Rollback

If activation produces an unexpected result, immediately set
`KHULA_OWNER_SETUP_DISABLED=1` in Railway; it closes owner setup/recovery
without disabling existing authenticated member logins. Verify the mounted
`/data` member ledger before any deployment rollback. Do not restore or
replace the member volume from an untested backup.

Central handoff: https://github.com/ttmodupe-hash/khula-collective/issues/18
