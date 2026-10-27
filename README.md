# Khula Collective — savings and investment-club platform

A South African, member-governed collective savings platform. The October 2026
working branch combines the existing Streamlit v4 application with useful
capabilities recovered from the [original Khula Collective application](https://github.com/ttmodupe-hash/ttmodupe-hashttmodupe-hash-khula-collective-app).
**Development branch only: not approved for production financial records.**

## What actually works in this branch

- Invitation-only member signup (new members require administrator activation);
  strong bcrypt password storage and a controlled first-admin bootstrap.
- Member dashboards, profiles, group holdings, contribution progress and reporting.
- Payment *claims* requiring an administrator to check bank evidence before
  posting to the recorded paid ledger, with auditable decisions.
- Manual, administrator-attested club bank snapshots and reserved-funds tracking,
  distinctly labelled as **not a live FNB account balance**.
- Versioned **draft constitution acknowledgement**, group savings goals,
  time-limited member proposals and single-vote enforcement.
- Original Hall of Fame restored with member consent/visibility controls.
- Original WhatsApp reminder styles restored as copyable previews (no sends).
- An explainable investment research guide based on *available club cash* after
  reserves; projections start with 0% investment return, not invented yields.
- Optional Twelve Data quotes and FX when **a commercial/exchange data licence,
  API key and explicit launch flag** are configured. Quotes show actual provider
  timestamps and may be delayed. No fabricated market ticks.
- Optional consent-triggered OpenAI educational commentary (off by default).

**Not enabled**: real FNB/Stitch bank APIs, automated investment orders, card
payments, WhatsApp/Twilio sending, production FICA certification, and real-time
quote display without the requisite licensed market-data credentials.

See [Legacy feature parity and recovery plan](docs/LEGACY_PARITY.md) and
[Production readiness checklist](docs/PRODUCTION_READINESS.md).

## Start locally

```bash
python -m pip install -r requirements.txt
export KHULA_DEMO_MODE=1     # LOCAL DEMO ONLY; never use in production
streamlit run app.py
```

Demo mode creates non-real demonstration credentials and holdings and must never
be used for members' money. For proper onboarding without demo accounts, set
private `KHULA_BOOTSTRAP_ADMIN_USER` and `KHULA_BOOTSTRAP_ADMIN_PASSWORD`
(strong unique password at least 12 bytes), start the app, then remove the
bootstrap secret after account creation. On first login the bootstrap administrator
**must rotate the temporary password**. From the administrator menu, create a unique
seven-day, single-use invitation for each intended member email. Members are
inactive until the administrator confirms them. Shared invitation passwords
are no longer accepted.

## Production configuration — private Railway environment variables

| Variable | Meaning |
|---|---|
| `KHULA_PRODUCTION=1` | Reject relative/ephemeral DB paths at startup |
| `KHULA_DB_PATH=/data/khula_collective.db` | **Requires real mounted persistent volume** at `/data`; not just a directory |
| Member invitation codes | Created by an active administrator, email-bound, expiring and single-use; no shared environment secret |
| `KHULA_BOOTSTRAP_ADMIN_USER` / `KHULA_BOOTSTRAP_ADMIN_PASSWORD` | First admin only; remove once successfully provisioned |
| `KHULA_ENABLE_LEGACY_HASH_LOGIN=1` | Temporary, controlled migration of strong SHA-256 legacy passwords; normally off |
| `KHULA_MARKET_DATA_PROVIDER=twelvedata` | Market adapter selection |
| `KHULA_TWELVEDATA_API_KEY` | Secret data-provider key, never commit |
| `KHULA_MARKET_DATA_LICENSE_APPROVED=1` | Only enable once your commercial and exchange display rights are confirmed |
| `KHULA_AI_PROVIDER=openai` + `OPENAI_API_KEY` | Optional educational LLM calls; off without both |
| `KHULA_AI_MODEL` | Optional configured model name, default gpt-4o-mini |
| `KHULA_BANK_IMPORT_HMAC_KEY` | Private 32+ character secret to permit admin CSV evidence import with masked, keyed transaction identifiers |\n| `KHULA_ID_HMAC_KEY` | Keyed identifier digest (32+ characters); enable only after privacy review |
| `KHULA_ENABLE_ID_PRECHECK=1` | Optional local OCR-format check; **not** identity/FICA approval |
| `KHULA_ENABLE_PRIVATE_STATEMENT_IMPORT=1` | Permit private PDF/CSV imports only after privacy and retention review |
| `KHULA_WHATSAPP_GROUP_LINK` | Optional approved members-only group link |
| `KHULA_DEMO_MODE` | Keep **unset** in production |

Do not store secret values in the repository or GitHub workflow logs. Back up
the database with tested restore procedures before migrating any existing
member records. Old seeded files and demonstration user profiles are not
real bank balances or approved identities.

## Run checks

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py khula_*.py
```

GitHub Actions runs syntax, imports and core financial-control tests on push
and pull requests. A passing CI build is **not** a substitute for data-migration,
penetration, operational and compliance acceptance testing.

## Live pilot onboarding and real data

- The public landing/login screen can retrieve **actual, dated SARB economic indicators**
  from the official SARB Web API. Stale observations are labelled historical.
- Active administrators issue member-specific invitations from **Member Invitations**.
  New accounts cannot access financial records until manually activated.
- Members submit contribution claims; the administrator imports **actual club
  bank-exported CSV evidence** on the Reconciliation page. Raw CSVs are not retained.
  Each claim must be linked to one matching, unallocated incoming bank row before
  being marked paid. This is **manual reconciliation, not live bank API access**.
- The club's available cash is calculated only from an administrator-attested
  statement balance minus reserves and only if the snapshot is recent enough.
- The legacy repo remains untouched. Its SQLite file is seeded demonstration data,
  not proof of a bank balance or actual member identity.
- Enable **daily Railway volume backups** from the service's Backups tab and perform
  a test restore before relying on the ledger with real contributions.
- The app does not initiate a bank transfer, send investment orders, or send
  automated WhatsApp reminders.

## October 27, 2026: install Khula on a phone (PWA)

Members can **install Khula from its HTTPS website** on supported Android
and iPhone browsers, without an APK or an app-store listing. The public
login page and authenticated member sidebar provide a **📲 Install Khula**
link to an accessible installation guide.

- [Install page](https://khula-collective-production.up.railway.app/app/static/install.html)
- [Android and iPhone steps, security, acceptance](docs/MOBILE_INSTALL.md)
- The installable manifest is served at `/app/static/khula-manifest.json`
  with 192px/512px PNG icons, a standalone display and root start URL.
- The app requires internet access. **No service worker or offline financial
  data cache** is installed; access still requires an administrator-approved
  member account. Real-member privacy approval requirements remain unchanged.
- The root Streamlit HTML head is patched during Docker build from a pinned,
  local source script. CI verifies the installed framework's HTML format
  so upgrades do not silently break mobile installation.

## October 27, 2026: first-member pilot improvements

**Register → track → verify → approve → sign in** is now a visible,
auditable member journey. After a genuine legal/privacy sign-off, new
prospective adult members may request an account. Every public or
invitation-based application is inactive until independently reviewed by an
active club administrator via **Membership Approvals**.

A successful signup presents a private status-tracking code (45-day expiry,
digest-only storage). Visitors can check a non-identifying application status
from the public login page without exposing member information. No
transactional email service is assumed: approved/rejected email notices are
prepared as private copyable drafts in the administrator queue.

The protected **🚦 Launch Control** page reports current member/application
counts, missing POPIA/legal settings, SQLite quick-check results, the
manual-bank-snapshot freshness and **unverified** backup state. This page
cannot enable approvals or claim that FNB is connected.

The production compliance gate remains intentionally **fail closed** until
the responsible party provides genuine reviews and ratified documents.
Railway volume-backup creation/restoration must be verified externally.

Read the complete [real-member pilot runbook](docs/REAL_MEMBER_PILOT_RUNBOOK.md)
before sharing the signup flow beyond the club committee.

## October 27, 2026: public membership applications & Khula Compass

Visitors can **request a membership account without an invitation code** when
the club's verified POPIA and governance prerequisites permit actual member
onboarding. Every public application creates an inactive, non-admin account,
records privacy acknowledgement and overseas hosting consent, and appears in
the active club administrator's **Membership Approvals** queue.

**Registration alone never grants access.** The club administrator must
independently verify contact/identity and membership eligibility before
approving the applicant; rejection preserves a private audit record. Public
applications cannot be enabled with the generic active-account checkbox,
and ordinary members cannot assign themselves an administrator role.

Members who are approved see **Khula Compass**: actual ledger contributions,
savings goals, decisions, and a manual source-labelled cash snapshot with
age/reserve safeguards. No unverified deposit, portfolio value or historical
market price becomes spendable bank cash. Pending applicants cannot view
member reports or private data.

The production service remains **fail-closed** for new real-member details
until the responsible party records real privacy, Information Officer,
cloud-operator, overseas-transfer and constitution approvals. Do not set
review flags to `1` without genuine evidence. This is not regulator-issued
certification. The operator guide is in
[Public membership pilot](docs/PUBLIC_MEMBERSHIP_LIVE_PILOT.md).

## October 2026: member invitations and official FNB bank-access application

The **Member Invitations** admin page issues individual expiring codes with
ready-to-copy personal emails. Codes are never sent to a mailing list, and no
live members are silently imported from the old demonstration database.

**Production invitation/registration is intentionally blocked until the
Khula responsible party completes its POPIA and governance gates.** The public
login page explains the purposes of processing and shows the draft privacy
notice while the approval requirements are outstanding. Existing approved
member accounts are not affected by this new-registration hold.
The gate also requires the actual ratified constitution text, its approved
version and matching SHA-256 digest; the original draft cannot be accepted
as a final legal document.

The **FNB Bank Access** admin page prepares an application for the bank's
official **Transaction History API** and can record a genuine application
case reference. This does not imply an account is connected. The bank's actual
eligibility for a specific Khula Stokvel or business account, OAuth consent,
fees and data-residency requirements must be confirmed by FNB first.

Personalised investment allocations and share-affordability figures are
**disabled by default** pending a documented FSCA/FAIS assessment.
Contribution-only savings projections and official dated SARB research remain.

See:
- [POPIA, bank and FSCA readiness gates](docs/POPIA_FAIS_LAUNCH_GATES.md)
- [FNB API application scope](docs/FNB_READ_ONLY_INTEGRATION_APPLICATION.md)
- [Draft signatory authorisation](docs/FNB_SIGNATORY_RESOLUTION_TEMPLATE.md)
- [Member invitations](docs/MEMBER_INVITATION_POLICY.md)

## Important financial and regulatory limits

Khula's financial intelligence is **educational and read-only**. An attested
manual balance is not independent bank verification; never double-count
contributions and investment holdings. The application does not autonomously
select investments, initiate payments or execute orders. Confirm whether
any personalised investment advice feature requires a licensed financial
services provider under the South African FAIS/FSCA framework before launch.

Data providers are subject to contract, exchange and commercial display
restrictions. See the deployment checklist before setting any LIVE flags.
