"""The 'gather the full picture first' checklist.

MoneyMan looks at what you've provided and figures out what's present, what's
partial, and what's still missing — then it tells you what to add next to unlock
better insights and the payoff/independence plan. More data → better advice.
"""

from __future__ import annotations

from .config import CHECKLIST, MIN_MONTHS_FOR_TRENDS

DONE, PARTIAL, MISSING = "done", "partial", "missing"


def evaluate(analysis: dict, debts: list, metas: list) -> dict:
    summary = analysis.get("summary", {}) if not analysis.get("empty") else {}
    months = summary.get("months_span", 0)
    income = summary.get("income", 0)
    cats = {c["category"] for c in analysis.get("category_totals", [])
            if c["total"] > 0}
    meta_kinds = {m.kind for m in metas}
    debt_kinds = {d.kind for d in debts}
    has_cc = ("credit card" in meta_kinds
              or any("credit" in k for k in debt_kinds))
    has_loan = any(k in ("auto loan", "student loan", "personal loan",
                         "mortgage", "medical") or "loan" in k for k in debt_kinds) \
        or "loan" in meta_kinds

    def status_for(key: str) -> str:
        if key == "months":
            return DONE if months >= 3 else PARTIAL if months >= 1 else MISSING
        if key == "income":
            return DONE if income > 0 else MISSING
        if key == "checking":
            return DONE if (income > 0 and "bank" in meta_kinds) or income > 0 \
                else PARTIAL if not analysis.get("empty") else MISSING
        if key == "savings":
            return DONE if any("savings" in (a or "").lower()
                               for a in summary.get("accounts", [])) else MISSING
        if key == "credit_cards":
            return DONE if has_cc else MISSING
        if key == "loans":
            return DONE if has_loan else MISSING
        if key == "housing":
            return DONE if "Housing" in cats else MISSING
        if key == "utilities":
            return DONE if "Utilities" in cats else MISSING
        if key == "insurance":
            return DONE if "Insurance" in cats else MISSING
        return MISSING

    items = []
    req_total = req_score = 0.0
    for spec in CHECKLIST:
        st = status_for(spec["key"])
        items.append({**spec, "status": st})
        if spec["required"]:
            req_total += 1
            req_score += 1.0 if st == DONE else 0.5 if st == PARTIAL else 0.0

    completeness = round(req_score / req_total * 100) if req_total else 0
    next_steps = [it for it in items
                  if it["status"] != DONE and it["required"]][:4]
    next_steps += [it for it in items
                   if it["status"] == MISSING and not it["required"]][:2]

    return {
        "items": items,
        "completeness": completeness,
        "next_steps": next_steps,
        "enough_for_trends": months >= MIN_MONTHS_FOR_TRENDS,
        "enough_for_payoff": any(d.balance > 0 for d in debts),
        "have_apr": all(d.apr > 0 for d in debts) if debts else False,
        "months": months,
    }
