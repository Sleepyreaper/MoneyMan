"""Local SQLite storage.  This is the ONLY place transactions are persisted —
a single file on your disk (database/moneyman.db). Nothing is uploaded anywhere.

Duplicates are handled by the transaction fingerprint (see model.Txn):
re-importing the same statement, or importing two statements whose date ranges
overlap, will not create double entries.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .model import Txn

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    txn_id          TEXT PRIMARY KEY,
    account         TEXT NOT NULL,
    date            TEXT NOT NULL,
    amount          REAL NOT NULL,
    merchant        TEXT NOT NULL,
    category        TEXT NOT NULL,
    source_category TEXT DEFAULT '',
    raw_description TEXT NOT NULL,
    source_file     TEXT NOT NULL,
    fitid           TEXT
);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_txn_merchant ON transactions(merchant);
"""


class Store:
    def __init__(self, db_file: Path):
        db_file.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        # Migrate older databases that predate a column.
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(transactions)")}
        if "source_category" not in cols:
            self.conn.execute("ALTER TABLE transactions "
                              "ADD COLUMN source_category TEXT DEFAULT ''")
            self.conn.commit()

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def upsert_many(self, txns: list[Txn]) -> tuple[int, int]:
        """Insert transactions, skipping duplicates.

        Returns (inserted, duplicates_skipped).
        """
        inserted = 0
        for t in txns:
            t.txn_id = t.fingerprint()
            cur = self.conn.execute(
                """INSERT OR IGNORE INTO transactions
                   (txn_id, account, date, amount, merchant, category,
                    source_category, raw_description, source_file, fitid)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (t.txn_id, t.account, t.date, t.amount, t.merchant, t.category,
                 t.source_category, t.raw_description, t.source_file, t.fitid))
            inserted += cur.rowcount
        self.conn.commit()
        return inserted, len(txns) - inserted

    def all_rows(self) -> list[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM transactions ORDER BY date, txn_id"))

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    def reset(self) -> None:
        self.conn.execute("DELETE FROM transactions")
        self.conn.commit()
