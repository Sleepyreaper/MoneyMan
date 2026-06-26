"""Command-line entry point.

    python -m moneyman             analyze the Statements folder and open the report
    python -m moneyman --demo      create realistic sample data and analyze it
    python -m moneyman init        just create the folders (no analysis yet)
    python -m moneyman --reset     forget all stored transactions, then re-import
    python -m moneyman --no-open   build the report but don't open the browser
    python -m moneyman --data DIR  use a different data folder
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from . import (__version__, debts as debts_mod, discover, forecast, homevalue,
               ingest, intake, people as people_mod, planning, sample)
from .analyze import analyze
from .config import (CHECKLIST, Paths, SUBSCRIPTION_CATEGORIES, data_home,
                     load_user_rules, write_default_user_config)
from .debts import Debt, infer_apr
from .model import categorize
from .report import write_report
from .store import Store

ESSENTIAL_CATS = {"Housing", "Utilities", "Insurance", "Groceries", "Transport & Gas"}

START_HERE = """\
WELCOME TO MONEYMAN  (your private, offline finance analyst & planner)
======================================================================

WHAT GOES WHERE
---------------
  Statements\\   <-- PUT YOUR BANK / CARD / LOAN FILES HERE.
                    Download from each account's website (PDF, CSV, or .QFX) and
                    drop them in. Make one sub-folder per account, e.g.
                         Statements\\Chase Checking\\
                         Statements\\Amex Card\\
                         Statements\\Car Loan\\

  config\\       <-- Files you can fill in (open in Notepad/Excel):
                       Accounts-and-Debts.csv  - balances, interest rates, minimums
                       My-Profile.csv          - age, savings, home, cars, retirement
                       Who-Is-Spending.csv     - (optional) track spending per person
                    These power the payoff plan, the per-person view, and the roadmap.
                    Tip: the easiest way to fill these in is the interview
                    (Interview.bat) or the editable web app (Edit-MoneyMan.bat).

  Reports\\      <-- Your finished report appears here and opens automatically.
  database\\     <-- MoneyMan's local memory. Don't edit by hand.

HOW TO RUN
----------
  First time only: double-click  Setup.bat  (installs the PDF reader, offline).
  Then double-click  Run-MoneyMan.bat  whenever you add statements.
  To see a demo with fake data, double-click  Try-Demo.bat

GATHER THE FULL PICTURE
-----------------------
  MoneyMan gives better advice the more you give it. Aim for: 3-12 months of
  every bank + credit-card statement, all loans, household bills (power, gas,
  water, internet), insurance, and your filled-in profile. The report shows a
  checklist of what's still missing.

YOUR PRIVACY
------------
  Everything happens on THIS computer. No login, no internet, no data sent
  anywhere. We never look up your address or accounts online.
