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

export interface TickerSearchResult {
  symbol: string
  shortname: string
  exchange: string
  quoteType: string
}

export async function searchTickers(q: string): Promise<TickerSearchResult[]> {
  if (!q) return []
  const r = await fetch(`${API}/api/tickers/search?q=${encodeURIComponent(q)}&limit=10`)
  if (!r.ok) return []
  return r.json()
}

export interface Recommendation {
  strategy_id: string
  name: string
  family: string
  oos_sharpe?: number
  total_return?: number
  max_dd?: number
  error?: string
  reason?: string
}

export async function fetchRecommendations(tickers: string[], period: string = "1y"): Promise<{
  as_of: string
  tickers: string[]
  ranked: Recommendation[]
}> {
  const r = await fetch(`${API}/api/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tickers, period }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export interface TradePlan {
  ticker: string
  decision: "BUY" | "SELL" | "HOLD"
  confidence: number
  entry: number
  stop_loss: number
  target: number
  stop_pct: number
  target_pct: number
  risk_reward: number
  timeframe: string
  timeframe_detail: string
  price: number
  atr: number
  atr_pct: number
  day_change_pct: number
  above_sma200: boolean | null
  leaders: string[]
  voter_weight_pct: number
  insight: string
  note: string
  as_of: string
  live_entry: boolean
  entry_label: string
}

export interface Decision {
  ticker: string
  decision: string
  confidence: number
  long_pct: number
  short_pct: number
  score: number
  long_strategies: string[]
  short_strategies: string[]
  n_long: number
  n_short: number
  n_flat: number
  plan?: TradePlan
}

export async function fetchDecisions(tickers: string[], period: string = "3mo"): Promise<{
  as_of: string
  tickers: string[]
  decisions: Decision[]
}> {
  const r = await fetch(`${API}/api/decisions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tickers, period }),
  })
  if (!r.ok) throw new Error(await r.text())
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
  params: Record<string, unknown> | null,
  capital: number = 1_000_000
): Promise<BacktestResult> {
  const r = await fetch(`${API}/api/backtest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy_id, tickers, period, params, capital }),
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

// === Portfolio & Upstox ===
export interface UpstoxHolding {
  ticker: string
  name: string
  quantity: number
  avg_price: number
  current_price: number | null
  invested: number
  current_value: number
  pnl: number
  pnl_pct: number
}

export interface PortfolioData {
  authenticated: boolean
  message?: string
  error?: string
  profile?: any
  holdings?: UpstoxHolding[]
  positions?: any[]
  funds?: any
  summary?: {
    n_holdings: number
    total_invested: number
    total_current: number
    total_pnl: number
    total_pnl_pct: number
  }
}

export async function fetchPortfolio(): Promise<PortfolioData> {
  const r = await fetch(`${API}/api/portfolio`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function setUpstoxToken(access_token: string): Promise<{ ok: boolean; token_length: number }> {
  const r = await fetch(`${API}/api/upstox/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchUpstoxAuthUrl(redirect_uri: string = window.location.origin + "/callback"): Promise<{ url: string; redirect_uri: string }> {
  const r = await fetch(`${API}/api/upstox/auth-url?redirect_uri=${encodeURIComponent(redirect_uri)}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function exchangeUpstoxCode(code: string, redirect_uri: string): Promise<{ ok: boolean; token_length: number }> {
  const r = await fetch(`${API}/api/upstox/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, redirect_uri }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchUpstoxStatus(): Promise<{ authenticated: boolean }> {
  const r = await fetch(`${API}/api/upstox/status`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchIndiaVix(): Promise<any> {
  const r = await fetch(`${API}/api/upstox/india-vix`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchInsightsPortfolio(): Promise<any> {
  const r = await fetch(`${API}/api/insights/portfolio`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

// === AI ===
export async function fetchAIStatus(): Promise<{ available: boolean }> {
  const r = await fetch(`${API}/api/ai/status`)
  if (!r.ok) return { available: false }
  return r.json()
}

export async function aiExplainStrategy(strategy_id: string, metrics: any, user_question = ""): Promise<{ text: string; ai_enabled: boolean }> {
  const r = await fetch(`${API}/api/ai/explain-strategy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy_id, metrics, user_question }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function aiPersonalized(): Promise<{ text: string; ai_enabled: boolean; stats: any }> {
  const r = await fetch(`${API}/api/ai/personalized`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export interface StrategyStat {
  strategy_id: string
  count: number
  last_used: string
}

export async function fetchStrategyStats(): Promise<StrategyStat[]> {
  // No dedicated endpoint — derive from recommendations or just return [] for now
  return []
}
