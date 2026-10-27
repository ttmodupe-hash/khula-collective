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


def activate_owner_admin(
        db_path, email, username, challenge, new_password, *,
        approved=False, env=None, now=None):
    """Create one new admin after private challenge/verified-email proof.

    An existing user is *never* silently promoted, overwritten or deactivated.
    Explicitly creates a separate administrator account instead. The token
    and user write are atomic. No financial, club or member data is touched.
    """
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
    if not USERNAME.fullmatch(username):
        raise ValueError("Choose a username of 3–30 letters, numbers or underscores.")
    hashed_password = hash_password(new_password)
    with sqlite3.connect(db_path, timeout=15) as conn:
        conn.execute("BEGIN IMMEDIATE")
        # Validate timing again after a potentially long database lock.
        if _settings(env=env, now=datetime.now(timezone.utc) if now is None else now) is None:
            raise ValueError("Owner activation is unavailable or has expired.")
        ensure_owner_setup_table(conn)
        if conn.execute(
            "SELECT 1 FROM Owner_Admin_Activations WHERE challenge_sha256=?",
            (digest,),
        ).fetchone():
            raise ValueError("This activation code has already been used.")
        if conn.execute(
            "SELECT 1 FROM Users WHERE LOWER(username)=?",
            (username,),
        ).fetchone():
            raise ValueError("That administrator username is already in use.")
        timestamp = now.astimezone(timezone.utc).isoformat()
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
    return new_user_id


def render_owner_setup():
    """Render only from the owner's email-linked, token-free setup URL."""
    from khula_config import DB_PATH
    if st.query_params.get("owner_setup") != "1":
        return
    with st.container(border=True):
        st.subheader("🔐 Khula owner administrator activation")
        st.caption(
            "Only the verified Railway account owner may activate an administrator. "
            "Open this page using your official private activation email. "
            "The code is not in the URL and expires automatically."
        )
        if not owner_setup_available():
            st.warning(
                "Owner activation is unavailable or expired. "
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
                "Choose administrator username", value="khula_owner",
                key="owner_admin_username"
            )
            password = st.text_input(
                "Choose a new strong administrator password",
                type="password", key="owner_admin_password"
            )
            confirmation = st.text_input(
                "Confirm administrator password",
                type="password", key="owner_admin_password_confirmation"
            )
            approval = st.checkbox(
                "I control the verified Railway project-owner email and "
                "understand that this account may review private membership requests.",
                key="owner_admin_confirm",
            )
            submit = st.form_submit_button(
                "Activate my administrator account", type="primary",
                use_container_width=True,
            )
        if submit:
            if password != confirmation:
                st.error("The administrator passwords do not match.")
            else:
                try:
                    activate_owner_admin(
                        DB_PATH, owner_email, username, activation_code,
                        password, approved=approval,
                    )
                except (ValueError, PermissionError) as exc:
                    st.error(str(exc))
                else:
                    st.success(
                        "Your administrator account is activated. "
                        "Sign in above with your new username and password, "
                        "then open Membership Approvals in the sidebar."
                    )
                    # Never echo or retain the entered activation code, password
                    # or any member identity in the session state.
