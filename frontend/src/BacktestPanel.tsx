import { useEffect, useState } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Loader2, Play } from "lucide-react"
import { fetchStrategies, fetchTickers, runBacktest } from "@/api"
import type { Strategy, BacktestResult } from "@/api"

const FAMILY_COLORS: Record<string, string> = {
  Trend: "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20",
  MR: "bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/20",
  Momentum: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/20",
  Factor: "bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/20",
  Volume: "bg-orange-500/10 text-orange-700 dark:text-orange-300 border-orange-500/20",
  Pattern: "bg-pink-500/10 text-pink-700 dark:text-pink-300 border-pink-500/20",
  Volatility: "bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/20",
  Options: "bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border-indigo-500/20",
  Event: "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-500/20",
  Stat: "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/20",
  Stat_arb: "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/20",
  Cross_sect: "bg-lime-500/10 text-lime-700 dark:text-lime-300 border-lime-500/20",
  Hedge: "bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-500/20",
  ML: "bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300 border-fuchsia-500/20",
  Allocation: "bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-500/20",
  Carry: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300 border-yellow-500/20",
  Other: "bg-gray-500/10 text-gray-700 dark:text-gray-300 border-gray-500/20",
}

export default function BacktestPanel() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [tickers, setTickers] = useState<string[]>([])
  const [strategyId, setStrategyId] = useState<string>("")
  const [selectedTickers, setSelectedTickers] = useState<string[]>([])
  const [tickerInput, setTickerInput] = useState("")
  const [period, setPeriod] = useState("2y")
  const [paramsText, setParamsText] = useState("{}")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch(e => setError(e.message))
    fetchTickers().then(setTickers).catch(e => setError(e.message))
  }, [])

  const strategy = strategies.find(s => s.id === strategyId)

  const addTicker = (t: string) => {
    const sym = t.trim().toUpperCase()
    if (!sym) return
    if (selectedTickers.includes(sym)) return
    if (selectedTickers.length >= 20) return
    setSelectedTickers([...selectedTickers, sym])
    setTickerInput("")
  }

  const removeTicker = (t: string) => {
    setSelectedTickers(selectedTickers.filter(x => x !== t))
  }

  const onRun = async () => {
    if (!strategyId) {
      setError("Pick a strategy")
      return
    }
    if (selectedTickers.length === 0) {
      setError("Add at least one ticker")
      return
    }
    setError(null)
    setLoading(true)
    setResult(null)
    try {
      let params = null
      try {
        const parsed = JSON.parse(paramsText || "{}")
        params = Object.keys(parsed).length ? parsed : null
      } catch (e) {
        setError("Invalid JSON in params")
        setLoading(false)
        return
      }
      const r = await runBacktest(strategyId, selectedTickers, period, params)
      setResult(r)
    } catch (e: any) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card className="lg:col-span-1">
        <CardHeader>
          <CardTitle>Backtest Configuration</CardTitle>
          <CardDescription>Pick a strategy, tickers, period, and run.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Strategy</Label>
            <Select value={strategyId} onValueChange={setStrategyId}>
              <SelectTrigger><SelectValue placeholder="Select strategy..." /></SelectTrigger>
              <SelectContent className="max-h-96">
                {strategies.map(s => (
                  <SelectItem key={s.id} value={s.id}>
                    <span className="flex items-center gap-2">
                      <Badge variant="outline" className={FAMILY_COLORS[s.family] || FAMILY_COLORS.Other}>
                        {s.family}
                      </Badge>
                      {s.name}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {strategy && <p className="text-xs text-muted-foreground">{strategy.description}</p>}
          </div>

          <div className="space-y-2">
            <Label>Tickers ({selectedTickers.length}/20)</Label>
            <div className="flex gap-2">
              <Input
                value={tickerInput}
                onChange={e => setTickerInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addTicker(tickerInput) } }}
                placeholder="e.g. RELIANCE.NS, TCS.NS"
              />
              <Button type="button" variant="outline" onClick={() => addTicker(tickerInput)}>Add</Button>
            </div>
            <div className="flex flex-wrap gap-1">
              {selectedTickers.map(t => (
                <Badge key={t} variant="secondary" className="cursor-pointer" onClick={() => removeTicker(t)}>
                  {t} ×
                </Badge>
              ))}
            </div>
            <div className="text-xs text-muted-foreground">
              Common: {tickers.slice(0, 8).join(", ")}…
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-2">
              <Label>Period</Label>
              <Select value={period} onValueChange={setPeriod}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["1y", "2y", "5y", "10y", "max"].map(p => (
                    <SelectItem key={p} value={p}>{p}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Params (JSON, optional)</Label>
            <Input
              value={paramsText}
              onChange={e => setParamsText(e.target.value)}
              placeholder='{"top_n": 5}'
              className="font-mono text-xs"
            />
            {strategy && (
              <p className="text-xs text-muted-foreground">
                Defaults: {JSON.stringify(strategy.params)}
              </p>
            )}
          </div>

          <Button onClick={onRun} disabled={loading} className="w-full">
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            {loading ? "Running..." : "Run Backtest"}
          </Button>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>

      <div className="lg:col-span-2 space-y-4">
        {result && (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Equity Curve</CardTitle>
                <CardDescription>{result.info.strategy} on {result.info.tickers.join(", ")} ({result.info.n_trades} trades)</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={result.equity_curve}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="equity" stroke="#2563eb" strokeWidth={2} dot={false} name="Equity (₹)" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metrics</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <Metric label="Total Return" value={fmt(result.metrics.total_return)} />
                  <Metric label="CAGR" value={fmt(result.metrics.cagr)} />
                  <Metric label="Sharpe" value={result.metrics.sharpe?.toFixed(2) ?? "—"} />
                  <Metric label="Max Drawdown" value={fmt(result.metrics.max_drawdown)} negative />
                  <Metric label="Final Equity" value={`₹${result.metrics.final_equity?.toLocaleString()}`} />
                  <Metric label="Bars" value={String(result.metrics.n_bars)} />
                </div>
              </CardContent>
            </Card>

            {result.trades.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Recent Trades ({result.trades.length})</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="max-h-64 overflow-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-card">
                        <tr className="border-b">
                          <th className="text-left p-2">Date</th>
                          <th className="text-left p-2">Ticker</th>
                          <th className="text-left p-2">Action</th>
                          <th className="text-right p-2">Price</th>
                          <th className="text-right p-2">Shares</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.trades.slice(0, 50).map((t, i) => (
                          <tr key={i} className="border-b">
                            <td className="p-2">{String(t.date)}</td>
                            <td className="p-2">{String(t.ticker)}</td>
                            <td className="p-2">{String(t.action)}</td>
                            <td className="p-2 text-right">{typeof t.price === "number" ? t.price.toFixed(2) : "—"}</td>
                            <td className="p-2 text-right">{String(t.shares ?? "—")}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {!result && !loading && (
          <Card>
            <CardHeader>
              <CardTitle>Ready</CardTitle>
              <CardDescription>Configure and run a backtest to see the equity curve and metrics.</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </div>
  )
}

function Metric({ label, value, negative }: { label: string; value: string; negative?: boolean }) {
  return (
    <div className="space-y-1">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={`text-2xl font-semibold tabular-nums ${negative ? "text-destructive" : ""}`}>{value}</div>
    </div>
  )
}

function fmt(v: number | undefined): string {
  if (v == null || Number.isNaN(v)) return "—"
  const pct = (v * 100).toFixed(2)
  return `${pct}%`
}
