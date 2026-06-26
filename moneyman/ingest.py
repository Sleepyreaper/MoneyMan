"""Reading bank/credit-card statement files from the Statements folder.

Supported out of the box (no extra software):
    * .csv  — almost every bank/card lets you "Download as CSV/Excel"
    * .ofx / .qfx — the "Quicken"/"Money" download format (best accuracy: it
      carries a unique transaction id, so de-duplication is exact)
    * .txt — treated as CSV

PDF statements are detected and reported, but parsing them reliably needs an
extra library. MoneyMan stays dependency-free, so it will tell the user to use
the CSV/OFX export instead (every major bank offers one).
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from .model import Txn, clean_merchant

SUPPORTED = (".csv", ".txt", ".ofx", ".qfx")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _account_name(file: Path, statements_root: Path) -> str:
    """Account = the sub-folder under Statements/, else the file's own name."""
    try:
        rel = file.relative_to(statements_root)
    except ValueError:
        rel = Path(file.name)
    if len(rel.parts) > 1:
        return rel.parts[0]
    # No sub-folder: derive from filename, dropping trailing dates/numbers.
    stem = re.sub(r"[-_ ]*\d[\d\-_ ]*$", "", file.stem).strip(" -_")
    return stem or file.stem


def _parse_amount(text: str) -> float | None:
    """Parse '$1,234.56', '(45.00)', '-12.30', '12.30 CR' into a signed float."""
    if text is None:
        return None
    t = text.strip()
    if not t:
        return None
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
    up = t.upper()
    if up.endswith("CR"):
        t = t[:-2]
    elif up.endswith("DR") or up.endswith("DB"):
        neg, t = True, t[:-2]
    t = t.replace("$", "").replace(",", "").replace(" ", "")
    if t.startswith("-"):
        neg, t = True, t[1:]
    if not t:
        return None
    try:
        val = float(t)
    except ValueError:
        return None
    return -val if neg else val


_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%m-%d-%Y",
                 "%Y/%m/%d", "%d-%b-%Y", "%b %d %Y", "%m/%d/%Y %H:%M",
                 "%Y%m%d", "%d.%m.%Y")


