"""The financial-planner brain: beyond getting out of debt, where should money
go to build security and independence?

Everything here is transparent, rule-of-thumb math you can see and adjust — not
black-box advice. It is educational and personalized to the numbers you provide;
it is **not** professional financial advice.

Privacy note: nothing here calls the internet. Things we can't compute locally
(your home's market value, your retirement balances) are read from a profile
file you fill in. We never send your address or balances anywhere.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


# --------------------------------------------------------------------------- #
# Profile (the few personal facts we can't read from statements)
# --------------------------------------------------------------------------- #
@dataclass
class Car:
    name: str = "Car"
    year: int | None = None
    mileage: int | None = None
    purchase_date: str | None = None
    purchase_price: float | None = None


@dataclass
class Profile:
    age: int | None = None
    cash_savings: float = 0.0
    retirement_balance: float = 0.0
    employer_match_up_to_pct: float = 0.0     # e.g. 5 means matches up to 5% of pay
    contributing_enough_for_match: bool | None = None
    monthly_retirement_contribution: float = 0.0
    expected_return_pct: float = 7.0
    inflation_pct: float = 2.5                 # to report projections in today's dollars
    social_security_monthly: float = 0.0       # est. household SS benefit (today's $)
    target_retirement_age: int | None = None
    other_assets: float = 0.0
    monthly_income_override: float | None = None   # take-home you set yourself
    filing_status: str = "mfj"                  # "single" | "mfj" (tax estimate)
    hsa_eligible: bool = False
    has_pension_or_trs: bool = False
    owns_home: bool = False
    home_value: float = 0.0
    home_sqft: int | None = None
    owns_rental: bool = False
    rental_value: float = 0.0
    rental_rent_income: float = 0.0
    rental_mortgage_balance: float = 0.0
    rental_mortgage_apr: float = 0.0
    home_value_source: str = "you"            # "you" | "online estimate"
    lookup_home_value_online: bool = False
    home_address: str = ""
    monthly_goal_override: float | None = None
    whatif_amount: float | None = None
    cars: list[Car] = field(default_factory=list)


def _f(v: str) -> float | None:
    v = (v or "").strip().replace("$", "").replace(",", "").replace("%", "")
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _b(v: str) -> bool | None:
    v = (v or "").strip().lower()
    if v in ("y", "yes", "true", "1"):
        return True
    if v in ("n", "no", "false", "0"):
        return False
    return None


def load_profile(path: Path) -> Profile:
    p = Profile()
    if not path.exists():
        return p
    rows: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.reader(f):
                if len(r) >= 2 and r[0].strip() and not r[0].strip().startswith("#"):
                    rows[r[0].strip().lower()] = r[1].strip()
    except Exception:
        return p

    def g(*keys):
        for k in keys:
            if k in rows:
                return rows[k]
        return ""

    p.age = int(_f(g("your age", "age")) or 0) or None
    p.cash_savings = _f(g("cash savings", "emergency fund", "savings balance")) or 0.0
    p.retirement_balance = _f(g("retirement balance", "401k balance",
                                "retirement savings")) or 0.0
    p.employer_match_up_to_pct = _f(g("employer 401k match up to (%)",
                                      "employer match up to (%)",
                                      "employer match")) or 0.0
    p.contributing_enough_for_match = _b(g("getting full employer match? (y/n)",
                                           "getting full match"))
    p.hsa_eligible = _b(g("hsa eligible? (y/n)", "hsa eligible")) or False
    p.has_pension_or_trs = _b(g("pension or trs? (y/n)", "pension",
                                "trs")) or False
    p.owns_home = _b(g("own your home? (y/n)", "owns home", "homeowner")) or False
    p.home_value = _f(g("home value (your estimate)", "home value")) or 0.0
    sq = _f(g("home size (sq ft)", "home sqft"))
    p.home_sqft = int(sq) if sq else None
    p.monthly_goal_override = _f(g("monthly amount for goals (optional)",
                                   "monthly goal"))
    p.monthly_income_override = _f(g("monthly take-home income",
                                     "monthly household income", "monthly income",
                                     "take-home income"))
    fs = g("filing status (single/mfj)", "filing status").strip().lower()
    if fs in ("single", "mfj", "married", "joint", "married filing jointly"):
        p.filing_status = "single" if fs == "single" else "mfj"
    p.monthly_retirement_contribution = _f(g(
        "monthly retirement contribution", "retirement contribution")) or 0.0
    p.expected_return_pct = _f(g("expected return (%)", "expected return")) or 7.0
    p.inflation_pct = _f(g("inflation assumption (%)", "inflation")) or 2.5
    p.social_security_monthly = _f(g(
        "estimated social security (monthly, household)",
        "social security monthly", "social security")) or 0.0
    rage = _f(g("target retirement age"))
    p.target_retirement_age = int(rage) if rage else None
    p.other_assets = _f(g("other assets / investments", "other assets")) or 0.0
    p.whatif_amount = _f(g("what-if lump sum amount", "what if amount"))
    p.lookup_home_value_online = _b(g(
        "look up home value online? (y/n)", "lookup home value online")) or False
    p.home_address = g("home address (street, city, state zip)", "home address")
    p.owns_rental = _b(g("own a rental property? (y/n)", "owns rental")) or False
    p.rental_value = _f(g("rental property value", "rental value")) or 0.0
    p.rental_rent_income = _f(g("rental monthly rent income", "rental rent")) or 0.0
    p.rental_mortgage_balance = _f(g("rental mortgage balance")) or 0.0
    p.rental_mortgage_apr = _f(g("rental mortgage apr (%)", "rental mortgage apr")) or 0.0

    for i in (1, 2, 3):
        yr = _f(g(f"car{i} year"))
        mi = _f(g(f"car{i} mileage"))
        if yr or mi or g(f"car{i} name"):
            p.cars.append(Car(
                name=g(f"car{i} name") or f"Car {i}",
                year=int(yr) if yr else None,
                mileage=int(mi) if mi else None,
                purchase_date=g(f"car{i} purchase date") or None,
                purchase_price=_f(g(f"car{i} purchase price"))))
    return p


PROFILE_TEMPLATE = """\
# MoneyMan — My Profile.  Fill in what you can; leave the rest blank.
# This stays 100%% on your computer. Two columns: Field,Value
Field,Value
Your age,
# Your household take-home income each month (what actually lands in your accounts).
# Leave blank to let MoneyMan estimate it from your deposits.
Monthly take-home income,
# Tax estimate only: "single" or "mfj" (married filing jointly). Default mfj.
Filing status (single/mfj),
Cash savings,
Retirement balance,
Monthly retirement contribution,
Expected return (%),
# Inflation assumption — lets MoneyMan show your projection in TODAY'S dollars
# (what it'll actually buy). 2.5-3 is typical. Leave blank for 2.5.
Inflation assumption (%),
# Optional: your household's estimated Social Security benefit per month, in
# today's dollars (see ssa.gov). Counts as retirement income and lowers the
# nest egg you need. Leave blank if unsure.
Estimated Social Security (monthly, household),
Target retirement age,
Other assets / investments,
Employer 401k match up to (%),
Getting full employer match? (y/n),
HSA eligible? (y/n),
Pension or TRS? (y/n),
Own your home? (y/n),
Home value (your estimate),
Home size (sq ft),
# Optional online home-value lookup. Sends ONLY the address below to a property
# service - never your finances. Leave 'n' to keep everything 100%% offline.
Look up home value online? (y/n),n
Home address (street, city, state zip),
Monthly amount for goals (optional),
What-if lump sum amount,
Car1 name,
Car1 year,
Car1 mileage,
Car1 purchase date,
Car1 purchase price,
Car2 name,
Car2 year,
Car2 mileage,
Car2 purchase date,
Car2 purchase price,
"""


def write_profile_template(path: Path) -> None:
    if not path.exists():
        path.write_text(PROFILE_TEMPLATE, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Emergency fund
# --------------------------------------------------------------------------- #
def emergency_fund(essentials_monthly: float, current_cash: float) -> dict:
    starter = 1500.0
    target_min = essentials_monthly * 3
    target_full = essentials_monthly * 6
    return {
        "essentials_monthly": round(essentials_monthly, 2),
        "starter": starter,
        "target_min": round(target_min, 2),
        "target_full": round(target_full, 2),
        "current": round(current_cash, 2),
        "months_covered": round(current_cash / essentials_monthly, 1)
        if essentials_monthly > 0 else 0,
        "gap_to_min": round(max(0.0, target_min - current_cash), 2),
        "gap_to_full": round(max(0.0, target_full - current_cash), 2),
    }


# --------------------------------------------------------------------------- #
# Car wear-and-tear & replacement
# --------------------------------------------------------------------------- #
def car_plan(car: Car, today: date | None = None) -> dict:
    today = today or date.today()
    age = (today.year - car.year) if car.year else None
    miles = car.mileage or 0

    base = 600.0
    age_factor = 45.0 * max(0, (age or 0) - 3)
    mileage_factor = (800.0 if miles > 150_000 else
                      400.0 if miles > 100_000 else
                      150.0 if miles > 60_000 else 0.0)
    annual_maint = min(3800.0, base + age_factor + mileage_factor)

    miles_per_year = 12_000
    years_by_miles = max(1.0, (180_000 - miles) / miles_per_year) if miles else 12.0
    years_by_age = max(1.0, 15 - (age or 0))
    years_left = round(min(years_by_miles, years_by_age), 1)

    replace_cost = max(18_000.0, (car.purchase_price or 0) * 0.85) or 25_000.0
    monthly_replace = replace_cost / (years_left * 12)

    risk = ("high" if (age and age >= 10) or miles > 130_000 else
            "rising" if (age and age >= 7) or miles > 90_000 else "low")
    return {
        "name": car.name, "age": age, "miles": miles,
        "annual_maintenance": round(annual_maint, 2),
        "monthly_repair_reserve": round(annual_maint / 12, 2),
        "years_to_replace": years_left,
        "replace_cost": round(replace_cost, 2),
        "monthly_replace_reserve": round(monthly_replace, 2),
        "repair_risk": risk,
    }


# --------------------------------------------------------------------------- #
# Home maintenance reserve (the classic ~1%/yr rule of thumb)
# --------------------------------------------------------------------------- #
def home_plan(home_value: float) -> dict | None:
    if not home_value or home_value <= 0:
        return None
    annual = home_value * 0.01
    return {"home_value": round(home_value, 2),
            "annual_maintenance": round(annual, 2),
            "monthly_reserve": round(annual / 12, 2)}


# --------------------------------------------------------------------------- #
# "Save for these" — probability-weighted upcoming surprises (sinking funds)
# --------------------------------------------------------------------------- #
def planned_surprises(profile: Profile, categories_present: set[str],
                      essentials_monthly: float) -> list[dict]:
    """Each item: a likely irregular cost, its rough annual probability and
    typical size, and the *expected* monthly amount to set aside for it."""
    out: list[dict] = []

    for car in profile.cars:
        cp = car_plan(car)
        age = cp["age"] or 0
        prob = min(0.65, 0.05 * max(0, age - 2) + (0.2 if cp["miles"] > 120_000 else 0))
        typical = 1600.0
        out.append({
            "name": f"Major repair — {car.name}",
            "annual_prob": round(prob, 2), "typical_cost": typical,
            "expected_monthly": round(prob * typical / 12, 2),
            "basis": f"{age}-yr-old car, {cp['miles']:,} miles ({cp['repair_risk']} risk)"})
        out.append({
            "name": f"Replace {car.name} in ~{cp['years_to_replace']} yrs",
            "annual_prob": 1.0, "typical_cost": cp["replace_cost"],
            "expected_monthly": cp["monthly_replace_reserve"],
            "basis": "spread the cost of the next car over its remaining life"})

    if profile.owns_home and profile.home_value:
        hp = home_plan(profile.home_value)
        out.append({
            "name": "Home repairs & maintenance",
            "annual_prob": 1.0, "typical_cost": hp["annual_maintenance"],
            "expected_monthly": hp["monthly_reserve"],
            "basis": "~1%/yr of home value (roof, HVAC, appliances, plumbing)"})

    # Medical out-of-pocket surprise
    out.append({
        "name": "Medical / dental out-of-pocket",
        "annual_prob": 0.4, "typical_cost": 2500.0,
        "expected_monthly": round(0.4 * 2500 / 12, 2),
        "basis": "an unplanned deductible / procedure"})

    if "Pets" in categories_present:
        out.append({
            "name": "Pet emergency (vet)",
            "annual_prob": 0.3, "typical_cost": 1500.0,
            "expected_monthly": round(0.3 * 1500 / 12, 2),
            "basis": "you have pet spending; vet bills spike unexpectedly"})

    # Major appliance / home electronics replacement (everyone)
    out.append({
        "name": "Appliance / tech replacement",
        "annual_prob": 0.5, "typical_cost": 900.0,
        "expected_monthly": round(0.5 * 900 / 12, 2),
        "basis": "fridge, laptop, phone, washer — something breaks each year"})

    out.sort(key=lambda x: x["expected_monthly"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Net worth & retirement / financial-independence projection
# --------------------------------------------------------------------------- #
def estimate_car_value(car: Car, today: date | None = None) -> float:
    """Rough resale value: depreciate the purchase price ~15%/yr, floor $1,500."""
    if not car.purchase_price:
        return 0.0
    today = today or date.today()
    years = 0
    if car.purchase_date:
        try:
            pd = datetime.strptime(car.purchase_date[:10], "%Y-%m-%d").date()
            years = max(0, (today - pd).days // 365)
        except ValueError:
            years = 0
    return round(max(1500.0, car.purchase_price * (0.85 ** years)), 2)


def net_worth_from_balances(by_account: dict[str, float]) -> dict:
    """Real net worth from an account-balance export (positives=assets, neg=debts)."""
    assets = {a: v for a, v in by_account.items() if v > 0}
    debt_accts = {a: -v for a, v in by_account.items() if v < 0}
    total_assets = round(sum(assets.values()), 2)
    total_debts = round(sum(debt_accts.values()), 2)
    return {"assets": {a: round(v, 2) for a, v in
                       sorted(assets.items(), key=lambda x: -x[1])},
            "debt_accounts": {a: round(v, 2) for a, v in
                              sorted(debt_accts.items(), key=lambda x: -x[1])},
            "total_assets": total_assets, "total_debts": total_debts,
            "net_worth": round(total_assets - total_debts, 2),
            "from_balances": True}


def networth_series(rows: list[tuple[str, str, float]]) -> list[tuple[str, float]]:
    """Monthly net-worth time series (forward-fills each account's last balance)."""
    if not rows:
        return []
    from collections import defaultdict
    by: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for d, a, b in rows:
        by[a].append((d, b))
    for a in by:
        by[a].sort()
    alldates = sorted(d for d, _, _ in rows)
    sy, sm = int(alldates[0][:4]), int(alldates[0][5:7])
    ey, em = int(alldates[-1][:4]), int(alldates[-1][5:7])
    series: list[tuple[str, float]] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        nxt = f"{y + (1 if m == 12 else 0):04d}-{(1 if m == 12 else m + 1):02d}-01"
        nw = 0.0
        for lst in by.values():
            last = None
            for d, b in lst:
                if d < nxt:
                    last = b
                else:
                    break
            if last is not None:
                nw += last
        series.append((f"{y:04d}-{m:02d}", round(nw, 2)))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return series


def net_worth(profile: Profile, debts) -> dict:
    car_total = sum(estimate_car_value(c) for c in profile.cars)
    assets = {
        "Cash & savings": round(profile.cash_savings, 2),
        "Retirement": round(profile.retirement_balance, 2),
        "Home (your estimate)": round(profile.home_value, 2),
        "Vehicles (est. resale)": round(car_total, 2),
        "Other investments": round(profile.other_assets, 2),
    }
    assets = {k: v for k, v in assets.items() if v > 0}
    total_assets = sum(assets.values())
    total_debts = sum(d.balance for d in debts)
    return {"assets": assets, "total_assets": round(total_assets, 2),
            "total_debts": round(total_debts, 2),
            "net_worth": round(total_assets - total_debts, 2)}


def retirement_projection(profile: Profile, essentials_monthly: float,
                          total_spend_monthly: float | None = None) -> dict:
    """Project the nest egg and the financial-independence ("work-optional") number.

    Everything that gets *compared* — the projected balance, the income it throws
    off, and the FI number — is reported in TODAY'S dollars so the comparison is
    apples-to-apples. We do that by growing savings at the *real* (after-inflation)
    return, which is the standard way to express a long-horizon projection in
    current purchasing power (it assumes you raise contributions with inflation).

    Social Security is treated as income you'll also receive, so it lowers the
    portfolio you need: the 4% rule only has to cover spending SS doesn't.
    """
    nominal = max(0.0, profile.expected_return_pct) / 100.0
    infl = max(0.0, profile.inflation_pct) / 100.0
    real = (1 + nominal) / (1 + infl) - 1          # real annual return (today's $)

    age = profile.age or 35
    target = profile.target_retirement_age or 65
    years = max(1, target - age)
    n = years * 12
    bal = profile.retirement_balance
    c = profile.monthly_retirement_contribution
    ss = max(0.0, profile.social_security_monthly)

    def future_value(annual_rate: float) -> float:
        mr = annual_rate / 12.0
        if mr > 0:
            return bal * ((1 + mr) ** n) + c * (((1 + mr) ** n - 1) / mr)
        return bal + c * n

    fv_real = future_value(real)                   # today's dollars (primary)
    fv_nominal = future_value(nominal)             # face value at retirement

    # FI number: the PORTFOLIO needed so a 4% draw covers what SS doesn't.
    full_spend = total_spend_monthly if total_spend_monthly is not None \
        else essentials_monthly
    gap_full = max(0.0, full_spend - ss) * 12      # annual spend SS won't cover
    gap_lean = max(0.0, essentials_monthly - ss) * 12
    fi_number = gap_full * 25
    fi_number_lean = gap_lean * 25

    # Years until the portfolio alone reaches the FI number (real terms).
    rm = real / 12.0
    yrs_to_fi = None
    if (c > 0 or bal > 0) and fi_number > 0:
        b, months = bal, 0
        while b < fi_number and months < 1200:
            b = b * (1 + rm) + c
            months += 1
        yrs_to_fi = round(months / 12, 1) if months < 1200 else None
    elif fi_number <= 0:
        yrs_to_fi = 0.0                            # SS already covers your spending

    portfolio_income_monthly = fv_real * 0.04 / 12  # 4% safe withdrawal, today's $
    return {
        "current_age": age, "target_age": target, "years": years,
        "current_balance": round(bal, 2), "monthly_contribution": round(c, 2),
        "return_pct": round(profile.expected_return_pct, 1),
        "inflation_pct": round(profile.inflation_pct, 1),
        "real_return_pct": round(real * 100, 1),
        "social_security_monthly": round(ss, 2),
        "projected_balance": round(fv_real, 2),          # today's dollars
        "projected_balance_nominal": round(fv_nominal, 2),
        "portfolio_income_monthly": round(portfolio_income_monthly, 2),
        "projected_income_monthly": round(portfolio_income_monthly + ss, 2),
        "fi_number": round(fi_number, 2),                # full lifestyle
        "fi_number_lean": round(fi_number_lean, 2),      # essentials only
        "years_to_fi": yrs_to_fi,
        "on_track": fv_real >= fi_number,
        "in_todays_dollars": True,
    }


# --------------------------------------------------------------------------- #
# Liquid cash (for the cash-flow forecast & a more honest emergency-fund "current")
# --------------------------------------------------------------------------- #
_CASH_WORDS = ("checking", "savings", "cash", "money market", "mma",
               "credit union", "debit")
_NONCASH_WORDS = ("401", "403", "ira", "roth", "retire", "hsa", "health savings",
                  "broker", "tod", "invest", "529", "pension", "annuity")


def liquid_cash_from_balances(by_account: dict[str, float]) -> dict:
    """Best-effort sum of spendable cash (checking/savings) from a balances export.

    Whitelists cash-like account names and excludes investment/retirement ones, so
    a 401(k) or brokerage balance is never mistaken for money you can spend now.
    """
    accts: dict[str, float] = {}
    for a, v in by_account.items():
        low = a.lower()
        if v > 0 and any(w in low for w in _CASH_WORDS) \
                and not any(w in low for w in _NONCASH_WORDS):
            accts[a] = round(v, 2)
    return {"total": round(sum(accts.values()), 2), "accounts": accts}


# --------------------------------------------------------------------------- #
# Amortization & mortgage extra-principal analysis
# --------------------------------------------------------------------------- #
def standard_payment(balance: float, apr: float, years: int) -> float:
    """The level monthly payment that amortizes `balance` over `years` at `apr`."""
    r = apr / 100.0 / 12.0
    n = years * 12
    if r <= 0:
        return balance / n if n else balance
    return balance * r / (1 - (1 + r) ** -n)


def amortize(balance: float, apr: float, payment: float, extra: float = 0.0,
             max_months: int = 1200) -> dict:
    """Run a loan down month by month at `payment` (+ optional `extra` principal)."""
    r = apr / 100.0 / 12.0
    bal = float(balance)
    pay = payment + max(0.0, extra)
    total_interest = 0.0
    months = 0
    # Guard: a payment that doesn't beat the first month's interest never finishes.
    if pay <= bal * r + 0.01:
        monthly_interest = bal * r
        return {"months": None, "total_interest": None, "finished": False,
                "monthly_interest": round(monthly_interest, 2)}
    while bal > 0.005 and months < max_months:
        interest = bal * r
        total_interest += interest
        bal = bal + interest - pay
        if bal < 0:
            bal = 0.0
        months += 1
    return {"months": months, "total_interest": round(total_interest, 2),
            "finished": bal <= 0.005, "monthly_interest": round(balance * r, 2)}


def mortgage_analysis(name: str, balance: float, apr: float,
                      payment: float | None = None,
                      extras=(100, 250, 500), term_years: int = 30,
                      payment_is_estimated: bool = False) -> dict | None:
    """Show what paying extra principal does: months & interest saved per option.

    Needs a real interest rate. If we don't know the scheduled payment we estimate
    a standard amortizing one (flagged), so the *relative* savings still illustrate
    the lever even before the user confirms their exact payment.
    """
    if balance <= 0 or apr <= 0:
        return None
    if payment is None or payment <= balance * (apr / 1200.0):
        payment = standard_payment(balance, apr, term_years)
        payment_is_estimated = True
    base = amortize(balance, apr, payment)
    if not base["finished"]:
        return None
    options = []
    for x in extras:
        alt = amortize(balance, apr, payment, extra=float(x))
        if not alt["finished"]:
            continue
        options.append({
            "extra": int(x),
            "months": alt["months"],
            "months_saved": base["months"] - alt["months"],
            "interest_saved": round(base["total_interest"] - alt["total_interest"], 2),
            "new_payment": round(payment + x, 2)})
    return {
        "name": name, "balance": round(balance, 2), "apr": round(apr, 2),
        "payment": round(payment, 2), "payment_is_estimated": payment_is_estimated,
        "base_months": base["months"], "base_interest": base["total_interest"],
        "monthly_interest": base["monthly_interest"],
        "options": options}


# --------------------------------------------------------------------------- #
# Tax awareness (educational estimate — NOT tax advice)
# --------------------------------------------------------------------------- #
# 2025 federal ordinary-income brackets (close enough for planning in 2026).
_BRACKETS = {
    "single": [(0, 0.10), (11925, 0.12), (48475, 0.22), (103350, 0.24),
               (197300, 0.32), (250525, 0.35), (626350, 0.37)],
    "mfj": [(0, 0.10), (23850, 0.12), (96950, 0.22), (206700, 0.24),
            (394600, 0.32), (501050, 0.35), (751600, 0.37)],
}
_STD_DEDUCTION = {"single": 15000, "mfj": 30000}


def _federal_tax(taxable: float, filing: str) -> float:
    brackets = _BRACKETS.get(filing, _BRACKETS["mfj"])
    tax = 0.0
    for i, (floor, rate) in enumerate(brackets):
        ceil = brackets[i + 1][0] if i + 1 < len(brackets) else float("inf")
        if taxable > floor:
            tax += (min(taxable, ceil) - floor) * rate
        else:
            break
    return tax


def _marginal_rate(taxable: float, filing: str) -> float:
    brackets = _BRACKETS.get(filing, _BRACKETS["mfj"])
    rate = brackets[0][1]
    for floor, r in brackets:
        if taxable >= floor:
            rate = r
        else:
            break
    return rate


def tax_insights(gross_annual_income: float, filing_status: str = "mfj") -> dict | None:
    """Estimate the household's bracket and offer Traditional-vs-Roth guidance.

    A rough federal-only estimate using the standard deduction — meant to orient
    decisions, not to file with. State tax and credits are not modeled.
    """
    if gross_annual_income <= 0:
        return None
    filing = "single" if filing_status == "single" else "mfj"
    std = _STD_DEDUCTION[filing]
    taxable = max(0.0, gross_annual_income - std)
    marginal = _marginal_rate(taxable, filing)
    tax = _federal_tax(taxable, filing)
    effective = tax / gross_annual_income if gross_annual_income else 0.0

    # A dollar of Traditional 401(k)/IRA contribution defers tax at the marginal rate.
    trad_saving_per_1k = round(1000 * marginal, 0)
    if marginal >= 0.32:
        guidance = ("You're in a high bracket, so <b>Traditional</b> (pre-tax) "
                    "401(k)/IRA contributions give the biggest up-front tax break. "
                    "Use Roth space mainly for tax diversification.")
    elif marginal >= 0.22:
        guidance = ("You're in a middle bracket — a <b>blend</b> works well: enough "
                    "Traditional to trim this year's tax, plus some Roth so not all "
                    "your retirement money is taxable later.")
    else:
        guidance = ("You're in a low bracket, which usually favors <b>Roth</b> "
                    "(after-tax) — pay the low rate now and withdraw tax-free later.")
    return {
        "filing": filing,
        "gross_income": round(gross_annual_income, 2),
        "taxable_income": round(taxable, 2),
        "std_deduction": std,
        "marginal_rate": round(marginal * 100, 1),
        "effective_rate": round(effective * 100, 1),
        "est_federal_tax": round(tax, 2),
        "trad_saving_per_1k": trad_saving_per_1k,
        "guidance": guidance,
    }


# --------------------------------------------------------------------------- #
# Lower-your-bills optimizer (insurance, utilities, phone, internet)
# --------------------------------------------------------------------------- #
_BILL_BENCHMARKS = [
    ("auto insurance", ("geico", "progressive", "state farm", "allstate",
                        "auto insurance"), 165, 0.20,
     "Get 3 quotes and ask about bundling — auto rates vary wildly between insurers."),
    ("insurance", ("insurance", "premium", "metlife", "aetna", "blue cross"), 200, 0.15,
     "Re-shop yearly; raising your deductible often cuts the premium a lot."),
    ("internet / cable", ("comcast", "xfinity", "spectrum", "cox", "internet",
                          "fiber"), 85, 0.25,
     "Call the retention line, drop unused TV tiers, or switch providers."),
    ("phone", ("verizon", "at&t", "t-mobile", "sprint", "wireless"), 90, 0.30,
     "Discount carriers (Mint, Visible, US Mobile) run on the same towers for less."),
]


def bill_optimizer(recurring: list[dict]) -> list[dict]:
    """Flag likely-overpaid fixed bills with a rough potential saving."""
    out: list[dict] = []
    seen = set()
    for r in recurring:
        if not r.get("active"):
            continue
        name = (r["merchant"] + " " + r.get("category", "")).lower()
        monthly = r["typical_amount"] * (r["periods_per_year"] / 12)
        for label, kws, bench, frac, tip in _BILL_BENCHMARKS:
            if any(k in name for k in kws) and monthly > bench and label not in seen:
                seen.add(label)
                out.append({
                    "name": r["merchant"], "kind": label,
                    "monthly": round(monthly, 2),
                    "benchmark": bench,
                    "potential_annual": round(monthly * 12 * frac, 2),
                    "tip": tip})
                break
    out.sort(key=lambda x: x["potential_annual"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# "What if I had a lump sum?" — the possibilities box
# --------------------------------------------------------------------------- #
def lump_sum_options(amount: float, debts, emergency_gap: float,
                     assumed_return: float = 0.07, years: int = 10) -> dict:
    """Compare the highest-impact uses of a windfall."""
    from .debts import simulate_payoff   # local import avoids a cycle

    live = [d for d in debts if d.balance > 0.005]
    min_total = sum(d.min_payment for d in live)

    # 1) Apply to debt (avalanche): interest & time saved vs. minimums-only.
    debt_block = None
    if live:
        base = simulate_payoff(live, min_total, "avalanche")
        # Model the lump sum by knocking it off the highest-APR balance(s) now.
        reduced = []
        remaining = amount
        for d in sorted(live, key=lambda x: x.apr, reverse=True):
            from .debts import Debt
            cut = min(remaining, d.balance)
            reduced.append(Debt(d.name, d.kind, d.balance - cut, d.apr,
                                d.min_payment, d.credit_limit))
            remaining -= cut
        after = simulate_payoff([d for d in reduced if d.balance > 0.005] or reduced,
                                min_total, "avalanche")
        top_apr = max(d.apr for d in live)
        debt_block = {
            "interest_saved": round(base.total_interest - after.total_interest, 2),
            "months_saved": base.months - after.months,
            "guaranteed_return_pct": round(top_apr, 2),
            "note": f"Paying high-interest debt is a guaranteed, tax-free "
                    f"{top_apr:.1f}% return — usually the best first move."}

    # 2) Top up the emergency fund.
    emerg_block = None
    if emergency_gap > 0:
        used = min(amount, emergency_gap)
        emerg_block = {"applied": round(used, 2),
                       "closes_gap": used >= emergency_gap - 1,
                       "note": "Cash safety net so the next surprise doesn't become "
                               "new debt."}

    # 3) Invest it (compound growth).
    grown = amount * ((1 + assumed_return) ** years)
    invest_block = {"future_value": round(grown, 2), "years": years,
                    "assumed_return_pct": round(assumed_return * 100, 1),
                    "note": f"At ~{assumed_return*100:.0f}%/yr, ${amount:,.0f} could "
                            f"grow to about ${grown:,.0f} in {years} years."}

    # Quantified, apples-to-apples comparison so the choice is a number, not a vibe.
    top_apr = max((d.apr for d in live), default=0.0)
    comparison: list[dict] = []
    if debt_block:
        comparison.append({
            "label": "Pay down debt",
            "dollars": debt_block["interest_saved"],
            "guaranteed": True,
            "basis": f"interest you simply won't pay — a guaranteed "
                     f"{debt_block['guaranteed_return_pct']:.0f}% return"})
    comparison.append({
        "label": "Invest it",
        "dollars": round(invest_block["future_value"] - amount, 2),
        "guaranteed": False,
        "basis": f"expected growth over {years} yrs at "
                 f"{assumed_return*100:.0f}%/yr (not guaranteed)"})
    if emerg_block:
        avoided = round(emerg_block["applied"] * (top_apr or 22.0) / 100.0, 2)
        comparison.append({
            "label": "Emergency fund",
            "dollars": avoided,
            "guaranteed": True,
            "basis": f"keeps the next surprise off a "
                     f"{(top_apr or 22.0):.0f}% card (~1 yr of avoided interest)"})
    comparison.sort(key=lambda x: x["dollars"], reverse=True)
    best = comparison[0]["label"] if comparison else None

    # Recommendation follows the standard order of operations.
    if debt_block and debt_block["guaranteed_return_pct"] >= 7:
        rec = ("Pay down your highest-interest debt first — it's a guaranteed "
               f"{debt_block['guaranteed_return_pct']:.0f}% return.")
    elif emerg_block and not emerg_block["closes_gap"]:
        rec = "Finish funding your emergency fund — it prevents future debt."
    else:
        rec = "Invest it for long-term growth (retirement / brokerage)."

    return {"amount": round(amount, 2), "debt": debt_block,
            "emergency": emerg_block, "invest": invest_block,
            "comparison": comparison, "best": best, "recommendation": rec}


# --------------------------------------------------------------------------- #
# Financial Order of Operations — "show the way"
# --------------------------------------------------------------------------- #
def order_of_operations(profile: Profile, debts, emergency: dict) -> list[dict]:
    """A personalized waterfall. Each step: status + what to do + why + how."""
    steps: list[dict] = []
    live = [d for d in debts if d.balance > 0.005]
    high_int = [d for d in live if d.apr >= 7]
    cash = profile.cash_savings

    def step(status, title, action, why, how=""):
        steps.append({"status": status, "title": title, "action": action,
                      "why": why, "how": how})

    # 1. Starter emergency fund
    step("done" if cash >= emergency["starter"] else "todo",
         "1. Starter emergency fund ($1,500)",
         "Park $1,500 in a high-yield savings account before anything else.",
         "It stops a small surprise from becoming a new credit-card balance.",
         "Open a high-yield savings account (many pay ~4%+). Keep it separate.")

    # 2. Employer match — free money
    if profile.employer_match_up_to_pct > 0:
        got = profile.contributing_enough_for_match
        step("done" if got else "todo",
             f"2. Capture the full employer match ({profile.employer_match_up_to_pct:.0f}%)",
             f"Contribute at least {profile.employer_match_up_to_pct:.0f}% to your "
             "401(k)/403(b)/TRS to get every matching dollar.",
             "An employer match is an instant 50–100% return. Never leave it on "
             "the table.",
             "Set your contribution in your payroll/benefits portal.")
    else:
        step("todo",
             "2. Capture any employer retirement match",
             "Check if your employer matches 401(k)/403(b)/457/TRS contributions, "
             "and contribute enough to get all of it.",
             "It's free money and the highest guaranteed return you'll find.",
             "Ask HR for your plan's match formula; fill it into your profile.")

    # 3. High-interest debt
    step("done" if not high_int else "todo",
         "3. Crush high-interest debt (APR ≥ 7%)",
         "Use the payoff plan above (avalanche) to clear cards and high-rate loans.",
         "No investment reliably beats a 20%+ credit-card APR. Clearing it is a "
         "guaranteed return.",
         "Redirect the waste MoneyMan found into the highest-APR balance first.")

    # 4. Full emergency fund
    step("done" if cash >= emergency["target_min"] else
         ("partial" if cash >= emergency["starter"] else "todo"),
         "4. Full emergency fund (3–6 months of essentials)",
         f"Build cash to ${emergency['target_min']:,.0f}–${emergency['target_full']:,.0f}.",
         "Job loss or a big repair won't derail you or create new debt.",
         "Automate a monthly transfer to high-yield savings.")

    # 5. HSA
    step("todo" if profile.hsa_eligible else "n/a",
         "5. Max your HSA (if on a high-deductible plan)",
         "Contribute to a Health Savings Account and invest it.",
         "Triple tax advantage: deductible in, grows tax-free, tax-free for medical. "
         "The best account in the tax code.",
         "Available with HDHP health plans; set it up via your employer or a broker.")

    # 6. IRA
    step("todo", "6. Fund an IRA (Roth or Traditional)",
         "Contribute up to the annual IRA limit at a low-cost broker.",
         "Roth = tax-free growth and withdrawals (great if you expect higher taxes "
         "later); Traditional = tax break now.",
         "Open at Fidelity/Schwab/Vanguard; buy a low-cost index fund.")

    # 7. More retirement
    step("todo", "7. Increase retirement toward the max",
         "Push 401(k)/403(b)/457 contributions up toward the annual limit; aim to "
         "invest 15%+ of income for retirement.",
         "Tax-advantaged compounding is how independence is actually built.",
         "Raise your contribution 1% each raise until it stops hurting.")

    # 8. Taxable / advanced
    step("todo", "8. Taxable brokerage & advanced moves",
         "Invest surplus in a taxable brokerage; explore 529 (kids), I bonds (safe "
         "inflation-protected), and mega-backdoor Roth if available.",
         "Keeps money working once tax-advantaged space is full.",
         "Low-cost total-market index funds are a sensible default.")

    return steps


# Educational pointers to "obscure" wealth/benefit holdings people forget.
HIDDEN_HOLDINGS = [
    ("Employer match", "The #1 forgotten free money. Confirm your 401(k)/403(b)/"
     "457/TRS match formula with HR and contribute enough to get all of it."),
    ("Old 401(k)s", "Left jobs? Track down old 401(k)s and roll them into an IRA so "
     "they're not lost or bleeding fees. Try the DOL abandoned-plan database and "
     "unclaimed-property sites (unclaimed.org / your state treasurer)."),
    ("Pensions & TRS", "Teachers/public workers: your Teacher Retirement System (TRS) "
     "or pension is a major asset. Log in to your TRS portal for your accrued "
     "benefit and vesting date. Note WEP/GPO rules can affect Social Security — "
     "check ssa.gov."),
    ("Social Security", "Create a my Social Security account at ssa.gov to see your "
     "estimated benefit. Delaying from 62 to 70 raises the monthly benefit by ~8%/yr "
     "— a huge, guaranteed, inflation-adjusted increase if you can wait."),
    ("HSA", "If you have a high-deductible health plan, the HSA is the only "
     "triple-tax-advantaged account. Invest it; don't let it sit as cash."),
    ("I Bonds & TIPS", "Treasury I bonds (TreasuryDirect.gov) are safe and "
     "inflation-protected — a good emergency-fund overflow."),
    ("Unclaimed property", "Check unclaimed.org for old paychecks, deposits, and "
     "insurance payouts in your name. It's free and surprisingly common."),
]
