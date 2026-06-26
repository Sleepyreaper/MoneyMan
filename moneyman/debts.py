"""Debts, interest, and payoff planning — the part that gets you to $0 owed.

This is judgment-free and personalized: it works from YOUR real balances, YOUR
real interest rates, and the spare money YOUR budget actually has (including the
waste MoneyMan finds and you choose to redirect). It does not lecture.

Two well-known strategies are modeled:
  * Avalanche  — pay the highest-interest debt first  (mathematically cheapest)
  * Snowball   — pay the smallest balance first        (fastest visible wins)

And three intensity paths, all of which always cover your minimum payments:
  * Easy       — a gentle nudge above the minimums
  * Average    — a balanced amount
  * Aggressive — throw everything spare at it (debt-free soonest)
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class Debt:
    name: str
    kind: str                      # credit card | auto loan | student loan | ...
    balance: float
    apr: float                     # annual percentage rate, e.g. 24.99
    min_payment: float
    credit_limit: float = 0.0
    apr_estimated: bool = False    # True if we inferred it from interest charged
    source: str = "manual"

    @property
    def monthly_rate(self) -> float:
        return self.apr / 100.0 / 12.0

    @property
    def monthly_interest(self) -> float:
        return self.balance * self.monthly_rate

    @property
    def utilization(self) -> float | None:
        if self.credit_limit and self.credit_limit > 0:
            return self.balance / self.credit_limit * 100.0
        return None


@dataclass
class PayoffResult:
    strategy: str
    monthly_budget: float
    months: int
    total_interest: float
    total_paid: float
    payoff_date: str
    order: list[str]                       # names, in the order they're cleared
    covers_minimums: bool
    finished: bool
    balances_over_time: list[float] = field(default_factory=list)  # total owed/month


DEBTS_TEMPLATE = """\
# MoneyMan — Accounts & Debts.  List every balance you OWE (cards, loans).
# MoneyMan also tries to read these from your statements, but typing them here
# guarantees an accurate payoff plan. Delete the example rows and add your own.
# Type can be: credit card, auto loan, student loan, personal loan, mortgage, medical, other
Name,Type,Balance Owed,APR (%),Minimum Monthly Payment,Credit Limit
Example Visa,credit card,6200,24.99,155,8000
Example Car Loan,auto loan,14800,6.4,410,
"""


def write_debts_template(path: Path) -> None:
    if not path.exists():
        path.write_text(DEBTS_TEMPLATE, encoding="utf-8")


def write_detected_debts(path: Path, debts: list[Debt]) -> None:
    """Pre-fill the debts file with balances we detected; user adds APR & minimum."""
    import io
    comments = (
        "# MoneyMan detected these debts from your account balances.\n"
        "# Add the APR (interest rate) and Minimum Monthly Payment for each one to\n"
        "# unlock your full payoff plan. (Find them on your latest statement.)\n"
        "# Type can be: credit card, auto loan, student loan, personal loan, mortgage, medical, other\n")
    buf = io.StringIO()
    w = csv.writer(buf)        # csv.writer quotes fields containing commas/quotes
    w.writerow(["Name", "Type", "Balance Owed", "APR (%)",
                "Minimum Monthly Payment", "Credit Limit"])
    for d in sorted(debts, key=lambda x: x.balance, reverse=True):
        w.writerow([d.name, d.kind, f"{d.balance:.2f}", "", "", ""])
    path.write_text(comments + buf.getvalue(), encoding="utf-8")


def _money(v: str) -> float:
    v = (v or "").strip().replace("$", "").replace(",", "").replace("%", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def load_debts_csv(path: Path) -> list[Debt]:
    if not path.exists():
        return []
    out: list[Debt] = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(
                row for row in f if row.strip() and not row.lstrip().startswith("#"))
            cols = {(c or "").strip().lower(): c for c in (reader.fieldnames or [])}

            def col(*names):
                for n in names:
                    if n in cols:
                        return cols[n]
                return None

            c_name = col("name")
            c_type = col("type", "kind")
            c_bal = col("balance owed", "balance", "amount owed")
            c_apr = col("apr (%)", "apr", "interest rate", "rate")
            c_min = col("minimum monthly payment", "minimum payment", "min payment")
            c_lim = col("credit limit", "limit")
            for r in reader:
                name = (r.get(c_name) or "").strip() if c_name else ""
                bal = _money(r.get(c_bal, "")) if c_bal else 0.0
                if not name or bal <= 0:
                    continue
                if name.lower().startswith("example "):
                    continue
                out.append(Debt(
                    name=name,
                    kind=(r.get(c_type) or "other").strip().lower() if c_type else "other",
                    balance=bal,
                    apr=_money(r.get(c_apr, "")) if c_apr else 0.0,
                    min_payment=_money(r.get(c_min, "")) if c_min else 0.0,
                    credit_limit=_money(r.get(c_lim, "")) if c_lim else 0.0,
                    source="manual"))
    except Exception:
        return out
    return out


def infer_apr(interest_charged: float, average_balance: float) -> float | None:
    """Estimate APR from one period's interest and the balance it accrued on."""
    if average_balance and average_balance > 0 and interest_charged > 0:
        monthly = interest_charged / average_balance
        return round(monthly * 12 * 100, 2)
    return None


