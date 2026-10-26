"""Pure, testable savings intelligence for Khula Collective.

Amounts are in ZAR and use Decimal, not binary floats. These are educational
scenarios only: no order placement, promises of returns or implied bank access.
"""
from decimal import Decimal, InvalidOperation, ROUND_DOWN

CENT = Decimal("0.01")


def zar(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not amount.is_finite():
        raise ValueError("Monetary amount must be finite")
    return amount.quantize(CENT)


def available_savings(bank_balance, reserved=0, committed=0):
    """Only a documented club bank snapshot can establish an available balance.

    Paid contributions, uploaded personal transactions and market-valued
    investments are NOT added again to the bank balance.
    """
    if bank_balance is None:
        return None
    cash, reserve, commitments = zar(bank_balance), zar(reserved), zar(committed)
    if min(cash, reserve, commitments) < 0:
        raise ValueError("Amounts cannot be negative")
    return max(Decimal("0.00"), cash - reserve - commitments).quantize(CENT)


def contribution_progress(paid_amount, monthly_target):
    paid, target = zar(paid_amount), zar(monthly_target)
    if paid < 0 or target <= 0:
        raise ValueError("Paid amount must be nonnegative and target positive")
    return {
        "paid": paid,
        "target": target,
        "shortfall": max(Decimal("0.00"), target - paid),
        "completion_pct": min(Decimal("100"), (paid / target * 100).quantize(CENT)),
    }


def illustrative_allocation(risk="moderate", years=3):
    """Simple educational buckets; not a product recommendation."""
    if risk not in ("conservative", "moderate", "aggressive"):
        raise ValueError("Unsupported risk profile")
    if not isinstance(years, int) or not 1 <= years <= 40:
        raise ValueError("Horizon must be 1-40 years")
    if years < 3:
        return {"cash": 80, "bonds": 20, "diversified_equity": 0}
    if risk == "conservative":
        return {"cash": 45, "bonds": 45, "diversified_equity": 10}
    if risk == "aggressive" and years >= 7:
        return {"cash": 15, "bonds": 20, "diversified_equity": 65}
    if risk == "moderate" and years >= 5:
        return {"cash": 25, "bonds": 35, "diversified_equity": 40}
    return {"cash": 40, "bonds": 40, "diversified_equity": 20}


def allocation_amounts(available, buckets):
    available = zar(available)
    if available < 0 or sum(buckets.values()) != 100:
        raise ValueError("Invalid amount or allocation")
    raw = {name: (available * Decimal(str(weight)) / 100).quantize(CENT, rounding=ROUND_DOWN)
           for name, weight in buckets.items()}
    first = next(iter(raw))
    raw[first] += available - sum(raw.values())
    return raw


def affordable_units(available, price_zar, exposure_limit_pct=10, cost_buffer_zar=0):
    """A capped affordability illustration, not a recommendation to buy."""
    if available is None:
        return None
    available = zar(available)
    price = zar(price_zar)
    costs = zar(cost_buffer_zar)
    pct = Decimal(str(exposure_limit_pct))
    if available < 0 or price <= 0 or costs < 0 or not Decimal(0) <= pct <= Decimal(100):
        raise ValueError("Invalid amounts or exposure")
    discretionary = max(Decimal(0), available * pct / 100 - costs)
    return int(discretionary // price)


def no_growth_projection(balance, monthly_contribution, months):
    """Contributions-only baseline; deliberately assumes no investment return."""
    start, monthly = zar(balance), zar(monthly_contribution)
    if start < 0 or monthly < 0 or not isinstance(months, int) or not 0 <= months <= 480:
        raise ValueError("Invalid projection inputs")
    return (start + monthly * months).quantize(CENT)
