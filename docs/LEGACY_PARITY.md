# Khula Collective — legacy feature parity and data-safety recovery

Reviewed: 2026-10-26
Source of truth for historical features:
- [Original repository](https://github.com/ttmodupe-hash/ttmodupe-hashttmodupe-hash-khula-collective-app)
- Files `khula_final.py`, `khula_database.py`, `khula_ai_advisor.py`, `khula_whatsapp.py`, `khula_schema.sql`
- Its [unmerged automation PR #1](https://github.com/ttmodupe-hash/ttmodupe-hashttmodupe-hash-khula-collective-app/pull/1).
- [Current v4 repository](https://github.com/ttmodupe-hash/khula-collective).

**IMPORTANT**: The original code includes demonstration members, fixed R300
targets, assumed income yields and optimistic descriptions of live integrations.
These cannot be imported blindly into a club-handling financial application.

## Feature-by-feature matrix

| Original Khula capability | State in this v4 branch | Important gap / next action |
|---|---|---|
| Member accounts & registration | **Restored and strengthened** | Invitation code + admin activation; add email verification/reset and session expiry before launch |
| Admin and membership management | **Present** | Add change audit for all admin access changes and tighter data permissions |
| RICA cellphone, FICA ID/docs | **Partial / gated** | Preliminary ID format checking only; independent verification, safe document custody, consent and retention still required |
| Individual payment progress | **Restored and corrected** | Member submits unverified claim, admin attests bank evidence before ledger posting |
| Contribution arrears and monthly targets | **Present and admin-governed** | Earlier app says R300, v4 R500; ratify a single rule; reconcile prior records before arrears enforcement |
| Manual bank transaction import | **Present, gated** | Review storage/access/retention; uploaded personal statements are NOT automatic club receipts |
| FNB banking API | **Not connected** | Earlier v4 had simulated tokens/transactions; removed fake success. Obtain approved bank API access |
| Stitch integration | **Not connected** | Old `khula_final.py` built auth/GraphQL skeleton but returned success without persisting parsed transactions; design real OAuth, webhooks and reconciliation |
| Club bank balance / total pot | **Partially restored** | Admin-attested snapshot minus reserve, explicitly not independently/live bank verified |
| Investment tracking | **Present** | Reconcile actual holdings, prices, fees, NAV and ownership with custody statements |
| Member proposal voting | **Present, hardened** | One active member vote per proposal, enforced deadline and atomic tally; legal investment approval policy still needed |
| Constitution signing | **Restored as draft acknowledgement** | Content requires member ratification; replace with approved version, secure signed documents and authoritative retention |
| Collective savings goals | **Restored** | Add richer monthly milestones/progress alerts after source reconciliation |
| Hall of Fame leaderboard | **Restored with opt-in privacy** | Records marked paid pre-migration require independent verification |
| WhatsApp payment/welcome/milestone templates | **Restored as previews** | Explicit consent, Twilio Business setup, STOP handling, deliverability, costs and audit before sends |
| 12-month savings projections | **Improved** | Deterministic 0%-return scenarios and longer horizons, no fabricated market forecast |
| Old AI investment recommendations | **Replaced for active UI** | Risk/horizon educational buckets, actual available cash, optional controlled LLM explanation; no personalised product advice by default |
| Global equity/FX quotes | **Real API adapter implemented** | Requires approved Twelve Data commercial/exchange display licence and key; checked timestamps, error handling and FX conversion |
| Reports / CSV export | **Present** | Restrict personal data exports to administrators; add permission tests and PDF reports after legal/layout review |
| Mobile navigation/dark theme | **Existing v4** | Run accessible mobile/browser UAT and add PWA only if desired |
| Scheduled FNB/monthly automations | **Not merged** | Earlier repository PR #1 remains open; evaluate scripts individually, do not automatically enable bank sync or send messages |
| Supabase/PostgreSQL proposal | **Not migrated** | Review original PR schema/row-level security; select durable database and rehearse migration before production |

## Migration principles

1. Freeze backup and create a checksum for the actual *authoritative* member
   database outside GitHub, with proper user consent and access control.
   Never take the old committed `khula_collective.db` as production truth.
2. Map users by a verified club-issued identifier after separate identity
   checks. Do not assume legacy usernames or hashes imply verified identity.
3. Compare the old database schema (original `khula_schema.sql`) with
   today's schema and document each mapping. Legacy `Transactions`,
   `GlobalAccountSync`, `Monthly_Contributions` and `Investment_Goals`
   have different field meanings and status rules.
4. Reconcile bank cash independently, validate opening balances, ensure
   investments and contributions are not double-counted, and retain source
   evidence before writing financial opening balances.
5. **Never** import old seeded users' identities, old weak/demo login passwords,
   financial projections or suggested annual returns as factual production data.
6. Make the import an explicit, backed-up, dry-run-reviewed migration with
   a reversible cutover. Do not auto-run on Streamlit page loads.
7. Release individual capabilities only after financial controls, POPIA,
   FSCA/FAIS and provider contract checks are documented and signed off.

## Distinctive direction

The long-term Khula experience should integrate member governance, banking
truth, contribution accountability, transparent club goals, savings-aware
investing education, African/South African market coverage, opt-in community
recognition, and source-labelled research — not just a generic stocks chatbot.
Decisions that move club money must always require an authorised human,
independent reconciliation and governance approvals.

No code or data has been copied or overwritten in the original repository.
