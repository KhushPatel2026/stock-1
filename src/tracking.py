"""Track strategy usage + runs for personalization insights."""
from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterator


DEFAULT_DB = "data/paper.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id TEXT NOT NULL,
    tickers TEXT NOT NULL,
    period TEXT NOT NULL,
    capital REAL NOT NULL,
    sharpe REAL,
    total_return REAL,
    max_dd REAL,
    n_trades INTEGER,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_strategy_runs_strategy ON strategy_runs(strategy_id, created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn(db_path: str) -> Iterator[sqlite3.Connection]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection):
    conn.executescript(SCHEMA)


def log_strategy_run(strategy_id: str, tickers: list[str], period: str,
                     capital: float, metrics: dict,
                     db_path: str = DEFAULT_DB) -> int:
    """Insert into strategy_runs. Returns row id."""
    ts = _now()
    with _conn(db_path) as conn:
        _ensure_schema(conn)
        cur = conn.execute(
            "INSERT INTO strategy_runs "
            "(strategy_id, tickers, period, capital, sharpe, total_return, max_dd, n_trades, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                strategy_id,
                json.dumps(list(tickers)),
                period,
                float(capital),
                metrics.get("sharpe"),
                metrics.get("total_return"),
                metrics.get("max_drawdown"),
                metrics.get("n_trades"),
                ts,
            ),
        )
        return int(cur.lastrowid)


def log_strategy_selection(strategy_id: str, db_path: str = DEFAULT_DB) -> None:
    """When user adds a strategy to their selection in UI. Stored as a strategy_runs row with period='selection'.

    ponytail: piggyback on strategy_runs — keeps schema minimal, count() works for usage stats.
    """
    ts = _now()
    with _conn(db_path) as conn:
        _ensure_schema(conn)
        conn.execute(
            "INSERT INTO strategy_runs "
            "(strategy_id, tickers, period, capital, n_trades, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (strategy_id, "[]", "selection", 0.0, -1, ts),
        )


def get_most_used_strategies(limit: int = 10,
                             db_path: str = DEFAULT_DB) -> list[dict]:
    """Top strategies by usage count (selections + runs) in last 30 days."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    with _conn(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT strategy_id, COUNT(*) AS cnt, MAX(created_at) AS last_used "
            "FROM strategy_runs WHERE created_at >= ? "
            "GROUP BY strategy_id "
            "ORDER BY cnt DESC, last_used DESC LIMIT ?",
            (cutoff, int(limit)),
        ).fetchall()
        return [
            {"strategy_id": r["strategy_id"], "count": int(r["cnt"]),
             "last_used": r["last_used"]}
            for r in rows
        ]


def get_recent_runs(limit: int = 20, db_path: str = DEFAULT_DB) -> list[dict]:
    """Recent strategy_runs rows. tickers deserialized from JSON."""
    with _conn(db_path) as conn:
        _ensure_schema(conn)
        rows = conn.execute(
            "SELECT id, strategy_id, tickers, period, capital, sharpe, "
            "total_return, max_dd, n_trades, created_at "
            "FROM strategy_runs ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        out: list[dict] = []
        for r in rows:
            d = dict(r)
            try:
                d["tickers"] = json.loads(d["tickers"])
            except Exception:
                pass
            out.append(d)
        return out
