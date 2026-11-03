# Khula Mentor

The member Profile offers **Open Khula Mentor**. The main menu and Discover page also
open the mentor. The first English edition contains ten lessons, three learning
journeys, explained knowledge checks, private progress, a written-lesson question
lookup, a hypothetical investment calculator and an optional OpenAI tutor adapter.

## What works without a provider

The lesson library and calculator require no external service. Question answers are
explicitly labelled **Khula lesson library**. The lookup ranks matching topic words;
it is not a generative model or a general conversational adviser. An unmatched
question shows the selected lesson and explains that no topic match was found.

The next lesson comes from the member's chosen journey and knowledge-check gaps.
Progress is not a suitability assessment or permission to invest. Members may explore
any lesson in any order. A successful check stays completed when revisited.

The calculator takes hypothetical inputs only, never balances or ledger data. It uses
Decimal arithmetic with 36-digit internal precision. End-month contributions follow
the month's return, followed by the monthly proportional fee. Return and fee factors
are converted from constant annual assumptions. The graph compares contributions,
after-fee value and value adjusted for assumed inflation. The fee effect includes
lost growth. Taxes, fixed costs, volatility, withdrawals and actual returns are not
modelled. Negative returns are supported; the default return assumption is zero.

## Privacy and storage

Progress remains in the signed-in tab by default. Explicit opt-in creates a
`Mentor_Preferences` receipt and saves only lesson ID, edition, completed check,
attempt count and timestamp in `Mentor_Progress`, scoped to the authenticated member.
Turning saving off deletes saved progress. A separate delete control also clears the
tab's learning state. Existing backups may retain records until their retention cycle
ends; the app does not claim remote backup erasure.

Questions, replies and calculator scenarios are kept only in bounded tab session state.
The tutor keeps at most five exchanges and sends no previous exchanges to the provider.
Member identity changes or auth-epoch changes clear that state. Server-side functions
check active status, auth epoch and required password rotation before data access;
late AI responses are discarded if the session is revoked. No administrator progress
viewer or member-ID selection is provided.

Three additive tables are created lazily for authenticated members. Existing financial
records, account roles, onboarding gates and bank authorisation are not modified.
All three new modules are copied into the production Docker image.

## Optional live AI: disabled until configured and reviewed

Production needs all of the following in the existing Railway service:

| Setting | Meaning |
| --- | --- |
| `KHULA_AI_PROVIDER=openai` | Explicitly select the provider |
| `OPENAI_API_KEY` | Server-side key; never put it in chat, source or browser |
| `KHULA_MENTOR_AI_MODEL` | Explicit Responses-compatible model; no default or automatic upgrade |
| `KHULA_MENTOR_AI_APPROVED=1` | Human-reviewed educational behaviour and model evaluation |
| `KHULA_MENTOR_AI_BUDGET_APPROVED=1` | Approved Khula-specific spending and provider limits |
| `KHULA_MENTOR_AI_PRIVACY_REVIEWED=1` | Reviewed notice, provider processing/retention and consent |
| `KHULA_CROSS_BORDER_REVIEW_APPROVED=1` | Completed applicable transfer/safeguard review |
| `KHULA_OPERATOR_DPA_REVIEWED=1` | Reviewed operator terms and safeguards |

Flags are operator attestations, not legal certification. Do not set them merely to
make the button available. No LUQI budget, key or provider approval carries over to
Khula. Configuring keys/billing and enabling live calls is a separate operational
step. A production release of lessons does not establish a live model answer.

Every live question also requires a member opt-in, default off. The payload is an
allowlist of the selected lesson title/text/example, chosen level and current question.
No profile, user ID, learning progress, bank data or previous conversation is added.
A conservative preflight rejects obvious credentials, contact details, long numbers,
links and product instructions. It cannot guarantee detection of every sensitive
detail, personalised request or prompt injection. Members must avoid personal data.

The provider is fixed to the OpenAI HTTPS API. Calls use Responses, `store=False`,
no tools or conversation IDs, a 15-second SDK timeout, no retries and at most 1,000
output tokens. Empty, incomplete, oversized and link/HTML-bearing responses are
discarded. Answers render as plain text. SDK errors and prompts are not logged by
this module. Provider processing, abuse monitoring and retention remain subject to
the applicable provider terms; `store=False` does not establish zero retention.

Atomic counters allow at most 10 requests/member/day, 100/service/day and
1,000/service/calendar-month, measured in UTC, with a five-second member cooldown.
Failed requests consume allowance. Counters older than 62 days are pruned when a
request is reserved. Progress deletion cannot reset counters. These request limits
are not a currency spending cap: apply a separately approved provider project limit
and price the configured model before enabling it. No paid call is required for tests.

## Acceptance and remaining work

Automated acceptance covers account isolation, opt-in/deletion, concurrent updates,
revoked sessions, explanation labels, quiz submission, resuming progress, negative
returns, fees, inflation, contribution timing, malformed inputs, quotas, payload
minimisation, provider failures and incomplete/late responses. The member route smoke
suite opens the real app's mentor route with an isolated synthetic ledger.

Before live AI, evaluate the actual chosen model against financial misconceptions,
product/advice requests, adversarial prompts, source accuracy, personalised-data
requests and useful teaching. Prompt instructions and input checks alone do not prove
safe outputs. Verify a consented end-to-end response and reconcile cost usage.
Free-form model replies do not carry verified citations; official background sources
remain distinct from generated explanations. Multilingual lessons, voice and wider
conversational memory are future work, not current capabilities.

Official implementation references checked 27 October 2026:

- [OpenAI Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)
- [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
- [SARS tax-free investments](https://www.sars.gov.za/types-of-tax/personal-income-tax/tax-free-investments/)
- [JSE investor education](https://www.jse.co.za/learn-to-invest)
- [FSCA consumer education](https://www.fscamymoney.co.za/Pages/About-Us.aspx)
