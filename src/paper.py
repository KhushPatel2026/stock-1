"""Paper trading broker — SQLite persistence, mark-to-market, slippage, multi-portfolio."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    capital REAL NOT NULL DEFAULT 1000000,
    cash REAL NOT NULL DEFAULT 1000000,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    shares INTEGER NOT NULL,
    avg_cost REAL NOT NULL,
    opened_at TEXT NOT NULL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    UNIQUE(portfolio_id, ticker)
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    ticker TEXT NOT NULL,
    side TEXT NOT NULL,
    qty INTEGER NOT NULL,
    price REAL NOT NULL,
    fill_price REAL NOT NULL,
    strategy_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

CREATE TABLE IF NOT EXISTS pnl_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    ts TEXT NOT NULL,
    equity REAL NOT NULL,
    cash REAL NOT NULL,
    positions_value REAL NOT NULL,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

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

CREATE INDEX IF NOT EXISTS idx_trades_portfolio ON trades(portfolio_id, created_at);
CREATE INDEX IF NOT EXISTS idx_strategy_runs_strategy ON strategy_runs(strategy_id, created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PaperBroker:
    """Long-only paper broker. SQLite-backed. One broker = one named portfolio."""

    def __init__(self, name: str = "default", db_path: str = "data/paper.db",
                 capital: float = 1_000_000, slippage_bps: float = 5,
                 state_path: str | None = None):
        self.name = name
        if state_path and (db_path == "data/paper.db" or not db_path):
            db_path = str(Path(state_path).with_suffix(".db"))
        self.db_path = db_path
        self.capital = float(capital)
        self.slippage_bps = float(slippage_bps)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)
            row = conn.execute(
                "SELECT id, capital FROM portfolios WHERE name = ?", (self.name,)
            ).fetchone()
            now = _now()
            if row is None:
                conn.execute(
                    "INSERT INTO portfolios (name, capital, cash, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (self.name, self.capital, self.capital, now, now),
                )
            else:
                self.capital = float(row["capital"])

    def _portfolio_id(self, conn: sqlite3.Connection) -> int:
        row = conn.execute(
            "SELECT id FROM portfolios WHERE name = ?", (self.name,)
        ).fetchone()
        if row is None:
            raise RuntimeError(f"portfolio {self.name!r} missing — _init_db should have created it")
        return int(row["id"])

    def get_state(self, prices: dict[str, float] | None = None) -> dict:
        """Mark to market. prices optional; missing tickers marked at avg_cost."""
        prices = prices or {}
        with self._conn() as conn:
            pid = self._portfolio_id(conn)
            port = conn.execute(
                "SELECT cash, capital FROM portfolios WHERE id = ?", (pid,)
            ).fetchone()
            cash = float(port["cash"])
            capital = float(port["capital"])
            pos_rows = conn.execute(
                "SELECT ticker, shares, avg_cost FROM positions WHERE portfolio_id = ?",
                (pid,),
            ).fetchall()

            positions: dict[str, dict] = {}
            positions_value = 0.0
            for r in pos_rows:
                ticker = r["ticker"]
                shares = int(r["shares"])
                avg_cost = float(r["avg_cost"])
                last_price = float(prices.get(ticker, avg_cost))
                mv = last_price * shares
                positions_value += mv
                positions[ticker] = {
                    "shares": shares,
                    "avg_cost": round(avg_cost, 4),
                    "last_price": round(last_price, 4),
                    "market_value": round(mv, 2),
                    "unrealized_pnl": round(mv - avg_cost * shares, 2),
                }
            equity = cash + positions_value
            return {
                "cash": round(cash, 2),
                "positions_value": round(positions_value, 2),
                "equity": round(equity, 2),
                "n_positions": len(pos_rows),
                "total_pnl": round(equity - capital, 2),
                "positions": positions,
            }

    def mark_to_market(self, prices: dict[str, float] | None = None) -> dict:
        """Alias for get_state() that adds daily_pnl (vs latest pnl_snapshot). Kept for api/main.py."""
        state = self.get_state(prices)
        with self._conn() as conn:
            pid = self._portfolio_id(conn)
            last = conn.execute(
                "SELECT equity FROM pnl_snapshots WHERE portfolio_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (pid,),
            ).fetchone()
        prev_eq = float(last["equity"]) if last else None
        state["daily_pnl"] = 0.0 if prev_eq is None else round(state["equity"] - prev_eq, 2)
        return state

    def place_order(self, ticker: str, side: str, qty: int, price: float,
                    strategy_id: str | None = None) -> dict:
        if qty <= 0:
            raise ValueError(f"qty must be > 0, got {qty}")
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {side}")

        slip = self.slippage_bps / 10_000
        ts = _now()
        result: dict = {
            "ticker": ticker, "side": side, "qty": int(qty),
            "ref_price": float(price), "fill_price": 0.0, "notional": 0.0,
            "filled": 0, "reason": "", "ts": ts, "strategy_id": strategy_id,
        }

        with self._conn() as conn:
            pid = self._portfolio_id(conn)
            cash = float(conn.execute(
                "SELECT cash FROM portfolios WHERE id = ?", (pid,)
            ).fetchone()["cash"])
            pos = conn.execute(
                "SELECT id, shares, avg_cost FROM positions "
                "WHERE portfolio_id = ? AND ticker = ?",
                (pid, ticker),
            ).fetchone()

            if side == "buy":
                fill_price = float(price) * (1 + slip)
                cost_per = fill_price if fill_price > 0 else 0.0
                max_qty = int(cash / cost_per) if cost_per > 0 else 0
                buy_qty = int(qty)
                if buy_qty > max_qty:
                    if max_qty <= 0:
                        result.update({"fill_price": fill_price, "reason": "insufficient cash"})
                        conn.execute(
                            "INSERT INTO trades (portfolio_id, ticker, side, qty, price, "
                            "fill_price, strategy_id, created_at) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (pid, ticker, side, buy_qty, float(price), fill_price,
                             strategy_id, ts),
                        )
                        conn.execute(
                            "UPDATE portfolios SET updated_at = ? WHERE id = ?", (ts, pid)
                        )
                        return result
                    buy_qty = max_qty
                cost = fill_price * buy_qty
                conn.execute(
                    "UPDATE portfolios SET cash = ?, updated_at = ? WHERE id = ?",
                    (cash - cost, ts, pid),
                )
                if pos is None:
                    conn.execute(
                        "INSERT INTO positions (portfolio_id, ticker, shares, avg_cost, opened_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (pid, ticker, buy_qty, fill_price, ts),
                    )
                else:
                    old_shares = int(pos["shares"])
                    old_avg = float(pos["avg_cost"])
                    new_shares = old_shares + buy_qty
                    new_avg = ((old_avg * old_shares) + fill_price * buy_qty) / new_shares \
                        if new_shares > 0 else 0.0
                    conn.execute(
                        "UPDATE positions SET shares = ?, avg_cost = ? WHERE id = ?",
                        (new_shares, new_avg, pos["id"]),
                    )
                result.update({
                    "filled": buy_qty, "fill_price": fill_price,
                    "notional": round(cost, 2),
                })
            else:  # sell
                fill_price = float(price) * (1 - slip)
                if pos is None or int(pos["shares"]) <= 0:
                    result.update({"fill_price": fill_price, "reason": "no position"})
                    conn.execute(
                        "INSERT INTO trades (portfolio_id, ticker, side, qty, price, "
                        "fill_price, strategy_id, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (pid, ticker, side, int(qty), float(price), fill_price,
                         strategy_id, ts),
                    )
                    conn.execute(
                        "UPDATE portfolios SET updated_at = ? WHERE id = ?", (ts, pid)
                    )
                    return result
                sell_qty = min(int(qty), int(pos["shares"]))
                proceeds = fill_price * sell_qty
                conn.execute(
                    "UPDATE portfolios SET cash = ?, updated_at = ? WHERE id = ?",
                    (cash + proceeds, ts, pid),
                )
                new_shares = int(pos["shares"]) - sell_qty
                if new_shares <= 0:
                    conn.execute("DELETE FROM positions WHERE id = ?", (pos["id"],))
                else:
                    conn.execute(
                        "UPDATE positions SET shares = ? WHERE id = ?",
                        (new_shares, pos["id"]),
                    )
                result.update({
                    "filled": sell_qty, "fill_price": fill_price,
                    "notional": round(proceeds, 2),
                })

            conn.execute(
                "INSERT INTO trades (portfolio_id, ticker, side, qty, price, "
                "fill_price, strategy_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, ticker, side, int(qty), float(price),
                 float(result["fill_price"]), strategy_id, ts),
            )
            return result

    def rebalance_to_targets(self, targets: dict[str, float], prices: dict[str, float],
                             strategy_id: str | None = None) -> dict:
        """targets: {ticker: weight 0..1}. Long-only. Sells first, then buys."""
        if not prices:
            return {"trades": [], "n_trades": 0, "note": "no prices"}

        state = self.get_state(prices)
        eq = state["equity"]
        desired: dict[str, int] = {}
        for t, w in targets.items():
            if w <= 0 or t not in prices:
                continue
            px = float(prices[t])
            if px <= 0:
                continue
            sh = int((eq * w) / px)
            if sh > 0:
                desired[t] = sh

        trades: list[dict] = []
        for t in list(state["positions"].keys()):
            cur = int(state["positions"][t]["shares"])
            tgt = desired.get(t, 0)
            p = float(prices.get(t, state["positions"][t]["avg_cost"]))
            sell_qty = 0
            if tgt > 0 and cur > tgt:
                sell_qty = cur - tgt
            elif tgt <= 0 and cur > 0:
                sell_qty = cur
            if sell_qty > 0:
                r = self.place_order(t, "sell", int(sell_qty), p, strategy_id=strategy_id)
                trades.append({"ticker": t, "side": "sell", "qty": int(sell_qty), "result": r})

        # re-read state after sells (positions + cash changed)
        state = self.get_state(prices)

        for t, tgt in desired.items():
            cur = int(state["positions"].get(t, {}).get("shares", 0))
            if tgt > cur:
                buy_qty = tgt - cur
                p = float(prices[t])
                r = self.place_order(t, "buy", int(buy_qty), p, strategy_id=strategy_id)
                trades.append({"ticker": t, "side": "buy", "qty": int(buy_qty), "result": r})

        return {"trades": trades, "n_trades": len(trades)}

    def snapshot_pnl(self, prices: dict[str, float]) -> dict:
        """Insert pnl_snapshot row, return current state."""
        state = self.get_state(prices)
        with self._conn() as conn:
            pid = self._portfolio_id(conn)
            conn.execute(
                "INSERT INTO pnl_snapshots (portfolio_id, ts, equity, cash, positions_value) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, _now(), state["equity"], state["cash"], state["positions_value"]),
            )
        return state

    def list_trades(self, limit: int = 100) -> list[dict]:
        with self._conn() as conn:
            pid = self._portfolio_id(conn)
            rows = conn.execute(
                "SELECT id, ticker, side, qty, price, fill_price, strategy_id, created_at "
                "FROM trades WHERE portfolio_id = ? ORDER BY id DESC LIMIT ?",
                (pid, int(limit)),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_portfolios(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, name, capital, cash, created_at, updated_at "
                "FROM portfolios ORDER BY id"
            ).fetchall()
            out: list[dict] = []
            for r in rows:
                pv = float(conn.execute(
                    "SELECT COALESCE(SUM(shares * avg_cost), 0) FROM positions "
                    "WHERE portfolio_id = ?",
                    (r["id"],),
                ).fetchone()[0])
                equity = float(r["cash"]) + pv
                out.append({
                    "id": int(r["id"]),
                    "name": r["name"],
                    "capital": float(r["capital"]),
                    "cash": float(r["cash"]),
                    "positions_value": round(pv, 2),
                    "equity": round(equity, 2),
                    "total_pnl": round(equity - float(r["capital"]), 2),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                })
            return out

    def reset(self):
        with self._conn() as conn:
            pid = self._portfolio_id(conn)
            conn.execute("DELETE FROM trades WHERE portfolio_id = ?", (pid,))
            conn.execute("DELETE FROM positions WHERE portfolio_id = ?", (pid,))
            conn.execute("DELETE FROM pnl_snapshots WHERE portfolio_id = ?", (pid,))
            conn.execute(
                "UPDATE portfolios SET cash = capital, updated_at = ? WHERE id = ?",
                (_now(), pid),
            )
