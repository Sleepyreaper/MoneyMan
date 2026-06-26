"""Track spending by person — who in the household is money going to/for.

This is rule-based and fully local, just like categorization. You tell MoneyMan
who the people are and how to recognize their spending in two simple ways:

  * by ACCOUNT  — "this whole card/account is my son's"
  * by KEYWORD  — "anything that says 'roblox' or 'american girl' is Emma"

Everything else lands in a shared "Everyone / Household" bucket. You edit it in
plain language in config\\Who-Is-Spending.csv, or right in the web app — and it
persists. Nothing about this leaves your computer.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .config import NON_SPENDING_CATEGORIES

SHARED = "Everyone / Household"


@dataclass
class Person:
    name: str
    accounts: list[str] = field(default_factory=list)   # whole accounts they own
    keywords: list[str] = field(default_factory=list)    # merchant/desc keywords

    def matches(self, record: dict) -> bool:
        acct = (record.get("account") or "").lower()
        if any(a and a == acct for a in self._low(self.accounts)):
            return True
        text = f'{record.get("merchant", "")} {record.get("raw_description", "")}'.lower()
        return any(k and k in text for k in self._low(self.keywords))

    @staticmethod
    def _low(items: list[str]) -> list[str]:
        return [i.strip().lower() for i in items if i.strip()]


def _split(cell: str) -> list[str]:
    """Split a 'a; b; c' (or comma) cell into a clean list."""
    if not cell:
        return []
    raw = cell.replace(",", ";").split(";")
    return [x.strip() for x in raw if x.strip()]


def load_people(path: Path) -> list[Person]:
    if not path.exists():
        return []
    out: list[Person] = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(
                row for row in f if row.strip() and not row.lstrip().startswith("#"))
            for i, r in enumerate(reader):
                if not r:
                    continue
                name = (r[0] or "").strip()
                if not name or name.lower() in ("person", "name"):
                    continue            # header row
                if name.lower().startswith("example"):
                    continue            # template placeholder
                accounts = _split(r[1]) if len(r) > 1 else []
                keywords = _split(r[2]) if len(r) > 2 else []
                out.append(Person(name=name, accounts=accounts, keywords=keywords))
    except Exception:
        return out
    return out


PEOPLE_TEMPLATE = """\
# MoneyMan — Who Is Spending.  OPTIONAL: track spending by person (e.g. each kid).
# One row per person. Two easy ways to claim spending:
#   Accounts        - whole accounts that are theirs (e.g. their debit card)
#   Merchant words  - words that identify their charges on any card (e.g. roblox)
# Separate multiple entries with a semicolon ;  Leave a cell blank to skip it.
# Anything not claimed lands in a shared "Everyone / Household" total.
# Delete the example rows and add your own (or add people in the web app).
Person,Accounts (separate with ;),Merchant keywords (separate with ;)
Example - Emma,,roblox; american girl; justice; claires
Example - Liam,,gamestop; nintendo; pokemon; minecraft
"""


def write_people_template(path: Path) -> None:
    if not path.exists():
        path.write_text(PEOPLE_TEMPLATE, encoding="utf-8")


def write_people(path: Path, people: list[Person]) -> None:
    """Persist the people list (used by the web app's editor)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Person", "Accounts (separate with ;)",
                "Merchant keywords (separate with ;)"])
    for p in people:
        w.writerow([p.name, "; ".join(p.accounts), "; ".join(p.keywords)])
    path.write_text(
        "# MoneyMan — Who Is Spending. Edited in the web app; safe to edit here too.\n"
        "# Separate multiple accounts / keywords with a semicolon ;\n"
        + buf.getvalue(), encoding="utf-8")


def load_assignments(path: Path) -> dict[str, str]:
    """Per-merchant 'who is this for' overrides set visually in the web app.

    Returns {merchant_lowercased: person}. These beat the keyword/account rules,
    so dragging a single merchant to someone always wins.
    """
    out: dict[str, str] = {}
    if not path.exists():
        return out
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(
                row for row in f if row.strip() and not row.lstrip().startswith("#"))
            for r in reader:
                if len(r) >= 2 and r[0].strip() and r[0].strip().lower() != "merchant":
                    out[r[0].strip().lower()] = r[1].strip() or SHARED
    except Exception:
        return out
    return out


