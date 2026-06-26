"""The normalized transaction model + merchant-name cleaning + categorization.

Sign convention used everywhere in MoneyMan:
    amount < 0  -> money OUT (an expense / payment / fee)
    amount > 0  -> money IN  (income / refund / deposit)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


@dataclass
class Txn:
    """A single normalized transaction."""

    account: str
    date: str            # ISO yyyy-mm-dd
    amount: float        # signed; negative = expense
    raw_description: str
    source_file: str
    fitid: str | None = None          # bank-provided unique id (OFX/QFX only)
    occ: int = 1                       # nth identical row within its source file
    merchant: str = ""                 # cleaned, human-friendly name
    source_category: str = ""          # category from the export (Monarch/Copilot)
    category: str = "Uncategorized"
    txn_id: str = field(default="", init=False)

    def fingerprint(self) -> str:
        """Stable id used to detect duplicates across overlapping statements."""
        if self.fitid:
            basis = f"{self.account}|FITID|{self.fitid}"
        else:
            basis = f"{self.account}|{self.date}|{self.amount:.2f}|{self.merchant}|{self.occ}"
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Merchant-name cleaning.  Bank descriptions are noisy:
#   "SQ *BLUE BOTTLE COFFEE  OAKLAND CA 0123" -> "Blue Bottle Coffee"
#   "AMZN MKTP US*2X9KL1   AMZN.COM/BILL WA"  -> "Amazon"
#   "NETFLIX.COM           866-579-7172 CA"   -> "Netflix"
# --------------------------------------------------------------------------- #
_KNOWN = {
    "amzn": "Amazon", "amazon": "Amazon", "netflix": "Netflix", "spotify": "Spotify",
    "hulu": "Hulu", "disney": "Disney+", "hbo": "HBO Max", "youtubepremium": "YouTube Premium",
    "starbucks": "Starbucks", "dunkin": "Dunkin", "doordash": "DoorDash",
    "ubereats": "Uber Eats", "uber": "Uber", "lyft": "Lyft", "grubhub": "Grubhub",
    "paramount": "Paramount+", "peacock": "Peacock", "audible": "Audible",
    "adobe": "Adobe", "microsoft": "Microsoft", "msft": "Microsoft", "dropbox": "Dropbox",
    "google": "Google", "icloud": "Apple iCloud", "1password": "1Password",
    "notion": "Notion", "openai": "OpenAI", "chatgpt": "OpenAI", "nordvpn": "NordVPN",
    "peloton": "Peloton", "classpass": "ClassPass", "equinox": "Equinox",
    "planetfit": "Planet Fitness", "geico": "GEICO", "progressive": "Progressive",
    "statefarm": "State Farm", "costco": "Costco", "walmart": "Walmart",
    "target": "Target", "safeway": "Safeway", "kroger": "Kroger", "wholefoods": "Whole Foods",
    "traderjoe": "Trader Joe's", "shell": "Shell", "chevron": "Chevron", "exxon": "Exxon",
    "comcast": "Comcast", "xfinity": "Xfinity", "verizon": "Verizon", "at&t": "AT&T",
    "tmobile": "T-Mobile", "pg&e": "PG&E",
}

_NOISE_PREFIXES = ("sq *", "tst* ", "tst*", "pp*", "paypal *", "paypal*", "sp ",
                   "pos ", "pos debit ", "debit card purchase ", "purchase ",
                   "recurring ", "ach debit ", "ach ", "visa ", "check card ",
                   "checkcard ", "dbt crd ", "dda ", "ext ", "web ")
_CITY_STATE = re.compile(r"\b[A-Z]{2}\b\s*\d{0,5}\s*$")           # trailing "CA 94016"
_PHONE = re.compile(r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b")
_LONGNUM = re.compile(r"[#*]?\b[A-Z0-9]{0,3}\d{4,}[A-Z0-9]*\b")    # order/store ids
_DATE_TAIL = re.compile(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b")
_MULTISPACE = re.compile(r"\s{2,}")
_NONWORD_EDGES = re.compile(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$")


def clean_merchant(raw: str) -> str:
    """Turn a noisy bank description into a tidy, groupable merchant name."""
    s = (raw or "").strip()
    low = s.lower()

    # Strip common payment-processor / channel prefixes.
    for p in _NOISE_PREFIXES:
        if low.startswith(p):
            s = s[len(p):]
            low = s.lower()
            break

    s = _PHONE.sub(" ", s)
    s = _DATE_TAIL.sub(" ", s)
    s = _CITY_STATE.sub(" ", s)
    s = _LONGNUM.sub(" ", s)
    s = s.replace("*", " ").replace("/", " ")
    s = _MULTISPACE.sub(" ", s).strip()
    s = _NONWORD_EDGES.sub("", s)

    # Map to a known canonical name if any token matches.
    collapsed = re.sub(r"[^a-z&]", "", low)
    for key, name in _KNOWN.items():
        if key in collapsed:
            return name

    if not s:
        return raw.strip()[:40] or "Unknown"

    # Title-case but keep short all-caps acronyms readable.
    words = []
    for w in s.split():
        words.append(w if (w.isupper() and len(w) <= 4) else w.capitalize())
    return " ".join(words)[:40]


# Source (Monarch/Copilot) categories that mean "moving money", not spending.
# Mortgage / HELOC / loan payments are debt service: they pay down a balance tracked
# in net worth, so counting them as "spending" double-counts. (Rent is NOT here — it
# stays a real housing expense.)
_SRC_TRANSFER = ("transfer", "credit card payment", "balance adjustment",
                 "payment", "investment", "buy", "sell",
                 "mortgage", "home equity", "heloc", "loan repayment")
_SRC_INCOME = ("paycheck", "income", "interest income", "dividend", "deposit")

# Accounting artifacts that aren't real money in or out: balance-transfer promos and
# internal offsets that net to zero but distort both income and spending if counted.
_ARTIFACT_NOISE = ("promotional apr", "promotional balance", "offer moved to standard",
                   "apr ended", "balance transfer", "promo balance")

# Map common Monarch/Copilot category names onto MoneyMan's buckets so the
# spending breakdown and insights stay meaningful on real exports.
_SRC_MAP = {
    "restaurants & bars": "Restaurants", "coffee shops": "Coffee",
    "fast food": "Restaurants", "groceries": "Groceries", "gas": "Transport & Gas",
    "auto & transport": "Transport & Gas", "parking & tolls": "Transport & Gas",
    "public transit": "Transport & Gas", "taxi & ride shares": "Rideshare",
    "shopping": "Shopping", "clothing": "Shopping", "electronics": "Shopping",
    "entertainment & recreation": "Entertainment", "streaming": "Streaming",
    "software & tech": "Software & Apps", "subscriptions": "Software & Apps",
    "medical": "Health & Fitness", "dentist": "Health & Fitness",
    "fitness": "Health & Fitness", "pharmacy": "Health & Fitness",
    "insurance": "Insurance", "rent": "Housing", "mortgage": "Housing",
    "home improvement": "Housing", "water": "Utilities", "gas & electric": "Utilities",
    "internet & cable": "Utilities", "phone": "Utilities", "utilities": "Utilities",
    "pets": "Pets", "child care": "Kids", "travel & vacation": "Travel",
    "taxes": "Taxes", "financial fees": "Fees & Interest",
    "interest charged": "Fees & Interest", "loan payment": "Loans & Debt",
}


def _normalize_source_category(sc: str) -> str:
    low = sc.strip().lower()
    if low in _SRC_MAP:
        return _SRC_MAP[low]
    return sc.strip()[:30] or "Uncategorized"


def categorize(merchant: str, raw_description: str, amount: float,
               rules: list[tuple[str, list[str]]], source_category: str = "") -> str:
    """Assign a category using keyword rules, with income/expense awareness.

    When the export already provides a category (Monarch/Copilot), we use it to
    nail the structural buckets (Transfers/Income) — critical so transfers between
    your own accounts aren't mistaken for spending — and as a fallback otherwise.
    """
    hay = f"{merchant} {raw_description}".lower()
    # Strip out accounting artifacts first (balance-transfer promos, internal offsets):
    # they net to zero and would otherwise inflate income AND spending.
    if any(k in hay for k in _ARTIFACT_NOISE):
        return "Transfers"

    sc = (source_category or "").strip().lower()
    if sc:
        if any(k in sc for k in _SRC_TRANSFER):
            return "Transfers"
        if amount > 0 and any(k in sc for k in _SRC_INCOME):
            return "Income"

    for category, keywords in rules:
        for kw in keywords:
            if kw in hay:
                if amount > 0 and category not in ("Income", "Transfers",
                                                    "Fees & Interest"):
                    continue
                return category

    if sc:                                   # trust the export's own category
        return _normalize_source_category(source_category)
    if amount > 0:
        return "Income"
    return "Uncategorized"