def _parse_date(text: str) -> str | None:
    if not text:
        return None
    t = text.strip().strip('"')
    # OFX dates look like 20240115120000[-8:PST]
    m = re.match(r"^(\d{8})", t)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d").date().isoformat()
        except ValueError:
            pass
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(t, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _find(header: list[str], *candidates: str) -> int | None:
    low = [h.strip().lower() for h in header]
    for cand in candidates:
        for i, h in enumerate(low):
            if h == cand:
                return i
    for cand in candidates:                       # fall back to "contains"
        for i, h in enumerate(low):
            if cand in h:
                return i
    return None


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def parse_csv(file: Path, account: str) -> tuple[list[Txn], list[str]]:
    warnings: list[str] = []
    text = file.read_text(encoding="utf-8-sig", errors="replace")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return [], [f"{file.name}: empty file"]

    # Find the header row (first row that names a date and an amount-ish column).
    header_idx = 0
    for i, r in enumerate(rows[:5]):
        joined = ",".join(c.lower() for c in r)
        if ("date" in joined) and any(k in joined for k in
                                      ("amount", "debit", "credit", "withdraw",
                                       "deposit", "amt")):
            header_idx = i
            break
    header = rows[header_idx]
    body = rows[header_idx + 1:]

    i_date = _find(header, "date", "transaction date", "posted date",
                   "posting date", "trans date", "date posted")
    i_desc = _find(header, "original statement", "description", "memo", "details",
                   "notes", "narrative", "transaction", "payee", "name")
    i_merchant = _find(header, "merchant")        # Monarch/Copilot pre-clean these
    i_acct_col = _find(header, "account")         # per-row account (Monarch export)
    i_category = _find(header, "category")        # export's own category, if any
    i_amt = _find(header, "amount", "amt", "transaction amount")
    i_debit = _find(header, "debit", "withdrawal", "withdrawals", "money out",
                    "paid out", "outflow")
    i_credit = _find(header, "credit", "deposit", "deposits", "money in",
                     "paid in", "inflow")
    i_type = _find(header, "transaction type", "type", "dr/cr", "debit/credit")

    if i_date is None or (i_amt is None and i_debit is None and i_credit is None):
        return [], [f"{file.name}: couldn't recognize columns "
                    f"(found header: {header}). Skipped."]

    seen: Counter = Counter()
    txns: list[Txn] = []
    skipped = 0
    for r in body:
        if not r or all(not c.strip() for c in r):
            continue

        def cell(idx):
            return r[idx].strip() if (idx is not None and idx < len(r)) else ""

        date = _parse_date(cell(i_date))
        if not date:
            skipped += 1
            continue

        if i_amt is not None:
            amount = _parse_amount(cell(i_amt))
        else:
            deb = _parse_amount(cell(i_debit)) or 0.0
            cre = _parse_amount(cell(i_credit)) or 0.0
            amount = cre - abs(deb)
        if amount is None:
            skipped += 1
            continue

        # Respect an explicit Debit/Credit type column when amounts are unsigned.
        ttype = cell(i_type).lower()
        if ttype and amount > 0:
            if ttype.startswith("d") and "credit" not in ttype:   # debit/dr
                amount = -amount

        raw = cell(i_desc) or cell(i_merchant) or "(no description)"
        # Trust a pre-cleaned Merchant column (Monarch/Copilot); else clean it.
        mcell = cell(i_merchant)
        merchant = mcell if mcell else clean_merchant(raw)
        acct = cell(i_acct_col) or account
        key = (date, round(amount, 2), merchant)
        seen[key] += 1
        txns.append(Txn(account=acct, date=date, amount=round(amount, 2),
                        raw_description=raw, source_file=file.name,
                        merchant=merchant, source_category=cell(i_category),
                        occ=seen[key]))

    if skipped:
        warnings.append(f"{file.name}: skipped {skipped} unparseable row(s).")
    return txns, warnings


# --------------------------------------------------------------------------- #
# OFX / QFX  (tolerant of both SGML 1.x and XML 2.x variants)
# --------------------------------------------------------------------------- #
_TRN_SPLIT = re.compile(r"<STMTTRN>", re.IGNORECASE)
_TRN_END = re.compile(r"</STMTTRN>|<STMTTRN>|</BANKTRANLIST>", re.IGNORECASE)


def _ofx_tag(block: str, tag: str) -> str:
    # Handles both "<TAG>value" (SGML 1.x) and "<TAG>value</TAG>" (XML 2.x).
    m = re.search(rf"<{tag}>([^<\r\n]*)", block, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _ofx_blocks(text: str) -> list[str]:
    """Extract each <STMTTRN> record. Tolerant of OFX 1.x (no closing tags)."""
    chunks = _TRN_SPLIT.split(text)[1:]
    return [_TRN_END.split(c)[0] for c in chunks]


def parse_ofx(file: Path, account: str) -> tuple[list[Txn], list[str]]:
    text = file.read_text(encoding="utf-8", errors="replace")
    blocks = _ofx_blocks(text)
    if not blocks:
        return [], [f"{file.name}: no transactions found in OFX/QFX."]
    txns: list[Txn] = []
    seen: Counter = Counter()
    for b in blocks:
        date = _parse_date(_ofx_tag(b, "DTPOSTED"))
        amount = _parse_amount(_ofx_tag(b, "TRNAMT"))
        if not date or amount is None:
            continue
        name = _ofx_tag(b, "NAME")
        memo = _ofx_tag(b, "MEMO")
        raw = (name + (" " + memo if memo and memo != name else "")).strip() or "(no description)"
        fitid = _ofx_tag(b, "FITID") or None
        merchant = clean_merchant(raw)
        key = (date, round(amount, 2), merchant)
        seen[key] += 1
        txns.append(Txn(account=account, date=date, amount=round(amount, 2),
                        raw_description=raw, source_file=file.name,
                        fitid=fitid, merchant=merchant, occ=seen[key]))
    return txns, []


# --------------------------------------------------------------------------- #
# Account-balance files (e.g. Monarch "Balances" export: Date, Balance, Account)
# --------------------------------------------------------------------------- #
def _looks_like_balances(header: list[str]) -> bool:
    low = [h.strip().lower() for h in header]
    return ("balance" in low and "account" in low
            and not any(k in low for k in ("amount", "merchant",
                                           "original statement", "debit", "credit")))


def parse_balances(file: Path) -> list[tuple[str, str, float]]:
    """Return (date, account, balance) rows from a balances time-series CSV."""
    text = file.read_text(encoding="utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return []
    header = rows[0]
    i_date = _find(header, "date")
    i_bal = _find(header, "balance")
    i_acct = _find(header, "account")
    if None in (i_date, i_bal, i_acct):
        return []
    out: list[tuple[str, str, float]] = []
    for r in rows[1:]:
        if max(i_date, i_bal, i_acct) >= len(r):
            continue
        d = _parse_date(r[i_date])
        bal = _parse_amount(r[i_bal])
        acct = r[i_acct].strip()
        if d and bal is not None and acct:
            out.append((d, acct, round(bal, 2)))
    return out


def _csv_header(file: Path) -> list[str]:
    try:
        with file.open(encoding="utf-8-sig", errors="replace", newline="") as f:
            return next(csv.reader(f), [])
    except Exception:
        return []


# --------------------------------------------------------------------------- #
# Folder scan
# --------------------------------------------------------------------------- #
def discover(statements_root: Path) -> list[Path]:
    if not statements_root.exists():
        return []
    return sorted(p for p in statements_root.rglob("*")
                  if p.is_file() and p.suffix.lower() in SUPPORTED + (".pdf",))


def ingest_folder(statements_root: Path):
    """Parse every supported file.

    Returns (transactions, warnings, stats, statement_metas, balances) where
    statement_metas are structured summaries from PDF statements and balances is
    the (date, account, balance) time-series from any balances export.
    """
    from . import pdf                              # local import (optional dep)

    all_txns: list[Txn] = []
    warnings: list[str] = []
    metas = []
    balances: list[tuple[str, str, float]] = []
    stats = {"files": 0, "pdf": 0, "balances": 0, "by_file": {}}
    for f in discover(statements_root):
        account = _account_name(f, statements_root)
        ext = f.suffix.lower()
        try:
            if ext == ".pdf":
                txns, meta, w = pdf.parse_pdf(f, account)
                stats["pdf"] += 1
                if meta is not None:
                    metas.append(meta)
            elif ext in (".ofx", ".qfx"):
                txns, w = parse_ofx(f, account)
            elif ext in (".csv", ".txt") and _looks_like_balances(_csv_header(f)):
                rows = parse_balances(f)
                balances.extend(rows)
                stats["balances"] += 1
                stats["files"] += 1
                stats["by_file"][f.name] = f"{len(rows)} balance rows"
                continue
            else:
                txns, w = parse_csv(f, account)
        except Exception as e:                     # never let one bad file stop us
            warnings.append(f"{f.name}: could not read ({e}).")
            continue
        stats["files"] += 1
        stats["by_file"][f.name] = len(txns)
        all_txns.extend(txns)
        warnings.extend(w)
    return all_txns, warnings, stats, metas, balances
