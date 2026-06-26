"""The insight engine.

Given the normalized transactions, this finds the things a person usually
*doesn't* notice: recurring subscriptions and what they add up to, price
increases that crept in, redundant services, avoidable bank fees, spending
that quietly snowballs, and month-to-month anomalies.

All math is local and explainable — no black-box ML, no cloud calls.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .config import (NON_SPENDING_CATEGORIES, SUBSCRIPTION_CATEGORIES,
                     WASTE_PRONE_CATEGORIES)


def _d(iso: str) -> date:
    return datetime.strptime(iso, "%Y-%m-%d").date()


def _cv(values: list[float]) -> float:
    """Coefficient of variation (spread relative to the mean). 0 = identical."""
    if len(values) < 2:
        return 0.0
    m = statistics.fmean(values)
    if m == 0:
        return 999.0
    return statistics.pstdev(values) / abs(m)


@dataclass
class Recurring:
    merchant: str
    category: str
    account: str
    count: int
    cadence: str
    periods_per_year: float
    typical_amount: float          # magnitude, positive dollars
    first_amount: float
    current_amount: float
    first_date: str
    last_date: str
    annual_cost: float
    active: bool
    lifetime_total: float = 0.0    # sum of every charge we've seen for this stream
    typical_day: int = 0           # usual day-of-month it hits
    months_paying: int = 0         # how long you've been paying it


@dataclass
class Insight:
    severity: str                  # high | medium | low
    icon: str
    title: str
    detail: str
    annual_impact: float = 0.0     # estimated $/yr (0 if not applicable)
    items: list[str] = field(default_factory=list)
    recoverable: bool = False      # True if annual_impact is money you could redirect
    match_categories: list[str] = field(default_factory=list)  # for drill-down
    match_merchants: list[str] = field(default_factory=list)


_CADENCES = [
    ("weekly", 7, 52, 5, 9),
    ("every 2 weeks", 14, 26, 11, 18),
    ("monthly", 30, 12, 24, 37),
    ("quarterly", 91, 4, 75, 110),
    ("twice a year", 182, 2, 150, 210),
    ("yearly", 365, 1, 300, 400),
]


def _classify_cadence(median_gap: float) -> tuple[str, float] | None:
    for label, _ideal, ppy, lo, hi in _CADENCES:
        if lo <= median_gap <= hi:
            return label, float(ppy)
    return None


def fmt_money(x: float) -> str:
    return f"${x:,.2f}"


# --------------------------------------------------------------------------- #
# Recurring / subscription detection
# --------------------------------------------------------------------------- #
def detect_recurring(records: list[dict], data_max: date) -> list[Recurring]:
    by_merchant: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in records:
        if r["amount"] >= 0 or r["category"] in NON_SPENDING_CATEGORIES:
            continue
        by_merchant[(r["merchant"], r["account"])].append(r)

    found: list[Recurring] = []
    for (merchant, account), txns in by_merchant.items():
        if len(txns) < 3:
            continue
        txns = sorted(txns, key=lambda r: r["date"])
        dates = [_d(r["date"]) for r in txns]
        amounts = [abs(r["amount"]) for r in txns]

        gaps = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
        gaps = [g for g in gaps if g > 0]
        if len(gaps) < 2:
            continue
        median_gap = statistics.median(gaps)
        cad = _classify_cadence(median_gap)
        if cad is None:
            continue
        # Must be reasonably regular in timing *and* in amount.
        if _cv(gaps) > 0.45 or _cv(amounts) > 0.40:
            continue

        label, ppy = cad
        typical = statistics.median(amounts)
        annual = typical * ppy
        last_charge = dates[-1]
        active = (data_max - last_charge).days <= max(45, median_gap * 1.6)
        months_paying = max(1, round((dates[-1] - dates[0]).days / 30.4))

        found.append(Recurring(
            merchant=merchant, category=txns[0]["category"], account=account,
            count=len(txns), cadence=label, periods_per_year=ppy,
            typical_amount=typical, first_amount=amounts[0],
            current_amount=amounts[-1], first_date=dates[0].isoformat(),
            last_date=last_charge.isoformat(), annual_cost=annual, active=active,
            lifetime_total=round(sum(amounts), 2),
            typical_day=int(statistics.median([d.day for d in dates])),
            months_paying=months_paying))

    found.sort(key=lambda x: x.annual_cost, reverse=True)
    return found


# --------------------------------------------------------------------------- #
# Top-level analysis
# --------------------------------------------------------------------------- #
def analyze(rows) -> dict:
    records = [dict(r) for r in rows]
    if not records:
        return {"empty": True}

    dates = [_d(r["date"]) for r in records]
    data_min, data_max = min(dates), max(dates)
    months_span = max(1, (data_max.year - data_min.year) * 12
                      + (data_max.month - data_min.month) + 1)

    income = sum(r["amount"] for r in records if r["amount"] > 0
                 and r["category"] != "Transfers")
    expense = sum(-r["amount"] for r in records if r["amount"] < 0
                  and r["category"] not in NON_SPENDING_CATEGORIES)
    net = income - expense

    # ---- monthly cash flow ------------------------------------------------ #
    m_income: dict[str, float] = defaultdict(float)
    m_expense: dict[str, float] = defaultdict(float)
    for r in records:
        mk = r["date"][:7]
        if r["amount"] > 0 and r["category"] != "Transfers":
            m_income[mk] += r["amount"]
        elif r["amount"] < 0 and r["category"] not in NON_SPENDING_CATEGORIES:
            m_expense[mk] += -r["amount"]
    months = sorted(set(m_income) | set(m_expense))
    cash_flow = [{"month": m, "income": round(m_income.get(m, 0), 2),
                  "expense": round(m_expense.get(m, 0), 2),
                  "net": round(m_income.get(m, 0) - m_expense.get(m, 0), 2)}
                 for m in months]

    # ---- spending by category -------------------------------------------- #
    cat_totals: dict[str, float] = defaultdict(float)
    for r in records:
        if r["amount"] < 0 and r["category"] not in NON_SPENDING_CATEGORIES:
            cat_totals[r["category"]] += -r["amount"]
    category_totals = sorted(({"category": c, "total": round(v, 2)}
                              for c, v in cat_totals.items()),
                             key=lambda x: x["total"], reverse=True)

    # ---- top merchants ---------------------------------------------------- #
    merch_totals: dict[str, float] = defaultdict(float)
    merch_count: dict[str, int] = defaultdict(int)
    for r in records:
        if r["amount"] < 0 and r["category"] not in NON_SPENDING_CATEGORIES:
            merch_totals[r["merchant"]] += -r["amount"]
            merch_count[r["merchant"]] += 1
    top_merchants = sorted(({"merchant": m, "total": round(v, 2),
                             "count": merch_count[m]}
                            for m, v in merch_totals.items()),
                           key=lambda x: x["total"], reverse=True)[:15]

    # ---- recurring / subscriptions --------------------------------------- #
    recurring = detect_recurring(records, data_max)

    insights = _build_insights(records, recurring, cat_totals, cash_flow,
                               income, expense, months_span, data_min, data_max)

    return {
        "empty": False,
        "summary": {
            "data_min": data_min.isoformat(), "data_max": data_max.isoformat(),
            "months_span": months_span,
            "n_txns": len(records),
            "n_accounts": len({r["account"] for r in records}),
            "accounts": sorted({r["account"] for r in records}),
            "income": round(income, 2), "expense": round(expense, 2),
            "net": round(net, 2),
            "avg_monthly_spend": round(expense / months_span, 2),
            "savings_rate": round((net / income * 100) if income > 0 else 0, 1),
        },
        "cash_flow": cash_flow,
        "category_totals": category_totals,
        "top_merchants": top_merchants,
        "recurring": [r.__dict__ for r in recurring],
        "insights": [i.__dict__ for i in insights],
        "records": records,
    }


# --------------------------------------------------------------------------- #
# Insight builders
# --------------------------------------------------------------------------- #
def _build_insights(records, recurring, cat_totals, cash_flow, income, expense,
                    months_span, data_min, data_max) -> list[Insight]:
    out: list[Insight] = []
    active = [r for r in recurring if r.active]

    # 1) Total recurring commitments -- the headline people underestimate.
    if active:
        monthly = sum(r.annual_cost for r in active) / 12
        annual = sum(r.annual_cost for r in active)
        out.append(Insight(
            "high", "🔁",
            f"You have {len(active)} recurring charges totaling about "
            f"{fmt_money(monthly)}/month ({fmt_money(annual)}/year)",
            "These are charges that repeat on a schedule. Costs add up quietly — "
            "review the list below and cancel anything you don't use.",
            annual_impact=annual,
            match_merchants=[r.merchant for r in active],
            items=[f"{r.merchant} — {fmt_money(r.typical_amount)} {r.cadence} "
                   f"(~{fmt_money(r.annual_cost)}/yr)"
                   for r in sorted(active, key=lambda x: x.annual_cost,
                                   reverse=True)[:12]]))

    # 2) Avoidable bank fees & interest.
    fees = [r for r in records if r["category"] == "Fees & Interest"
            and r["amount"] < 0]
    if fees:
        total = sum(-f["amount"] for f in fees)
        per_year = total / months_span * 12
        by_acct = defaultdict(float)         # group by account: shows WHICH card
        for f in fees:
            by_acct[f["account"]] += -f["amount"]
        top = sorted(by_acct.items(), key=lambda x: x[1], reverse=True)[:6]
        out.append(Insight(
            "high", "⚠️",
            f"{fmt_money(total)} lost to fees & interest "
            f"({len(fees)} charges)",
            "Mostly credit-card interest on carried balances, plus the odd annual or "
            "bank fee. Paying these cards down (and paying on time) erases it. "
            "Here's which account each dollar came from:",
            annual_impact=per_year, recoverable=True,
            match_categories=["Fees & Interest"],
            items=[f"{acct}: {fmt_money(amt)}" for acct, amt in top]))

    # 3) Redundant services in the same category (e.g. 2+ streaming apps).
    by_cat: dict[str, list] = defaultdict(list)
    for r in active:
        if r.category in SUBSCRIPTION_CATEGORIES:
            by_cat[r.category].append(r)
    for cat, subs in by_cat.items():
        if len(subs) >= 2:
            annual = sum(s.annual_cost for s in subs)
            out.append(Insight(
                "medium", "👯",
                f"{len(subs)} separate {cat} subscriptions "
                f"(~{fmt_money(annual)}/year combined)",
                "These all sit in the same category, so some may overlap. Check "
                "whether you actually use each one — dropping the ones you don't "
                "could recover most of this.",
                annual_impact=annual - min(s.annual_cost for s in subs),
                recoverable=True, match_merchants=[s.merchant for s in subs],
                items=[f"{s.merchant} — {fmt_money(s.annual_cost)}/yr" for s in
                       sorted(subs, key=lambda x: x.annual_cost, reverse=True)]))

    # 4) Price creep on subscriptions (only true subscriptions — not travel/shopping
    #    that naturally varies in price).
    for r in recurring:
        if r.category in SUBSCRIPTION_CATEGORIES and \
                r.current_amount > r.first_amount * 1.05 and \
                (r.current_amount - r.first_amount) >= 0.50:
            rise = r.current_amount - r.first_amount
            pct = rise / r.first_amount * 100
            out.append(Insight(
                "medium", "📈",
                f"{r.merchant} quietly raised its price "
                f"{fmt_money(r.first_amount)} → {fmt_money(r.current_amount)} "
                f"(+{pct:.0f}%)",
                "Subscription prices often rise without notice. That increase alone "
                f"costs about {fmt_money(rise * r.periods_per_year)} more per year.",
                annual_impact=rise * r.periods_per_year, recoverable=True,
                match_merchants=[r.merchant]))

    # 5) Newly-started recurring charges (possible free-trial conversions).
    #    Signal: the first charge appears well after the data starts (so it's a
    #    recently adopted commitment), it's still active, and there aren't many
    #    charges yet.
    for r in active:
        started_after_start = (_d(r.first_date) - data_min).days >= 45
        # Only flag smallish subscription-type charges (a real trial-conversion
        # pattern) — not large recurring items like rent, tuition, or transfers.
        if (started_after_start and r.count <= 6
                and r.category in SUBSCRIPTION_CATEGORIES
                and r.typical_amount <= 100):
            out.append(Insight(
                "medium", "🆕",
                f"New recurring charge started: {r.merchant} "
                f"({fmt_money(r.typical_amount)} {r.cadence})",
                f"This began on {r.first_date} — partway through your history. If it "
                "followed a free trial, make sure you still want it.",
                annual_impact=r.annual_cost, recoverable=True,
                match_merchants=[r.merchant]))

    # 6) "Death by a thousand cuts" — small frequent discretionary spend.
    for cat in WASTE_PRONE_CATEGORIES:
        if cat == "Fees & Interest":
            continue
        items = [r for r in records if r["category"] == cat and r["amount"] < 0]
        total = sum(-r["amount"] for r in items)
        if len(items) >= 8 and total > 0:
            per_year = total / months_span * 12
            avg = total / len(items)
            out.append(Insight(
                "low", "☕",
                f"{cat}: {len(items)} purchases adding up to {fmt_money(total)} "
                f"(~{fmt_money(per_year)}/year)",
                f"Small buys (avg {fmt_money(avg)}) are easy to overlook but compound. "
                "Even halving this is real money.",
                annual_impact=per_year / 2, recoverable=True,
                match_categories=[cat]))

    # 7) Monthly spending anomalies per category.
    cat_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in records:
        if r["amount"] < 0 and r["category"] not in NON_SPENDING_CATEGORIES:
            cat_month[r["category"]][r["date"][:7]] += -r["amount"]
    for cat, mm in cat_month.items():
        if len(mm) < 4:
            continue
        vals = list(mm.values())
        med = statistics.median(vals)
        if med < 40:
            continue
        worst_month, worst_val = max(mm.items(), key=lambda x: x[1])
        if worst_val >= med * 2.2 and worst_val - med >= 100:
            out.append(Insight(
                "low", "🔎",
                f"Unusual {cat} spike in {worst_month}: {fmt_money(worst_val)} "
                f"(typical month is about {fmt_money(med)})",
                "A one-off, or the start of a trend? Worth a quick look.",
                annual_impact=0.0, match_categories=[cat]))

    # 8) Cash-flow / savings health.
    if income > 0:
        rate = (income - expense) / income * 100
        if expense > income:
            out.append(Insight(
                "high", "🛟",
                f"You spent more than you earned by "
                f"{fmt_money(expense - income)} over this period",
                "Outflows exceeded income. The categories and recurring charges "
                "above are the fastest places to find cuts.",
                annual_impact=0.0))
        elif rate < 10:
            out.append(Insight(
                "medium", "💧",
                f"Low savings rate: you kept only {rate:.0f}% of your income",
                "A common target is 20%. Trimming the recurring and discretionary "
                "items above is the easiest lever.",
                annual_impact=0.0))

    # Highest-dollar, highest-severity first.
    sev = {"high": 0, "medium": 1, "low": 2}
    out.sort(key=lambda i: (sev[i.severity], -i.annual_impact))
    return out
