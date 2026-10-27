"""One-use, email-verified owner administration setup for Khula.

This is *not* public sign-up, a passwordless admin role toggle, or a bypass of
POPIA member-onboarding controls. An infrastructure owner must first configure
a 256-bit SHA-256 challenge digest and a short UTC expiry via their verified
Railway account. The plaintext challenge is delivered privately, never stored
in source control, Railway variables, database, logs, URLs or this UI after
consumption. The matching email is the verified Railway project-owner email.
"""
import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime, timezone, timedelta

import streamlit as st

from khula_security import hash_password

SHA256 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")
USERNAME = re.compile(r"^[a-z][a-z0-9_]{2,29}$")
SETUP_MAX_LIFETIME = timedelta(hours=24)
EXPIRES_FIELD = "KHULA_OWNER_SETUP_EXPIRES_UTC"
DIGEST_FIELD = "KHULA_OWNER_SETUP_TOKEN_SHA256"
EMAIL_FIELD = "KHULA_OWNER_SETUP_EMAIL"
DISABLED_FIELD = "KHULA_OWNER_SETUP_DISABLED"


def _settings(*, env=None, now=None):
    env = env if env is not None else os.environ
    now = now if now is not None else datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("Owner activation requires an aware timestamp.")
    email = str(env.get(EMAIL_FIELD, "")).strip().lower()
    digest = str(env.get(DIGEST_FIELD, "")).strip().lower()
    expires_raw = str(env.get(EXPIRES_FIELD, "")).strip()
    if env.get(DISABLED_FIELD) == "1":
        return None
    if not EMAIL_OK(email) or not SHA256.fullmatch(digest) or not expires_raw:
        return None
    try:
        expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if expires.tzinfo is None:
        return None
    expires = expires.astimezone(timezone.utc)
    if expires <= now or expires - now > SETUP_MAX_LIFETIME:
        return None
    return {"email": email, "digest": digest, "expires": expires}


def EMAIL_OK(value):
    return (isinstance(value, str) and len(value) <= 254
            and bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value)))


def owner_setup_available(*, env=None, now=None):
    """Only indicates a time-bounded recovery capability, never admin status."""
    return _settings(env=env, now=now) is not None


