"""Forward-looking cash management.

Two things people most want from a money app and rarely get from a ledger:

  1. **A cash-flow forecast** — "given how money has actually been moving, where
     will my checking balance be over the next few months, and do I dip into the
     red?" We project from real history, not a guess.
  2. **A 'safe to spend' number** — what's genuinely free to spend this month after
     the bills you can't skip and the money you've decided to save.

Plus a small **goal planner**: name a target and a date, and we tell you the
monthly amount it takes — and whether your current surplus can cover it.

All of this is plain arithmetic on numbers MoneyMan already computed. No network,
no forecasting black box — just your own cash flow, made visible ahead of time.
"""

from __future__ import annotations

import csv
import io
import statistics
from datetime import date, datetime
from pathlib import Path


# --------------------------------------------------------------------------- #
# Cash-flow forecast
# --------------------------------------------------------------------------- #
def expected_monthly_net(cash_flow: list[dict], lookback: int = 12) -> dict:
    """A robust estimate of your typical monthly net (income − spending).

    Uses the median of recent months (not the mean) so one giant bonus or one
    rough month doesn't distort the picture, and reports a cautious 'lean' month
    (a low-but-not-worst recent month) for stress-testing.
    """
    nets = [m["net"] for m in cash_flow]
    if not nets:
        return {"typical": 0.0, "lean": 0.0, "months_used": 0}
    recent = nets[-lookback:] if len(nets) > lookback else nets
    typical = statistics.median(recent)
    # 'lean' = 25th-percentile-ish month: the lower quartile, so a normal bad month.
    lean = statistics.quantiles(recent, n=4)[0] if len(recent) >= 4 else min(recent)
    return {"typical": round(typical, 2), "lean": round(lean, 2),
            "months_used": len(recent)}


def _month_label(start: str, offset: int) -> str:
    """start = 'YYYY-MM'; return the label `offset` months later."""
    y, m = int(start[:4]), int(start[5:7])
    m += offset
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}"


def cashflow_forecast(starting_cash: float, cash_flow: list[dict],
                      months: int = 6, cash_floor: float = 0.0,
                      lookback: int = 12) -> dict:
    """Project the cash balance forward `months` months from `starting_cash`.

    Returns the projected balance each month under a typical and a lean scenario,
    the lowest point, the first month (if any) you'd drop below `cash_floor`, and —
    if you're running a deficit — how many months of runway the cash buys.
    """
    est = expected_monthly_net(cash_flow, lookback)
    typical, lean = est["typical"], est["lean"]
    last_month = cash_flow[-1]["month"] if cash_flow else date.today().strftime("%Y-%m")

    points: list[dict] = []
    cash_t = cash_l = starting_cash
    for i in range(1, months + 1):
        cash_t += typical
        cash_l += lean
        points.append({
            "month": _month_label(last_month, i),
            "typical": round(cash_t, 2),
            "lean": round(cash_l, 2)})

    lowest = min((p["lean"] for p in points), default=starting_cash)
    shortfall_month = next((p["month"] for p in points if p["lean"] < cash_floor), None)
    runway_months = None
    if typical < 0 < (starting_cash - cash_floor):
        runway_months = int((starting_cash - cash_floor) / -typical)

    return {
        "starting_cash": round(starting_cash, 2),
        "typical_net": typical,
        "lean_net": lean,
        "months_used": est["months_used"],
        "months": months,
        "points": points,
        "ending_typical": points[-1]["typical"] if points else round(starting_cash, 2),
        "lowest_projected": round(lowest, 2),
        "cash_floor": round(cash_floor, 2),
        "shortfall_month": shortfall_month,
        "runway_months": runway_months,
        "healthy": shortfall_month is None,
    }


