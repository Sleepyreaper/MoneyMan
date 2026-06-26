"""Get to know you — turn 6+ months of real spending into (a) a plain-English
profile of who this household looks like, and (b) the smart questions a good
planner would ask to fill in the gaps.

This is the reusable version of the data-driven interview: it reads the patterns
(income sources, life-stage merchant clusters, accounts, recurring charges) and
generates personalized questions, so MoneyMan can build a real profile of anyone —
not just with canned questions, but from what their money actually shows.

Everything is local, rule-based, and explainable.
"""

from __future__ import annotations

from collections import defaultdict

from .config import NON_SPENDING_CATEGORIES

MIN_MONTHS = 6        # need enough history before patterns are trustworthy

# Life-stage / household "tells" — clusters of merchants that reveal who lives here
# and how they spend. (label, why-it-matters, keyword tuple)
SIGNAL_SETS = [
    ("college", "Someone in college",
     ("campus edge", "paypath", "gcsu", "banner web", "university of", "college",
      "tuition", "dorm", "student hous", "bursar", "radboud"),
     "Tuition, student housing or university payments — usually a child in school. "
     "Worth knowing which child, and for how many more years."),
    ("gaming", "A gamer in the house",
     ("roblox", "nintendo", "xbox", "playstation", "steam games", "epic games",
      "minecraft", "fortnite", "discord", "twitch", "supercell"),
     "Gaming and app-store charges — often a teen or young adult."),
    ("self_care", "Regular salon / beauty spending",
     ("nail", "salon", "sephora", "ulta", "lululemon", "great clips", "barber",
      " spa ", "blowout", "lash", "brow"),
     "Salons, nails and beauty add up — and it helps to know whose it is."),
    ("pets", "A pet in the family",
     ("vet ", "veterin", "petco", "petsmart", "chewy", "whisker", "litter-robot",
      "pet supplies", "pet boutique", "grooming"),
     "Pet food, grooming and vet visits — plus the occasional big surprise vet bill."),
    ("baby", "A baby or young child",
     ("carter", "buybuy baby", "pampers", "huggies", "daycare", "childcare",
      "kindercare", "the children's place"),
     "Diapers, daycare and kid gear — large and fast-changing costs."),
    ("charity", "Regular charitable giving",
     ("world vision", "compassion", "unicef", "red cross", "st jude", "ministr",
      "church", "donation", "charity", "goodwill"),
     "Recurring giving — part of who you are, and usually tax-deductible."),
    ("ev", "An electric vehicle",
     ("tesla", "supercharg", "chargepoint", "electrify america", "ev charging",
      "evgo"),
     "EV charging shows up instead of gas — a different maintenance & fuel picture."),
    ("investing", "Active investing / brokerage",
     ("fidelity", "vanguard", "schwab", "robinhood", "coinbase", "e*trade",
      "etrade", "betterment", "wealthfront"),
     "Brokerage activity — make sure it's working toward your goals tax-efficiently."),
]


def _expense_records(records):
    return [r for r in records if r.get("amount", 0) < 0
            and r.get("category") not in NON_SPENDING_CATEGORIES]


