const API = (import.meta as any).env?.VITE_API_URL || ""

export interface Strategy {
  id: string
  name: string
  family: string
  description: string
  params: Record<string, unknown>
}

export interface BacktestResult {
  equity_curve: { date: string; equity: number }[]
  metrics: {
    total_return: number
    cagr: number
    sharpe: number
    max_drawdown: number
    n_bars: number
    final_equity: number
  }
  trades: Record<string, unknown>[]
  info: {
    strategy: string
    tickers: string[]
    params: Record<string, unknown>
    n_trades: number
  }
}

export async function fetchStrategies(): Promise<Strategy[]> {
  const r = await fetch(`${API}/api/strategies`)
  if (!r.ok) throw new Error("failed to fetch strategies")
  return r.json()
}

export async function fetchTickers(): Promise<string[]> {
  const r = await fetch(`${API}/api/tickers`)
  if (!r.ok) throw new Error("failed to fetch tickers")
  return r.json()
}

export async function fetchFamilies(): Promise<{ name: string; count: number }[]> {
  const r = await fetch(`${API}/api/families`)
  if (!r.ok) throw new Error("failed to fetch families")
  return r.json()
}

export async function runBacktest(
  strategy_id: string,
  tickers: string[],
  period: string,
  params: Record<string, unknown> | null
): Promise<BacktestResult> {
  const r = await fetch(`${API}/api/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy_id, tickers, period, params }),
  })
  if (!r.ok) {
    const txt = await r.text()
    throw new Error(txt || r.statusText)
  }
  return r.json()
}

export interface Signal {
  strategy_id: string
  ticker: string
  signal: "long" | "short" | "flat"
  strength: number
}

export interface SignalsResponse {
  as_of: string
  signals: Signal[]
}

export async function fetchSignals(tickers?: string[]): Promise<SignalsResponse> {
  const qs = tickers ? `?tickers=${tickers.join(",")}` : ""
  const r = await fetch(`${API}/api/signals${qs}`)
  if (!r.ok) throw new Error("failed to fetch signals")
  return r.json()
}

export interface PaperPosition {
  shares: number
  avg_cost: number
  last_price: number
  market_value: number
  unrealized_pnl: number
}

export interface PaperState {
  cash: number
  positions_value: number
  equity: number
  n_positions: number
  daily_pnl: number
  total_pnl: number
  positions: Record<string, PaperPosition>
}

export async function fetchPaperState(): Promise<PaperState> {
  const r = await fetch(`${API}/api/paper/state`)
  if (!r.ok) throw new Error("failed to fetch paper state")
  return r.json()
}

export async function paperOrder(ticker: string, side: "buy" | "sell", qty: number, price?: number) {
  const qs = new URLSearchParams({ ticker, side, qty: String(qty) })
  if (price) qs.append("price", String(price))
  const r = await fetch(`${API}/api/paper/order?${qs}`, { method: "POST" })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function paperRebalance(strategy_id: string, tickers?: string[]) {
  const r = await fetch(`${API}/api/paper/rebalance`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy_id, tickers }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
