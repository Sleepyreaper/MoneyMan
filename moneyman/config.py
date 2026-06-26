"""Configuration: where files live and the rules used to categorize spending.

Everything is local. The data folder defaults to:  ~/Documents/MoneyMan
You can override it by setting the MONEYMAN_HOME environment variable, or by
passing --data on the command line.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "MoneyMan"


# --------------------------------------------------------------------------- #
# Folder layout (all under the user's Documents folder by default)
# --------------------------------------------------------------------------- #
def data_home(override: str | None = None) -> Path:
    """Return the root MoneyMan data folder, creating nothing yet."""
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("MONEYMAN_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "Documents" / APP_NAME).resolve()


class Paths:
    """Resolved folder paths for one run."""

    def __init__(self, root: Path):
        self.root = root
        self.statements = root / "Statements"   # user drops bank exports here
        self.reports = root / "Reports"          # generated dashboards land here
        self.database = root / "database"        # local SQLite store
        self.config = root / "config"            # user-editable rules
        self.db_file = self.database / "moneyman.db"

    def ensure(self) -> None:
        for p in (self.root, self.statements, self.reports, self.database, self.config):
            p.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Categorization rules.  First matching keyword wins.  Lowercase keywords.
# These are deliberately broad; users can extend them via config/categories.json
# --------------------------------------------------------------------------- #
DEFAULT_CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("Income", ["payroll", "direct dep", "direct deposit", "salary", "deposit from",
                "irs treas", "ach credit", "interest paid", "dividend", "refund",
                "reimbursement", "venmo cashout", "zelle from", "tax ref"]),
    ("Transfers", ["transfer", "xfer", "online banking transfer", "to savings",
                   "from savings", "autopay payment", "credit card payment",
                   "pymt", "epayment", "bill pay", "withdrawal to", "wire"]),
    ("Fees & Interest", ["overdraft", "nsf", "insufficient funds", "late fee",
                         "service fee", "maintenance fee", "monthly fee",
                         "annual fee", "atm fee", "foreign transaction",
                         "finance charge", "interest charge", "interest charged",
                         "cash advance fee", "returned item", "overlimit"]),
    ("Housing", ["rent", "mortgage", "landlord", "property mgmt", "hoa", "leasing",
                 "campus edge", "apartment", "apartments", "realty", "property mgmt",
                 "leasing office", "resident portal"]),
    ("Utilities", ["electric", "pg&e", "con edison", "comcast", "xfinity", "verizon",
                   "at&t", "t-mobile", "spectrum", "water dept", "gas company",
                   "utility", "sewer", "internet", "google fiber"]),
    ("Streaming", ["netflix", "hulu", "disney", "disney+", "hbo", "max.com", "peacock",
                   "spotify", "apple music", "youtube premium", "youtubepremium",
                   "paramount", "espn+", "sling", "audible", "pandora", "tidal",
                   "crunchyroll", "apple tv", "prime video"]),
    ("Software & Apps", ["adobe", "microsoft", "msft", "dropbox", "google storage",
                         "google one", "icloud", "1password", "notion", "github",
                         "openai", "chatgpt", "canva", "evernote", "lastpass",
                         "norton", "mcafee", "vpn", "nordvpn", "expressvpn",
                         "patreon", "substack", "linkedin premium", "zoom.us"]),
    ("Health & Fitness", ["gym", "fitness", "planet fit", "equinox", "peloton",
                          "crossfit", "yoga", "pharmacy", "cvs", "walgreens",
                          "doctor", "dental", "clinic", "hospital", "medical",
                          "classpass", "lifetime fit", "24 hour fit"]),
    ("Insurance", ["insurance", "geico", "progressive", "state farm", "allstate",
                   "policy", "premium", "metlife", "aetna", "blue cross", "humana"]),
    ("Groceries", ["grocery", "safeway", "kroger", "trader joe", "whole foods",
                   "aldi", "costco", "wal-mart", "walmart", "target", "publix",
                   "wegmans", "h-e-b", "heb ", "food lion", "sprouts", "instacart"]),
    ("Coffee", ["starbucks", "dunkin", "peet", "blue bottle", "philz", "coffee",
                "cafe", "caribou", "espresso"]),
    ("Food Delivery", ["doordash", "uber eats", "ubereats", "grubhub", "postmates",
                       "seamless", "caviar", "deliveroo", "gopuff"]),
    ("Restaurants", ["restaurant", "grill", "pizza", "sushi", "taco", "burger",
                     "kitchen", "bar &", "diner", "bistro", "chipotle", "mcdonald",
                     "wendy", "chick-fil", "panera", "subway", "kfc", "popeyes",
                     "thai", "ramen", "bbq", "steak"]),
    ("Rideshare", ["uber", "lyft", "uber trip"]),
    ("Transport & Gas", ["shell", "chevron", "exxon", "bp ", "arco", "gas station",
                         "fuel", "76 ", "valero", "marathon", "parking", "toll",
                         "metro", "transit", "mta", "bart", "caltrain", "amtrak",
                         "ev charging", "chargepoint", "tesla supercharg"]),
    ("Travel", ["airlines", "airline", "delta air", "united air", "american air",
                "southwest", "hotel", "marriott", "hilton", "airbnb", "vrbo",
                "expedia", "booking.com", "hertz", "enterprise rent", "tripadvisor"]),
    ("Shopping", ["amazon", "amzn", "ebay", "etsy", "best buy", "ikea", "home depot",
                  "lowe's", "macy", "nordstrom", "nike", "apple store", "wayfair",
                  "shein", "temu", "zara", "h&m", "sephora", "ulta"]),
    ("Entertainment", ["cinema", "movie", "amc ", "regal", "fandango", "ticketmaster",
                       "stubhub", "steam games", "playstation", "xbox", "nintendo",
                       "concert", "theater", "museum"]),
    ("Kids", ["daycare", "childcare", "school tuition", "kindercare", "babysit"]),
    ("Pets", ["petco", "petsmart", "chewy", "veterinar", "vet clinic", "pet "]),
    ("Cash & ATM", ["atm withdrawal", "cash withdrawal", "atm cash", "withdrawal atm"]),
    ("Taxes", ["irs ", "franchise tax", "tax payment", "dept of revenue"]),
]

# Categories that represent "service subscriptions" — used to flag redundancy
# (e.g. two streaming services) and to summarize recurring spend.
SUBSCRIPTION_CATEGORIES = {"Streaming", "Software & Apps", "Health & Fitness"}

# Categories excluded from "spending" totals (they're not consumption).
NON_SPENDING_CATEGORIES = {"Income", "Transfers"}

# Categories considered avoidable / low-value-per-dollar for the waste finder.
WASTE_PRONE_CATEGORIES = {"Coffee", "Food Delivery", "Fees & Interest"}


# --------------------------------------------------------------------------- #
# Intake checklist — what MoneyMan wants in order to give you the full picture.
# The more of this you provide, the better the insights and the payoff plan.
# Each item is detected from your data in intake.py.
# --------------------------------------------------------------------------- #
CHECKLIST = [
    {"key": "months", "label": "At least 3 months of history (6–12 is best)",
     "why": "Trends, recurring charges and price changes need time to show up.",
     "required": True},
    {"key": "income", "label": "Your income / pay",
     "why": "We can't tell what's 'left over' without knowing what comes in.",
     "required": True},
    {"key": "checking", "label": "Checking account statement(s)",
     "why": "Your day-to-day money in and out.", "required": True},
    {"key": "savings", "label": "Savings account statement(s)",
     "why": "So savings transfers aren't mistaken for spending.", "required": False},
    {"key": "credit_cards", "label": "All credit-card statements",
     "why": "Where most high-interest debt and hidden subscriptions live.",
     "required": True},
    {"key": "loans", "label": "Loan statements (car, student, personal)",
     "why": "Needed to build your payoff plan and total interest.",
     "required": False},
    {"key": "housing", "label": "Rent or mortgage",
     "why": "Usually the biggest fixed cost.", "required": True},
    {"key": "utilities", "label": "Household bills: power, gas, water, internet",
     "why": "Recurring essentials that affect your true monthly need.",
     "required": True},
    {"key": "insurance", "label": "Insurance: auto, home, health, life",
     "why": "Often overlooked recurring cost; sometimes overpaid.",
     "required": False},
]

# Gating: how much is needed before a section becomes meaningful.
MIN_MONTHS_FOR_TRENDS = 3
MIN_MONTHS_FOR_PRICE_CREEP = 4


def load_user_rules(paths: Paths) -> list[tuple[str, list[str]]]:
    """Merge user-defined rules (config/categories.json) ahead of defaults."""
    rules = list(DEFAULT_CATEGORY_RULES)
    f = paths.config / "categories.json"
    if f.exists():
        try:
            user = json.loads(f.read_text(encoding="utf-8"))
            # user format: {"Category": ["keyword", ...], ...}; checked first.
            # Skip helper keys (starting with "_") and any non-list values so a
            # stray string can't be exploded into single-character keywords.
            extra = [(cat, [str(k).lower() for k in kws])
                     for cat, kws in user.items()
                     if not cat.startswith("_") and isinstance(kws, list)]
            rules = extra + rules
        except Exception:
            pass  # malformed user file is ignored — never crash on bad config
    return rules


def write_default_user_config(paths: Paths) -> None:
    """Drop a starter categories.json so non-technical users can tweak rules."""
    f = paths.config / "categories.json"
    if not f.exists():
        sample = {
            "_README": "Add your own merchant keywords. Example below puts any "
                       "transaction containing 'joes diner' into 'Restaurants'.",
            "Restaurants": ["joes diner"],
        }
        f.write_text(json.dumps(sample, indent=2), encoding="utf-8")
