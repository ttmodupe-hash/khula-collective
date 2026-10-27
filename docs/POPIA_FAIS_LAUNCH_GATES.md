# Khula Collective — POPIA, bank and financial-services go-live gates
Updated: 27 October 2026

**NOT A LEGAL CERTIFICATE.** This checklist is based on the current South
African regulator and FNB material. An authorised Information Officer,
independent legal/FAIS specialist and the account-holding bank must confirm
the facts before real member records are processed.

## First: establish the organisation and authority

- [ ] Identify the responsible party's full legal/association name, contact
  details, constitution and authorised signatories; resolve whether Khula is
  merely a member-only savings club or provides services to the public.
- [ ] Ratify actual contribution amount and rules (old repo states R300,
  v4 originally stated R500), voting quorums, withdrawals, investments,
  disputes and member exit/retention rules.
- [ ] Ensure bank account is in an authorised name and FNB accepts its account
  classification for Integration Channel Transaction History access.
- [ ] Appoint/register the responsible party's Information Officer with the
  South African Information Regulator. Publish accurate privacy contact.
- [ ] Complete privacy impact assessment, access/correction/objection workflow,
  PAIA manual applicability, records retention & deletion schedule, and member
  notices before importing any actual member identities or records.

## POPIA security and international transfers

- [ ] POPIA sections 19–21: data minimisation, a documented risk assessment,
  restricted role-based access, breach response, protected credentials,
  audit logging and appropriate written terms with every cloud operator.
- [ ] POPIA section 22: regulator and affected-member notification workflow
  when there are reasonable grounds of unauthorised access/acquisition.
  Do not invent a fixed statutory 72-hour period.
- [ ] **Section 72**: the Railway ledger was observed on a 512 MB mounted
  volume in a US (SFO) service region. Have counsel document the applicable
  permitted cross-border transfer basis and adequacy/binding safeguards
  (and onward-transfer rules) before switching production registration on.
  Obtain/assess Railway operator/data protection terms and subprocessors.
- [ ] Test Railway ledger backups and an isolated restore; confirm
  separation of production data and development/testing.
- [ ] Independent vulnerability/penetration assessment, authentication
  controls, least-privilege approvals, access-revocation and secure update
  process before admitting real financial documents.
- [ ] Do not claim a privacy badge, POPIA certification, bank approval or
  FSCA registration that has not been independently established.

## Investment / money-laundering scope

- [ ] Obtain specialist classification of the actual business model under
  the FAIS Act / FSCA framework. AI-specific buy/sell/portfolio-allocation
  guidance and intermediary services stay disabled unless the appropriate
  authorisation and operating requirements are independently established.
- [ ] Confirm whether any Khula activities make the responsible person an
  accountable institution listed in Schedule 1 of the FIC Act. If so, follow
  registration/AML/CFT, customer-due-diligence and reporting obligations.
  A member-only stokvel should not be assumed exempt or registered without
  confirming its real activities and legal form.
- [ ] Keep membership contributions separate from paid investment products,
  promised returns and investor recruitment. No guarantee of any yield.

## FNB API readiness

Official FNB Transaction History API documents:
https://www.fnb.co.za/integration-channel/catalogue/serviceCatalogue-ZA/services.html?catalogue=serviceCatalogue-ZA&service=Transaction-History&type=API

- [ ] Contact FNB's **Digital Profile Manager / Transactional Portfolio
  Manager / Implementation Manager** or secure Online Banking Enterprise
  Integration Channel.
- [ ] Confirm eligibility and required registration/club-signatory mandate.
- [ ] Apply **only** for read-only transaction history and balances
  (date, amount, currency, debit/credit, reference, bank transaction ID,
  balance and source timestamp). No transfer/payment-initiation scope.
- [ ] Obtain a documented sandbox and signed commercial terms, supported
  OAuth 2.0 authorisation-code and consent process, token refresh/revocation,
  official endpoints, polling limits and test credentials from FNB.
- [ ] Do not enter online-banking usernames, passwords, PINs or OTPs in the
  Khula app or ordinary emails; hold all approved keys/tokens in a managed
  secret store and never log them.
- [ ] Implement idempotent import with bank transaction identifiers and
  booking dates, reconcile ledger against bank statement totals, and
  alert on gaps, duplicates, failed calls and revocation.
- [ ] Run a supervised read-only UAT with approved account signatories and
  verify an actual bank-origin balance and transaction on two independent days
  before representing the account as **connected**.

## Khula launch variables (set privately, only with genuine proof)

Before production invitation/registration:
- `KHULA_RESPONSIBLE_PARTY_NAME`: verified legal name
- `KHULA_PRIVACY_CONTACT_EMAIL`: verified privacy/Information Officer contact
- `KHULA_PRIVACY_NOTICE_VERSION`: approved immutable version identifier
- `KHULA_PRIVACY_NOTICE_APPROVED=1`: only after formal sign-off
- `KHULA_INFORMATION_OFFICER_REGISTERED=1`
- `KHULA_CROSS_BORDER_REVIEW_APPROVED=1`
- `KHULA_OPERATOR_DPA_REVIEWED=1`
- `KHULA_CONSTITUTION_RATIFIED=1`

The above are **self-attested operator controls**, not legal certification.
They must never be turned on merely to hide warnings.

`KHULA_FSP_ADVISORY_APPROVED` remains unset until a financial-services
legal review/appropriate authorisation is documented; currently the investment
guide is education + savings arithmetic, with no personally tailored allocations.

Source references:
- Information Regulator POPIA: https://inforegulator.org.za/popia/
- Information Officer e-services: https://eservices.inforegulator.org.za/services.aspx
- POPIA full Act (s72): https://lawlibrary.org.za/akn/za/act/2013/4/eng%402013-11-26
- POPIA compromise guidance: https://inforegulator.org.za/2025/08/19/fact-sheet-handling-of-security-compromises/
- FSCA FSP licensing: https://www.fsca.co.za/New-Financial-Service-Provider/
- FIC accountable institution registration: https://goweb.fic.gov.za/goAMLWeb_PRD/Account/LogOn