# --------------------------------------------------------------------------- #
# Safe to spend
# --------------------------------------------------------------------------- #
def safe_to_spend(income_monthly: float, essentials_monthly: float,
                  subscriptions_monthly: float, savings_setaside_monthly: float) -> dict:
    """What's genuinely free to spend each month after the non-negotiables.

    safe = income − essentials − subscriptions − money you've chosen to save
    (sinking funds + building the emergency fund + any extra debt payment).
    """
    committed = (max(0.0, essentials_monthly) + max(0.0, subscriptions_monthly)
                 + max(0.0, savings_setaside_monthly))
    safe = income_monthly - committed
    return {
        "income": round(income_monthly, 2),
        "essentials": round(essentials_monthly, 2),
        "subscriptions": round(subscriptions_monthly, 2),
        "savings_setaside": round(savings_setaside_monthly, 2),
        "committed": round(committed, 2),
        "safe_to_spend": round(safe, 2),
        "weekly": round(safe / 4.345, 2),
        "negative": safe < 0,
    }


# --------------------------------------------------------------------------- #
# Goal planner
# --------------------------------------------------------------------------- #
GOALS_TEMPLATE = """\
# MoneyMan — Goals.  Name anything you're saving toward and (optionally) a date.
# MoneyMan works out the monthly amount it takes and whether your surplus covers it.
# Date format: YYYY-MM-DD (or leave blank to just see how long it would take).
Name,Target Amount,Target Date,Saved So Far
Example - New roof,18000,2028-06-01,2000
Example - Family trip,6000,2027-07-01,0
"""


def write_goals_template(path: Path) -> None:
    if not path.exists():
        path.write_text(GOALS_TEMPLATE, encoding="utf-8")


def _money(v: str) -> float:
    v = (v or "").strip().replace("$", "").replace(",", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def load_goals(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(
                r for r in f if r.strip() and not r.lstrip().startswith("#"))
            cols = {(c or "").strip().lower(): c for c in (reader.fieldnames or [])}

            def col(*names):
                for n in names:
                    if n in cols:
                        return cols[n]
                return None

            c_name = col("name", "goal")
            c_amt = col("target amount", "amount", "target")
            c_date = col("target date", "date", "by")
            c_saved = col("saved so far", "saved", "current")
            for r in reader:
                name = (r.get(c_name) or "").strip() if c_name else ""
                target = _money(r.get(c_amt, "")) if c_amt else 0.0
                if not name or target <= 0 or name.lower().startswith("example"):
                    continue
                out.append({
                    "name": name, "target": target,
                    "saved": _money(r.get(c_saved, "")) if c_saved else 0.0,
                    "target_date": (r.get(c_date) or "").strip() if c_date else ""})
    except Exception:
        return out
    return out


def _months_until(target_date: str, today: date) -> int | None:
    try:
        d = datetime.strptime(target_date[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    months = (d.year - today.year) * 12 + (d.month - today.month)
    return max(0, months)


def goal_plan(goals: list[dict], monthly_capacity: float,
              today: date | None = None) -> dict:
    """For each goal: the monthly amount needed, and whether you can afford it —
    sharing your monthly surplus across all dated goals."""
    today = today or date.today()
    items: list[dict] = []
    required_total = 0.0
    for g in goals:
        remaining = max(0.0, g["target"] - g.get("saved", 0.0))
        months_left = _months_until(g.get("target_date", ""), today)
        required_monthly = (round(remaining / months_left, 2)
                            if months_left and months_left > 0 else None)
        if required_monthly:
            required_total += required_monthly
        eta_months = (int(remaining / monthly_capacity) + 1
                      if monthly_capacity > 0 and remaining > 0 else None)
        items.append({
            "name": g["name"], "target": round(g["target"], 2),
            "saved": round(g.get("saved", 0.0), 2), "remaining": round(remaining, 2),
            "target_date": g.get("target_date", ""),
            "months_left": months_left,
            "required_monthly": required_monthly,
            "eta_months": eta_months,
            "on_pace": (required_monthly is None or
                        required_monthly <= max(0.0, monthly_capacity))})
    items.sort(key=lambda x: (x["required_monthly"] or 0), reverse=True)
    return {
        "goals": items,
        "monthly_capacity": round(monthly_capacity, 2),
        "required_total": round(required_total, 2),
        "affordable": required_total <= max(0.0, monthly_capacity),
        "leftover_after_goals": round(monthly_capacity - required_total, 2),
    }