def write_assignments(path: Path, mapping: dict[str, str]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Merchant", "Person"])
    for m, p in mapping.items():
        w.writerow([m, p])
    path.write_text(
        "# MoneyMan — Spending Assignments (who each merchant's spending is for).\n"
        "# Set this visually in the web app's People tab (drag the cards). You can\n"
        "# edit here too: Person is a name from Who-Is-Spending.csv, or "
        f"'{SHARED}'.\n" + buf.getvalue(), encoding="utf-8")


def assign(record: dict, people: list[Person],
           assignments: dict[str, str] | None = None) -> str:
    """Return the name of the person this expense belongs to, or the shared bucket.

    Order: an explicit per-merchant assignment (set by dragging in the web app)
    wins; then keyword/account rules; otherwise the shared household bucket.
    """
    if assignments:
        m = (record.get("merchant") or "").strip().lower()
        if m in assignments:
            return assignments[m]
    for p in people:                 # first match wins (file order)
        if p.matches(record):
            return p.name
    return SHARED


def assignment_board(records: list[dict], people: list[Person],
                     assignments: dict[str, str] | None, limit: int = 36) -> list[dict]:
    """Top merchants by spend with their current owner — feeds the drag-drop board."""
    spend: dict[str, float] = defaultdict(float)
    cnt: dict[str, int] = defaultdict(int)
    for r in records:
        if r.get("amount", 0) >= 0 or r.get("category") in NON_SPENDING_CATEGORIES:
            continue
        spend[r["merchant"]] += -float(r["amount"])
        cnt[r["merchant"]] += 1
    names = {p.name for p in people}
    out = []
    for m, total in sorted(spend.items(), key=lambda x: x[1], reverse=True)[:limit]:
        who = assign({"merchant": m, "raw_description": "", "account": ""},
                     people, assignments)
        if who not in names and who != SHARED:
            who = SHARED
        out.append({"merchant": m, "total": round(total, 2),
                    "count": cnt[m], "person": who})
    return out


def spending_by_person(records: list[dict], people: list[Person],
                       months_span: int,
                       assignments: dict[str, str] | None = None) -> dict | None:
    """Summarize expenses per person: total, monthly, top categories, their txns."""
    if not people:
        return None
    months = max(1, months_span)
    names = [p.name for p in people] + [SHARED]
    totals = {n: 0.0 for n in names}
    counts = {n: 0 for n in names}
    cats: dict[str, dict[str, float]] = {n: {} for n in names}
    txns: dict[str, list[dict]] = {n: [] for n in names}

    grand_total = 0.0
    for r in records:
        if r.get("amount", 0) >= 0 or r.get("category") in NON_SPENDING_CATEGORIES:
            continue
        who = assign(r, people, assignments)
        amt = -float(r["amount"])
        totals[who] += amt
        counts[who] += 1
        cats[who][r["category"]] = cats[who].get(r["category"], 0.0) + amt
        txns[who].append(r)
        grand_total += amt

    people_out = []
    for n in names:
        if totals[n] <= 0 and n != SHARED:
            # keep configured people visible even at $0 so the user sees the effect
            pass
        top_cats = sorted(cats[n].items(), key=lambda x: x[1], reverse=True)[:4]
        people_out.append({
            "name": n,
            "is_shared": n == SHARED,
            "total": round(totals[n], 2),
            "monthly": round(totals[n] / months, 2),
            "count": counts[n],
            "pct": round(totals[n] / grand_total * 100, 1) if grand_total else 0.0,
            "top_categories": [(c, round(v, 2)) for c, v in top_cats],
            "txns": sorted(txns[n], key=lambda r: r["date"], reverse=True),
        })
    # People first (by spend), shared bucket last.
    people_out.sort(key=lambda p: (p["is_shared"], -p["total"]))
    return {
        "people": people_out,
        "grand_total": round(grand_total, 2),
        "monthly_total": round(grand_total / months, 2),
        "tracked": [p for p in people_out if not p["is_shared"]],
    }
