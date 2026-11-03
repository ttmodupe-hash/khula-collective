# Khula Collective — privacy-first observability and adaptive UX

This release instruments the existing Streamlit experience without an external
analytics collector, browser fingerprinting, user-level clickstream, or changes
to the persistent financial/member ledger.

## Coverage, reliability and ethical boundaries

- Native navigation clicks: fixed feature labels, including dashboard, mentor,
  payments, and administrator actions. No arbitrary page URL or component label.
- Owner setup/recovery, login, membership applications, human approval/rejection,
  contribution claims and mentor questions: anonymous aggregate ok, blocked or
  failed outcomes and coarse server-side processing time.
- Live upstream roundtrips: licensed market-data, official SARB macro/market
  data, and (only if separately approved) the external AI tutor.
- Landing impressions are counted once *per consenting Streamlit session* to
  avoid double counting reruns. **This is not unique-user measurement.**
- Read-only SARB and licensed market-data requests use an in-process breaker:
  three consecutive upstream errors in a minute temporarily pause the
  source (15 to 120 seconds), retaining the existing official-source error
  and link instead of fabricating a quote. Bank and login workflows are
  never modified by this breaker. Process-local throttling resets on restart.
- The existing Streamlit cache protects sourced public APIs; a bounded 2x
  extension to the public cache TTL is allowed **only** after at least 20
  consenting API observations over seven days and >=50% observed errors.
  The displayed original observation dates remain mandatory. No fabricated
  financial data, private record caching or extra model calls.
- Existing fixed login lockouts, limited tutor AI budgets, member verification,
  POPIA gates and audit history remain authoritative and unchanged.
- All persistent telemetry entries are daily aggregates with one of a fixed
  allowlist of event labels and outcome labels, a count, sum and max of *rounded*
  latency. No user ID, email, IP, contact, session ID, timestamp finer than day,
  response body, question, card/bank detail or secret. **No third-party SDKs**.
- The separate SQLite file is beside the permanent DB
  (/data/khula-telemetry.sqlite3 in Railway production), never replaces
  the existing KHULA_DB_PATH, and expires counters older than 14 days on
  the next safe write. If its storage is unavailable or locked, recording
  fails open and cannot break club workflows.
- The administrator-only performance screen checks active administrator status
  against the original ledger before reading anonymous aggregates.
- popular_shortcuts() only suggests up to three non-privileged pages after a
  20-observation floor; it does not reorder required controls or consent.
- CSS feedback on native Streamlit buttons respects reduced-motion settings;
  no hover effects change layout dimensions. There is no optimistic approval,
  payment, or role mutation before authoritative server confirmation.

## Enabling production telemetry — do not invent approvals

Production metrics are **off by default** until the actual responsible party
has completed a reviewed telemetry-specific privacy notice/consent statement,
lawful cross-border assessment, and reviewed Railway operator terms. Require
**all** these genuine environment attestations before collection:

- KHULA_PRIVACY_NOTICE_APPROVED=1
- KHULA_CROSS_BORDER_REVIEW_APPROVED=1
- KHULA_OPERATOR_DPA_REVIEWED=1
- KHULA_TELEMETRY_POLICY_APPROVED=1

KHULA_TELEMETRY_ENABLED=0 is an additional immediate kill switch.
Even after approvals, each member or visitor must actively check:
"I agree to anonymous feature and performance counts." The checkbox
defaults off and applies only to the current browser session. Stopping
consent prevents further collection, and anonymous historical totals cannot
be attributed to one person. These toggles do NOT open real-member
registration or approve members. The separate club constitution, Information
Officer and overseas transfer prerequisites still apply.

**Current production:** absence of telemetry approval flags means zero
persistent interaction telemetry. Railway itself maintains platform HTTP
and resource metrics under its own terms, and these are not voluntary
application telemetry.

## Exact hooks for future features

    # Consent is checked automatically from the real Streamlit session.
    from khula_telemetry import note, note_once, timed

    # Explicit form or navigation action:
    note("nav.payments")
    note("member.application", "blocked", started=request_started_perf_counter)

    # Avoid double counting Streamlit reruns:
    note_once("screen.login")

    # External request: only elapsed time and success/failure recorded.
    with timed("api.sarb_macro"):
        resp = requests.get(OFFICIAL_SARB_URL, timeout=(4, 12))
        resp.raise_for_status()

Only fixed labels in EVENTS may be recorded. To add a new hook, review
whether its label could identify one person or protected attribute and
add source-based tests before extending the allowlist. Never attach an
arbitrary string, URL, error, username, query, financial figure,
database row or token.

## Feedback loop — not autonomous privilege changes

The dashboard highlights coarse sign-in, application or admission friction
when at least 20 observations have been counted and 40% or more are
blocked/failed. These are aggregate submission counts, not proven unique-user
drop-off or individual journey tracking. Operators must reproduce friction
with consented, non-sensitive test data before adjusting UX.

Sourced public API caches may respond to repeated failures through a bounded,
deterministic hint; no autonomous code rewriting, unreviewed financial
decisions, hidden approval changes, broad user profiling or secret-bearing
event capture is permitted. The metrics schema is idempotently created in
its own SQLite file, using a unique daily key as automatic index. It does not
rewrite or "heal" the financial ledger.

## Acceptance and rollback

1. Run python -m unittest discover -s tests -v including synthetic telemetry.
2. Run python scripts/smoke_member_pages.py (all member/admin pages).
3. Validate PWA, syntax, Docker imports and existing financial-controls.
4. In production verify the exact merged GitHub SHA, Railway SUCCESS, the
   unchanged domain and persistent /data volume attachment.
5. Until approved, confirm the admin performance view says collection is off.
   Do not add fake approval flags just to populate the dashboard.
6. Roll back app code via normal GitHub/Railway controls; setting
   KHULA_TELEMETRY_ENABLED=0 also stops collection after configuration
   takes effect. Never delete or replace a member/financial database.

Telemetry is not a replacement for Railway operational monitoring, signed
privacy governance, privileged activity audit, backups or incident response.
