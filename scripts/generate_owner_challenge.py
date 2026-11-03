"""Generate a private Khula owner challenge OFFLINE, without storing secrets.

This script does not connect to Railway, Gmail, Khula, or any network. Run it
locally on the verified owner's computer, NOT in GitHub Actions or cloud logs.

The code is a strong 256-bit one-time bearer secret. Only its SHA-256 digest
belongs in Railway; the original code must remain with the owner and be
entered directly into Khula's official /?owner_setup=1 form.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_CODE = re.compile(r"^[A-Za-z0-9_-]{43}$")


@dataclass(frozen=True)
class OwnerChallenge:
    email: str
    code: str
    sha256: str
    expires_utc: str


def generate_owner_challenge(email: str, *, hours: int = 6,
                             now: datetime | None = None) -> OwnerChallenge:
    """Return fresh local-only credentials; caller must NOT log the code.

    Expiry is a short UTC timestamp, accepted by Khula's existing owner
    challenge validator. Generates a distinct random code on every call.
    """
    if not isinstance(email, str):
        raise ValueError("Enter the exact verified Railway owner email.")
    email = email.strip().lower()
    if len(email) > 254 or not _EMAIL.fullmatch(email):
        raise ValueError("Enter the exact verified Railway owner email.")
    if type(hours) is not int or not 1 <= hours <= 12:
        raise ValueError("The challenge must expire within 1 to 12 hours.")
    when = datetime.now(timezone.utc) if now is None else now
    if not isinstance(when, datetime) or when.tzinfo is None:
        raise ValueError("Use a timezone-aware current time.")
    token = secrets.token_urlsafe(32)
    if not _CODE.fullmatch(token):
        raise RuntimeError("Secure token generation failed.")
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    expiry = (when.astimezone(timezone.utc) + timedelta(hours=hours))
    return OwnerChallenge(
        email=email,
        code=token,
        sha256=digest,
        expires_utc=expiry.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a one-use Khula owner setup code on YOUR computer."
    )
    parser.add_argument("--owner-email", required=True,
                        help="Exact email on your verified Railway account")
    parser.add_argument("--hours", type=int, default=6,
                        help="Validity period in hours (1-12, default 6)")
    opts = parser.parse_args(argv)
    if not sys.stdout.isatty():
        parser.error(
            "For safety, generate the code in your own interactive terminal. "
            "Do not pipe secrets into scripts, logs, email tools or CI output."
        )
    try:
        result = generate_owner_challenge(opts.owner_email, hours=opts.hours)
    except ValueError as exc:
        parser.error(str(exc))
    # The output is ephemeral and only visible in the owner's own terminal.
    # No plaintext token is stored on disk or submitted to any remote service.
    print()
    print("KHULA — PRIVATE OWNER ACTIVATION (keep this screen private)")
    print()
    print("In Railway > production > khula-collective > Variables set:")
    print("KHULA_OWNER_SETUP_EMAIL=" + result.email)
    print("KHULA_OWNER_SETUP_TOKEN_SHA256=" + result.sha256)
    print("KHULA_OWNER_SETUP_EXPIRES_UTC=" + result.expires_utc)
    print("KHULA_OWNER_SETUP_DISABLED=0")
    print()
    print("On https://khula-collective-production.up.railway.app/?owner_setup=1")
    print("enter this ONE-TIME CODE in the private activation-code field:")
    print(result.code)
    print()
    print("Do not copy that code into GitHub, ChatGPT, screenshots or emails.")
    print("Create your own strong password in the Khula form; never share it.")
    print("The code expires at the UTC timestamp above and is one-use only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