def _looks_like_interest(record: dict) -> bool:
    """An interest/finance charge we can back a rate out of — covers credit-card
    'Fees & Interest', a HELOC/loan 'Interest' line, or any 'interest charge' text."""
    cat = record.get("category", "")
    if cat in ("Fees & Interest", "Interest"):
        return True
    text = f'{record.get("merchant", "")} {record.get("raw_description", "")}'.lower()
    if "finance charge" in text:
        return True
    return "interest" in text and "income" not in text and "paid to you" not in text


def _interest_by_account_month(records: list[dict]) -> dict[str, dict[str, float]]:
    """{account: {YYYY-MM: interest charged that month}}.

    Uses the magnitude of the charge so it works whether interest is recorded as a
    negative on a card or a positive on a liability account (e.g. a HELOC).
    """
    from collections import defaultdict
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in records:
        if not _looks_like_interest(r):
            continue
        out[r.get("account", "")][r["date"][:7]] += abs(float(r["amount"]))
    return out


def _balance_as_of(series: list[tuple[str, float]], month: str) -> float | None:
    """Most recent (absolute) balance on/before the end of `month` (YYYY-MM)."""
    last = None
    for d, bal in series:                 # series is sorted ascending by date
        if d[:7] <= month:
            last = bal
        else:
            break
    return last


def infer_aprs_from_records(debts: list[Debt], records: list[dict],
                            balances: list[tuple[str, str, float]],
                            months_span: int) -> int:
    """Fill in a missing APR on each debt from the interest its account was charged.

    The accurate way: for each month a card was charged interest, divide that
    month's interest by *that month's* balance (read from the balance history when
    we have it), then take the median across months. That stays right even when the
    balance grew or shrank over time — unlike dividing a total by the latest balance.

    Returns how many APRs we estimated. Recurring interest is the signature of a
    revolving credit card, so we also classify the debt that way and give it a
    workable minimum if one is missing — which is what unlocks the payoff plan
    automatically, without the user having to type the rate.
    """
    import statistics
    from collections import defaultdict

    interest_by = _interest_by_account_month(records)
    series: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for d, acct, bal in balances:
        series[acct].append((d, abs(bal)))
    for acct in series:
        series[acct].sort()

    estimated = 0
    for d in debts:
        if d.apr > 0 or d.balance <= 0:
            continue
        months = interest_by.get(d.name)
        if not months:
            continue
        ser = series.get(d.name)
        rates: list[float] = []
        for mon, interest in months.items():
            if interest <= 0:
                continue
            bal = (_balance_as_of(ser, mon) if ser else None) or d.balance
            if bal and bal > 0:
                rates.append(interest / bal)
        if not rates:
            continue
        apr = round(statistics.median(rates) * 12 * 100, 2)
        if apr <= 0:
            continue
        d.apr = min(apr, 99.0)                  # sane cap against data quirks
        d.apr_estimated = True
        estimated += 1
        # Give revolving cards a workable minimum (unlocks payoff). Leave secured
        # home debt (mortgage/HELOC) and named installment loans as-is.
        secured = "mortgage" in d.kind or "heloc" in d.kind
        if d.min_payment <= 0 and not secured:
            if d.kind not in ("auto loan", "student loan", "personal loan"):
                d.kind = "credit card"          # interest every month => revolving
            d.min_payment = max(25.0, round(d.balance * 0.02, 2))
    return estimated


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    return date(y, m % 12 + 1, 1)


def _pick_target(active: list[Debt], strategy: str) -> Debt:
    if strategy == "snowball":
        return min(active, key=lambda x: (x.balance, -x.apr))
    return max(active, key=lambda x: (x.apr, -x.balance))   # avalanche


