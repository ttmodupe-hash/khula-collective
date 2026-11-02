"""Consent-first, aggregate-only instrumentation for Khula.

No identifier, URL, email, IP, user input, token, financial value, exception
message or session history is accepted by this API. This is NOT an audit log.
Privileged membership/financial actions retain their existing audit ledger.

Production telemetry stays OFF until the reviewed opt-in privacy notice,
cross-border assessment, cloud operator safeguards and a dedicated telemetry
approval are explicitly configured. A user's per-session opt-in is also needed.
The isolated SQLite metrics database lives beside -- not inside or instead of
-- the existing persisted member ledger, and retains only 14 days of daily
aggregate counters. No analytics vendors or remote telemetry calls are used.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import os
import sqlite3
import time

RETENTION_DAYS = 14
CONSENT_KEY = "khula_anonymous_telemetry_consent"
NAV_PAGES = frozenset({
    "dashboard", "fnb_sync", "payments", "features", "mentor", "voice",
    "constitution", "goals", "economy", "leaderboard", "directory",
    "notifications", "reports", "ai_advisor", "global_markets", "whatsapp",
    "fnb_api_guide", "admin", "membership_approvals", "launch_center",
    "reconciliation", "invites", "bank_access", "compliance", "recoveries",
    "id_verify", "profile", "telemetry",
})
EVENTS = frozenset({
    "screen.login", "auth.login", "owner.setup", "member.application",
    "member.review", "member.approval", "member.rejection", "payment.claim",
    "mentor.ask", "api.sarb_macro", "api.sarb_markets", "api.licensed_market",
    "api.mentor",
}) | frozenset("nav." + page for page in NAV_PAGES)
OUTCOMES = frozenset({"ok", "failed", "blocked", "cache"})
# The following flags must represent real, external approval, not auto-attestation.
PRODUCTION_APPROVALS = (
    "KHULA_PRIVACY_NOTICE_APPROVED",
    "KHULA_CROSS_BORDER_REVIEW_APPROVED",
    "KHULA_OPERATOR_DPA_REVIEWED",
    "KHULA_TELEMETRY_POLICY_APPROVED",
)


def telemetry_permitted(env=None):
    env = os.environ if env is None else env
    if env.get("KHULA_TELEMETRY_ENABLED", "1") != "1":
        return False
    live = (env.get("KHULA_PRODUCTION") == "1"
            or env.get("RAILWAY_ENVIRONMENT_NAME", "").lower() == "production")
    return not live or all(env.get(key) == "1" for key in PRODUCTION_APPROVALS)


def _metric_path(db_path=None):
    if db_path is not None:
        return Path(db_path)
    # The runtime verifies the persistent /data mount *before* application
    # startup. An isolated file prevents telemetry from locking/replacing the
    # private member/financial ledger.
    from khula_config import DB_PATH
    return Path(DB_PATH).resolve().with_name("khula-telemetry.sqlite3")


def _bounded_latency(duration_ms):
    if (type(duration_ms) not in (int, float)
            or not math.isfinite(duration_ms)):
        return 0
    # Coarse resolution, bounded cardinality and no microsecond fingerprint.
    return (int(max(0, min(60000, duration_ms))) // 100) * 100


def record(event, outcome="ok", *, duration_ms=0, consent=False,
           db_path=None, env=None, now=None):
    """Store one anonymous DAILY aggregate; never record unapproved labels.

    Telemetry failure must never cause an authentication, payment or compliance
    decision to fail. No event-level timestamps or session identifiers persist.
    """
    if consent is not True or not telemetry_permitted(env):
        return False
    if event not in EVENTS or outcome not in OUTCOMES:
        raise ValueError("Telemetry event and outcome must be fixed safe labels.")
    timestamp = datetime.now(timezone.utc) if now is None else now
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None:
        raise ValueError("Telemetry requires an aware timestamp.")
    day = timestamp.astimezone(timezone.utc).date().isoformat()
    cutoff = (timestamp.astimezone(timezone.utc).date()
              - timedelta(days=RETENTION_DAYS)).isoformat()
    latency = _bounded_latency(duration_ms)
    target = _metric_path(db_path)
    # Never follow a symlink or a misconfigured telemetry file into the
    # permanent member/financial ledger.
    from khula_config import DB_PATH
    if target.is_symlink() or target.resolve() == Path(DB_PATH).resolve():
        return False
    try:
        # No mkdir: production ledger mount must already be provisioned.
        with sqlite3.connect(str(target), timeout=0.2) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS Telemetry_Daily (
                utc_day TEXT NOT NULL,
                event TEXT NOT NULL,
                outcome TEXT NOT NULL,
                samples INTEGER NOT NULL DEFAULT 0 CHECK(samples>=0),
                total_latency_ms INTEGER NOT NULL DEFAULT 0,
                max_latency_ms INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (utc_day,event,outcome)
            )""")
            conn.execute("""INSERT INTO Telemetry_Daily
                (utc_day,event,outcome,samples,total_latency_ms,max_latency_ms)
                VALUES (?,?,?,1,?,?)
                ON CONFLICT(utc_day,event,outcome) DO UPDATE SET
                samples=samples+1,
                total_latency_ms=total_latency_ms+excluded.total_latency_ms,
                max_latency_ms=MAX(max_latency_ms,excluded.max_latency_ms)
            """, (day, event, outcome, latency, latency))
            conn.execute("DELETE FROM Telemetry_Daily WHERE utc_day<?", (cutoff,))
        return True
    except (OSError, sqlite3.Error):
        return False


