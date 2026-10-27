# Khula Collective — secure owner administrator activation
**27 October 2026**

## Account purpose

The connected Railway project operator needs an **active administrator account**
to review real-member requests through **Membership Approvals**, as well as
access Khula's reconciliation and Launch Control screens. This is a
special-purpose recovery for the verified infrastructure owner. It is **not**
public membership registration and grants no permission to another member.

## Verification and one-time recovery

1. Confirm the **email reported by Railway's authenticated `whoami`** belongs
   to the project owner. Independently verify the sender Gmail connection is
   using the same email. Do not use an email obtained from public comments,
   source code or a registration request.
2. Generate a cryptographically strong 256-bit code privately. In Railway,
   store only its **SHA-256 digest**, verified email and a short-lived UTC
   expiry, never the plaintext. Set these on the **production Khula service**
   with its persistent `/data` ledger already mounted:
   - `KHULA_OWNER_SETUP_EMAIL` — verified Railway operator email.
   - `KHULA_OWNER_SETUP_TOKEN_SHA256` — SHA-256 hex digest of secret code.
   - `KHULA_OWNER_SETUP_EXPIRES_UTC` — aware future ISO UTC timestamp;
      recommended expiration approximately 60 minutes after issuing.
   - `KHULA_OWNER_SETUP_DISABLED` may be set to `1` to shut down
      owner activation immediately.
3. Deliver the one-time plaintext challenge **only to the verified email**
   via a private, approved message. Never include it in GitHub, browser URL
   query parameters, logs or ChatGPT share links.
4. Direct the owner to the HTTPS site with the **non-secret route switch**:
   `https://khula-collective-production.up.railway.app/?owner_setup=1`
5. Owner enters their verified email, code, a new unique administrator username
   and strong password (12–72 UTF-8 bytes), then confirms their rights
   and consent to overseas hosting.
6. An atomic transaction checks the SHA-256 challenge using constant-time
   comparison, expiry, exact owner email and original username availability;
   it creates a separate `role='admin',is_active=1` account, records a
   one-time consumption receipt and logs an administrative audit event.
   A previously existing member or admin is **not silently promoted,
   demoted, deleted or overwritten**.
7. Khula clears the activation form's password/code from the browser session
   and returns to the regular sign-in form. The owner signs in with their
   chosen credentials and opens **Membership Approvals** in the sidebar.
8. After success or expiry, clear/disable the recovery challenge variables
   in Railway using a safe operator review. Rotate the original bootstrap
   administrator password if it is still configured and no longer needed.

## What is and is not authorised

- The recovered owner account can review pending applications, reject requests,
  and **approve only after independently confirming applicant identity/contact
  and club eligibility**. Approvals remain logged.
- The same privacy, ratified-constitution, POPIA and cloud-operator safeguards
  still gate real-member onboarding and approvals. Owner recovery does not
  set or bypass any of those compliance flags.
- Other administrator accounts are not removed. If the owner wishes to be the
  *only* approver, the club must audit existing active admins and adopt an
  explicitly approved policy change—not simply overwrite the original
  account or silently remove access.
- The owner challenge itself is an elevated-privilege bearer secret; only
  the verified Railway and email account owner should receive it.
- Never ask the user to type a password, one-time code or FNB PIN into ChatGPT.
- The app has no independent WebAuthn/MFA security guarantee yet. Treat owner
  login as a privileged account requiring additional hardening.

## Recovery failure

- If the code has expired, create a **new** approved one-time recovery code
  through the verified Railway project owner, not through public registration.
- If the account username already exists, choose another unique admin name;
  do not try to take over an existing username.
- If the project owner cannot access their verified email, use the
  Railway platform's official account recovery procedures first.
- The permanent member ledger is never reset for administrator recovery.
