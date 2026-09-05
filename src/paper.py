"""Paper trading broker — mock positions, mark-to-market, JSON persistence."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone


class PaperBroker:
    def __init__(self, capital: float = 1_000_000, slippage_bps: float = 5, state_path: str = "data/paper_state.json"):
        self.capital = capital
        self.slippage_bps = slippage_bps
        self.state_path = state_path
        self.cash = capital
        self.positions: dict[str, dict] = {}
        self.trade_log: list[dict] = []
        self.last_prices: dict[str, float] = {}
        self.prev_equity: float | None = None
        self._load_state()

    def place_order(self, ticker: str, side: str, qty: int, price: float) -> dict:
        """side: 'buy' or 'sell'. Fills at price*(1+slippage) for buy, (1-slippage) for sell."""
        if qty <= 0:
            raise ValueError(f"qty must be > 0, got {qty}")
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be 'buy' or 'sell', got {side}")

        slip = self.slippage_bps / 10_000
        ts = datetime.now(timezone.utc).isoformat()
        trade: dict = {"ts": ts, "ticker": ticker, "side": side, "qty": int(qty),
                       "ref_price": float(price), "fill_price": 0.0, "notional": 0.0,
                       "filled": 0, "reason": ""}

        if side == "buy":
            fill_price = float(price) * (1 + slip)
            cost = fill_price * int(qty)
            if cost > self.cash:
                max_qty = int(self.cash / (float(price) * (1 + slip))) if float(price) * (1 + slip) > 0 else 0
                if max_qty <= 0:
                    trade.update({"filled": 0, "reason": "insufficient cash", "fill_price": fill_price})
                    self.trade_log.append(trade)
                    self._save_state()
                    return trade
                qty = max_qty
                fill_price = float(price) * (1 + slip)
                cost = fill_price * int(qty)
            self.cash -= cost
            pos = self.positions.get(ticker, {"shares": 0, "avg_cost": 0.0})
            new_shares = pos["shares"] + int(qty)
            pos["avg_cost"] = ((pos["avg_cost"] * pos["shares"]) + cost) / new_shares if new_shares > 0 else 0.0
            pos["shares"] = new_shares
            self.positions[ticker] = pos
        else:  # sell
            pos = self.positions.get(ticker)
            if not pos or pos["shares"] <= 0:
                trade.update({"filled": 0, "reason": "no position", "fill_price": float(price) * (1 - slip)})
                self.trade_log.append(trade)
                self._save_state()
                return trade
            sell_qty = min(int(qty), pos["shares"])
            if sell_qty <= 0:
                trade.update({"filled": 0, "reason": "no position"})
                self.trade_log.append(trade)
                self._save_state()
                return trade
            fill_price = float(price) * (1 - slip)
            proceeds = fill_price * sell_qty
            self.cash += proceeds
            pos["shares"] -= sell_qty
            if pos["shares"] <= 0:
                del self.positions[ticker]
            qty = sell_qty

        self.last_prices[ticker] = float(price)
        trade.update({"filled": int(qty), "fill_price": float(fill_price if side == "buy" else float(price) * (1 - slip)),
                      "notional": float((fill_price if side == "buy" else float(price) * (1 - slip)) * int(qty))})
        self.trade_log.append(trade)
        self._save_state()
        return trade

    def mark_to_market(self, prices: dict[str, float]) -> dict:
        """Mark positions to current prices; return portfolio snapshot + per-position P&L."""
        for t, p in prices.items():
            try:
                self.last_prices[t] = float(p)
            except (TypeError, ValueError):
                continue

        positions_value = 0.0
        position_pnl: dict[str, dict] = {}
        for t, pos in list(self.positions.items()):
            ref = prices.get(t, self.last_prices.get(t, pos["avg_cost"]))
            try:
                last_price = float(ref)
            except (TypeError, ValueError):
                last_price = float(pos["avg_cost"])
            mv = last_price * pos["shares"]
            cost = pos["avg_cost"] * pos["shares"]
            positions_value += mv
            position_pnl[t] = {
                "shares": pos["shares"],
                "avg_cost": round(float(pos["avg_cost"]), 4),
                "last_price": round(last_price, 4),
                "market_value": round(float(mv), 2),
                "unrealized_pnl": round(float(mv - cost), 2),
            }

        equity = self.cash + positions_value
        daily_pnl = 0.0 if self.prev_equity is None else equity - self.prev_equity
        self.prev_equity = equity
        self._save_state()

        return {
            "cash": round(float(self.cash), 2),
            "positions_value": round(float(positions_value), 2),
            "equity": round(float(equity), 2),
            "n_positions": len(self.positions),
            "daily_pnl": round(float(daily_pnl), 2),
            "total_pnl": round(float(equity - self.capital), 2),
            "positions": position_pnl,
        }

    def rebalance_to_targets(self, targets: dict[str, float], prices: dict[str, float]) -> dict:
        """targets: {ticker: weight in [0,1]}. Sell first, then buy to reach targets.

        ponytail: long-only paper broker — negative weights clamped to 0 (no short-selling).
        """
        if not prices:
            return {"trades": [], "n_trades": 0, "note": "no prices"}

        eq = self.cash + sum(
            pos["shares"] * float(prices.get(t, pos["avg_cost"]))
            for t, pos in self.positions.items()
        )

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
        # sells first
        for t in list(self.positions.keys()):
            cur = self.positions[t]["shares"]
            tgt = desired.get(t, 0)
            if cur > tgt > 0:
                sell_qty = cur - tgt
                p = float(prices.get(t, self.positions[t]["avg_cost"]))
                result = self.place_order(t, "sell", int(sell_qty), p)
                trades.append({"ticker": t, "side": "sell", "qty": int(sell_qty), "result": result})
            elif tgt <= 0 and cur > 0:
                p = float(prices.get(t, self.positions[t]["avg_cost"]))
                result = self.place_order(t, "sell", int(cur), p)
                trades.append({"ticker": t, "side": "sell", "qty": int(cur), "result": result})
        # then buys
        for t, tgt in desired.items():
            cur = self.positions.get(t, {"shares": 0})["shares"]
            if tgt > cur:
                buy_qty = tgt - cur
                p = float(prices[t])
                result = self.place_order(t, "buy", int(buy_qty), p)
                trades.append({"ticker": t, "side": "buy", "qty": int(buy_qty), "result": result})

        return {"trades": trades, "n_trades": len(trades)}

    def reset(self):
        self.cash = self.capital
        self.positions = {}
        self.trade_log = []
        self.last_prices = {}
        self.prev_equity = None
        self._save_state()

    def _save_state(self):
        try:
            p = Path(self.state_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "capital": self.capital,
                "slippage_bps": self.slippage_bps,
                "cash": self.cash,
                "positions": self.positions,
                "trade_log": self.trade_log[-500:],
                "last_prices": self.last_prices,
                "prev_equity": self.prev_equity,
            }
            p.write_text(json.dumps(state, indent=2, default=str))
        except Exception:
            pass

    def _load_state(self):
        p = Path(self.state_path)
        if not p.exists():
            return
        try:
            state = json.loads(p.read_text())
            self.capital = state.get("capital", self.capital)
            self.slippage_bps = state.get("slippage_bps", self.slippage_bps)
            self.cash = state.get("cash", self.capital)
            self.positions = state.get("positions", {})
            self.trade_log = state.get("trade_log", [])
            self.last_prices = state.get("last_prices", {})
            self.prev_equity = state.get("prev_equity")
        except Exception:
            pass
