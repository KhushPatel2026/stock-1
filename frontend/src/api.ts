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
