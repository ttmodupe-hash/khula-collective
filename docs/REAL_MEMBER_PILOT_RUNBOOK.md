# Khula Collective — real-member pilot operation
**27 October 2026 · Operational guide — no secrets or personal records**

The Khula public site: https://khula-collective-production.up.railway.app

## Current honest position

The web application is deployed on Railway with a persistent member ledger,
but Khula is **not yet certified as legally compliant**, FNB is **not API
connected**, no independently verified bank account balance is live and no
verified backup/restore has yet been established through the app.

Technical readiness is only one part of an authorised real-money pilot.
Do not set false environment flags or upload actual bank statements or
individual ID scans just to bypass a compliance warning.

## How the new application process works

- Approved active member: can sign in and use Khula Compass. Ordinary members
  see only their own payment history and aggregated club information.
- New public applicant: when the gate is legally open, enters a username,
  full name, email and private password, acknowledges the published privacy
  notice and overseas hosting, and submits an application.
- Invited applicant: uses the unique 7-day invitation in the same form.
  **Invitations also create inactive applications** in production.
- New applicants have `Users.is_active=0` and cannot sign in. Nothing is
  automatically counted as a paid contribution, bank cash or club membership.
- The form issues a **private 45-day tracking code**. Only its SHA-256 digest
  is recorded, and it is shown only after the request. The applicant should
  save it privately. Public tracking returns *pending / approved / rejected /
  inactive* only; no personal data, bank figures or application ID are
  returned.
- Admin signs into **Membership Approvals**. Before approval, the admin
  checks the individual through a trusted independent channel and confirms
  the club constitution's eligibility rules. Pending applications cannot be
  activated through the generic Members panel.
- Approved applications become active, recorded with admin ID, decision time
  and audit history. The admin can copy a personalised approval email from
  the protected approvals page and send it via a verified private address.
  No outbound email provider is automatically connected.

## Pre-launch controls requiring real, external evidence

These requirements are independent of software implementation:

1. Verify the organisation's lawful name, role and authorised signatories.
2. Adopt and preserve the exact member-ratified constitution, including
   voting, contributions, withdrawal/exit rules and dispute resolution.
3. Finalise the responsible-party privacy notice and confirm that the
   Information Officer is registered with the Information Regulator.
4. Review the Railway cloud processor/operator terms, hosting geography,
   the actual POPIA section 72 cross-border basis and other security safeguards.
5. Document a records-retention schedule, right to access/correction and
   personal-information incident-response procedure.
6. Confirm whether any proposed services require FSCA/FAIS authorisation or
   FIC accountable-institution registration. Do not offer unauthorised
   personalised investment advice, payment initiation or promises of returns.
7. Configure **Railway service → Backups** for the attached
   `khula-member-ledger` volume at daily and weekly cadences as appropriate.
   Railway documents daily retention for 6 days, weekly for 27 days,
   monthly for 89 days (check current plan terms). Make a manual snapshot,
   document the backup ID and test an **isolated** restore workflow, not a
   destructive restore over live member data.
8. Revoke the one-time bootstrap admin password from Railway once a verified
   administrator has rotated the active account password. Require a proper
   MFA and IP/edge bot protection plan before broad signup.
9. Validate verified transactional email delivery (SPF/DKIM/DMARC),
   individual consent and unsubscribing where relevant. Until then,
   notifications are only *copyable drafts*.

## Enabling the onboarding gate once genuine approvals exist

Open the protected **🚦 Launch Control** screen. It displays each missing
approval and a read-only SQLite quick-check; no email addresses, passwords
or bank references are printed. Then the verified club operator can
privately configure the approved values in Railway:

- `KHULA_RESPONSIBLE_PARTY_NAME`
- `KHULA_PRIVACY_CONTACT_EMAIL`
- `KHULA_PRIVACY_NOTICE_VERSION` (non-draft)
- `KHULA_PRIVACY_NOTICE_APPROVED=1`
- `KHULA_INFORMATION_OFFICER_REGISTERED=1`
- `KHULA_OPERATOR_DPA_REVIEWED=1`
- `KHULA_CROSS_BORDER_REVIEW_APPROVED=1`
- `KHULA_CONSTITUTION_RATIFIED=1`
- `KHULA_CONSTITUTION_DOCUMENT_TEXT` (exact final text)
- `KHULA_CONSTITUTION_VERSION` (non-draft)
- `KHULA_CONSTITUTION_SHA256` (SHA-256 of exact UTF-8 final text)

`KHULA_PUBLIC_REGISTRATION_PAUSED=1` can temporarily stop open requests;
absence permits them only if all other prerequisites really pass.
These flags **record operator attestations; they do not create legal approval
or bank authorisation**.

## First test with consenting real adults (after those checks)

1. Administrator verifies backups, login, constitution, consent and data
   location before asking anyone for a personal email.
2. Two real adult invitees independently open the website on mobile and
   desktop, read the privacy notice and register.
3. Verify each applicant has a private tracking receipt and **cannot login**.
4. Test a deliberately wrong tracking code: no identity is disclosed.
5. Check the membership approval queue from an active admin account; confirm
   only verified applicant details and that no ID/PIN/OTP was requested.
6. Approve one individual, reject the other, record reasons outside the
   public UI where required and use an approved private communication method.
7. Approved member signs in; rejected member cannot.
8. Approved member opens Dashboard, Reports, Directory and contribution
   submission; verify no other member's email, personal payment totals,
   phone or verification status is exposed.
9. Verify a pending payment claim leaves the paid ledger and cash balance
   unchanged. Upload genuine *club* bank CSV only after privacy retention
   controls are approved, and match a real credit to exactly one claim.
10. Verify a dated administrator-attested balance appears as **manual**,
    becomes stale after 14 days and never includes market-valued holdings.
11. Revoke test-member access and confirm active sessions are invalidated.
12. Verify backup creation, alerting and isolated recovery evidence.

## Incident stop

If you notice an exposed member list, compromised admin login, lost financial
record, unexpected account activation or duplicate contribution, set
`KHULA_PUBLIC_REGISTRATION_PAUSED=1` (after validating the environment).
Remove unauthorised access, preserve logs, notify the Information Officer and
follow the documented POPIA compromise process. Do not delete evidence or
silently mark an unresolved payment as paid.

Sources:
- Railway volumes/backups: https://docs.railway.com/volumes/backups
- Information Regulator: https://inforegulator.org.za/popia/
- FNB Integration Channel: https://www.fnb.co.za/integration-channel/index.html
