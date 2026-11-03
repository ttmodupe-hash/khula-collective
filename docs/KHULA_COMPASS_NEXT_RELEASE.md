# Khula Compass — next release proposal

**Planning draft, 27 October 2026** · Build on Khula v4 and the original club
repository without inventing banking data, real members or product advice.

## Product promise

A transparent, mobile-first member-governance and collective savings platform
for South Africa. Every material amount must disclose where it came from,
when it was last reviewed and whether it is independent bank evidence,
administrator-attested, pending or illustrative.

## P0 — protection before real members

- [ ] Complete POPIA Information Officer, cloud/overseas-transfer and
  operator-agreement review, final ratified club constitution and the
  contribution policy. Do not bypass onboarding gates using placeholder
  environment variables.
- [ ] Audit all member pages and exported reports for cross-member disclosure.
  The accompanying PR protects **Reports** and **Member Directory** with
  database-checked role constraints and privacy regression tests.
- [ ] Configure verified email delivery and email validation for invited
  members; do not send one-use invitation codes through public group chats.
  Provide welcome, approval, rejection and consent-update emails only after
  a verified domain has correct SPF, DKIM and DMARC.
- [ ] Remove temporary admin bootstrap secrets from production after
  documented successful password rotation; enforce MFA for privileged users.
- [ ] Test automated daily encrypted ledger backups and an isolated restore.
  Confirm audit-log retention, breach response, rate limits, security scans
  and the approved hosting region, or migrate to a suitable data store.

## P1 — Khula Compass, the signature member experience

One clear dashboard for each member and an expanded role-scoped treasurer view.

- **Club cash**: Latest source-labelled bank balance, original observation
  date, freshness, last reconciliation, ledger/bank variance and any missing
  evidence. Never treat a manually attested balance as bank API-verified.
- **Available to plan**: Only evidenced cash minus explicitly recorded
  reserved funds, approved but unpaid withdrawals, committed club purchases,
  known fees/liabilities, with no duplicate deduction or addition of holdings.
  Any missing required input means "Not verified" rather than a confident
  investable amount.
- **My contributions**: Member's own due/paid/pending/rejected amounts and
  private evidence-linked payment progress; no other member's amounts unless
  they independently opted into the Hall of Fame.
- **Club milestones**: Progress against ratified savings targets, cash buffers
  and forthcoming commitments.
- **What needs a decision?**: Member proposals to vote on, meeting minutes
  to acknowledge and a clear "Nothing to approve" state.
- **Where does this figure come from?**: Each value opens an age/source
  explanation; only authorised administrators can access individual bank
  references. No fictional market headlines or guaranteed investment returns.

### Acceptance tests

1. Member A never sees Member B's total, email, phone, FICA status or bank
   reference through charts, CSVs, page state or data queries.
2. A pending deposit claim does not increase paid contributions or cash.
   Matched bank transactions can be allocated exactly once.
3. Club bank cash and investment NAV are separately labelled and never added
   together as investable funds.
4. An out-of-date or missing club bank snapshot blocks affordability
   and product-level financial actions.
5. A recorded reserve or approved unpaid withdrawal reduces the available
   amount only once, with an audit trail and reversible correction procedure.
6. Mobile member UAT covers invitation, privacy consent, first login,
   password recovery, payment-claim submission and proposal voting.

## P1 — modern governance and treasury controls

- Implement an append-only, balanced transaction journal with account codes,
  amount in integer cents/Decimal, idempotency keys, immutable source
  identifiers and corrections by reversal—not quiet row overwrites.
- Require dual sign-off for withdrawals, cash transfers, investment
  commitments, membership policy changes and high-risk administrator actions.
  One person must not both propose and independently approve the same
  financial disbursement.
- Add constitution-bound quorum, eligibility dates, conflicts-of-interest,
  voting window, meeting resolution PDF and signer/decision audit evidence.
  **Votes and approvals are not instructions for the app to move money.**
- Investment holdings require broker/custodian reference, price currency,
  timestamp, valuation source, fees and separate reconciliation status.
  Administrator-entered values remain labelled "unverified holdings".
- Add treasurer reconciliation exceptions with categories:
  Unmatched deposit, Possible duplicate, Refund pending, Old balance,
  Unverified investment valuation, Reserve missing and Incomplete sign-off.

## P2 — richer intelligence while FNB is pending

- Offer an **educational "What if we save..." lab** for 10–20 members,
  different contribution targets, liquidity buffers and payment consistency,
  clearly marked as scenarios, not actual balances.
- Add sourced and date-labelled SARB rates, Treasury bill / government bond
  references and financial education cards. Do not call historical rates
  current investment offers or imply they are achievable.
- Build a **Khula Learning Assistant** to explain club terms, cash-flow
  concepts, emergency funds, inflation, diversification, compound growth,
  investment risks and the ratified constitution. It must distinguish
  actual data from simulated or incomplete data and cite the source.
- Individualised financial-product buy/sell/allocation recommendations remain
  disabled until a specialist FAIS/FSCA review and appropriate authorisation.
  For regulated automated advice, document suitability, algorithm testing,
  human review and an emergency stop before activation.

## P2 — ready when FNB grants access

- Read-only, consented Transaction History API integration for bank-selected
  accounts with narrow scopes and bank-approved OAuth flow.
- Scheduled incremental retrieval with duplicate/reversal handling, daily
  balancing, provenance timestamps, error alerts and consent revocation.
- Actual bank-source verification before any balance is labelled "live".
- Continue manually imported CSV evidence as a clearly labelled fallback
  while API access is unavailable.

## P3 — delightful, inclusive member experience

- Mobile-first progressive web app (PWA), easy install, fast load, low-data
  screens, simple accessible navigation and print/PDF reports.
- Optional isiZulu, Sesotho, Setswana and English language experiences after
  translation checks; no unreviewed translation of legal terms.
- Private opt-in payment reminders and member achievement badges without
  public shaming, and consent-respecting WhatsApp/email integrations.
- Smart but explainable admin insights: overdue reconciliation, upcoming vote
  deadlines, absent treasury evidence, unreviewed withdrawals, missing backup
  verification—not automated financial transfers.

## Healthy product metrics

- Invitation accepted → signup completed → identity/club approval → first
  successful login → first documented contribution.
- % of incoming bank credits reconciled, unmatched/duplicate count,
  last source update, age of bank snapshot, restore-test date.
- Monthly active approved members, voting participation, goal comprehension,
  support requests and zero unauthorised cross-member data exposure.

## Costs and permissions

Keep all new services disabled by default until they have an approved cost,
credentials, privacy terms and operational owner. Avoid commercial live market
licenses, mass outbound messaging and expensive model calls until confirmed
usage justifies them.

Primary dependencies: formal Khula club constitution, verified real signatories,
POPIA review, commercial bank API authorisation, custody evidence and actual
member consent. A nice dashboard is not proof of legal or banking compliance.
