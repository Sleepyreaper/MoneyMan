"""Generates realistic demo data so anyone can see MoneyMan work in seconds —
no real bank data required.

It writes: two CSV statements, one PDF credit-card statement (to exercise the PDF
reader and the statement→debt auto-extraction), a populated Accounts-and-Debts.csv,
and a filled-in My-Profile.csv. The data deliberately contains problems the engine
should catch (price hikes, duplicate subscriptions, fees, high-interest debt, an
aging car, a thin emergency fund).
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

CHECKING = "Demo Checking"
CARD = "Demo Credit Card"
PDFCARD = "Demo Rewards Card"


def _months(start: date, n: int):
    y, m = start.year, start.month
    for _ in range(n):
        yield date(y, m, 1)
        m += 1
        if m > 12:
            m, y = 1, y + 1


def _day(month: date, dom: int) -> date:
    return month.replace(day=min(dom, 28))


def _write_pdf(lines: list[str], path: Path) -> None:
    """Minimal, valid single-page PDF containing the given text lines."""
    cl = ["BT", "/F1 9 Tf", "40 760 Td", "11 TL"]
    for ln in lines:
        e = ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        cl += [f"({e}) Tj", "T*"]
    cl.append("ET")
    content = "\n".join(cl).encode("latin-1", "replace")
    objs = [b"<</Type/Catalog/Pages 2 0 R>>",
            b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
            b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Resources"
            b"<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>",
            b"<</Length %d>>\nstream\n" % len(content) + content + b"\nendstream",
            b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>"]
    out = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += (b"%d 0 obj\n" % i) + o + b"\nendobj\n"
    xref = len(out)
    n = len(objs) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % n
    for off in offs:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF" % (n, xref)
    path.write_bytes(out)


DEMO_DEBTS = """\
Name,Type,Balance Owed,APR (%),Minimum Monthly Payment,Credit Limit
Store Card,credit card,1150,29.99,40,1500
Visa,credit card,6200,24.99,155,8000
Auto Loan,auto loan,14800,6.4,410,
Student Loan,student loan,9300,5.2,120,
"""

DEMO_PEOPLE = """\
# MoneyMan — Who Is Spending (demo). Track spending per person.
Person,Accounts (separate with ;),Merchant keywords (separate with ;)
Emma,,roblox; american girl; claires
Liam,,nintendo; gamestop; pokemon
"""

DEMO_PROFILE = """\
Field,Value
Your age,38
Cash savings,2500
Retirement balance,24000
Employer 401k match up to (%),5
Getting full employer match? (y/n),n
HSA eligible? (y/n),y
Pension or TRS? (y/n),n
Own your home? (y/n),y
Home value (your estimate),480000
Home size (sq ft),1800
Monthly retirement contribution,400
Expected return (%),7
Target retirement age,65
Look up home value online? (y/n),n
Monthly amount for goals (optional),
What-if lump sum amount,10000
Car1 name,Honda Civic
Car1 year,2014
Car1 mileage,142000
Car1 purchase date,2018-06-01
Car1 purchase price,16000
Car2 name,Subaru Outback
Car2 year,2021
Car2 mileage,38000
Car2 purchase date,2021-03-01
Car2 purchase price,31000
"""


def generate(paths, n_months: int = 14) -> list[str]:
    rng = random.Random(42)
    statements_root = paths.statements
    today = date.today()
    start = (date(today.year - 1, today.month, 1) + timedelta(days=31)).replace(day=1)
    months = list(_months(start, n_months))

    checking: list[tuple[date, str, float]] = []
    card: list[tuple[date, str, float]] = []

    def chk(d, desc, amt): checking.append((d, desc, round(amt, 2)))
    def crd(d, desc, amt): card.append((d, desc, round(amt, 2)))

    for i, mo in enumerate(months):
        chk(_day(mo, 1), "DIRECT DEPOSIT PAYROLL ACME CORP", 4200.00)
        chk(_day(mo, 2), "RENT PAYMENT GREENTREE LANDLORD", -1950.00)
        chk(_day(mo, 9), "COMCAST XFINITY INTERNET", -95.99)
        chk(_day(mo, 11), "VERIZON WIRELESS", -112.00)
        chk(_day(mo, 12), "PG&E ELECTRIC UTILITY", -round(rng.uniform(58, 165), 2))
        chk(_day(mo, 15), "GEICO AUTO INSURANCE PREMIUM", -172.00)
        chk(_day(mo, 6), "ONLINE TRANSFER TO SAVINGS", -300.00)
        chk(_day(mo, 20), "CREDIT CARD PAYMENT THANK YOU", -round(rng.uniform(900, 1600), 2))

        netflix = 9.99 if mo < date(today.year, 1, 1) else 15.49
        crd(_day(mo, 5), "NETFLIX.COM 866-579-7172 CA", netflix)
        crd(_day(mo, 7), "Spotify USA New York NY", 10.99)
        crd(_day(mo, 8), "HULU 877-8244858 CA", 7.99)
        crd(_day(mo, 8), "DISNEY PLUS 888-905-7888", 7.99)
        crd(_day(mo, 14), "PLANET FITNESS CLUB FEE", 10.00)
        crd(_day(mo, 3), "EQUINOX FITNESS MONTHLY", 185.00)
        crd(_day(mo, 18), "ADOBE *CREATIVE CLOUD", 54.99)
        crd(_day(mo, 22), "APPLE.COM/BILL ICLOUD STORAGE", 2.99)
        crd(_day(mo, 22), "GOOGLE *GOOGLE ONE STORAGE", 1.99)
        if i >= n_months - 3:
            crd(_day(mo, 11), "OPENAI *CHATGPT SUBSCRIPTION", 20.00)

        for _ in range(rng.randint(10, 16)):
            crd(_day(mo, rng.randint(1, 28)),
                rng.choice(["STARBUCKS STORE #1123", "BLUE BOTTLE COFFEE OAKLAND",
                            "PEET'S COFFEE 442"]), round(rng.uniform(4.25, 7.80), 2))
        for _ in range(rng.randint(3, 6)):
            crd(_day(mo, rng.randint(1, 28)),
                rng.choice(["DOORDASH*MCDONALDS", "UBER EATS *THAI HOUSE",
                            "GRUBHUB*PIZZA NIGHT"]), round(rng.uniform(22, 47), 2))
        for _ in range(rng.randint(3, 5)):
            crd(_day(mo, rng.randint(1, 28)),
                rng.choice(["TRADER JOE'S #455", "SAFEWAY STORE 1842",
                            "WHOLE FOODS MKT"]), round(rng.uniform(38, 145), 2))
        for _ in range(2):
            crd(_day(mo, rng.randint(1, 28)), "SHELL OIL 5774421", round(rng.uniform(42, 71), 2))
        for _ in range(rng.randint(2, 4)):
            crd(_day(mo, rng.randint(1, 28)),
                rng.choice(["CHIPOTLE 1456", "SUSHI KOMA RESTAURANT", "PANERA BREAD"]),
                round(rng.uniform(14, 39), 2))
        crd(_day(mo, rng.randint(1, 28)), "AMZN MKTP US*RT4D9 AMZN.COM/BILL WA",
            round(rng.uniform(60, 210), 2))

        # Kids' spending — so the "by person" feature has something to show.
        crd(_day(mo, 13), "ROBLOX *ROBUX PURCHASE", 9.99)            # Emma
        if i % 2 == 0:
            crd(_day(mo, 21), "AMERICAN GIRL STORE", round(rng.uniform(28, 64), 2))
        crd(_day(mo, 16), "NINTENDO ESHOP DIGITAL", round(rng.uniform(7.99, 39.99), 2))  # Liam
        if i % 3 == 0:
            crd(_day(mo, 24), "GAMESTOP #455", round(rng.uniform(20, 70), 2))

        if i in (2, 7):
            chk(_day(mo, 24), "OVERDRAFT FEE", -35.00)
        if i % 4 == 0:
            chk(_day(mo, 17), "ATM FEE NON-NETWORK", -3.50)
        if i == 5:
            crd(_day(mo, 19), "FOREIGN TRANSACTION FEE", 8.75)

    spike_mo = months[len(months) // 2]
    crd(_day(spike_mo, 16), "BEST BUY ELECTRONICS", 1280.00)

    # --- write the two CSV statements ---
    chk_dir = statements_root / CHECKING
    card_dir = statements_root / CARD
    pdf_dir = statements_root / PDFCARD
    for d in (chk_dir, card_dir, pdf_dir):
        d.mkdir(parents=True, exist_ok=True)

    chk_path = chk_dir / "checking_transactions.csv"
    with chk_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Description", "Amount"])
        for d, desc, amt in sorted(checking):
            w.writerow([d.strftime("%m/%d/%Y"), desc, f"{amt:.2f}"])

    card_path = card_dir / "creditcard_statement.csv"
    with card_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Transaction Date", "Description", "Debit", "Credit"])
        for d, desc, amt in sorted(card):
            if amt >= 0:
                w.writerow([d.strftime("%m/%d/%Y"), desc, f"{amt:.2f}", ""])
            else:
                w.writerow([d.strftime("%m/%d/%Y"), desc, "", f"{abs(amt):.2f}"])

    # --- write a PDF statement (no APR line, so APR is inferred from interest) ---
    pdf_path = pdf_dir / "rewards_card_statement.pdf"
    _write_pdf([
        "DEMO REWARDS CARD", "Statement Period: 01/10/2026 to 02/09/2026",
        "Account ending in 7788", "Payment Information",
        "New Balance $2,400.00", "Minimum Payment Due $60.00",
        "Credit Limit $5,000.00", "Available Credit $2,600.00",
        "Interest Charged $44.00",
        "Transactions",
        "01/12 NETFLIX.COM 866-579-7172 15.49",
        "01/15 WHOLE FOODS MKT #221 88.20",
        "01/18 SHELL OIL 5774421 47.10",
        "01/22 PAYMENT THANK YOU -150.00",
        "01/28 AMZN MKTP US 8843KL 64.30",
    ], pdf_path)

    # --- populate the profile + debts + people files (overwrite for the demo) ---
    (paths.config / "Accounts-and-Debts.csv").write_text(DEMO_DEBTS, encoding="utf-8")
    (paths.config / "My-Profile.csv").write_text(DEMO_PROFILE, encoding="utf-8")
    (paths.config / "Who-Is-Spending.csv").write_text(DEMO_PEOPLE, encoding="utf-8")

    return [str(chk_path), str(card_path), str(pdf_path),
            str(paths.config / "Accounts-and-Debts.csv"),
            str(paths.config / "My-Profile.csv"),
            str(paths.config / "Who-Is-Spending.csv")]