def consented():
    """Only a real Streamlit session may opt in. Tests and background calls are off."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx(suppress_warning=True) is None:
            return False
        import streamlit as st
        return st.session_state.get(CONSENT_KEY) is True
    except (ImportError, RuntimeError, AttributeError):
        return False


def note(event, outcome="ok", *, started=None):
    """Safe UI/backend hook. No free-form properties, payload or user ID."""
    duration = (time.perf_counter() - started) * 1000 if started is not None else 0
    return record(event, outcome, duration_ms=duration, consent=consented())


def note_once(event):
    if not consented():
        return False
    import streamlit as st
    # Avoid counting Streamlit form reruns as a new page visit.
    key = "_khula_observed_" + event.replace(".", "_")
    if st.session_state.get(key):
        return False
    ok = note(event)
    if ok:
        st.session_state[key] = True
    return ok


@contextmanager
def timed(event):
    """Track a fixed API operation's latency/outcome, never its request/response."""
    if event not in EVENTS or not event.startswith("api."):
        raise ValueError("Only allowlisted API operations may be timed.")
    started = time.perf_counter()
    try:
        yield
    except Exception:
        note(event, "failed", started=started)
        raise
    else:
        note(event, "ok", started=started)


def render_consent():
    """Visible opt-in without browser fingerprinting or third-party scripts."""
    import streamlit as st
    with st.expander("Help improve Khula (optional)", expanded=False):
        st.caption(
            "With your permission, Khula counts only broad feature actions and "
            "rounded response times per UTC day on its Railway storage. "
            "No account, contact, banking, message, password or browser details "
            "are recorded. Data is deleted after 14 days. Turning this off "
            "stops new collection; anonymous past totals cannot identify you."
        )
        if not telemetry_permitted():
            st.info("Optional analytics are paused pending verified privacy and overseas-hosting approvals.")
            return
        st.checkbox(
            "I agree to anonymous feature and performance counts",
            value=False, key=CONSENT_KEY,
        )


def _rows(path, days=7):
    target = _metric_path(path)
    from khula_config import DB_PATH
    if (target.is_symlink() or target.resolve() == Path(DB_PATH).resolve()
            or not target.is_file()):
        return []
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    try:
        with sqlite3.connect(str(target), timeout=0.2) as conn:
            return conn.execute(
                "SELECT utc_day,event,outcome,samples,total_latency_ms,max_latency_ms "
                "FROM Telemetry_Daily WHERE utc_day>=? "
                "ORDER BY utc_day DESC,event,outcome LIMIT 500",
                (cutoff,),
            ).fetchall()
    except (OSError, sqlite3.Error):
        return []


