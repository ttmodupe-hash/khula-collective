"""Versioned Khula-authored lessons; links are background reading, not endorsements."""

CONTENT_VERSION = "2026-10-27.1"
SOURCES = {
    "habits": ("FSCA MyMoney — Good financial habits", "https://www.fscamymoney.co.za/Pages/Financially%20Smart/Good-Financial-Habits.aspx"),
    "saving": ("FSCA MyMoney — Saving and investing", "https://www.fscamymoney.co.za/Financial%20Safeguard/Savings%20vs%20Investments%20More%20about.pdf"),
    "investing": ("JSE — Learn to invest", "https://www.jse.co.za/learn-to-invest"),
    "funds": ("JSE — Exchange traded products", "https://www.jse.co.za/trade/equities-market/exchange-traded-products"),
    "tax": ("SARS — Tax free investments (check current rules)", "https://www.sars.gov.za/types-of-tax/personal-income-tax/tax-free-investments/"),
    "fraud": ("FSCA MyMoney — Safeguarding finances against fraud", "https://www.fscamymoney.co.za/Pages/10-tips-to-safeguard-your-finances-against-fraud.aspx"),
}


def _lesson(key, title, stage, body, example, question, options, answer, why, activity, tags, sources):
    return dict(id=key, title=title, stage=stage, body=body, example=example,
                question=question, options=options, answer=answer, why=why,
                activity=activity, tags=tags.split(), sources=sources)


