# Khula Collective — production launch gates

**Current status: NOT YET CLEARED for real member money or personal ID uploads.**

## P0 — before deploying to real members

- [ ] Choose **one** canonical Railway production project. Currently two
  projects have successful container builds from the same repository with
  no public domains; do not confuse build success with tested application UX.
- [ ] Attach an actual persistent volume/database and set
  `KHULA_DB_PATH=/data/khula_collective.db`. Confirm the mount survives a new
  deployment and that backup **and restore** were tested on a disposable copy.
- [ ] Protect the production branch, require the new CI checks, test the PR on
  a non-production environment, and complete registration/admin/member UAT.
- [ ] Set `KHULA_PRODUCTION=1` and private admin bootstrap credentials, then
  remove the bootstrap password after first admin creation.
- [ ] Activate only genuinely approved members; enforce invitation handling,
  email verification and password reset/recovery before broad onboarding.
- [ ] Agree on correct contribution policy: old app says **R300 per member**
  whereas new v4 originally displayed **R500**. Configure member targets
  by admin after the collective ratifies them.
- [ ] Reconcile historic ledger entries marked paid before treating their
  totals as verified. New contribution claims require admin evidence review.
- [ ] Lock down sensitive APIs, Streamlit deployment, access logs and XSRF/CORS,
  set request rate limits, and perform independent authentication/privacy tests.
- [ ] Approve document privacy notices, retention/deletion, POPIA procedures,
  secure backup custody and relevant FICA/AML policies. Do not present checksum
  matching as identity verification.
- [ ] Resolve financial-product advice and intermediary regulatory obligations
  (FSCA/FAIS) and ensure professional supervision where required.

## P1 — live market data and financial intelligence

- [x] Transparent calculations use actual administrator-recorded bank snapshot
  less reserved cash; no double count of contributions or investment holdings.
- [x] Real quote/FX adapter validates provider response and displays the
  original quote timestamp and currency. No mock quote fallback.
- [ ] Select a Twelve Data **business** plan and obtain required
  South African/other exchange commercial display approvals. Confirm access
  for desired JSE symbols and contract rights. Add private key; enable
  `KHULA_MARKET_DATA_PROVIDER=twelvedata` and
  `KHULA_MARKET_DATA_LICENSE_APPROVED=1` only after approval.
- [ ] Check stock price units/denominations (some exchanges quote in cents),
  market hours, halted or stale prices, FX conversion and attribution.
- [ ] Obtain real read-only bank API access (FNB/Stitch or authorised provider),
  source bank transaction references, reconcile deposits, handle webhook
  replay/idempotency and separate cash from investable NAV.
- [ ] Add contribution targets, committed investment/payout liabilities and
  cash reserves according to the ratified club rules.
- [ ] If enabling OpenAI, approve a **separate** Khula AI budget/keys,
  service-rate and monthly spend caps, and a sensitive-data sharing policy.
  LLM descriptions must not fabricate returns or issue executable trades.

## P2 — recover remaining original capabilities

- [x] Versioned member constitution draft acknowledgement, goals,
  opt-in Hall of Fame and reminder templates.
- [x] Admin-reviewed payment claims and single-vote proposal controls.
- [ ] Move constitution to approved legally ratified version and documented
  digital signature/identity custody where required.
- [ ] Verify Twilio/WhatsApp opt-ins, STOP/unsubscribe, outbound-provider
  template approval and explicit delivery authorisation. No default sends.
- [ ] Review the legacy open automation PR and add safe jobs incrementally;
  do not merge unfinished banking placeholders.
- [ ] Add password reset, email verification, independent member activation
  audit, safer bank uploads, statement duplicate detection and a migration dry run.
- [ ] Mobile UAT/accessibility, browser testing and a practical member
  acceptance session before any public domain exposure.

## Config flags left intentionally off

- `KHULA_ENABLE_ID_PRECHECK`
- `KHULA_ENABLE_PRIVATE_STATEMENT_IMPORT`
- `KHULA_AI_PROVIDER`
- `KHULA_MARKET_DATA_LICENSE_APPROVED`
- `KHULA_DEMO_MODE` (must remain off)

## Source contracts and advice boundaries

Twelve Data's commercial-data terms require an appropriate business plan
and possible exchange-specific approvals. Yahoo/yfinance research feeds do
not automatically grant third-party commercial display rights.

In South Africa, financial-product advice may fall under FAIS/FSCA
authorisation. An AI output must stay educational and be subject to
professional and group-governance controls; a disclaimer alone does not
create a regulatory exemption.
