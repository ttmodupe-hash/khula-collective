"""Real, dated public South African money and capital market observations.

This uses SARB's official WebIndicators/CurrentMarketRates endpoint. It is NOT
a licensed equity trading feed, a current executable quote, or a portfolio
recommendation; records are shown only with their own observation dates.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

import requests

SOURCE = "South African Reserve Bank"
API_URL = "https://custom.resbank.co.za/SarbWebApi/WebIndicators/CurrentMarketRates"

# The original Khula investment club considers liquid cash, bonds and
# diversified investments. These are macro/market references, not guaranteed
# rates available to an individual club.
SERIES = {
    "MMRD203A": ("91-day Treasury bill tender rate", "%", "Money markets"),
    "MMRD206A": ("182-day Treasury bill tender rate", "%", "Money markets"),
    "MMRD212A": ("364-day Treasury bill tender rate", "%", "Money markets"),
    "MMRD851A": ("Sabor", "%", "Money markets"),
    "MMRD855A": ("Zaronia", "%", "Money markets"),
    "MMRD708A": ("2030 RSA bond closing yield", "%", "Bonds"),
    "MMRD709A": ("2036 RSA bond closing yield", "%", "Bonds"),
    "EXCX135D": ("ZAR per USD", "ZAR/USD", "Exchange rates"),
    "EXCZ002D": ("ZAR per EUR", "ZAR/EUR", "Exchange rates"),
    "GDPL203D": ("Gold per fine ounce", "ZAR/oz", "Commodities"),
}


class SarbMarketError(Exception):
    pass


def normalise_current_market_rates(payload, *, today=None):
    if not isinstance(payload, list):
        raise SarbMarketError("Unexpected official market-data response.")
    today = today or date.today()
    output = []
    for record in payload:
        if not isinstance(record, dict):
            continue
        series = record.get("TimeseriesCode")
        if series not in SERIES:
            continue
        try:
            observed = date.fromisoformat(str(record.get("Date")))
            value = Decimal(str(record.get("Value")))
            if not value.is_finite() or value <= 0 or value > 100000000:
                continue
        except (TypeError, ValueError, InvalidOperation):
            continue
        name, unit, category = SERIES[series]
        age = (today - observed).days
        fresh_window = 7 if category in ("Exchange rates", "Commodities") else 14
        output.append({
            "code": series,
            "name": name,
            "value": value,
            "units": unit,
            "group": category,
            "as_of": observed.isoformat(),
            "age_days": age,
            "stale": age < 0 or age > fresh_window,
            "source": SOURCE,
        })
    if not output:
        raise SarbMarketError("No usable public market observations were returned.")
    return sorted(output, key=lambda r: (r["group"], r["name"]))


def fetch_current_market_rates():
    try:
        response = requests.get(
            API_URL,
            timeout=(4, 12),
            headers={"Accept": "application/json", "User-Agent": "KhulaCollective/4.2"},
        )
        response.raise_for_status()
        if len(response.content) > 250000:
            raise SarbMarketError("Official market response exceeds size limits.")
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise SarbMarketError("Official money and capital market data is temporarily unavailable.") from exc
    return {
        "observations": normalise_current_market_rates(data),
        "source_url": API_URL,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def render_current_market_rates():
    import streamlit as st

    @st.cache_data(ttl=3600, show_spinner=False)
    def _cached():
        return fetch_current_market_rates()

    st.subheader("🏦 South African money, bonds & currency")
    st.caption(
        "Observed official rates—not offered deposit rates, guaranteed returns "
        "or tradeable prices. Dates are supplied by the SARB."
    )
    try:
        bundle = _cached()
    except SarbMarketError as exc:
        st.warning(str(exc))
        st.link_button("SARB official source", "https://www.resbank.co.za/")
        return
    st.caption(
        "Source: South African Reserve Bank · checked "
        + bundle["checked_at"][:16].replace("T", " ") + " UTC"
    )
    entries = bundle["observations"]
    for group in ["Money markets", "Bonds", "Exchange rates", "Commodities"]:
        matching = [r for r in entries if r["group"] == group]
        if not matching:
            continue
        with st.expander(group, expanded=(group == "Money markets")):
            for r in matching:
                st.write(f"**{r['name']}**: {r['value']:,.4f} {r['units']}")
                st.caption(
                    "Observed " + r["as_of"]
                    + (" · HISTORICAL / STALE" if r["stale"] else "")
                )
    if any(r["stale"] for r in entries):
        st.warning("Some official observations are out of date. Do not treat them as current investable rates.")
    st.link_button("See SARB published market data", bundle["source_url"])
