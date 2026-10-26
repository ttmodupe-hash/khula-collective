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
bootstrap secret after account creation. Set a private `KHULA_INVITE_CODE`
(at least 12 characters) for member sign-up. Members are initially inactive
until the admin activates them.

## Production configuration — private Railway environment variables

| Variable | Meaning |
|---|---|
| `KHULA_PRODUCTION=1` | Reject relative/ephemeral DB paths at startup |
| `KHULA_DB_PATH=/data/khula_collective.db` | **Requires real mounted persistent volume** at `/data`; not just a directory |
| `KHULA_INVITE_CODE` | Private member invitation code; choose a strong value |
| `KHULA_BOOTSTRAP_ADMIN_USER` / `KHULA_BOOTSTRAP_ADMIN_PASSWORD` | First admin only; remove once successfully provisioned |
| `KHULA_ENABLE_LEGACY_HASH_LOGIN=1` | Temporary, controlled migration of strong SHA-256 legacy passwords; normally off |
| `KHULA_MARKET_DATA_PROVIDER=twelvedata` | Market adapter selection |
| `KHULA_TWELVEDATA_API_KEY` | Secret data-provider key, never commit |
| `KHULA_MARKET_DATA_LICENSE_APPROVED=1` | Only enable once your commercial and exchange display rights are confirmed |
| `KHULA_AI_PROVIDER=openai` + `OPENAI_API_KEY` | Optional educational LLM calls; off without both |
| `KHULA_AI_MODEL` | Optional configured model name, default gpt-4o-mini |
| `KHULA_ID_HMAC_KEY` | Keyed identifier digest (32+ characters); enable only after privacy review |
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

## Important financial and regulatory limits

Khula's financial intelligence is **educational and read-only**. An attested
manual balance is not independent bank verification; never double-count
contributions and investment holdings. The application does not autonomously
select investments, initiate payments or execute orders. Confirm whether
any personalised investment advice feature requires a licensed financial
services provider under the South African FAIS/FSCA framework before launch.

Data providers are subject to contract, exchange and commercial display
restrictions. See the deployment checklist before setting any LIVE flags.
