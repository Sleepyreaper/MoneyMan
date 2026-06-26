"""Reading PDF statements (the format most banks hand you).

Statements are usually many pages. We pull two things out of them:

  1. The numbers that drive the payoff plan — new balance, minimum payment,
     credit limit, APR, interest charged. These are printed on predictable lines
     and extract reliably.
  2. The individual transactions (best-effort). PDF layouts vary a lot between
     banks, so this is the part we tune against real examples; the report marks
     PDF-sourced transactions so you can sanity-check them.

We use pdfplumber (preferred) or pypdf — both are offline parsers. They read the
file on your disk and transmit nothing.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .model import Txn, clean_merchant

try:
    import pdfplumber                       # type: ignore
    _HAVE_PDFPLUMBER = True
except Exception:
    _HAVE_PDFPLUMBER = False
try:
    import pypdf                            # type: ignore
    _HAVE_PYPDF = True
except Exception:
    _HAVE_PYPDF = False

PDF_AVAILABLE = _HAVE_PDFPLUMBER or _HAVE_PYPDF

INSTALL_HINT = ("PDF reading needs a small offline library. Install it once with:\n"
                "    python -m pip install pdfplumber pypdf\n"
                "(or double-click Setup.bat). It reads PDFs locally and sends nothing.")


@dataclass
class StatementMeta:
    account: str
    kind: str = "bank"                      # bank | credit card | loan
    period_start: str | None = None
    period_end: str | None = None
    new_balance: float | None = None
    min_payment: float | None = None
    credit_limit: float | None = None
    apr: float | None = None
    interest_charged: float | None = None
    n_txns: int = 0
    source_file: str = ""


_MONEY = r"\(?-?\$?\s?([\d,]+\.\d{2})\)?"
_DATE = r"\d{1,2}/\d{1,2}(?:/\d{2,4})?"


def _num(s: str) -> float:
    return float(s.replace(",", "").replace("$", "").strip())


def extract_text(path: Path) -> str:
    """Return all text from the PDF, pages joined by newlines."""
    if _HAVE_PDFPLUMBER:
        try:
            with pdfplumber.open(str(path)) as pdf:
                return "\n".join((pg.extract_text() or "") for pg in pdf.pages)
        except Exception:
            pass
    if _HAVE_PYPDF:
        try:
            reader = pypdf.PdfReader(str(path))
            return "\n".join((pg.extract_text() or "") for pg in reader.pages)
        except Exception:
            pass
    return ""


def _detect_kind(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("minimum payment", "credit limit", "available credit",
                            "new balance", "annual percentage rate")):
        return "credit card"
    if any(k in t for k in ("principal balance", "escrow", "loan number",
                            "amortization", "remaining balance", "payoff amount")):
        return "loan"
    return "bank"


def _search_money(text: str, *labels: str) -> float | None:
    for label in labels:
        m = re.search(label + r"[^\n$%]*?" + _MONEY, text, re.IGNORECASE)
        if m:
            try:
                return _num(m.group(1))
            except ValueError:
                continue
    return None


def _search_apr(text: str) -> float | None:
    cands: list[float] = []
    # "annual percentage rate ... 24.99%"  and  "24.99% ... APR/annual percentage rate"
    for pat in (r"(?:annual percentage rate|apr)[^\n%]*?(\d{1,2}\.\d{1,3})\s*%",
                r"(\d{1,2}\.\d{1,3})\s*%[^\n]{0,40}?(?:annual percentage rate|apr)"):
        for m in re.finditer(pat, text, re.IGNORECASE):
            try:
                v = float(m.group(1))
                if 0 < v < 60:
                    cands.append(v)
            except ValueError:
                pass
    if not cands:
        return None
    # Prefer a rate on a line mentioning "purchase" (the one a carried balance uses).
    for line in text.splitlines():
        if "purchase" in line.lower():
            m = re.search(r"(\d{1,2}\.\d{1,3})\s*%", line)
            if m and 0 < float(m.group(1)) < 60:
                return float(m.group(1))
    return max(cands)


def parse_metadata(text: str, account: str, source_file: str) -> StatementMeta:
    kind = _detect_kind(text)
    meta = StatementMeta(account=account, kind=kind, source_file=source_file)
    meta.new_balance = _search_money(text, r"new balance", r"statement balance",
                                     r"current balance", r"principal balance",
                                     r"outstanding balance")
    meta.min_payment = _search_money(text, r"minimum payment due", r"minimum payment",
                                     r"total minimum payment", r"amount due",
                                     r"monthly payment")
    meta.credit_limit = _search_money(text, r"credit limit", r"credit line",
                                      r"total credit")
    meta.interest_charged = _search_money(text, r"interest charged", r"finance charge",
                                          r"interest charged on purchases")
    meta.apr = _search_apr(text)
    # Statement period like "Jan 5, 2026 - Feb 4, 2026" or "01/05/2026 to 02/04/2026"
    m = re.search(r"(" + _DATE + r"|\w+ \d{1,2},? \d{4})\s*(?:-|to|through|–)\s*"
                  r"(" + _DATE + r"|\w+ \d{1,2},? \d{4})", text, re.IGNORECASE)
    if m:
        meta.period_start, meta.period_end = m.group(1), m.group(2)
    return meta


_TXN_LINE = re.compile(
    r"^\s*(" + _DATE + r")\s+(?:" + _DATE + r"\s+)?(.+?)\s+" + _MONEY + r"\s*(CR)?\s*$",
    re.IGNORECASE)
_CREDIT_WORDS = ("payment", "credit", "refund", "reversal", "thank you", "autopay")


def _parse_date(text: str, year_hint: int | None) -> str | None:
    t = text.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m/%d"):
        try:
            d = datetime.strptime(t, fmt)
            if fmt == "%m/%d":
                d = d.replace(year=year_hint or datetime.now().year)
            return d.date().isoformat()
        except ValueError:
            continue
    return None


def parse_transactions(text: str, account: str, source_file: str) -> list[Txn]:
    year_hint = None
    ym = re.search(r"/(20\d{2})\b", text)
    if ym:
        year_hint = int(ym.group(1))

    txns: list[Txn] = []
    seen: Counter = Counter()
    for line in text.splitlines():
        m = _TXN_LINE.match(line)
        if not m:
            continue
        date = _parse_date(m.group(1), year_hint)
        if not date:
            continue
        desc = re.sub(r"\s{2,}", " ", m.group(2)).strip()
        if not desc or len(desc) < 2:
            continue
        try:
            value = _num(m.group(3))
        except ValueError:
            continue
        low = line.lower()
        is_credit = bool(m.group(4)) or any(w in low for w in _CREDIT_WORDS)
        # A normal statement line is money out (a purchase / charge); a payment,
        # refund, or anything tagged "CR" is money in. Same on cards and loans.
        amount = value if is_credit else -value
        merchant = clean_merchant(desc)
        key = (date, round(amount, 2), merchant)
        seen[key] += 1
        txns.append(Txn(account=account, date=date, amount=round(amount, 2),
                        raw_description=desc, source_file=source_file,
                        merchant=merchant, occ=seen[key]))
    return txns


def parse_pdf(path: Path, account: str) -> tuple[list[Txn], StatementMeta | None,
                                                 list[str]]:
    if not PDF_AVAILABLE:
        return [], None, [f"{path.name}: {INSTALL_HINT}"]
    text = extract_text(path)
    if not text.strip():
        return [], None, [f"{path.name}: no extractable text — it may be a scanned "
                          f"image. A CSV/QFX export would work better."]
    meta = parse_metadata(text, account, path.name)
    txns = parse_transactions(text, account, path.name)
    meta.n_txns = len(txns)
    warns: list[str] = []
    if meta.kind == "credit card" and meta.new_balance is None:
        warns.append(f"{path.name}: couldn't read the balance/APR automatically — "
                     f"you can type them into Accounts-and-Debts.csv.")
    return txns, meta, warns
