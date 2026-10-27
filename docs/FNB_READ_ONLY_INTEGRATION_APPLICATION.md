# FNB Transaction History API — read-only application and technical scope
27 October 2026 · Khula Collective

## Banking objective

Obtain permission for a genuine, committee-authorised Khula club bank account
to be read through **FNB Integration Channel → Transaction History API**.
The goal is to verify contributions, account balances and cash availability
in the member portal. No authority to move club money is requested.

FNB states the API covers transaction IDs, value/booking dates, amounts,
credits/debits, references, currencies, balances and date ranges for eligible
business/commercial/corporate/investment accounts in South Africa. It permits
direct client access or third-party connections with account-holder consent,
including consent revocation, and uses authenticated OAuth 2.0 flows.
Eligibility is not automatic; the club and account type must be checked.

Official source:
https://www.fnb.co.za/integration-channel/catalogue/serviceCatalogue-ZA/services.html?catalogue=serviceCatalogue-ZA&service=Transaction-History&type=API

## Permissions request

IN SCOPE:
- Account balance inquiry and transaction-history GET endpoints
- One or more explicitly selected accounts only, with revocable consent
- Limited historical data needed for club contribution reconciliation
- Test/sandbox access, then approval for a separate production connection

OUT OF SCOPE:
- Transfers, payment initiation, beneficiary management, debit orders
- Bank login credentials, member PINs/OTPs, trading and financial-product orders
- Unauthorised third-party delegated account access
- Scopes or access to unrelated personal bank accounts

## Questions for FNB

1. Account eligibility and whether Online Banking Enterprise access is needed
2. Mandate, club constitution, account signatories and business/KYC documents
3. Direct versus approved intermediary, consent and signatory controls
4. Official API base URLs, sandbox, OAuth redirect requirements, token scopes,
   key rotation/expiry and allowed credential storage
5. Polling quotas, pagination, transaction ID stability, corrections, reversals,
   historical backfill, availability and pricing
6. Data residency and contractual/POPIA requirements with overseas cloud
   hosting and onward transfers
7. Bank-origin verification test procedure and operational incident reporting
8. Read-only secure file/SFTP alternative if our account type is not eligible

## Deployment process once FNB approves

1. Authorised signatories complete the bank's approval and consent procedure.
2. Provide private sandbox credentials via bank-approved method.
3. Build adapter against the **bank-supplied** API specification, not guessed
   endpoints, with allowlisted URLs, TLS, bounded responses and secret isolation.
4. Test token rotation, errors, duplicates, currency, transaction reversals,
   date-range pagination, user revocation and audit logs.
5. Confirm bank cash via independent latest statement and compare two days of
   actual transactions; do not merge investment valuations into bank balance.
6. Enable a narrowly scoped production read-only connection after finance,
   bank, Information Officer and security review; never enable transfer actions.

## Current implementation

The Khula admin page **FNB Bank Access** produces the application email
and logs genuine submission references. It has no secret inputs and cannot
label an FNB account connected. Manual bank CSV reconciliation is separate.
