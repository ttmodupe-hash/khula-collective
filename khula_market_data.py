"""Licensed market-data adapter; fail closed rather than fabricate quotes.

Production display requires an approved commercial/exchange licence and a
Twelve Data API key. Quote timestamps, currency and provenance are retained.
"""
import os
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import requests


class MarketDataError(Exception):
    pass


API_BASE = "https://api.twelvedata.com"
VALID_SYMBOL = re.compile(r"^[A-Za-z0-9./:_=\\-]{1,32}$")


def market_configured():
    return (
        os.environ.get("KHULA_MARKET_DATA_PROVIDER", "").lower() == "twelvedata"
        and os.environ.get("KHULA_MARKET_DATA_LICENSE_APPROVED") == "1"
        and bool(os.environ.get("KHULA_TWELVEDATA_API_KEY", ""))
    )


def _request(endpoint, params):
    if not market_configured():
        raise MarketDataError("Market data not configured or commercial display rights not confirmed.")
    key = os.environ["KHULA_TWELVEDATA_API_KEY"]
    try:
        response = requests.get(
            API_BASE + endpoint,
            params={**params, "apikey": key, "format": "JSON"},
            timeout=(3, 8),
            headers={"Accept": "application/json", "User-Agent": "KhulaCollective/4.1"},
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MarketDataError("Market provider unavailable; no quote can be shown.") from exc
    if not isinstance(data, dict) or data.get("status") == "error" or "code" in data:
        raise MarketDataError("Market provider rejected this symbol or reached its quota.")
    return data


def _money_positive(value):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0:
            raise ValueError("Non-positive provider value")
        return number
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise MarketDataError("Market provider returned an invalid number.") from exc


def fetch_quote(symbol):
    """Return a sourced quote or raise; no fallback to mock prices."""
    symbol = str(symbol).strip().upper()
    if not VALID_SYMBOL.fullmatch(symbol):
        raise MarketDataError("Invalid market symbol.")
    data = _request("/quote", {"symbol": symbol})
    price = _money_positive(data.get("close"))
    currency = str(data.get("currency") or "").upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise MarketDataError("Quote currency is unavailable.")
    # The provider reports either a Unix timestamp or an exchange-local
    # market date. Do not label the date as the time we fetched the quote.
    reported = data.get("timestamp")
    if reported is not None:
        try:
            as_of = datetime.fromtimestamp(int(reported), tz=timezone.utc).isoformat()
        except (ValueError, OverflowError, TypeError) as exc:
            raise MarketDataError("Market quote has an invalid timestamp.") from exc
    else:
        as_of = str(data.get("datetime") or "")
    if not as_of:
        raise MarketDataError("Quote has no exchange timestamp.")
    return {
        "symbol": symbol,
        "name": str(data.get("name") or symbol),
        "price": price,
        "currency": currency,
        "exchange": str(data.get("exchange") or "Not provided"),
        "as_of": as_of,
        "source": "Twelve Data",
        "is_market_open": data.get("is_market_open"),
        "price_type": "most recent provider close (not guaranteed real-time)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_fx_rate(from_currency, to_currency="ZAR"):
    """Real provider FX reference, with timestamp and no static conversion."""
    from_currency, to_currency = str(from_currency).upper(), str(to_currency).upper()
    if not re.fullmatch(r"[A-Z]{3}", from_currency) or not re.fullmatch(r"[A-Z]{3}", to_currency):
        raise MarketDataError("Invalid currency pair.")
    if from_currency == to_currency:
        return {"rate": Decimal("1"), "as_of": "not applicable", "source": "same currency"}
    data = _request("/exchange_rate", {"symbol": f"{from_currency}/{to_currency}"})
    rate = _money_positive(data.get("rate"))
    ts = data.get("timestamp")
    if ts is None:
        raise MarketDataError("FX timestamp unavailable.")
    try:
        as_of = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (ValueError, OverflowError, TypeError) as exc:
        raise MarketDataError("Invalid FX timestamp.") from exc
    age_seconds = (datetime.now(timezone.utc) - as_of).total_seconds()
    if age_seconds < -600 or age_seconds > 172800:
        raise MarketDataError("FX rate is stale; ZAR affordability disabled.")
    return {"rate": rate, "as_of": as_of.isoformat(), "source": "Twelve Data"}
