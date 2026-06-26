"""A friendly, plain-language interview that ASKS you for the details — instead
of making you edit spreadsheets. It writes your profile and fills in the interest
rates on your debts, then you just run MoneyMan again.

Runs in the terminal (double-click Interview.bat). Everything stays local.
Press Enter to skip any question you don't know.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from .config import Paths


def _in(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("\nInterview cancelled — nothing changed.")


def _money_or_blank(prompt: str) -> str:
    v = _in(prompt)
    if not v:
        return ""
    v = v.replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        float(v)
        return v
    except ValueError:
        print("   (didn't look like a number — skipped)")
        return ""


def _yn(prompt: str) -> str:
    v = _in(prompt + " (y/n): ").lower()
    return "y" if v.startswith("y") else "n" if v.startswith("n") else ""


def _section(title: str) -> None:
    print("\n" + title)
    print("-" * len(title))


def run(paths: Paths) -> int:
    paths.ensure()
    print("=" * 64)
    print("  MoneyMan Interview — let's personalize your plan.")
    print("  Everything stays on this computer. Press Enter to skip anything.")
    print("=" * 64)

    prof: dict[str, str] = {}

    _section("About you")
    prof["Your age"] = _money_or_blank("Your age? ")
    prof["Target retirement age"] = _money_or_blank("Age you'd like to retire (e.g. 65)? ")

    _section("Income, savings & retirement")
    prof["Monthly take-home income"] = _money_or_blank(
        "Household take-home income each month? (Enter to let me estimate) $")
    prof["Cash savings"] = _money_or_blank("Cash in savings / emergency fund? $")
    prof["Retirement balance"] = _money_or_blank("Total retirement balance (401k/IRA)? $")
    prof["Monthly retirement contribution"] = _money_or_blank(
        "How much do you put toward retirement each month? $")
    prof["Estimated Social Security (monthly, household)"] = _money_or_blank(
        "Est. monthly Social Security for your household? (ssa.gov; Enter to skip) $")
    prof["Employer 401k match up to (%)"] = _money_or_blank(
        "Employer match — up to what % of pay? (Enter if none) ")
    if prof["Employer 401k match up to (%)"]:
        prof["Getting full employer match? (y/n)"] = _yn(
            "Are you contributing enough to get the FULL match?")
    prof["HSA eligible? (y/n)"] = _yn("On a high-deductible health plan (HSA-eligible)?")
    prof["Pension or TRS? (y/n)"] = _yn("Do you have a pension or TRS (teacher/public)?")

    _section("Your home")
    if _yn("Do you OWN your home?") == "y":
        prof["Own your home? (y/n)"] = "y"
        prof["Home value (your estimate)"] = _money_or_blank("Roughly what's it worth? $")
        prof["Home size (sq ft)"] = _money_or_blank("Square footage? (Enter to skip) ")
    else:
        prof["Own your home? (y/n)"] = "n"

    _section("Rental property")
    if _yn("Do you own a rental property (rent it out)?") == "y":
        prof["Own a rental property? (y/n)"] = "y"
        prof["Rental property value"] = _money_or_blank("What's the rental worth? $")
        prof["Rental monthly rent income"] = _money_or_blank("Monthly rent it brings in? $")
        prof["Rental mortgage balance"] = _money_or_blank("Mortgage still owed on it? $")
        prof["Rental mortgage APR (%)"] = _money_or_blank("Its mortgage interest rate? % ")
    else:
        prof["Own a rental property? (y/n)"] = "n"

    _section("Vehicles")
    try:
        ncars = int(_money_or_blank("How many cars do you have? ") or "0")
    except ValueError:
        ncars = 0
    for i in range(1, min(ncars, 3) + 1):
        print(f"  Car {i}:")
        prof[f"Car{i} name"] = _in("   Name (e.g. Honda Civic)? ")
        prof[f"Car{i} year"] = _money_or_blank("   Year? ")
        prof[f"Car{i} mileage"] = _money_or_blank("   Current mileage? ")
        prof[f"Car{i} purchase price"] = _money_or_blank("   What you paid? $")

    _section("Goals")
    prof["Monthly amount for goals (optional)"] = _money_or_blank(
        "Monthly amount you can put toward debt/goals? (Enter to let me estimate) $")
    prof["What-if lump sum amount"] = _money_or_blank(
        "A lump sum to model in 'what-if' (e.g. 10000)? (Enter to skip) $")

    _write_profile(paths.config / "My-Profile.csv", prof)
    print(f"\n✔ Saved your profile to {paths.config / 'My-Profile.csv'}")

    _interview_people(paths.config / "Who-Is-Spending.csv")
    _interview_debts(paths.config / "Accounts-and-Debts.csv")

    print("\n" + "=" * 64)
    print("  All set! Now double-click Run-MoneyMan.bat to see your")
    print("  personalized plan with the payoff paths unlocked.")
    print("=" * 64)
    return 0


def _write_profile(path: Path, prof: dict) -> None:
    # Keep a stable, readable field order; include defaults we didn't ask.
    prof.setdefault("Expected return (%)", "7")
    prof.setdefault("Look up home value online? (y/n)", "n")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Field", "Value"])
    for k, v in prof.items():
        if v != "":
            w.writerow([k, v])
    path.write_text("# MoneyMan profile (created by the interview). Edit any time.\n"
                    + buf.getvalue(), encoding="utf-8")


def _interview_people(path: Path) -> None:
    _section("Track spending by person (optional)")
    print("Want to see what each person costs — a partner, or each kid?")
    print("For each, you can name an account that's theirs and/or merchant words")
    print("(like 'roblox') that identify their charges. Press Enter to skip.")
    try:
        npeople = int(_money_or_blank("How many people to track? (Enter to skip) ") or "0")
    except ValueError:
        npeople = 0
    if npeople <= 0:
        return
    people: list[list[str]] = []
    for i in range(1, min(npeople, 8) + 1):
        name = _in(f"  Person {i} name? ")
        if not name:
            continue
        accts = _in("     Account(s) that are theirs (separate with ;)? ")
        kws = _in("     Merchant words that are theirs (e.g. roblox; nintendo)? ")
        people.append([name, accts, kws])
    if not people:
        return
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Person", "Accounts (separate with ;)",
                "Merchant keywords (separate with ;)"])
    for r in people:
        w.writerow(r)
    path.write_text("# Who Is Spending (created by the interview). Edit any time.\n"
                    "# Separate multiple accounts / keywords with a semicolon ;\n"
                    + buf.getvalue(), encoding="utf-8")
    print(f"\n✔ Saved {len(people)} person(s) to {path}")


def _interview_debts(path: Path) -> None:
    _section("Your debts — interest rates & minimums")
    print("For each debt I'll show the balance; just type its interest rate (APR)")
    print("and minimum monthly payment. (Find them on the latest statement.)")

    rows: list[list[str]] = []
    header = ["Name", "Type", "Balance Owed", "APR (%)",
              "Minimum Monthly Payment", "Credit Limit"]
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.reader(x for x in f if not x.lstrip().startswith("#")):
                if r and r[0].strip().lower() != "name" and any(c.strip() for c in r):
                    rows.append((r + ["", "", "", "", "", ""])[:6])

    if not rows:
        print("\n(No debts detected yet — you can add them in Accounts-and-Debts.csv)")
        return

    out: list[list[str]] = []
    for r in rows:
        name, kind, bal = r[0], r[1] or "other", r[2]
        if name.lower().startswith("example"):
            continue
        print(f"\n  • {name}  —  balance ${bal}")
        apr = _money_or_blank("     Interest rate (APR) %? ")
        minp = _money_or_blank("     Minimum monthly payment? $")
        out.append([name, kind, bal, apr or r[3], minp or r[4], r[5]])

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in out:
        w.writerow(r)
    path.write_text("# Your debts (interest rates added via the interview).\n"
                    "# Type: credit card, auto loan, student loan, personal loan, mortgage, medical, other\n"
                    + buf.getvalue(), encoding="utf-8")
    print(f"\n✔ Updated {path}")