"""


def _setup_data_dir(paths: Paths) -> None:
    paths.ensure()
    write_default_user_config(paths)
    debts_mod.write_debts_template(paths.config / "Accounts-and-Debts.csv")
    planning.write_profile_template(paths.config / "My-Profile.csv")
    people_mod.write_people_template(paths.config / "Who-Is-Spending.csv")
    forecast.write_goals_template(paths.config / "Goals.csv")
    sh = paths.root / "START-HERE.txt"
    if not sh.exists():
        sh.write_text(START_HERE, encoding="utf-8")


def _trend_balances(balances, metas):
    """Input for the net-worth-over-time chart: the balances export, plus
    statement-derived balance points for any accounts the export doesn't cover —
    so the trend appears even for people who only have monthly statements."""
    export_accts = {a for _, a, _ in balances}
    extra = [r for r in planning.balances_from_statements(metas)
             if r[1] not in export_accts]
    return list(balances) + extra


def _build_debts(manual: list[Debt], metas) -> list[Debt]:
    """Merge manually-listed debts with debts read from PDF statements."""
    have = {d.name.lower() for d in manual}
    out = list(manual)
    # latest statement per account wins
    latest: dict[str, object] = {}
    for m in metas:
        if m.kind in ("credit card", "loan") and (m.new_balance or 0) > 0:
            latest[m.account] = m
    for acct, m in latest.items():
        if acct.lower() in have:
            continue
        apr = m.apr
        estimated = False
        if (not apr) and m.interest_charged and m.new_balance:
            apr = infer_apr(m.interest_charged, m.new_balance) or 0.0
            estimated = bool(apr)
        bal = m.new_balance or 0.0
        minp = m.min_payment or max(25.0, round(bal * 0.02, 2))
        out.append(Debt(name=acct, kind=m.kind, balance=bal, apr=apr or 0.0,
                        min_payment=minp, credit_limit=m.credit_limit or 0.0,
                        apr_estimated=estimated, source="statement"))
    # Give only credit cards a workable minimum when one is missing (loans and
    # mortgages keep min=0 if unknown, so we don't invent a giant payment).
    for d in out:
        if d.min_payment <= 0 and d.balance > 0 and "credit" in d.kind:
            d.min_payment = max(25.0, round(d.balance * 0.02, 2))
    return out


def _kind_from_name(name: str) -> str:
    n = name.lower()
    if "mortgage" in n or "home loan" in n:
        return "mortgage"
    if "home equity" in n or "heloc" in n or "equity line" in n:
        return "heloc"
    if any(k in n for k in ("visa", "amex", "mastercard", "card", "credit")):
        return "credit card"
    if "auto" in n or "car loan" in n or "vehicle" in n:
        return "auto loan"
    if "student" in n or "sallie" in n or "navient" in n:
        return "student loan"
    if "loan" in n or "heloc" in n or "line of credit" in n:
        return "personal loan"
    return "loan"


def _build_plan(analysis: dict, paths: Paths, metas, balances=None) -> dict:
    notes: list[str] = []
    balances = balances or []
    profile = planning.load_profile(paths.config / "My-Profile.csv")

    # Optional, opt-in, address-only online home-value lookup.
    if profile.lookup_home_value_online and profile.home_address \
            and not profile.home_value:
        print("Online home-value lookup is ON — sending only your address…")
        hv = homevalue.estimate(profile.home_address)
        if hv["value"]:
            profile.home_value = hv["value"]
            profile.home_value_source = "online estimate"
            notes.append(f"Home value ~{hv['value']:,.0f} from an online estimate "
                         f"(only your address was sent).")
        else:
            notes.append("Home value: " + hv["note"] + " " + hv["link"])

    manual = debts_mod.load_debts_csv(paths.config / "Accounts-and-Debts.csv")
    debts = _build_debts(manual, metas)

    # Latest balance per account (from a balances export), used for net worth and
    # to discover debts (any account with a negative balance is something you owe).
    by_account: dict[str, float] = {}
    latest_date: dict[str, str] = {}
    for d, acct, bal in balances:
        if acct not in latest_date or d >= latest_date[acct]:
            latest_date[acct], by_account[acct] = d, bal
    have_names = {x.name.lower() for x in debts}
    for acct, bal in by_account.items():
        if bal < 0 and acct.lower() not in have_names:
            debts.append(Debt(name=acct, kind=_kind_from_name(acct),
                              balance=round(-bal, 2), apr=0.0, min_payment=0.0,
                              source="balance"))
    # Bootstrap the debts file from detected balances (only if user hasn't filled
    # it in) so they just need to add interest rates.
    if not manual and any(d.source == "balance" for d in debts):
        debts_mod.write_detected_debts(
            paths.config / "Accounts-and-Debts.csv",
            [d for d in debts if d.source == "balance"])
        notes.append("I found your debt balances from the Balances export and wrote "
                     "them into config\\Accounts-and-Debts.csv — add each interest "
                     "rate (APR) and minimum payment to unlock your full payoff plan.")

    empty = analysis.get("empty")
    summary = {} if empty else analysis["summary"]
    months = max(1, summary.get("months_span", 1))
    cats = {} if empty else {c["category"]: c["total"]
                             for c in analysis["category_totals"]}
    cats_present = set(cats)

    essentials = sum(cats.get(c, 0) for c in ESSENTIAL_CATS) / months
    expense_monthly = 0.0 if empty else summary.get("expense", 0) / months
    detected_income_monthly = 0.0 if empty else summary.get("income", 0) / months
    # Let the user override their income (detected deposits are noisy — RSUs,
    # transfers and refunds sneak in). Their number drives the headline + leftover.
    income_is_override = bool(profile.monthly_income_override)
    income_monthly = (profile.monthly_income_override if income_is_override
                      else detected_income_monthly)
    leftover = 0.0 if empty else max(0.0, income_monthly - expense_monthly)
    recoverable = 0.0 if empty else sum(
        i["annual_impact"] for i in analysis["insights"]
        if i.get("recoverable")) / 12

    if profile.monthly_goal_override:               # user told us their number
        leftover, recoverable = profile.monthly_goal_override, 0.0

    # Label secured home debt correctly no matter where it came from (manual CSV,
    # statement, or balances) so it's shown right and kept out of the aggressive payoff.
    for d in debts:
        nl = d.name.lower()
        if "home equity" in nl or "heloc" in nl or "equity line" in nl:
            d.kind = "heloc"
        elif "mortgage" in nl or "home loan" in nl:
            d.kind = "mortgage"

    # Estimate any missing APRs from the interest each account was actually charged,
    # so the payoff plan unlocks without the user having to type every rate by hand.
    if not empty:
        n_est = debts_mod.infer_aprs_from_records(
            debts, analysis["records"], balances, months)
        if n_est:
            notes.append(
                f"I estimated the interest rate (APR) on {n_est} debt(s) from the "
                "interest those accounts were charged — each is marked with an “est” "
                "tag. Open “My info” to confirm or correct the exact rates.")

    # Only debts with a known rate + minimum (and not a mortgage) go into the
    # active payoff plan; the rest are still shown and counted in net worth.
    payoff_debts = [d for d in debts if d.apr > 0 and d.min_payment > 0
                    and "mortgage" not in d.kind and "heloc" not in d.kind]

    emergency = planning.emergency_fund(essentials, profile.cash_savings)
    payoff = (debts_mod.plan_paths(payoff_debts, leftover, recoverable)
              if payoff_debts else {"has_debts": False})

    amounts = [5000, 20000]
    if profile.whatif_amount and profile.whatif_amount not in amounts:
        amounts.append(int(profile.whatif_amount))
    lump_sums = [planning.lump_sum_options(amt, payoff_debts,
                                           emergency["gap_to_min"])
                 for amt in sorted(amounts)]

    waste_redirect = None
    if payoff_debts and recoverable > 1:
        mt = sum(d.min_payment for d in payoff_debts)
        without = debts_mod.simulate_payoff(payoff_debts, mt + leftover, "avalanche")
        with_w = debts_mod.simulate_payoff(payoff_debts, mt + leftover + recoverable,
                                           "avalanche")
        waste_redirect = {
            "monthly": round(recoverable, 2),
            "months_saved": without.months - with_w.months,
            "interest_saved": round(without.total_interest - with_w.total_interest, 2),
            "payoff_with": with_w.payoff_date}

    if by_account:
        networth = planning.net_worth_from_balances(by_account)
        networth["as_of"] = max(latest_date.values()) if latest_date else None
        notes.append("Cash flow excludes transfers between your own accounts, "
                     "credit-card payments, and loan/investment moves, so they're "
                     "not double-counted as spending. Debt paydown shows up in your "
                     "net worth and payoff plan instead.")
    else:
        networth = planning.net_worth(profile, debts)

    surprises = planning.planned_surprises(profile, cats_present, essentials)

    # Who's spending — per-person tracking (opt-in via config/Who-Is-Spending.csv).
    ppl = people_mod.load_people(paths.config / "Who-Is-Spending.csv")
    assigns = people_mod.load_assignments(paths.config / "Spending-Assignments.csv")
    people_summary = (None if empty else people_mod.spending_by_person(
        analysis["records"], ppl, months, assigns))
    assign_board = (None if (empty or not ppl) else people_mod.assignment_board(
        analysis["records"], ppl, assigns))

    # Data-driven "get to know you" — a profile + the smart questions (6+ months).
    discovery = (None if empty else discover.generate(
        analysis["records"], {"net_worth": networth}, profile, ppl, months))

    # ---- Forward cash management: forecast, safe-to-spend, goals -------------- #
    liquid = planning.liquid_cash_from_balances(by_account) if by_account \
        else {"total": 0.0, "accounts": {}}
    starting_cash = liquid["total"] or profile.cash_savings
    cash_flow = [] if empty else analysis["cash_flow"]
    cashflow = (forecast.cashflow_forecast(starting_cash, cash_flow, months=6)
                if cash_flow else None)

    subs_monthly = 0.0 if empty else sum(
        r["annual_cost"] / 12 for r in analysis["recurring"]
        if r["active"] and r["category"] in SUBSCRIPTION_CATEGORIES)
    debt_extra = (payoff["paths"]["average"]["extra"]
                  if payoff.get("has_debts") else 0.0)
    emergency_build = round(emergency["gap_to_min"] / 12, 2)
    surprises_monthly = sum(s["expected_monthly"] for s in surprises)
    savings_setaside = round(surprises_monthly + emergency_build + debt_extra, 2)
    sts = (None if empty else forecast.safe_to_spend(
        income_monthly, essentials, subs_monthly, savings_setaside))

    # Goals: user-defined (config/Goals.csv) plus a derived emergency-fund goal.
    user_goals = forecast.load_goals(paths.config / "Goals.csv")
    derived_goals = list(user_goals)
    if emergency["gap_to_min"] > 0 and not any(
            "emergency" in g["name"].lower() for g in user_goals):
        from datetime import date as _date
        tgt = _date.today().replace(day=1)
        tgt = tgt.replace(year=tgt.year + 1)
        derived_goals.insert(0, {
            "name": "Build a 3-month emergency fund",
            "target": emergency["target_min"], "saved": emergency["current"],
            "target_date": tgt.isoformat()})
    goals = (forecast.goal_plan(derived_goals, leftover) if derived_goals else None)

    # Mortgage / extra-principal analysis for any home debt with a known rate.
    mortgages = []
    for d in debts:
        if ("mortgage" in d.kind or "heloc" in d.kind) and d.apr > 0 and d.balance > 0:
            ma = planning.mortgage_analysis(d.name, d.balance, d.apr)
            if ma:
                mortgages.append(ma)
    if profile.owns_rental and profile.rental_mortgage_balance > 0 \
            and profile.rental_mortgage_apr > 0:
        ma = planning.mortgage_analysis(
            "Rental mortgage", profile.rental_mortgage_balance,
            profile.rental_mortgage_apr, term_years=30)
        if ma:
            mortgages.append(ma)

    # Tax bracket / Traditional-vs-Roth orientation from household income.
    tax = (None if income_monthly <= 0 else
           planning.tax_insights(income_monthly * 12, profile.filing_status))

    return {
        "intake": intake.evaluate(analysis, debts, metas),
        "people": people_summary,
        "people_config": ppl,
        "assign_board": assign_board,
        "discovery": discovery,
        "accounts": (summary.get("accounts", []) if not empty else []),
        "profile_present": any([profile.age, profile.cash_savings,
                                profile.home_value, profile.cars,
                                profile.retirement_balance]),
        "debts": debts,
        "payoff_eligible": len(payoff_debts),
        "payoff": payoff,
        "lump_sums": lump_sums,
        "waste_redirect": waste_redirect,
        "surprises": surprises,
        "surprises_total": round(sum(s["expected_monthly"] for s in surprises), 2),
        "liquid_cash": liquid,
        "cashflow": cashflow,
        "safe_to_spend": sts,
        "goals": goals,
        "mortgages": mortgages,
        "tax": tax,
        "cars": [planning.car_plan(c) for c in profile.cars],
        "home": planning.home_plan(profile.home_value),
        "emergency": emergency,
        "net_worth": networth,
        "net_worth_trend": planning.networth_series(_trend_balances(balances, metas)),
        "retirement": planning.retirement_projection(profile, essentials,
                                                      expense_monthly),
        "bills": planning.bill_optimizer(analysis.get("recurring", [])),
        "renewals": forecast.renewal_calendar(analysis.get("recurring", [])),
        "foo": planning.order_of_operations(profile, payoff_debts, emergency),
        "hidden": planning.HIDDEN_HOLDINGS,
        "essentials_monthly": round(essentials, 2),
        "income_monthly": round(income_monthly, 2),
        "income_is_override": income_is_override,
        "detected_income_monthly": round(detected_income_monthly, 2),
        "expense_monthly": round(expense_monthly, 2),
        "leftover": round(leftover, 2),
        "recoverable_waste": round(recoverable, 2),
        "home_value_source": profile.home_value_source,
        "profile": profile,
        "notes": notes,
    }


def compute(paths: Paths, reset: bool = False):
    """Full pipeline: read statements → analyze → build the plan.

    Returns (analysis, plan, warnings, stats, inserted, dup_skipped). Shared by
    the CLI and the local web app so they always agree.
    """
    txns, warnings, stats, metas, balances = ingest.ingest_folder(paths.statements)
    rules = load_user_rules(paths)
    for t in txns:
        t.category = categorize(t.merchant, t.raw_description, t.amount, rules,
                                t.source_category)
    store = Store(paths.db_file)
    if reset:
        store.reset()
    inserted, dup_skipped = store.upsert_many(txns)
    rows = []
    for r in store.all_rows():
        d = dict(r)
        d["category"] = categorize(d["merchant"], d["raw_description"], d["amount"],
                                   rules, d.get("source_category", ""))
        rows.append(d)
    store.close()
    analysis = analyze(rows)
    plan = _build_plan(analysis, paths, metas, balances)
    return analysis, plan, warnings, stats, inserted, dup_skipped


def run(args) -> int:
    if args.demo and not args.data:
        root = (Path.home() / "Documents" / "MoneyMan-Demo").resolve()
    else:
        root = data_home(args.data)
    paths = Paths(root)
    _setup_data_dir(paths)

    print(f"MoneyMan v{__version__}")
    print(f"Data folder: {paths.root}")

    if args.demo:
        print("Generating realistic demo statements, debts & profile…")
        made = sample.generate(paths)
        for m in made:
            print(f"  wrote {m}")

    analysis, plan, warnings, stats, inserted, dup_skipped = compute(
        paths, reset=args.reset or args.demo)
    print(f"Imported {inserted:,} new transactions "
          f"({dup_skipped:,} duplicates skipped) from {stats['files']} file(s); "
          f"{stats['pdf']} PDF(s).")

    report_path = write_report(analysis, paths, warnings, stats, dup_skipped, plan)
    print(f"\nReport ready: {report_path}")
    print(f"(latest copy: {paths.reports / 'MoneyMan_Latest.html'})")

    disc = plan.get("discovery")
    if disc and disc.get("enough"):
        discover.write_interview(paths.reports / "Getting-To-Know-You.txt", disc)

    ic = plan["intake"]["completeness"]
    nw = plan["net_worth"]["net_worth"]
    print(f"Data completeness: {ic}%  ·  debts found: {len(plan['debts'])}  ·  "
          f"net worth: {nw:,.0f}")
    if not analysis.get("empty"):
        s = analysis["summary"]
        print(f"In {s['income']:,.0f}  out {s['expense']:,.0f}  net {s['net']:,.0f}; "
              f"{len(analysis['insights'])} insight(s).")
    if plan["payoff"].get("has_debts"):
        agg = plan["payoff"]["paths"]["aggressive"]["avalanche"]
        print(f"Aggressive payoff: debt-free {agg.payoff_date} "
              f"({agg.months} months).")

    if not args.no_open:
        try:
            webbrowser.open(report_path.resolve().as_uri())
        except Exception:
            print("(Open the report file above in your web browser.)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="moneyman",
        description="MoneyMan — a 100%% local, private personal-finance planner.")
    p.add_argument("command", nargs="?", default="run",
                   choices=["run", "init", "interview", "serve"])
    p.add_argument("--demo", action="store_true")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--no-open", action="store_true")
    p.add_argument("--data", metavar="DIR")
    p.add_argument("--version", action="version", version=f"MoneyMan {__version__}")
    args = p.parse_args(argv)

    if args.command == "init":
        paths = Paths(data_home(args.data))
        _setup_data_dir(paths)
        print(f"Created MoneyMan folders at: {paths.root}")
        print("Add your statements to 'Statements', fill in the two files in "
              "'config', then run MoneyMan again.")
        return 0
    if args.command == "interview":
        from . import interview
        paths = Paths(data_home(args.data))
        return interview.run(paths)
    if args.command == "serve":
        from . import serve
        paths = Paths(data_home(args.data))
        _setup_data_dir(paths)
        return serve.run_server(paths)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
