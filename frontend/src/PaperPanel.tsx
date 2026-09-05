import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Loader2, RefreshCw } from "lucide-react"
import { fetchPaperState, paperOrder, paperRebalance, fetchStrategies, fetchTickers } from "@/api"
import type { PaperState, Strategy } from "@/api"

export default function PaperPanel() {
  const [state, setState] = useState<PaperState | null>(null)
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [tickers, setTickers] = useState<string[]>([])
  const [strategyId, setStrategyId] = useState("bollinger")
  const [orderTicker, setOrderTicker] = useState("RELIANCE.NS")
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy")
  const [orderQty, setOrderQty] = useState(10)
  const [orderPrice, setOrderPrice] = useState<number | "">("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const refresh = async () => {
    setLoading(true)
    try {
      const s = await fetchPaperState()
      setState(s)
    } catch (e: any) {
      setMessage(e.message)
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
    try {
      const r = await paperOrder(orderTicker, orderSide, orderQty, orderPrice === "" ? undefined : Number(orderPrice))
      setMessage(`${orderSide.toUpperCase()} ${orderQty} ${orderTicker} @ ${r.fill_price.toFixed(2)}`)
      refresh()
    } catch (e: any) {
      setMessage(`Error: ${e.message}`)
    }
  }

  const doRebalance = async () => {
    setMessage(null)
    try {
      const r = await paperRebalance(strategyId, tickers.slice(0, 10))
      setMessage(`Rebalanced to ${strategyId}: ${r.trades?.length ?? 0} trades`)
      refresh()
    } catch (e: any) {
      setMessage(`Error: ${e.message}`)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card className="lg:col-span-1">
        <CardHeader>
          <CardTitle>Place Order</CardTitle>
          <CardDescription>Mock broker — paper trades only.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label>Ticker</Label>
            <Input value={orderTicker} onChange={e => setOrderTicker(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-2">
              <Label>Side</Label>
              <Select value={orderSide} onValueChange={(v: any) => setOrderSide(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="buy">Buy</SelectItem>
                  <SelectItem value="sell">Sell</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Quantity</Label>
              <Input type="number" value={orderQty} onChange={e => setOrderQty(Number(e.target.value))} />
            </div>
          </div>
          <div className="space-y-2">
            <Label>Limit price (optional, blank = market)</Label>
            <Input type="number" value={orderPrice} onChange={e => setOrderPrice(e.target.value === "" ? "" : Number(e.target.value))} />
          </div>
          <Button onClick={submitOrder} className="w-full">{orderSide === "buy" ? "Buy" : "Sell"}</Button>
        </CardContent>
      </Card>

      <Card className="lg:col-span-1">
        <CardHeader>
          <CardTitle>Rebalance</CardTitle>
          <CardDescription>Run a strategy and rebalance the paper portfolio to its targets.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label>Strategy</Label>
            <Select value={strategyId} onValueChange={setStrategyId}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent className="max-h-96">
                {strategies.map(s => <SelectItem key={s.id} value={s.id}>{s.id} ({s.family})</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={doRebalance} className="w-full">Rebalance to {strategyId}</Button>
        </CardContent>
      </Card>

      <Card className="lg:col-span-1">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Portfolio
            <Button variant="outline" size="icon" onClick={refresh} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            </Button>
          </CardTitle>
          <CardDescription>State persists in data/paper_state.json.</CardDescription>
        </CardHeader>
        <CardContent>
          {state ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div><span className="text-muted-foreground">Cash:</span> ₹{state.cash.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                <div><span className="text-muted-foreground">Positions:</span> ₹{state.positions_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</div>
                <div className="col-span-2"><span className="text-muted-foreground">Equity:</span> <strong>₹{state.equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}</strong></div>
                <div><span className="text-muted-foreground">Total P&L:</span> <span className={state.total_pnl >= 0 ? "text-emerald-600" : "text-red-600"}>₹{state.total_pnl.toFixed(0)}</span></div>
                <div><span className="text-muted-foreground">Holdings:</span> {state.n_positions}</div>
              </div>
              <div className="space-y-1">
                {Object.entries(state.positions).map(([t, p]) => (
                  <div key={t} className="flex items-center justify-between text-sm border-b py-1">
                    <span>{t}</span>
                    <span className="text-xs">
                      <Badge variant="outline" className={p.unrealized_pnl >= 0 ? "bg-emerald-500/10" : "bg-red-500/10"}>
                        {p.shares} @ ₹{p.avg_cost.toFixed(0)} → ₹{p.last_price.toFixed(0)}
                      </Badge>
                    </span>
                    <span className={p.unrealized_pnl >= 0 ? "text-emerald-600" : "text-red-600"}>
                      ₹{p.unrealized_pnl.toFixed(0)}
                    </span>
                  </div>
                ))}
                {state.n_positions === 0 && <p className="text-xs text-muted-foreground">No open positions.</p>}
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Loading...</p>
          )}
          {message && <p className="text-xs text-muted-foreground mt-2">{message}</p>}
        </CardContent>
      </Card>
    </div>
  )
}