LESSONS = (
    _lesson("cashflow", "Give every rand a purpose", "Money foundations",
        "A budget is a plan for the money coming in and going out. Separate essentials, debt payments, "
        "flexible spending and savings. Include irregular costs, such as annual renewals. A useful plan "
        "is realistic enough to repeat and flexible enough to review when circumstances change.",
        "Hypothetical month: R5,000 income minus R3,800 planned spending leaves R1,200 before any unplanned costs. "
        "That remainder is not automatically money available to invest.",
        "What should a realistic budget include?",
        ("Only this week's spending", "Regular and irregular expenses", "Expected investment profits"), 1,
        "Irregular costs still use money. Planning for them helps prevent a misleading surplus.",
        "Privately list one expense you often forget. You do not need to share its amount here.",
        "budget budgeting cashflow income spending salary expenses", ("habits",)),
    _lesson("resilience", "Build resilience: emergencies and debt", "Money foundations",
        "Unexpected expenses can interrupt even a good plan. Accessible emergency savings provide a buffer. "
        "Debt interest and charges can compound too. Compare borrowing costs, repayment terms and the need "
        "for accessible cash before considering investment risk; there is no universal amount suitable for everyone.",
        "A hypothetical R1,000 debt charged 2% for one month adds R20 before other fees or repayments. "
        "An uncertain investment gain cannot be treated as a guaranteed way to pay that cost.",
        "Why keep emergency money accessible?",
        ("To guarantee high returns", "To avoid ever needing a budget", "To meet unexpected costs without relying on a sale"), 2,
        "An investment may be down or take time to sell exactly when money is needed.",
        "Identify one essential cost that could arise unexpectedly and how quickly it would need paying.",
        "emergency debt debts loan borrowing interest buffer resilience", ("habits", "saving")),
    _lesson("saving", "Saving and investing serve different goals", "Money foundations",
        "Saving sets money aside; investing exposes money to assets that may generate income or change in value. "
        "Match the discussion to when money is needed, access restrictions and the possibility of loss. "
        "Cash also faces inflation risk. Product terms matter more than a reassuring label.",
        "Money needed for a bill next month has a different job from hypothetical money set aside for ten years. "
        "A long horizon does not remove investment risk.",
        "Which fact matters when comparing options?",
        ("When the money is needed and whether it can lose value", "How popular the app is", "Whether a friend made a profit"), 0,
        "Time, access and risk affect the comparison; popularity and someone else's outcome do not establish suitability.",
        "Choose a fictional short-term goal and a long-term goal. Explain why their access needs differ.",
        "save saving savings invest investment investing horizon liquidity access", ("saving",)),
    _lesson("compounding", "Understand compounding", "Investing essentials",
        "Compounding means gains or costs build on a changing balance. Regular contributions and the timing "
        "of those contributions affect the result. Investment returns vary, so a smooth compound-growth curve "
        "is an illustration rather than a prediction. Losses and charges can also build up over time.",
        "With a hypothetical constant 5% annual return and no fees, R1,000 becomes R1,050 after one year "
        "and R1,102.50 after two. Real investments do not promise that path.",
        "What makes the second year's hypothetical gain larger?",
        ("A guarantee from the market", "Growth on the previous year's growth", "The removal of all risk"), 1,
        "The assumed return applies to R1,050 in year two, including the earlier R50 gain.",
        "Use the practice lab to compare a positive return, zero return and a loss using identical contributions.",
        "compound compounding growth return returns reinvest interest", ("habits", "investing")),
    _lesson("risk", "Diversify and understand losses", "Investing essentials",
        "Diversification spreads exposure across different assets, businesses or regions. It can reduce "
        "dependence on one outcome, but cannot prevent all losses. Several investments may hold the same "
        "underlying companies, so owning more products does not always mean broader exposure.",
        "If a hypothetical R1,000 falls 20%, R800 remains. Recovering from R800 to R1,000 takes a 25% gain. "
        "Equal percentage losses and gains do not cancel out.",
        "What can diversification do?",
        ("Remove market risk", "Guarantee a profit", "Reduce concentration while leaving other risks"), 2,
        "A broad market fall can affect many holdings together. Diversification addresses concentration, not every risk.",
        "For a fictional fund, ask whether its holdings overlap another fictional fund before calling them diversified.",
        "risk risks diversification diversify loss losses volatility drawdown concentration", ("investing",)),
    _lesson("funds", "Know what a share, bond or fund represents", "Investing essentials",
        "A share represents ownership in a business. A bond is lending subject to issuer and repayment risk. "
        "A fund pools holdings under a stated mandate; an ETF trades on an exchange. Examine the underlying "
        "assets, costs, liquidity and structure. An ETF can be concentrated or volatile; the label does not make it safe.",
        "Two fictional ETFs may follow different markets. One could hold a broad mix of companies while another "
        "focuses on a single sector. Their risks can differ greatly.",
        "Before comparing two funds, what should you inspect?",
        ("Their holdings, mandate, costs and risks", "Only their names", "Only last month's winner"), 0,
        "A product's structure and holdings explain exposure more reliably than its name or recent ranking.",
        "Write three questions you would ask about a fund's factsheet before discussing it with an authorised adviser.",
        "share shares stock stocks bond bonds fund funds etf etfs equity unit trusts", ("funds", "investing")),
    _lesson("fees", "Look beyond the headline return", "Investing essentials",
        "Fees reduce what stays invested. Inflation reduces what money can buy. Compare all relevant charges, "
        "including platform, fund, transaction and advice costs. A nominal gain can still mean a loss of "
        "purchasing power. Taxes and withdrawals can change outcomes further.",
        "If a hypothetical basket costs R100 today and R110 later, a balance growing from R100 to R105 "
        "cannot buy the same basket, even though its rand value increased.",
        "What does an inflation-adjusted balance help explain?",
        ("A guaranteed future balance", "Purchasing power in today's money", "The exact tax owed"), 1,
        "Adjusting for an assumed inflation rate expresses the future balance in today's purchasing power.",
        "In the practice lab, change only the fee assumption and compare the results. Then change inflation.",
        "fees fee costs charges inflation real nominal purchasing power", ("investing", "habits")),
    _lesson("tax", "Separate the tax wrapper from the investment", "Wise decisions",
        "A South African tax-free investment account is a tax wrapper, not a promise that its assets cannot fall. "
        "Contribution rules apply across accounts. Withdrawing and paying money back can use contribution "
        "capacity again. Limits and penalties can change: check the current SARS page and qualified guidance "
        "before contributing. This lesson does not calculate personal tax.",
        "Two fictional accounts can have different underlying investments while sharing tax-wrapper rules. "
        "Tax treatment and investment risk are separate questions.",
        "Does a tax-free label guarantee the invested capital?",
        ("Yes, for every product", "Yes, if there are several accounts", "No; the underlying investment still matters"), 2,
        "Tax treatment does not establish capital protection. Review the underlying assets and current rules.",
        "Open the SARS source and identify which tax year a contribution rule applies to.",
        "tax taxes tfsa wrapper sars taxfree retirement", ("tax",)),
    _lesson("scams", "Pause, verify and question the promise", "Wise decisions",
        "Pressure to act immediately, secrecy, referral rewards and claims of high guaranteed returns are "
        "reasons to pause. Verify a provider independently through the relevant official register and contact "
        "details. A copied logo, testimonial or registration number is not proof that the person contacting "
        "you is genuine. Keep passwords and one-time codes private.",
        "A fictional message promises to double money quickly if you pay today. The mentor cannot certify "
        "the offer: independently check who is receiving the money and their authority to offer the service.",
        "What is a sensible response to urgent guaranteed-return claims?",
        ("Pause and verify independently", "Pay a smaller amount to test it", "Share your one-time code"), 0,
        "A small initial payment can still be lost. Independent verification should happen before sending money.",
        "Describe two warning signs in a fictional offer without sharing a real person's details or payment information.",
        "scam scams fraud guaranteed promise crypto bitcoin forex pressure verify", ("fraud",)),
    _lesson("judgement", "Practise patient, collective judgement", "Wise decisions",
        "Excitement and fear can both rush decisions. Write down the purpose, evidence, downside, costs and "
        "exit conditions before discussing a proposal. In a stokvel, follow the ratified constitution, "
        "decision rules and conflict-of-interest process. A learning score or AI answer never grants authority "
        "to invest collective funds.",
        "A fictional club compares two proposals using the same checklist and records unanswered questions "
        "before any vote. A popular proposal still needs evidence and proper authority.",
        "What should happen when a proposal has unanswered material questions?",
        ("Treat an AI reply as approval", "Record the gaps and seek evidence before deciding", "Follow the loudest member"), 1,
        "Recording uncertainty supports informed discussion and accountable decisions.",
        "Draft a fictional decision checklist: purpose, access needs, possible loss, total fees, evidence and authority.",
        "behaviour behavioral psychology fear patience stokvel club governance wisdom decision decisions vote", ("habits", "investing")),
)

BY_ID = {lesson["id"]: lesson for lesson in LESSONS}
PATHS = {
    "Build my money foundations": tuple(BY_ID),
    "Understand investing": ("saving", "compounding", "risk", "funds", "fees", "tax", "scams", "judgement", "cashflow", "resilience"),
    "Make wiser decisions": ("scams", "risk", "judgement", "fees", "funds", "saving", "resilience", "cashflow", "compounding", "tax"),
}
LEVELS = ("Start with the basics", "Build my understanding", "Go deeper")