def metrics_for_admin(member_db_path, admin_id, *, metric_db_path=None, env=None):
    """Require fresh DB-backed administrator status, never session state alone."""
    with sqlite3.connect(member_db_path, timeout=1) as conn:
        account = conn.execute(
            "SELECT 1 FROM Users WHERE user_id=? AND role='admin' AND is_active=1",
            (admin_id,),
        ).fetchone()
    if not account:
        raise PermissionError("Active administrator required.")
    if not telemetry_permitted(env):
        return {"enabled": False, "rows": [], "sample_count": 0}
    rows = _rows(metric_db_path)
    return {
        "enabled": True,
        "rows": [
            {"UTC day": day, "Action": event, "Outcome": outcome, "Count": n,
             "Mean latency (ms)": round(total / n) if n else 0,
             "Max latency (ms)": maximum}
            for day, event, outcome, n, total, maximum in rows
        ],
        "sample_count": sum(r[3] for r in rows),
    }


def adaptive_cache_ttl(event, base_seconds, *, max_seconds=None,
                       metric_db_path=None, env=None):
    """Safe global cache hint: prolong PUBLIC reads after repeat upstream errors.

    Never changes auth/payment/approval caching or serves fabricated quotes.
    Baseline remains unchanged until >=20 opt-in observations for this API.
    """
    if (event not in ("api.sarb_macro", "api.sarb_markets")
            or type(base_seconds) is not int or base_seconds <= 0):
        raise ValueError("Only public sourced data may use adaptive caching.")
    ceiling = min(int(max_seconds or base_seconds * 2), base_seconds * 2)
    if ceiling < base_seconds or not telemetry_permitted(env):
        return base_seconds
    rows = [r for r in _rows(metric_db_path) if r[1] == event]
    total = sum(r[3] for r in rows)
    failed = sum(r[3] for r in rows if r[2] == "failed")
    return min(ceiling, base_seconds * 2) if total >= 20 and failed * 2 >= total else base_seconds


def popular_shortcuts(*, metric_db_path=None, env=None, minimum_samples=20):
    """Aggregate-only, stable optional links; privileged menu remains unchanged."""
    if not telemetry_permitted(env):
        return []
    public_pages = ("dashboard", "payments", "mentor", "goals", "economy",
                    "constitution", "reports", "features", "profile")
    counts = {key: 0 for key in public_pages}
    for _, event, outcome, n, _, _ in _rows(metric_db_path):
        if outcome == "ok" and event.startswith("nav."):
            page = event[4:]
            if page in counts:
                counts[page] += n
    if sum(counts.values()) < minimum_samples:
        return []
    return sorted(public_pages, key=lambda p: (-counts[p], public_pages.index(p)))[:3]


def render_admin_dashboard(member_db_path, admin_id):
    import streamlit as st
    status = metrics_for_admin(member_db_path, admin_id)
    st.title("📊 Khula performance & friction")
    if not status["enabled"]:
        st.info("Anonymous interaction counts are OFF until separate, genuine privacy and hosting approvals are configured.")
        return
    st.metric("Anonymous action counts (last 7 days)", status["sample_count"])
    if not status["rows"]:
        st.info("No consenting interactions measured yet.")
        return
    st.dataframe(status["rows"], hide_index=True, use_container_width=True)
    rows = status["rows"]
    for event, label in (
        ("auth.login", "Sign-in"),
        ("member.application", "Membership request"),
        ("member.approval", "Membership review"),
    ):
        group = [r for r in rows if r["Action"] == event]
        total = sum(r["Count"] for r in group)
        problems = sum(r["Count"] for r in group if r["Outcome"] in ("failed", "blocked"))
        if total >= 20 and problems / total >= 0.4:
            st.warning(f"{label}: {problems}/{total} counted attempts were blocked or unsuccessful. Review usability without weakening authorisation.")
    st.caption(
        "Only coarse daily aggregate actions/latencies; no individual journeys, "
        "unique-user drop-off claims, content or audit evidence. "
        "No telemetry affects security or payment decisions."
    )
