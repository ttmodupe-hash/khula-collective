# Khula owner control and recovery plan

Prepared 27 October 2026. **Design and operator tooling; not an activated
owner-only policy, production backup certificate or privacy approval.**
No passwords, challenge values, member information or financial records belong
in this document, the repository, pull requests or test artifacts.

## Verified starting point

- Railway `mellow-patience` / `khula-collective` / `production` was online with
  one running replica and SUCCESS deployment `156fe376-6e88-4cd0-9085-1683124e1727`.
- Deployed commit `28febc9aa0f1a023770ec1ff19c5a95505a74265` is the merged
  [PR #11](https://github.com/ttmodupe-hash/khula-collective/pull/11).
  Four GitHub Actions runs for that exact commit completed successfully.
- Source branch remains `feature/khula-parity-savings-intelligence-20261026`.
  [PR #2](https://github.com/ttmodupe-hash/khula-collective/pull/2) is still
  draft, open and unmerged. Do not switch production to old `main`.
- Volume `khula-member-ledger` remains mounted at `/data` in Railway's `sfo`
  region. No pending Railway configuration changes were reported.
- The activation message was found in the connected inbox, marked unread.
  Message content and activation secrets were not retrieved. Unread status
  does not prove the code is unused; expiry, redemption and successful owner
  sign-in remain unconfirmed.
- Public health, owner-setup shell and install page returned HTTP 200. A shell
  response is not proof that the activation challenge is valid or redeemed.

## Owner activation and access evidence

1. Owner opens their private activation email and the non-secret
   [owner activation page](https://khula-collective-production.up.railway.app/?owner_setup=1).
   Enter the email-delivered code only there and choose a unique admin username
   and new password. Never send either secret through chat or GitHub.
2. If setup reports expiry, reverify Railway/Gmail account ownership before
   issuing a fresh private challenge. Do not rotate a code merely because the
   message is unread or an OAuth integration withholds variable values.
3. Sign in normally, open Membership Approvals and verify the role. Record a
   non-secret success result. A privileged operator should separately verify
   the activation receipt joins to an active admin and `last_login` is after
   activation; do not extract account emails, password hashes or token hashes.
4. Privately inventory existing admins and session revocation state. No
   automatic demotion, deletion or account takeover is authorized by this plan.
5. Once owner login works, disable owner setup, retire the unused bootstrap
   secret, and rotate or revoke the actual old account through a tested flow.
   **Changing/deleting `KHULA_BOOTSTRAP_ADMIN_PASSWORD` does not rotate an
   existing database password:** `bootstrap_admin` only creates an initial
   account and skips creation when an active non-demo admin already exists.

## Proposed sole-approver policy

The owner's requested policy is that only their independently activated account
may admit or restore membership access. Account identity must be its immutable
database user ID, proven by `Owner_Admin_Activations`, never a username string,
public signup email or whoever is the first administrator.

Use an explicit persisted singleton policy with states `legacy`, `owner_only`
and `suspended`, a version, the verified owner user ID and an audit reference.
Creating a policy record must not change privileges automatically. Activation
requires a fresh authenticated owner session, recent password verification,
verified post-activation login, a private admin inventory and a recovery drill.
Record the transition atomically with the audit event. An absent, inactive or
demoted owner in `owner_only` must deny admissions, never fall back to other
admins. `suspended` denies admissions while preserving an audited recovery path.

| Surface | Required enforcement before enabling the policy |
| --- | --- |
| `review_membership_request` | Check active owner ID inside the same `BEGIN IMMEDIATE` transaction as each decision. Recheck privacy gates inside the lock. Preserve identity/eligibility checks and audit entries. |
| `list_membership_requests` and approvals UI | Restrict applicant contact details and decision history to the owner; hide controls for others and enforce again on the server. |
| `update_member_access` / Members panel | Prevent other admins from reactivating members or altering the owner. Fix the current inability to reinstate an approved then revoked member through a dedicated owner-reviewed reinstatement path; never bypass pending/rejected applications. |
| Invitations / public signup | Invitations remain inactive applications. No direct activation or role promotion. Limit invitation issuance to the owner if it would otherwise imply admission. |
| Member recovery | Consider recovery issuance an access-granting action: owner-only under this policy. Ordinary members can still change their own password after proving the current one. No admin-password recovery through the member flow. |
| Owner recovery | A fresh independently verified infrastructure/email challenge must not silently change the bound approver. Use a distinct, audited owner-transfer flow, invalidate superseded sessions and suspend admissions during transfer. |
| Emergency revocation | An audited emergency suspension may reduce access; it cannot grant access or transfer ownership. Never let an ordinary admin disable the sole owner without a defined recovery procedure. |
| Bootstrap / migrations | Neither startup nor environment-variable rotation may silently reset the policy, recreate a second approver or overwrite the current owner. |

Acceptance must cover owner success, ordinary-admin and member denial, stale
sessions, disabled owner, pending/rejected/reactivated accounts, concurrent
decisions, recovery transfer, policy corruption and restored older databases.
Check every underlying access mutation, not just menu visibility. Do not deploy
the policy until these tests and actual owner access are confirmed. No change to
existing investment, payment reconciliation or reporting privileges is implied.

## Snapshot and isolated restore tooling

`scripts/ledger_backup.py` is an operator CLI with no application dependencies.
It uses SQLite's online backup API, including committed WAL transactions. It
opens the source read-only, creates a new private directory and standalone
snapshot, checks SQLite integrity and foreign keys, and records a SHA-256
checksum, schema digest and per-table counts. It never reads credentials from
environment variables, imports the app, opens a web endpoint or uploads files.

On an approved machine with the authorized ledger already accessible, use
private directories on encrypted storage. Paths below are examples; substitute
the privately verified existing ledger path and storage locations. Do not guess
the production path or create a new empty ledger.

```sh
python scripts/ledger_backup.py create \
  --source /approved-private-location/ledger.sqlite3 \
  --destination /approved-encrypted-backups/khula-20261027.khula-backup

python scripts/ledger_backup.py verify \
  --snapshot /approved-encrypted-backups/khula-20261027.khula-backup \
  --work-dir /approved-encrypted-restore-work
```

`create` refuses an existing destination; failure removes only the new directory
it created. Directory mode is 0700, files 0600 on POSIX. `verify` checks the
manifest, copies the database into a new temporary directory, verifies the copy
and deletes that temporary directory on completion. It cannot replace the
running database. The source and existing snapshots are not overwritten.

The snapshot is **not encrypted by this script**. Filesystem permissions are
not encryption. Use approved encryption and separate access-controlled custody;
do not upload real snapshots into GitHub, ChatGPT or CI artifacts. The manifest
is a corruption check, **not a digital signature or proof of an independent
backup**. Keep a trusted checksum/evidence record separately. Temporary-file
deletion is not secure erasure; use encrypted scratch storage for real records.
The Docker image does not include this operator script yet, and there is no
scheduled production backup job in this change.

The automated tests use synthetic databases only. They cover committed and
uncommitted WAL data, corrupt files, changed manifests, foreign-key violations,
missing/wrong ledgers, symlink targets, overwrite refusal, private file modes,
disposable restore cleanup and unchanged source records.

## Production backup evidence still required

1. Confirm the actual database path, Railway backup capability/configuration,
   encrypted independent destination, authorized custodian, retention policy,
   backup frequency and recovery-time/recovery-point objectives.
2. Capture a consistent production snapshot in that approved destination.
   Record backup ID/time, trusted digest and custody/access details privately.
   A second file on the same `/data` volume is not an independent backup.
3. Retrieve from independent storage into an isolated encrypted workspace and
   run `verify`. Record elapsed recovery time and whether objectives are met.
4. Run application acceptance separately against that restored copy with network
   egress disabled and no live email, bank, AI, bootstrap or activation secrets.
   Check owner/admin access, member isolation, audit continuity, ledger totals
   and revocation history. The CLI's SQLite check does not establish these.
5. Before any future live restore, reconcile post-snapshot revocations and
   consumed one-time codes. Old snapshots can resurrect passwords, active
   accounts or replayable tokens. Disable setup, suspend admissions, invalidate
   restored sessions/recovery material and verify the bound owner before
   reopening. Obtain a pre-restore snapshot and explicitly review any live
   database replacement. Never restore over `/data` as an experiment.

## Privacy and first-member readiness

No new legal approval is asserted by this change. The current code's
`onboarding_gate_status` still requires real evidence for the responsible party,
privacy contact/notice, Information Officer registration, cross-border review,
operator safeguards and ratified constitution with matching text/version/hash.
The Railway variable-name inventory did not show those app approval fields;
independent documentary evidence and production gate verification remain open.
Do not fabricate flags or treat a checkbox as registration with a regulator.

Keep real-member onboarding and financial imports closed until the outstanding
privacy, owner-access and backup requirements are satisfied. Then use consenting
test members for inactive registration, owner review, login, personal-ledger
isolation and revocation. Bank API authorization remains a separate requirement;
manual snapshots must never be labelled verified bank API balances.
