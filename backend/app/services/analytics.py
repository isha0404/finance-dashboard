"""Pure functions that turn a list of transactions into dashboard numbers.

Kept free of database code so they are fast and simple to unit test.
"""
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

ZERO = Decimal("0.00")


class TxLike(Protocol):
    date: date
    amount: Decimal
    category: str


@dataclass
class SummaryData:
    month: str
    income: Decimal
    spending: Decimal
    net: Decimal
    savings_rate: float
    top_category: str | None
    transaction_count: int


def month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def previous_months(end: date, count: int) -> list[str]:
    """The `count` month keys ending at `end`'s month, oldest first."""
    y, m = end.year, end.month
    keys = []
    for _ in range(count):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(keys))


def summarise(transactions: Iterable[TxLike], month: str) -> SummaryData:
    income = spending = ZERO
    by_cat: dict[str, Decimal] = defaultdict(lambda: ZERO)
    count = 0
    for t in transactions:
        if month_key(t.date) != month:
            continue
        count += 1
        if t.amount > 0:
            income += t.amount
        else:
            spending += -t.amount
            by_cat[t.category] += -t.amount

    net = income - spending
    rate = float(round(net / income * 100, 1)) if income > 0 else 0.0
    top = max(by_cat, key=by_cat.get) if by_cat else None
    return SummaryData(month, income, spending, net, rate, top, count)


def monthly_totals(transactions: Iterable[TxLike], months: list[str]) -> list[dict]:
    buckets = {m: {"month": m, "income": ZERO, "spending": ZERO} for m in months}
    for t in transactions:
        k = month_key(t.date)
        if k not in buckets:
            continue
        if t.amount > 0:
            buckets[k]["income"] += t.amount
        else:
            buckets[k]["spending"] += -t.amount
    return [buckets[m] for m in months]


def spending_by_category(transactions: Iterable[TxLike], month: str | None = None) -> list[dict]:
    totals: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for t in transactions:
        if t.amount >= 0:
            continue
        if month and month_key(t.date) != month:
            continue
        totals[t.category] += -t.amount
    return [
        {"category": c, "total": v}
        for c, v in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    ]
