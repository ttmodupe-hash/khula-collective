"""Process-local, fail-closed upstream backoff for read-only provider calls.

Purpose: stop a thundering herd after repeated upstream errors while the
existing Streamlit cache and official-source fallback keep serving users.
This is intentionally NOT a replacement for admission, password, payment or
bank-API rate limits. It stores no personal data, messages, keys or metrics.
"""
from contextlib import contextmanager
from threading import Lock
import time

_PUBLIC_PROVIDERS = frozenset({
    "sarb_macro", "sarb_markets", "licensed_market",
})
_LOCK = Lock()
_STATE = {}


class ProviderBackoff(Exception):
    """Public upstream is cooling down; no data may be invented or substituted."""


@contextmanager
def public_request_guard(source, *, clock=None):
    """Use around a real public provider request with existing hard timeouts.

    Three failures inside 60 seconds cause 15 seconds of cooldown; repeated
    bursts double the delay up to 120 seconds. A successful request resets
    the breaker. It works in one process; each Railway replica is independent.
    """
    if source not in _PUBLIC_PROVIDERS:
        raise ValueError("Unknown public data source.")
    tick = time.monotonic if clock is None else clock
    with _LOCK:
        state = _STATE.get(source)
        if state and tick() < state["retry_at"]:
            raise ProviderBackoff("Data provider temporarily cooling down.")
    try:
        yield
    except Exception:
        now = tick()
        with _LOCK:
            old = _STATE.get(source)
            streak = old["failures"] if old and now - old["last_failure"] <= 60 else 0
            streak += 1
            retry_at = now
            if streak >= 3:
                retry_at += min(120, 15 * (2 ** min(streak - 3, 4)))
            _STATE[source] = {
                "failures": streak, "last_failure": now, "retry_at": retry_at,
            }
        raise
    else:
        with _LOCK:
            _STATE.pop(source, None)


def _clear_test_state():
    """Isolate synthetic unit tests, never used by application routes."""
    with _LOCK:
        _STATE.clear()
