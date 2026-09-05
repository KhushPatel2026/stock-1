import { useEffect, useState, useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import {
  Loader2,
  RefreshCw,
  Briefcase,
  Wallet,
  TrendingUp,
  XCircle,
  AlertCircle,
  RotateCcw,
} from "lucide-react"
import { fetchPaperState, paperOrder, paperRebalance, fetchStrategies, fetchTickers } from "@/api"
import type { PaperState, Strategy } from "@/api"

interface PaperPanelProps {
  prefilledOrder?: { ticker: string; side: "buy" | "sell"; qty?: number } | null
}

export default function PaperPanel({ prefilledOrder }: PaperPanelProps) {
  const [state, setState] = useState<PaperState | null>(null)
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [tickers, setTickers] = useState<string[]>([])
  const [strategyId, setStrategyId] = useState("bollinger")
  const [orderTicker, setOrderTicker] = useState("RELIANCE.NS")
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy")
  const [orderQty, setOrderQty] = useState(10)
  const [orderPrice, setOrderPrice] = useState<number | "">("")
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null)

  // React to prefilled orders from Backtest or Signals tab
  useEffect(() => {
    if (prefilledOrder) {
      setOrderTicker(prefilledOrder.ticker)
      setOrderSide(prefilledOrder.side)
      if (prefilledOrder.qty) setOrderQty(prefilledOrder.qty)
    }
  }, [prefilledOrder])

  const refresh = async () => {
    setLoading(true)
    try {
      const s = await fetchPaperState()
      setState(s)
    } catch (e: any) {
      setMessage({ text: e.message || "Failed to load paper state", type: "error" })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    fetchStrategies().then(setStrategies).catch(() => {})
    fetchTickers().then(setTickers).catch(() => {})
    const t = setInterval(refresh, 15000)
    return () => clearInterval(t)
  }, [])

  const submitOrder = async () => {
    setMessage(null)
    setActionLoading(true)
    try {
      const r = await paperOrder(orderTicker, orderSide, orderQty, orderPrice === "" ? undefined : Number(orderPrice))
      setMessage({
        text: `Executed ${orderSide.toUpperCase()} ${orderQty} ${orderTicker} @ ₹${r.fill_price.toFixed(2)}`,
        type: "success",
      })
      await refresh()
    } catch (e: any) {
      setMessage({ text: `Execution failed: ${e.message}`, type: "error" })
    } finally {
      setActionLoading(false)
    }
  }

  const closePosition = async (ticker: string, shares: number) => {
    setMessage(null)
    setActionLoading(true)
    try {
      const r = await paperOrder(ticker, "sell", shares)
      setMessage({
        text: `Closed position: Sold ${shares} ${ticker} @ ₹${r.fill_price.toFixed(2)}`,
        type: "success",
      })
      await refresh()
    } catch (e: any) {
      setMessage({ text: `Failed to close position: ${e.message}`, type: "error" })
    } finally {
      setActionLoading(false)
    }
  }

  const doRebalance = async () => {
    setMessage(null)
    setActionLoading(true)
    try {
      const r = await paperRebalance(strategyId, tickers.slice(0, 10))
      setMessage({
        text: `Rebalanced portfolio to ${strategyId}: ${r.trades?.length ?? 0} orders executed.`,
        type: "success",
      })
      await refresh()
    } catch (e: any) {
      setMessage({ text: `Rebalance failed: ${e.message}`, type: "error" })
    } finally {
      setActionLoading(false)
    }
  }

  // Calculate allocation percentage
  const allocation = useMemo(() => {
    if (!state || state.equity <= 0) return { cashPct: 100, posPct: 0 }
    const posPct = Math.min(100, Math.max(0, (state.positions_value / state.equity) * 100))
    const cashPct = 100 - posPct
    return { cashPct, posPct }
  }, [state])

  // Quick sizing based on cash
  const applyCashPercent = (pct: number) => {
    if (!state || state.cash <= 0) return
    // Approximate share price using orderPrice or last known price from positions, or 1000 default
    const estPrice = typeof orderPrice === "number" && orderPrice > 0
      ? orderPrice
      : state.positions[orderTicker]?.last_price || 1000
    const targetValue = state.cash * (pct / 100)
    const qty = Math.max(1, Math.floor(targetValue / estPrice))
    setOrderQty(qty)
  }

  return (
    <div className="space-y-4">
      {/* PORTFOLIO SUMMARY TILES */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="border-border/70 bg-card/90 shadow-sm p-4 space-y-1">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-1">
            <Wallet className="h-3.5 w-3.5 text-primary" />
            Net Portfolio Equity
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              ₹{state ? state.equity.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "—"}
            </span>
          </div>
        </Card>

        <Card className="border-border/70 bg-card/90 shadow-sm p-4 space-y-1">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
            Available Cash
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              ₹{state ? state.cash.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "—"}
            </span>
            <span className="text-xs text-muted-foreground font-mono">({allocation.cashPct.toFixed(0)}%)</span>
          </div>
        </Card>

        <Card className="border-border/70 bg-card/90 shadow-sm p-4 space-y-1">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
            Holdings Market Value
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              ₹{state ? state.positions_value.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "—"}
            </span>
            <span className="text-xs text-muted-foreground font-mono">({allocation.posPct.toFixed(0)}%)</span>
          </div>
        </Card>

        <Card className="border-border/70 bg-card/90 shadow-sm p-4 space-y-1">
          <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-1">
            <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
            Total Unrealized P&amp;L
          </span>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold font-mono ${
                (state?.total_pnl ?? 0) >= 0 ? "text-emerald-500" : "text-rose-500"
              }`}
            >
              {(state?.total_pnl ?? 0) >= 0 ? "+" : ""}₹
              {state ? state.total_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "0"}
            </span>
          </div>
        </Card>
      </div>

      {/* ALLOCATION VISUAL BAR */}
      <Card className="border-border/70 bg-card/90 p-3 shadow-sm">
        <div className="flex items-center justify-between text-xs mb-1.5 font-mono">
          <span className="text-muted-foreground">Capital Deployment:</span>
          <div className="flex items-center gap-3 text-[11px]">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              Equities: {allocation.posPct.toFixed(1)}%
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-muted-foreground" />
              Cash: {allocation.cashPct.toFixed(1)}%
            </span>
          </div>
        </div>
        <div className="w-full bg-muted/60 h-2 rounded-full overflow-hidden flex">
          <div
            className="bg-gradient-to-r from-blue-500 to-indigo-500 h-full transition-all duration-500"
            style={{ width: `${allocation.posPct}%` }}
          />
          <div
            className="bg-muted-foreground/30 h-full transition-all duration-500"
            style={{ width: `${allocation.cashPct}%` }}
          />
        </div>
      </Card>

      {/* FEEDBACK BANNER */}
      {message && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
            message.type === "success"
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
              : message.type === "error"
              ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
              : "bg-blue-500/10 text-blue-400 border-blue-500/30"
          }`}
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{message.text}</span>
        </div>
      )}

      {/* MAIN WORKBENCH: ORDER FORM + REBALANCE + ACTIVE POSITIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* LEFT: ORDER FORM */}
        <Card className="lg:col-span-4 border-border/70 shadow-sm bg-card/90 backdrop-blur">
          <CardHeader className="pb-3 pt-4 px-4">
            <CardTitle className="text-sm font-semibold flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Briefcase className="h-4 w-4 text-purple-400" />
                Paper Order Terminal
              </span>
              <Badge variant="outline" className="text-[10px] font-mono">
                Simulated Kite
              </Badge>
            </CardTitle>
            <CardDescription className="text-xs">
              Direct market execution against mock broker state.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-3.5 px-4 pb-4">
            {/* Ticker Input */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-foreground/90">Symbol</Label>
              <Input
                value={orderTicker}
                onChange={e => setOrderTicker(e.target.value.toUpperCase())}
                placeholder="RELIANCE.NS"
                className="h-9 font-mono text-xs bg-background/60"
              />
            </div>

            {/* Side Selector Buttons */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-foreground/90">Action</Label>
              <div className="grid grid-cols-2 gap-1.5">
                <button
                  type="button"
                  onClick={() => setOrderSide("buy")}
                  className={`h-9 rounded-lg font-semibold text-xs transition-all border ${
                    orderSide === "buy"
                      ? "bg-emerald-500 text-white border-emerald-600 shadow-sm"
                      : "bg-background/60 border-border/70 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  BUY
                </button>
                <button
                  type="button"
                  onClick={() => setOrderSide("sell")}
                  className={`h-9 rounded-lg font-semibold text-xs transition-all border ${
                    orderSide === "sell"
                      ? "bg-rose-500 text-white border-rose-600 shadow-sm"
                      : "bg-background/60 border-border/70 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  SELL
                </button>
              </div>
            </div>

            {/* Quantity with quick sizing */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium text-foreground/90">Quantity (Shares)</Label>
                <div className="flex items-center gap-1 text-[10px]">
                  {[10, 25, 50, 100].map(q => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => setOrderQty(q)}
                      className="px-1.5 py-0.5 rounded bg-muted/60 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/60 font-mono"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
              <Input
                type="number"
                min={1}
                value={orderQty}
                onChange={e => setOrderQty(Math.max(1, Number(e.target.value)))}
                className="h-9 font-mono text-xs bg-background/60"
              />

              {/* Sizing by % of Cash */}
              <div className="flex items-center justify-between text-[11px] pt-0.5">
                <span className="text-muted-foreground font-mono">Size by Cash:</span>
                <div className="flex items-center gap-1">
                  {[25, 50, 75, 100].map(p => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => applyCashPercent(p)}
                      className="px-1.5 py-0.5 rounded bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 text-[10px] font-mono"
                    >
                      {p}%
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Optional Limit Price */}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-foreground/90">
                Limit Price (₹) <span className="text-muted-foreground text-[11px] font-normal">(Leave blank for Market)</span>
              </Label>
              <Input
                type="number"
                placeholder="Market execution"
                value={orderPrice}
                onChange={e => setOrderPrice(e.target.value === "" ? "" : Number(e.target.value))}
                className="h-9 font-mono text-xs bg-background/60"
              />
            </div>

            {/* Execute Button */}
            <Button
              onClick={submitOrder}
              disabled={actionLoading || !orderTicker || orderQty <= 0}
              className={`w-full h-10 rounded-xl font-bold text-xs text-white shadow-lg transition-all ${
                orderSide === "buy"
                  ? "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-600/20"
                  : "bg-rose-600 hover:bg-rose-500 shadow-rose-600/20"
              }`}
            >
              {actionLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <span>
                  Execute {orderSide.toUpperCase()} · {orderQty} {orderTicker}
                </span>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* MIDDLE: STRATEGY REBALANCE DESK */}
        <Card className="lg:col-span-3 border-border/70 shadow-sm bg-card/90 backdrop-blur flex flex-col justify-between">
          <div>
            <CardHeader className="pb-3 pt-4 px-4">
              <CardTitle className="text-sm font-semibold flex items-center justify-between">
                <span>Algorithmic Rebalance</span>
                <RotateCcw className="h-4 w-4 text-blue-400" />
              </CardTitle>
              <CardDescription className="text-xs">
                Calculate target weights for the universe and automatically rebalance open holdings.
              </CardDescription>
            </CardHeader>

            <CardContent className="space-y-3 px-4 pb-4">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Target Strategy</Label>
                <Select value={strategyId} onValueChange={setStrategyId}>
                  <SelectTrigger className="h-9 text-xs bg-background/60">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-80">
                    {strategies.map(s => (
                      <SelectItem key={s.id} value={s.id} className="text-xs">
                        {s.name} ({s.family})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="p-2.5 rounded-lg border border-border/60 bg-muted/20 text-[11px] text-muted-foreground space-y-1">
                <p>• Computes indicator signals across top 10 Nifty large-caps.</p>
                <p>• Rebalances positions to target weights with fractional rounding.</p>
              </div>
            </CardContent>
          </div>

          <div className="p-4 pt-0">
            <Button
              onClick={doRebalance}
              disabled={actionLoading}
              variant="outline"
              className="w-full h-9 rounded-xl border-primary/40 text-primary hover:bg-primary/10 text-xs font-semibold"
            >
              {actionLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : null}
              Rebalance to {strategyId}
            </Button>
          </div>
        </Card>

        {/* RIGHT: LIVE POSITIONS TABLE */}
        <Card className="lg:col-span-5 border-border/70 shadow-sm bg-card/90 backdrop-blur">
          <CardHeader className="pb-2 pt-4 px-4 border-b border-border/50">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CardTitle className="text-sm font-semibold">Active Holdings</CardTitle>
                <Badge variant="outline" className="text-[10px] font-mono">
                  {state?.n_positions ?? 0} positions
                </Badge>
              </div>

              <Button
                variant="ghost"
                size="icon"
                onClick={refresh}
                disabled={loading}
                className="h-7 w-7 rounded-lg text-muted-foreground hover:text-foreground"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-primary" : ""}`} />
              </Button>
            </div>
          </CardHeader>

          <CardContent className="p-0">
            {state && Object.keys(state.positions).length > 0 ? (
              <div className="overflow-x-auto max-h-[380px] overflow-y-auto">
                <table className="w-full text-xs font-mono">
                  <thead className="bg-muted/40 border-b border-border/70 text-muted-foreground text-[11px]">
                    <tr>
                      <th className="text-left py-2 px-3 font-semibold">Holding</th>
                      <th className="text-right py-2 px-2 font-semibold">Cost</th>
                      <th className="text-right py-2 px-2 font-semibold">LTP</th>
                      <th className="text-right py-2 px-3 font-semibold">P&amp;L</th>
                      <th className="text-center py-2 px-2 font-semibold">Close</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {Object.entries(state.positions).map(([ticker, pos]) => {
                      const isProfit = pos.unrealized_pnl >= 0
                      const pnlPct = pos.avg_cost > 0 ? ((pos.last_price - pos.avg_cost) / pos.avg_cost) * 100 : 0

                      return (
                        <tr key={ticker} className="hover:bg-accent/30 transition-colors">
                          <td className="py-2.5 px-3">
                            <div className="font-semibold text-foreground">{ticker}</div>
                            <div className="text-[10px] text-muted-foreground">{pos.shares} shares</div>
                          </td>

                          <td className="py-2.5 px-2 text-right tabular-nums text-muted-foreground">
                            ₹{pos.avg_cost.toFixed(1)}
                          </td>

                          <td className="py-2.5 px-2 text-right tabular-nums font-medium text-foreground">
                            ₹{pos.last_price.toFixed(1)}
                          </td>

                          <td className="py-2.5 px-3 text-right tabular-nums">
                            <div className={`font-semibold ${isProfit ? "text-emerald-500" : "text-rose-500"}`}>
                              {isProfit ? "+" : ""}₹{pos.unrealized_pnl.toFixed(0)}
                            </div>
                            <div className={`text-[10px] ${isProfit ? "text-emerald-500/80" : "text-rose-500/80"}`}>
                              {isProfit ? "+" : ""}
                              {pnlPct.toFixed(1)}%
                            </div>
                          </td>

                          <td className="py-2.5 px-2 text-center">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => closePosition(ticker, pos.shares)}
                              disabled={actionLoading}
                              className="h-6 w-6 p-0 text-muted-foreground hover:text-rose-500 rounded-md"
                              title="Close position at market"
                            >
                              <XCircle className="h-3.5 w-3.5" />
                            </Button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="py-12 text-center text-xs text-muted-foreground">
                No active holdings. Execute a paper order or run a strategy rebalance above.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
