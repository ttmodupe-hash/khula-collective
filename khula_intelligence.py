"""Khula investment research UI — club savings + dated market evidence.

Read-only analysis: no trade execution and no assumptions that member-reported
payments or imported personal statements equal collective cash.
"""
import os
from decimal import Decimal

import streamlit as st

from khula_advisory_core import (
    affordable_units,
    bank_snapshot_fresh,
    allocation_amounts,
    illustrative_allocation,
    no_growth_projection,
    zar,
)
from khula_config import GLOBAL_TICKER_UNIVERSE, DB_PATH
from khula_market_data import (
    MarketDataError,
    fetch_fx_rate,
    fetch_quote,
    market_configured,
)
from khula_member_services import latest_club_balance
from khula_utils import get_ai_context, track_feature_usage


@st.cache_data(ttl=300, show_spinner=False)
def _cached_quote(symbol):
    return fetch_quote(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_fx(currency):
    return fetch_fx_rate(currency, "ZAR")


def _balance_summary():
    snap = latest_club_balance()
    if not snap:
        st.warning(
            "No club bank balance has been reconciled in the app. "
            "We cannot infer available savings from member deposits or investment values."
        )
        return None
    st.metric("Available for discussion (after reserved funds)", f"R{snap['available']:,.2f}")
    st.caption(
        "Manual, administrator-attested bank snapshot dated "
        + snap["as_of"]
        + ". NOT a live bank balance and not independent audit confirmation."
    )
    if not bank_snapshot_fresh(snap["as_of"]):
        st.error(
            "The bank snapshot is older than 14 days or has an invalid date. "
            "Available savings and affordability scenarios are disabled until "
            "an administrator checks a recent club bank statement."
        )
        return None
    return snap


def _select_market_symbol(key="market_asset"):
    catalogue = {f"{asset['name']} ({asset['ticker']})": asset["ticker"]
                 for asset in GLOBAL_TICKER_UNIVERSE}
    choice = st.selectbox("Research asset", list(catalogue), index=0, key=key)
    custom = st.text_input("Or look up another provider-supported symbol", key=key + "_custom")
    return custom.strip().upper() if custom.strip() else catalogue[choice]


def _render_quote(ticker, scenario_cash=None):
    if not market_configured():
        st.warning(
            "Real market quotes are not enabled. Configure a licensed Twelve Data "
            "business plan, KHULA_TWELVEDATA_API_KEY and the explicit display-rights flag. "
            "No simulated price is shown."
        )
        return
    try:
        quote = _cached_quote(ticker)
    except MarketDataError as exc:
        st.warning(str(exc))
        return
    st.subheader(f"{quote['name']} — {quote['symbol']}")
    st.metric("Most recent quoted close", f"{quote['currency']} {quote['price']:,.2f}")
    st.caption(
        f"{quote['source']} · {quote['exchange']} · quote as of {quote['as_of']} · "
        f"retrieved {quote['fetched_at']} · not guaranteed real-time"
    )
    if quote["is_market_open"] is False:
        st.info("The provider reports this market as closed.")

    if scenario_cash is None:
        st.caption("Affordability unavailable without a bank snapshot. No purchase proposal is made.")
        return

    native_price = quote["price"]
    if quote["currency"] == "ZAR":
        price_zar = native_price
        st.caption("Quote currency is ZAR; check whether the provider expresses JSE data in cents.")
    else:
        try:
            fx = _cached_fx(quote["currency"])
        except MarketDataError as exc:
            st.warning(f"No validated currency conversion: {exc}")
            return
        price_zar = native_price * fx["rate"]
        st.caption(f"FX {quote['currency']}/ZAR {fx['rate']:.4f} · {fx['source']} as of {fx['as_of']}")
    if price_zar <= 0:
        st.warning("Invalid converted price.")
        return
    if quote["symbol"].endswith(".JO") or quote["exchange"].upper() == "JSE":
        st.warning(
            "Share-price units (rand versus cents) and applicable venue fees "
            "require broker/provider verification. A quote is displayed for "
            "research only; JSE purchase quantities are intentionally disabled."
        )
        return
    units = affordable_units(scenario_cash, price_zar, exposure_limit_pct=10)
    st.info(
        f"Illustrative maximum at 10% of *reported investable cash*: {units} whole units, "
        f"before platform fees, taxes, slippage and liquidity constraints. "
        "This is not a recommendation or executable order."
    )


def _optional_llm_commentary(available, risk, years, allocation):
    if (os.environ.get("KHULA_AI_PROVIDER") != "openai"
            or not os.environ.get("OPENAI_API_KEY")):
        st.caption("Optional AI commentary is disabled; the transparent rules-based guide remains available.")
        return
    st.caption("AI requests send aggregate figures and a risk/horizon scenario only — never IDs or statements.")
    if st.button("Generate optional AI learning explanation"):
        try:
            from openai import OpenAI
            import json
            client = OpenAI(timeout=12, max_retries=0)
            payload = json.dumps({
                "club_cash_from_manual_attestation_zar": str(available) if available is not None else None,
                "risk_profile": risk,
                "time_horizon_years": years,
                "illustrative_allocation_percent": allocation,
            })
            msg = client.chat.completions.create(
                model=os.environ.get("KHULA_AI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content":
                        "You are an educational South African investment-club guide, not a licensed adviser. "
                        "Explain diversification, cash reserves, risks, fees, taxation, and the effect of time horizon. "
                        "No specific buy/sell instruction, no predicted returns, no fabricated prices. "
                        "Explain that cash is manually attested and independent bank reconciliation is pending. "
                        "Encourage a club vote and authorised professional review for product decisions."},
                    {"role": "user", "content": payload},
                ],
                max_tokens=420,
                temperature=0.2,
            )
            answer = msg.choices[0].message.content
            if answer:
                st.write(answer)
            else:
                st.warning("The AI provider returned no explanation.")
        except Exception:
            st.warning("AI commentary is temporarily unavailable; nothing has been traded.")


