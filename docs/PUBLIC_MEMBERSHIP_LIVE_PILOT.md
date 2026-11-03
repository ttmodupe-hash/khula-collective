# Khula Collective — public registration, private member access

**Updated 27 October 2026.** This is an operational runbook, not a certificate
of POPIA/FIC/FAIS compliance and not confirmation that a bank is connected.

## Member journey

1. Anyone visiting the public URL sees a sign-in page and a **Request
   membership** section. Existing authorised users can log in as before.
2. Public registration is switched on only after the privacy and governance
   prerequisites below have been documented and operator-attested.
3. A prospective adult member enters their **full name, unique username,
   email and private password**, acknowledges the published privacy notice,
   and separately consents to processing in the disclosed overseas hosting
   region. A pre-issued invitation code is **optional**.
4. An applicant without an invitation has a row recorded in
   `Membership_Applications` with `status='pending'`, `role='member'`
   and `is_active=0`. The user **cannot** sign in or see other members'
   details, even with a valid password, until approved.
5. Club administrator signs in to **Membership Approvals**, independently
   checks the applicant's identity/contact and club eligibility, records the
   attestation and approves or rejects the request. Rejected users remain
   inactive. All decisions are tracked in `Admin_Actions`.
6. The newly authorised member can sign in once; they land on **Khula
   Compass**, a club dashboard with source-labelled data and member-private
   financial history. No registered applicant is automatically upgraded to
   an administrator.
7. Khula does **not** currently dispatch automatic signup or approval emails;
   after approval the administrator informs the member via a verified
   communication channel. No bank transfer occurs through registration.

## To open genuine production registration — club to supply real evidence

The production service currently must NOT bypass its fail-closed onboarding
gate merely to show the form. The authorised operator must first complete
real checks and store the following values as **Railway production private
environment variables** (after independently confirming they are true):

- `KHULA_RESPONSIBLE_PARTY_NAME`: full verified club/association legal name.
- `KHULA_PRIVACY_CONTACT_EMAIL`: verified club Information Officer contact.
- `KHULA_PRIVACY_NOTICE_VERSION`: approved, non-draft notice version.
- `KHULA_PRIVACY_NOTICE_APPROVED=1`: actual reviewed/published member notice.
- `KHULA_INFORMATION_OFFICER_REGISTERED=1`: regulator registration completed.
- `KHULA_CROSS_BORDER_REVIEW_APPROVED=1`: actual POPIA section 72 assessment,
  documented lawful transfer basis and safeguards for the current Railway US
  hosting region.
- `KHULA_OPERATOR_DPA_REVIEWED=1`: Railway/operator processing agreement
  and access/retention/incident terms confirmed in writing.
- `KHULA_CONSTITUTION_RATIFIED=1`: actual club meeting approval (not a mock).
- `KHULA_CONSTITUTION_DOCUMENT_TEXT`: final, exact constitution text.
- `KHULA_CONSTITUTION_VERSION`: immutable, non-draft version identifier.
- `KHULA_CONSTITUTION_SHA256`: SHA-256 of the exact UTF-8 constitution text.

No banking API key, member PIN, ID number or bank statement should be entered
as a Railway variable or into a GitHub commit. The additional optional
`KHULA_PUBLIC_REGISTRATION_PAUSED=1` temporarily stops open signups if
necessary without taking authorised members offline.

The above are operator **attestations**, not automatic legal verification.
POPIA section 72 can potentially permit cross-border transfers through
one of several lawful bases, including **informed member consent**, but
correct disclosures, operator obligations and any special categories still
require review by the club's Information Officer/legal counsel. Registration
collects no ID scans or children’s information.

## Security acceptance checks

- [ ] Member A cannot see Member B's contribution chart, contact information,
      account status or statement references. Includes report exports.
- [ ] New applicant is `is_active=0` and login fails before approval.
- [ ] Ordinary Admin Panel checkbox cannot override a public application.
- [ ] Only an active administrator can review/approve with recorded evidence
      attestations. One applicant cannot self-approve.
- [ ] Rejected applicants remain inactive and cannot be reactivated by ordinary
      membership-control toggles.
- [ ] Registration email/username duplicates and bot bursts are rejected;
      Cloudflare/Railway upstream bot/IP controls still required.
- [ ] Published privacy notice acknowledgement and cross-border consent are
      recorded with a version, timestamp and SHA-256 digest.
- [ ] Login lockouts, bcrypt credentials and session invalidation work after
      role/deactivation changes.
- [ ] No fake bank balance, pending contribution claim or portfolio NAV is
      represented as spendable club cash.
- [ ] Actual Railway volume verified mounted; offsite encrypted backup &
      isolated restore are tested **before** real financial import.
- [ ] Responsive mobile registration, login, recovery and voting are tested
      with consenting real members on representative devices.
- [ ] FNB read-only access and licensed/personalised advice remain disabled
      until independently authorised.

## Banking and regulatory dependencies

**FNB Transaction History API** remains a request in progress, not a bank
link. Club account eligibility, signatory mandate, approved read-only scopes,
bank credentials, OAuth consent, security requirements and live bank-sourced
reconciliation must all be confirmed by FNB.

Financial-services activity and the club's actual legal structure must be
reviewed for any FAIS/FSCA or FIC registration obligations before offering
regulated advice/intermediary services. A club savings calculator is not a
licensed investment recommendation.

Sources:
- POPIA s18 & s72: https://lawlibrary.org.za/akn/za/act/2013/4/eng%402013-11-26
- Information Officer guidance: https://inforegulator.org.za/wp-content/uploads/2025/07/Guidance_Note_on_Information_Officers_.pdf
- FNB Integration Channel: https://www.fnb.co.za/integration-channel/index.html