def simulate_payoff(debts: list[Debt], monthly_budget: float,
                    strategy: str = "avalanche", start: date | None = None,
                    max_months: int = 1200) -> PayoffResult:
    """Month-by-month amortization. Interest accrues, minimums are paid on every
    debt, and all remaining money attacks one target debt per the strategy. When
    a debt is cleared its payment rolls onto the next target."""
    start = start or date.today()
    bal = {d.name: float(d.balance) for d in debts}
    rate = {d.name: d.monthly_rate for d in debts}
    minp = {d.name: float(d.min_payment) for d in debts}
    by_name = {d.name: d for d in debts}

    min_total = sum(minp.values())
    covers_minimums = monthly_budget + 1e-9 >= min_total

    total_interest = 0.0
    total_paid = 0.0
    order: list[str] = []
    history: list[float] = [round(sum(bal.values()), 2)]
    month = 0

    while any(v > 0.005 for v in bal.values()) and month < max_months:
        month += 1
        # 1) accrue interest
        for n, v in bal.items():
            if v > 0.005:
                itx = v * rate[n]
                bal[n] = v + itx
                total_interest += itx
        # 2) pay minimums (target order for determinism), capped by balance/budget
        active = [d for d in debts if bal[d.name] > 0.005]
        active_sorted = sorted(active, key=lambda d: (-d.apr if strategy != "snowball"
                                                       else d.balance))
        remaining = monthly_budget
        for d in active_sorted:
            pay = min(minp[d.name], bal[d.name], max(remaining, 0))
            bal[d.name] -= pay
            remaining -= pay
            total_paid += pay
        # 3) throw everything left at the single target debt, rolling as needed
        while remaining > 0.005:
            still = [d for d in debts if bal[d.name] > 0.005]
            if not still:
                break
            t = _pick_target(still, strategy)
            pay = min(remaining, bal[t.name])
            bal[t.name] -= pay
            remaining -= pay
            total_paid += pay
        # 4) record any debts cleared this month
        for d in debts:
            if bal[d.name] <= 0.005 and d.name not in order:
                order.append(d.name)
        history.append(round(sum(max(v, 0) for v in bal.values()), 2))

    finished = all(v <= 0.005 for v in bal.values())
    return PayoffResult(
        strategy=strategy, monthly_budget=round(monthly_budget, 2), months=month,
        total_interest=round(total_interest, 2), total_paid=round(total_paid, 2),
        payoff_date=_add_months(start, month).strftime("%b %Y"),
        order=order, covers_minimums=covers_minimums, finished=finished,
        balances_over_time=history)


def plan_paths(debts: list[Debt], monthly_leftover: float,
               recoverable_waste_monthly: float) -> dict:
    """Build Easy / Average / Aggressive plans plus the minimums-only baseline.

    'monthly_leftover'  = money currently left over after spending (>=0).
    'recoverable_waste' = monthly value of waste MoneyMan found you could redirect.
    All three paths always cover the minimum payments; the difference is how much
    *extra* goes on top.
    """
    debts = [d for d in debts if d.balance > 0.005]
    if not debts:
        return {"has_debts": False}

    min_total = sum(d.min_payment for d in debts)
    leftover = max(0.0, monthly_leftover)
    waste = max(0.0, recoverable_waste_monthly)
    capacity = leftover + waste            # spare money available for EXTRA payments

    extras = {
        "easy": round(max(25.0, 0.25 * capacity)),
        "average": round(max(50.0, 0.60 * capacity)),
        "aggressive": round(max(100.0, capacity)),
    }
    # never let "easy" exceed "average", etc., if capacity is tiny
    extras["average"] = max(extras["average"], extras["easy"])
    extras["aggressive"] = max(extras["aggressive"], extras["average"])

    baseline = simulate_payoff(debts, min_total, "avalanche")
    # If the minimums barely cover the interest (e.g. a 24% card with a 2% minimum),
    # the minimums-only baseline never actually clears the debt — it just runs to the
    # simulation cap. In that case "saved vs minimums" is a meaningless huge number,
    # so we flag it and let the report say the honest thing instead.
    minimums_never_payoff = not baseline.finished
    paths = {}
    for tier, extra in extras.items():
        res = simulate_payoff(debts, min_total + extra, "avalanche")
        res_snow = simulate_payoff(debts, min_total + extra, "snowball")
        paths[tier] = {
            "extra": extra,
            "avalanche": res,
            "snowball": res_snow,
            # Only quote a finite "saved" figure when minimums-only actually finishes.
            "interest_saved": (None if minimums_never_payoff else
                               round(baseline.total_interest - res.total_interest, 2)),
            "months_saved": (None if minimums_never_payoff else
                             baseline.months - res.months),
        }

    total_balance = sum(d.balance for d in debts)
    total_monthly_interest = sum(d.monthly_interest for d in debts)
    weighted_apr = (sum(d.apr * d.balance for d in debts) / total_balance
                    if total_balance else 0.0)

    # Interest you keep paying each year if you only ever pay the minimums.
    minimums_annual_interest = round(total_monthly_interest * 12, 2)

    return {
        "has_debts": True,
        "minimums_never_payoff": minimums_never_payoff,
        "minimums_annual_interest": minimums_annual_interest,
        "debts": sorted(debts, key=lambda d: d.apr, reverse=True),
        "min_total": round(min_total, 2),
        "total_balance": round(total_balance, 2),
        "total_monthly_interest": round(total_monthly_interest, 2),
        "weighted_apr": round(weighted_apr, 2),
        "leftover": round(leftover, 2),
        "recoverable_waste": round(waste, 2),
        "capacity": round(capacity, 2),
        "baseline": baseline,
        "paths": paths,
    }