def ensure_owner_setup_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS Owner_Admin_Activations (
        activation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        challenge_sha256 TEXT NOT NULL UNIQUE,
        owner_user_id INTEGER NOT NULL UNIQUE,
        activated_at TEXT NOT NULL,
        FOREIGN KEY(owner_user_id) REFERENCES Users(user_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS Owner_Admin_Recovery_Uses (
        challenge_sha256 TEXT PRIMARY KEY,
        owner_user_id INTEGER NOT NULL,
        recovered_at TEXT NOT NULL,
        FOREIGN KEY(owner_user_id) REFERENCES Users(user_id)
    )""")


def activate_owner_admin(
        db_path, email, username, challenge, new_password, *,
        approved=False, env=None, now=None):
    """Create one new admin after private challenge/verified-email proof."""
    return _complete_owner_access(
        db_path, email, username, challenge, new_password,
        approved=approved, env=env, now=now, recover_existing=False,
    )["user_id"]


def setup_or_recover_owner_admin(
        db_path, email, username, challenge, new_password, *,
        approved=False, env=None, now=None):
    """A fresh owner challenge creates the first owner or resets that owner.

    Existing accounts require an owner-activation receipt, matching verified
    email and active admin status. Never claim a bootstrap account, promote a
    member, reactivate a suspended user or choose among duplicate owners.
    """
    return _complete_owner_access(
        db_path, email, username, challenge, new_password,
        approved=approved, env=env, now=now, recover_existing=True,
    )


def _complete_owner_access(
        db_path, email, username, challenge, new_password, *,
        approved, env, now, recover_existing):
    override_time = now
    now = now if now is not None else datetime.now(timezone.utc)
    settings = _settings(env=env, now=now)
    if not settings:
        raise ValueError("Owner activation is unavailable or has expired.")
    if approved is not True:
        raise ValueError("Confirm the official owner-only account setup.")
    candidate_email = str(email).strip().lower()
    if not EMAIL_OK(candidate_email):
        raise ValueError("Enter your verified project-owner email.")
    if not hmac.compare_digest(candidate_email, settings["email"]):
        raise ValueError("Owner activation details are invalid or expired.")
    if not isinstance(challenge, str) or not TOKEN.fullmatch(challenge):
        raise ValueError("Owner activation details are invalid or expired.")
    digest = hashlib.sha256(challenge.encode("ascii")).hexdigest()
    if not hmac.compare_digest(digest, settings["digest"]):
        raise ValueError("Owner activation details are invalid or expired.")
    username = str(username).strip().lower()
    hashed_password = hash_password(new_password)
    with sqlite3.connect(db_path, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        # Validate timing and challenge again after a potentially long DB lock.
        again = _settings(
            env=env,
            now=now if override_time is not None else datetime.now(timezone.utc),
        )
        if (not again or not hmac.compare_digest(again["digest"], settings["digest"])
                or not hmac.compare_digest(again["email"], settings["email"])):
            raise ValueError("Owner activation is unavailable or has expired.")
        ensure_owner_setup_table(conn)
        if conn.execute(
            "SELECT 1 FROM Owner_Admin_Activations WHERE challenge_sha256=? "
            "UNION ALL SELECT 1 FROM Owner_Admin_Recovery_Uses WHERE challenge_sha256=?",
            (digest, digest),
        ).fetchone():
            raise ValueError("This private code has already been used. Request a fresh owner code.")
        owners = conn.execute(
            "SELECT DISTINCT u.user_id,u.username,u.role,u.is_active "
            "FROM Users u JOIN Owner_Admin_Activations a ON a.owner_user_id=u.user_id "
            "WHERE LOWER(u.email)=? LIMIT 2", (settings["email"],),
        ).fetchall()
        timestamp = now.astimezone(timezone.utc).isoformat()
        if owners:
            if not recover_existing:
                raise ValueError("An owner account already exists. Use the owner recovery form.")
            if len(owners) != 1 or owners[0][2:] != ("admin", 1):
                raise ValueError("Owner recovery requires a verified active owner account. Contact the project operator.")
            owner_id, owner_username, _, _ = owners[0]
            conn.execute(
                "UPDATE Users SET password_hash=?,auth_epoch=auth_epoch+1,must_change_password=0 "
                "WHERE user_id=? AND role='admin' AND is_active=1",
                (hashed_password, owner_id),
            )
            from khula_security import _init_login_tracking
            _init_login_tracking(conn)
            conn.execute(
                "DELETE FROM Login_Attempts WHERE username IN (?,?)",
                (owner_username.lower(), settings["email"]),
            )
            conn.execute(
                "INSERT INTO Owner_Admin_Recovery_Uses "
                "(challenge_sha256,owner_user_id,recovered_at) VALUES (?,?,?)",
                (digest, owner_id, timestamp),
            )
            conn.execute(
                "INSERT INTO Admin_Actions(admin_user_id,action_type,details) VALUES (?,?,?)",
                (owner_id, "owner_admin_password_recovered",
                 "Fresh verified owner challenge; password reset and prior sessions revoked."),
            )
            return {"user_id": owner_id, "username": owner_username, "action": "recovered"}
        if not USERNAME.fullmatch(username):
            raise ValueError("Choose a username of 3–30 letters, numbers or underscores, starting with a letter.")
        if conn.execute(
            "SELECT 1 FROM Users WHERE LOWER(username)=?",
            (username,),
        ).fetchone():
            raise ValueError("That username belongs to another account. Choose a different unused username for first-time owner setup.")
        try:
            cur = conn.execute(
                "INSERT INTO Users "
                "(username,full_name,email,password_hash,role,join_date,is_active,"
                "auth_epoch,must_change_password,fica_verified) "
                "VALUES (?,?,?,?,'admin',?,1,0,0,0)",
                (username, "Khula Platform Owner", settings["email"],
                 hashed_password, timestamp),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("Administrator username unavailable.") from exc
        new_user_id = cur.lastrowid
        conn.execute(
            "INSERT INTO Owner_Admin_Activations "
            "(challenge_sha256,owner_user_id,activated_at) VALUES (?,?,?)",
            (digest, new_user_id, timestamp),
        )
        conn.execute(
            "INSERT INTO Admin_Actions(admin_user_id,action_type,details) "
            "VALUES (?,?,?)",
            (new_user_id, "owner_admin_activated",
             "Verified Railway-owner email challenge; new owner account created."),
        )
    return {"user_id": new_user_id, "username": username, "action": "activated"}


def render_owner_setup():
    """Render only from the owner's email-linked, token-free setup URL."""
    from khula_config import DB_PATH
    if st.query_params.get("owner_setup") != "1":
        return
    with st.container(border=True):
        st.subheader("🔐 Set up or recover your Khula owner login")
        st.caption(
            "Use a fresh code from your private owner email to set a new password. "
            "If you already activated an owner account, this resets that same account "
            "and shows your username. Old sessions will be signed out."
        )
        if not owner_setup_available():
            st.warning(
                "The private owner code is unavailable or expired. "
                "Use your existing administrator login or request "
                "a new activation through the verified Railway project."
            )
            return
        with st.form("khula_owner_activation_form"):
            owner_email = st.text_input(
                "Your verified Railway account email", key="owner_verified_email"
            )
            activation_code = st.text_input(
                "Private one-time activation code", type="password",
                key="owner_private_activation_code",
            )
            username = st.text_input(
                "Username for first-time setup only", value="khula_owner",
                help="An existing verified owner keeps its username. If this name belongs to another account, choose a new unused name.",
                key="owner_admin_username"
            )
            password = st.text_input(
                "New administrator password (12–72 UTF-8 bytes)",
                type="password", key="owner_admin_password"
            )
            confirmation = st.text_input(
                "Confirm administrator password",
                type="password", key="owner_admin_password_confirmation"
            )
            approval = st.checkbox(
                "I control the verified Railway project-owner email, "
                "consent to my administrator account and password hash being "
                "stored in Khula's disclosed Railway hosting region, and "
                "authorise first-time setup or a password reset of my previously "
                "activated owner account, and understand it can review private membership requests.",
                key="owner_admin_confirm",
            )
            submit = st.form_submit_button(
                "Save my new owner password", type="primary",
                use_container_width=True,
            )
        if submit:
            if password != confirmation:
                st.error("The administrator passwords do not match.")
            else:
                try:
                    result = setup_or_recover_owner_admin(
                        DB_PATH, owner_email, username, activation_code,
                        password, approved=approval,
                    )
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
                else:
                    # Clear the entire public Streamlit session after a
                    # privileged recovery (including form-widget secrets).
                    # The next run displays only a non-secret success notice.
                    st.session_state.clear()
                    st.session_state["_khula_owner_setup_complete"] = result["username"]
                    st.query_params.clear()
                    st.rerun()
