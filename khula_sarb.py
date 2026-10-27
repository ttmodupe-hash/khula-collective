"""Sourced South African macroeconomic indicators.

Read-only official South African Reserve Bank public API. No API keys or
simulated values. Data can legitimately lag: display every original as-of date
and never call a historical observation a live trading quote.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import requests

API_URL = "https://custom.resbank.co.za/SarbWebApi/WebIndicators/HomePageRates"
OFFICIAL_PAGE = "https://www.resbank.co.za/"
SHOW = {
    "MMRD002A": "SARB policy rate",
    "MMRD000A": "Prime lending rate",
    "CPI1000F": "Consumer price inflation",
    "PPI1000F": "Producer price inflation",
    "EXCX135D": "Rand per US dollar",
    "EXCZ001D": "Rand per British pound",
    "EXCZ002D": "Rand per euro",
}
RATES = frozenset(("MMRD002A", "MMRD000A", "CPI1000F", "PPI1000F"))


class SarbDataError(Exception):
    pass


def normalise_indicators(payload, *, today=None):
    """Validate untrusted public API output, don't infer absent data."""
    if not isinstance(payload, list):
        raise SarbDataError("The SARB returned an unexpected response.")
    current = today or date.today()
    results = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        code = row.get("TimeseriesCode")
        if code not in SHOW:
            continue
        try:
            dated = date.fromisoformat(str(row.get("Date")))
            value = Decimal(str(row.get("Value")))
            if not value.is_finite():
                continue
            # Negative FX and interest rate outliers indicate bad feed data;
            # don't interpret malformed data as authoritative.
            if code not in RATES and value <= 0:
                continue
            if code in RATES and not (-10 <= value <= 100):
                continue
        except (ValueError, TypeError, InvalidOperation):
            continue
        days_old = (current - dated).days
        results.append({
            "code": code, "name": SHOW[code],
            "value": value, "as_of": dated.isoformat(),
            "units": "%" if code in RATES else "ZAR",
            "days_old": days_old,
            "stale": days_old < 0 or days_old > (100 if code in ("CPI1000F", "PPI1000F") else 30),
            "source": "South African Reserve Bank",
        })
    if not results:
        raise SarbDataError("No usable dated SARB observations were returned.")
    return sorted(results, key=lambda x: x["name"])


def fetch_sarb_indicators():
    try:
        resp = requests.get(
            API_URL,
            timeout=(4, 12),
            headers={"Accept": "application/json", "User-Agent": "KhulaCollective/4.1"},
        )
        resp.raise_for_status()
        if len(resp.content) > 200000:
            raise SarbDataError("Unexpectedly large macroeconomic response.")
        records = resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise SarbDataError("Official economic data is temporarily unavailable.") from exc
    return {
        "data": normalise_indicators(records),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_url": API_URL,
    }


def render_sarb_panel(*, expanded=True):
    import streamlit as st

    @st.cache_data(ttl=6 * 3600, show_spinner=False)
    def cached():
        return fetch_sarb_indicators()

    if expanded:
        st.subheader("🇿🇦 South Africa — official economic indicators")
    else:
        st.caption("Official economic indicators, not personal investment advice")
    try:
        bundle = cached()
    except SarbDataError as exc:
        st.warning(str(exc))
        st.markdown(f"[View the SARB website]({OFFICIAL_PAGE})")
        return
    observations = bundle["data"]
    st.caption(
        "Source: South African Reserve Bank · checked "
        + bundle["retrieved_at"][:16].replace("T", " ")
        + " UTC. Each observation has its own date; none is a live stock quote."
    )
    cols = st.columns(3)
    for idx, record in enumerate(observations):
        with cols[idx % 3]:
            st.metric(
                record["name"],
                f"{record['value']:,.4f} {record['units']}"
                if record["units"] == "ZAR"
                else f"{record['value']:,.2f}%",
            )
            st.caption("As of " + record["as_of"]
                       + (" · historical/stale" if record["stale"] else ""))
    if any(record["stale"] for record in observations):
        st.warning(
            "Some official observations are older than the expected reporting "
            "window. They are shown as historical figures, not current rates."
        )
    st.markdown(f"[Official SARB data source]({API_URL})")


def render_sarb_page():
    import streamlit as st
    st.title("🇿🇦 South African Economic Intelligence")
    st.write(
        "Public policy and economic indicators supplied by the SARB. "
        "These figures are separate from the club bank balance, stock quotations "
        "and personalised investment decisions."
    )
    render_sarb_panel()
    from khula_public_markets import render_current_market_rates
    render_current_market_rates()