def render_investment_guide():
    track_feature_usage(st.session_state.user_id, "savings_guide")
    st.title("🤖 Khula Savings & Investment Learning Guide")
    st.caption("Brought forward from the original Khula AI advisor, with clearer inputs and evidence.")
    st.info(
        "Educational research only. Investment advice and intermediary services may require FSCA "
        "authorisation. No automatic transactions, promised growth or guaranteed returns."
    )
    context = get_ai_context(st.session_state.user_id)
    snap = _balance_summary()

    st.subheader("Your contribution position")
    st.write(f"Recorded monthly target: R{context['monthly_target']:,.2f}")
    st.write(f"Recorded contributions marked paid this month: R{context['this_month_contrib']:,.2f}")
    st.caption("Historical statuses should be reconciled against actual bank records before reliance.")

    risk_values = ["conservative", "moderate", "aggressive"]
    previous = context.get("risk_profile", "moderate")
    risk = st.selectbox("Risk tolerance — for educational scenarios", risk_values,
                        index=risk_values.index(previous) if previous in risk_values else 1)
    years = st.slider("Investment horizon in years", 1, 30, 5)
    monthly = st.number_input(
        "Illustrative extra monthly club savings (R)",
        min_value=0.0,
        value=float(context.get("monthly_target") or 0),
        step=100.0,
    )
    allocation = illustrative_allocation(risk, years)
    st.subheader("Example allocation buckets")
    if years < 3:
        st.warning("Short horizons prioritise liquidity and capital preservation over market exposure.")
    st.write({
        "Cash and emergency liquidity": f"{allocation['cash']}%",
        "Diversified bonds": f"{allocation['bonds']}%",
        "Broad diversified equities": f"{allocation['diversified_equity']}%",
    })

    # Without a bank snapshot, do not infer available money or allocate it.
    investable = snap["available"] if snap else None
    if investable is None:
        st.info("Record an actual club-bank snapshot through Admin Reconciliation to activate amount scenarios.")
    else:
        amounts = allocation_amounts(investable, allocation)
        st.dataframe(
            [{"Illustrative bucket": key.replace("_", " ").title(), "ZAR": float(amount)}
             for key, amount in amounts.items()],
            use_container_width=True,
        )
        st.caption("Model allocation only. Reserve, current exposures, penalties and votes must be reviewed first.")
        estimated = no_growth_projection(investable, monthly, years * 12)
        st.metric("Contributions-only scenario (0% return)", f"R{estimated:,.2f}")
        st.caption("This scenario deliberately excludes investment returns, inflation, fees and tax.")

    _optional_llm_commentary(investable, risk, years, allocation)
    st.divider()
    from khula_public_markets import render_current_market_rates
    render_current_market_rates()
    st.divider()
    st.subheader("Explore an actual market quote")
    ticker = _select_market_symbol("guide_quote")
    if st.button("Retrieve dated quote", key="guide_fetch_quote"):
        _render_quote(ticker, investable)


def render_market_explorer():
    track_feature_usage(st.session_state.user_id, "global_markets")
    st.title("🌍 Khula Global Markets Research")
    st.caption(
        "Replaces synthetic ticker data. Quotes require an authorised provider and may "
        "be delayed, absent, or subject to exchange subscription restrictions."
    )
    snap = _balance_summary()
    symbol = _select_market_symbol("markets_quote")
    if st.button("Fetch provider quote", type="primary"):
        _render_quote(symbol, snap["available"] if snap else None)
    st.info(
        "Check the currency and price unit directly with the venue or broker before "
        "relying on any quote. This application does not execute orders."
    )