def _income_sources(records, months):
    inc = defaultdict(float)
    cnt = defaultdict(int)
    for r in records:
        if r.get("amount", 0) > 0 and r.get("category") == "Income":
            inc[r["merchant"]] += r["amount"]
            cnt[r["merchant"]] += 1
    out = []
    for m, total in inc.items():
        out.append({"name": m, "total": round(total, 2),
                    "monthly": round(total / max(1, months), 2),
                    "count": cnt[m], "regular": cnt[m] >= max(3, months // 3)})
    out.sort(key=lambda x: x["total"], reverse=True)
    return out


def detect_signals(records):
    """Find life-stage 'tells' in the spending, with the evidence behind each."""
    expenses = _expense_records(records)
    found = []
    for key, label, kws, why in SIGNAL_SETS:
        by_merchant = defaultdict(float)
        for r in expenses:
            text = f'{r.get("merchant", "")} {r.get("raw_description", "")}'.lower()
            if any(k in text for k in kws):
                by_merchant[r["merchant"]] += -r["amount"]
        if not by_merchant:
            continue
        top = sorted(by_merchant.items(), key=lambda x: x[1], reverse=True)[:5]
        total = round(sum(by_merchant.values()), 2)
        if total < 25:                       # ignore trivial one-off matches
            continue
        found.append({
            "key": key, "label": label, "why": why, "total": total,
            "merchants": [m for m, _ in top],
            "evidence": [f"{m} — ${v:,.0f}" for m, v in top]})
    found.sort(key=lambda s: s["total"], reverse=True)
    return found


def _covered_by_people(merchants, people):
    """True if every listed merchant already matches a configured person rule."""
    if not people:
        return False
    low = " ".join(merchants).lower()
    for p in people:
        for k in p.keywords:
            if k.strip() and k.strip().lower() in low:
                return True
    return False


def build_narrative(income, signals, plan):
    """A plain-English 'here's who you look like' paragraph, built from the data."""
    bits = []
    big = [s for s in income if s["regular"] and s["monthly"] >= 500]
    if len(big) >= 2:
        srcs = ", ".join(f"{s['name']} (~${s['monthly']:,.0f}/mo)" for s in big[:3])
        bits.append(f"You have {len(big)} steady income sources — {srcs} — which "
                     f"looks like a dual-income household.")
    elif big:
        s = big[0]
        bits.append(f"Your main income looks like {s['name']} "
                    f"(~${s['monthly']:,.0f}/mo).")

    labels = [s["label"].lower() for s in signals]
    if labels:
        bits.append("Your spending also shows " + _join_human(labels[:5]) + ".")

    nw = plan.get("net_worth", {})
    if nw.get("net_worth"):
        bits.append(f"Net worth is about ${nw['net_worth']:,.0f}.")
    return " ".join(bits)


def _join_human(items):
    items = list(items)
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def generate_questions(records, income, signals, plan, profile, people):
    """The smart, data-driven questions a planner would ask to finish the profile."""
    qs = []

    # 1) Income — whose paycheck is whose? (the backbone of a household profile)
    pay = [s for s in income if s["regular"] and s["monthly"] >= 400][:3]
    if len(pay) >= 2:
        qs.append({
            "q": "Who earns each of these paychecks?",
            "why": "Two or more steady incomes — knowing who earns what shapes "
                   "taxes, benefits, and whose retirement match to capture.",
            "evidence": [f"{s['name']} — ~${s['monthly']:,.0f}/mo" for s in pay]})
    elif pay:
        qs.append({
            "q": f"Is {pay[0]['name']} your only income, or does someone else in "
                 "the house earn too?",
            "why": "Knowing total household income is how we tell what's truly "
                   "left over each month.",
            "evidence": [f"{pay[0]['name']} — ~${pay[0]['monthly']:,.0f}/mo"]})

    # 2) Life-stage clusters not yet attributed to a person.
    for s in signals:
        if s["key"] in ("charity", "investing", "ev"):
            continue                          # not a 'who buys this' question
        if _covered_by_people(s["merchants"], people):
            continue
        qs.append({
            "q": f"These look like {s['label'].lower()} — who are they for?",
            "why": s["why"],
            "evidence": s["evidence"]})

    # 3) Accounts — whose is each one? (so spending can be split by person)
    spend = defaultdict(float)
    for r in _expense_records(records):
        spend[r["account"]] += -r["amount"]
    accts = sorted(spend.items(), key=lambda x: x[1], reverse=True)[:6]
    if len(accts) >= 2:
        qs.append({
            "q": "Whose account is each of these — yours, a partner's, shared, "
                 "or a kid's?",
            "why": "If a whole account belongs to one person, MoneyMan can "
                   "attribute everything on it to them automatically.",
            "evidence": [f"{a} — ${v:,.0f} of spending" for a, v in accts]})

    # 4) Profile gaps the data can't see.
    gaps = []
    if not profile.age:
        gaps.append("your age")
    if not profile.retirement_balance:
        gaps.append("your retirement balance")
    if not (profile.home_value or profile.owns_home):
        gaps.append("whether you own your home and its rough value")
    if not profile.cars:
        gaps.append("your cars (year + mileage)")
    if gaps:
        qs.append({
            "q": "A few things your statements can't show me — can you fill them in?",
            "why": "These unlock the retirement projection, home & car planning, "
                   "and your path to financial independence.",
            "evidence": [g.capitalize() for g in gaps]})

    return qs


def generate(records, plan, profile, people, months_span):
    """Top-level: returns the discovery block, or {'enough': False} if too little data."""
    if months_span < MIN_MONTHS:
        return {"enough": False, "months": months_span, "min_months": MIN_MONTHS}
    income = _income_sources(records, months_span)
    signals = detect_signals(records)
    return {
        "enough": True,
        "months": months_span,
        "narrative": build_narrative(income, signals, plan),
        "income": income[:8],
        "signals": signals,
        "questions": generate_questions(records, income, signals, plan,
                                        profile, people),
    }


def write_interview(path, discovery) -> None:
    """Save the generated interview to a friendly text file the user can answer."""
    if not discovery.get("enough"):
        return
    lines = [
        "MoneyMan — Getting to know you",
        "=" * 40,
        "",
        "Here's who your money looks like, and the questions that would sharpen",
        "your plan. Jot answers next to each (or just tell MoneyMan in the app).",
        "",
        "WHO YOU LOOK LIKE",
        "-" * 17,
        discovery["narrative"],
        "",
        "QUESTIONS",
        "-" * 9,
    ]
    for i, q in enumerate(discovery["questions"], 1):
        lines.append(f"{i}. {q['q']}")
        lines.append(f"   Why: {q['why']}")
        for e in q["evidence"]:
            lines.append(f"     • {e}")
        lines.append("   Your answer: ____________________________________________")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
