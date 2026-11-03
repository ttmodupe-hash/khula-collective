# Khula Mentor — proposed member learning experience

Status: scope specification, 27 October 2026. The first implementation is described in
[KHULA_MENTOR.md](KHULA_MENTOR.md). Deployment status must be verified independently.

## Member experience

Add a prominent **My financial mentor** section to Profile, with a dedicated learning view accessible from the main menu. Keep account settings separate from lessons.

Start with the member's chosen learning goal and experience level, without inferring investment suitability from their ledger. Offer three journeys: money foundations, understanding investing, and evaluating risks and scams. Recommend the next lesson from knowledge checks and completed topics. Explain why that lesson was selected.

Each session follows: explain a concept, show a hypothetical rand example, invite a question, check understanding, explain the answer, and suggest a short next activity. Let members ask for a simpler explanation or deeper detail. Progress describes learning completed, never investment readiness or expected wealth.

## Initial curriculum

1. Cash flow, budgeting and realistic savings goals.
2. Emergency funds, debt costs and liquidity.
3. Saving versus investing and the possibility of loss.
4. Compounding and the importance of contribution timing.
5. Diversification, concentration and market risk.
6. Shares, bonds, funds and ETFs, including their different risks.
7. Fees, inflation and real purchasing power.
8. South African tax wrappers, with current SARS sources and effective dates.
9. Investment scams, pressure tactics and verifying providers.
10. Stokvel governance, collective decisions and questions for an authorised adviser.

## Practice laboratory

Use explicitly hypothetical inputs, independent of real member balances. Compare contributions only with user-selected growth and loss scenarios. Show nominal and inflation-adjusted outcomes, cumulative contributions and fee effects. State contribution timing and compounding assumptions. Include negative returns and drawdowns; never label a selected return as a forecast. Calculations run in tested application code, not in model-generated arithmetic. Practice never creates a payment, holding or trade.

## AI tutor

Use a server-side provider adapter with an explicitly configured model. Ground explanations in a versioned lesson library and approved source extracts. Distinguish lesson sources from model-generated explanations; do not invent citations or imply that an unverified model answer is regulator approved.

Begin with lesson-specific follow-ups. Wider conversational mentoring requires evaluation against personalised product recommendations, fabricated market data, guaranteed returns, prompt injection and sensitive-data disclosure. A disclaimer alone does not settle the education/advice boundary. Product decisions should have an appropriate route to an authorised human adviser.

Keep identity documents, contact details, statements and other members' records outside tutor context. Describe exactly what is sent before opt-in. Saving learning progress must be optional, private to the authenticated member and deletable. Do not store raw financial conversations by default. Provider retention and cross-border arrangements need review before live use; disabling response storage is not a promise of zero provider retention.

Apply per-member and service request limits, timeouts, bounded output and a provider spending limit. Lessons remain usable during outages. Never enable billing or copy a provider budget from another project implicitly.

## Delivery and acceptance

Build on the current production feature branch, not old main. First deliver Profile entry, curriculum, knowledge checks, private progress and simulator. Then enable the tutor only after provider configuration, privacy review and answer-quality evaluation. Future additions can include reviewed African-language lessons and voice; do not advertise them until tested.

Acceptance includes member isolation, session revocation, progress deletion, arithmetic including losses, no external request without opt-in, no private ledger in provider payloads, provider failure behaviour, cost limits, source attribution and mobile navigation. Preserve the Railway service, ledger and onboarding gates.
