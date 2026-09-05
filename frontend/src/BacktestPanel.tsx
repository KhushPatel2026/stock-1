import { useEffect, useState, useMemo } from "react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Tooltip as TooltipUI, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Loader2, Play, Sparkles, TrendingUp, TrendingDown, RotateCw, Search, CheckCircle2, XCircle, MinusCircle, HelpCircle } from "lucide-react"
import { fetchStrategies, fetchTickers, searchTickers, runBacktest, fetchRecommendations, fetchDecisions } from "@/api"
import type { Strategy, BacktestResult, Recommendation, TickerSearchResult, Decision } from "@/api"
import { Combobox } from "@/Combobox"

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
  Stat_arb: "bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/20",
  Cross_sect: "bg-lime-500/10 text-lime-700 dark:text-lime-300 border-lime-500/20",
  Hedge: "bg-slate-500/10 text-slate-700 dark:text-slate-300 border-slate-500/20",
  ML: "bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300 border-fuchsia-500/20",
  Allocation: "bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-500/20",
  Carry: "bg-yellow-500/10 text-yellow-700 dark:text-yellow-300 border-yellow-500/20",
  Intraday: "bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/20",
  Other: "bg-gray-500/10 text-gray-700 dark:text-gray-300 border-gray-500/20",
}

const CHART_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#9333ea", "#ea580c", "#0891b2", "#db2777", "#65a30d"]

const DECISION_COLORS: Record<string, string> = {
  BUY: "bg-emerald-500 text-white border-emerald-600",
  SELL: "bg-red-500 text-white border-red-600",
  HOLD: "bg-gray-400 text-white border-gray-500",
}

const DECISION_ICONS: Record<string, any> = {
  BUY: CheckCircle2,
  SELL: XCircle,
  HOLD: MinusCircle,
}

const DEFAULT_TICKERS = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ITC.NS"]
const DEFAULT_STRATEGY = "magic_formula"
const DEFAULT_PERIOD = "2y"

const PRESETS = [
  { id: "smart", name: "Smart picks", icon: Sparkles, desc: "Top 5 by OOS Sharpe", action: "recommend" },
  { id: "decide", name: "What should I buy?", icon: CheckCircle2, desc: "Today's consensus", action: "decisions" },
  { id: "all56", name: "All 56 ranked", icon: TrendingUp, desc: "Run every strategy", action: "all" },
  { id: "compare", name: "Compare families", icon: RotateCw, desc: "Best from each family", action: "compare_families" },
  { id: "mom", name: "Top momentum", icon: TrendingUp, desc: "Trend + Momentum", action: "filter:Momentum,Trend" },
  { id: "mr", name: "Top mean-reversion", icon: TrendingDown, desc: "MR + Volume", action: "filter:MR,Volume" },
  { id: "fac", name: "Top factor", icon: TrendingUp, desc: "Factor + Allocation", action: "filter:Factor,Allocation" },
]

export default function BacktestPanel() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [, setTickers] = useState<string[]>([])
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([DEFAULT_STRATEGY])
  const [selectedTickers, setSelectedTickers] = useState<string[]>(DEFAULT_TICKERS)
  const [tickerSearch, setTickerSearch] = useState("")
  const [searchResults, setSearchResults] = useState<TickerSearchResult[]>([])
  const [showSearch, setShowSearch] = useState(false)
  const [period, setPeriod] = useState(DEFAULT_PERIOD)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<{ done: number; total: number; label: string } | null>(null)
  const [results, setResults] = useState<{ id: string; result: BacktestResult }[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [recLoading, setRecLoading] = useState(false)
  const [decLoading, setDecLoading] = useState(false)
  const [, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch(e => setError(e.message))
    fetchTickers().then(setTickers).catch(() => {})
  }, [])

  useEffect(() => {
    const t = setTimeout(() => {
      if (tickerSearch.length >= 1) {
        searchTickers(tickerSearch).then(setSearchResults).catch(() => setSearchResults([]))
      } else {
        setSearchResults([])
      }
    }, 250)
    return () => clearTimeout(t)
  }, [tickerSearch])

  const addTicker = (t: string) => {
    const sym = t.trim().toUpperCase()
    if (!sym) return
    if (selectedTickers.includes(sym)) return
    if (selectedTickers.length >= 25) return
    setSelectedTickers([...selectedTickers, sym])
    setTickerSearch("")
    setShowSearch(false)
  }

  const removeTicker = (t: string) => setSelectedTickers(selectedTickers.filter(x => x !== t))

  // Auto-load decisions + recommendations when tickers change
  useEffect(() => {
    if (selectedTickers.length === 0) {
      setDecisions([])
      setRecommendations([])
      return
    }
    setDecLoading(true)
    fetchDecisions(selectedTickers, "3mo")
      .then(r => setDecisions(r.decisions))
      .catch(() => setDecisions([]))
      .finally(() => setDecLoading(false))
    setRecLoading(true)
    fetchRecommendations(selectedTickers, "1y")
      .then(r => setRecommendations(r.ranked))
      .catch(() => setRecommendations([]))
      .finally(() => setRecLoading(false))
  }, [selectedTickers])

  const runOne = async (sid: string): Promise<{ id: string; result: BacktestResult; error?: string }> => {
    try {
      const r = await runBacktest(sid, selectedTickers, period, null)
      return { id: sid, result: r }
    } catch (e: any) {
      return { id: sid, result: { equity_curve: [], metrics: {} as any, trades: [], info: { strategy: sid, tickers: selectedTickers, params: {}, n_trades: 0 } }, error: e.message || String(e) }
    }
  }

  const runPreset = async (preset: typeof PRESETS[number]) => {
    setError(null)
    setResults([])
    setLoading(true)
    setProgress({ done: 0, total: 1, label: preset.name })

    try {
      if (preset.action === "recommend") {
        setProgress({ done: 0, total: recommendations.length, label: "Top 5 by Sharpe" })
        const top = recommendations.filter(r => !r.error && (r.oos_sharpe ?? -99) > -99).slice(0, 5)
        const ids = top.map(r => r.strategy_id)
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < ids.length; i += 3) {
          const batch = ids.slice(i, i + 3)
          const batchResults = await Promise.all(batch.map(runOne))
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({ done: Math.min(i + batch.length, ids.length), total: ids.length, label: "Top 5 by Sharpe" })
        }
        setResults(out)
      } else if (preset.action === "all") {
        const total = strategies.length
        setProgress({ done: 0, total, label: "All 56 strategies" })
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < strategies.length; i += 6) {
          const batch = strategies.slice(i, i + 6).map(s => s.id)
          const batchResults = await Promise.all(batch.map(runOne))
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({ done: Math.min(i + batch.length, total), total, label: "All 56 strategies" })
        }
        setResults(out.sort((a, b) => (b.result.metrics.sharpe ?? -99) - (a.result.metrics.sharpe ?? -99)))
      } else if (preset.action === "compare_families") {
        const byFamily = new Map<string, Recommendation>()
        for (const r of recommendations) {
          if (r.error) continue
          const cur = byFamily.get(r.family)
          if (!cur || (r.oos_sharpe ?? -99) > (cur.oos_sharpe ?? -99)) byFamily.set(r.family, r)
        }
        const ids = Array.from(byFamily.values()).map(r => r.strategy_id)
        setProgress({ done: 0, total: ids.length, label: "Best per family" })
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < ids.length; i += 3) {
          const batch = ids.slice(i, i + 3)
          const batchResults = await Promise.all(batch.map(runOne))
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({ done: Math.min(i + batch.length, ids.length), total: ids.length, label: "Best per family" })
        }
        setResults(out)
      } else if (preset.action.startsWith("filter:")) {
        const fams = preset.action.split(":")[1].split(",")
        const ids = strategies.filter(s => fams.includes(s.family)).map(s => s.id)
        setProgress({ done: 0, total: ids.length, label: preset.name })
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < ids.length; i += 4) {
          const batch = ids.slice(i, i + 4)
          const batchResults = await Promise.all(batch.map(runOne))
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({ done: Math.min(i + batch.length, ids.length), total: ids.length, label: preset.name })
        }
        setResults(out.sort((a, b) => (b.result.metrics.sharpe ?? -99) - (a.result.metrics.sharpe ?? -99)))
      } else if (preset.action === "decisions") {
        // Run top 3 strategies for the top BUY tickers
        const buys = decisions.filter(d => d.decision === "BUY").slice(0, 5)
        const topStrategies = recommendations.filter(r => !r.error && (r.oos_sharpe ?? -99) > 0.5).slice(0, 3).map(r => r.strategy_id)
        const tickersToRun = buys.length > 0 ? buys.map(b => b.ticker) : selectedTickers
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < topStrategies.length; i += 3) {
          const batch = topStrategies.slice(i, i + 3)
          const batchResults = await Promise.all(batch.map(async (sid) => {
            try {
              const r = await runBacktest(sid, tickersToRun, period, null)
              return { id: sid, result: r }
            } catch (e: any) {
              return { id: sid, result: { equity_curve: [], metrics: {} as any, trades: [], info: { strategy: sid, tickers: tickersToRun, params: {}, n_trades: 0 } }, error: e.message || String(e) }
            }
          }))
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({ done: Math.min(i + batch.length, topStrategies.length), total: topStrategies.length, label: "Today's top picks" })
        }
        setResults(out)
      }
    } catch (e: any) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
      setProgress(null)
    }
  }

  const onRun = async () => {
    if (selectedStrategies.length === 0) return
    if (selectedTickers.length === 0) return
    setError(null)
    setResults([])
    setLoading(true)
    setProgress({ done: 0, total: selectedStrategies.length, label: "Running" })

    const out: { id: string; result: BacktestResult }[] = []
    for (let i = 0; i < selectedStrategies.length; i += 4) {
      const batch = selectedStrategies.slice(i, i + 4)
      const batchResults = await Promise.all(batch.map(runOne))
      for (const r of batchResults) if (!r.error) out.push(r)
      setProgress({ done: Math.min(i + batch.length, selectedStrategies.length), total: selectedStrategies.length, label: "Running" })
    }
    setResults(out)
    setLoading(false)
    setProgress(null)
  }

  const combinedChart = useMemo(() => {
    if (results.length === 0) return []
    const dates = new Set<string>()
    results.forEach(r => r.result.equity_curve.forEach(p => dates.add(p.date)))
    const sortedDates = Array.from(dates).sort()
    return sortedDates.map(date => {
      const row: Record<string, number | string> = { date }
      results.forEach(r => {
        const point = r.result.equity_curve.find(p => p.date === date)
        if (point) row[r.id] = point.equity
      })
      return row
    })
  }, [results])

  const strategyOptions = strategies.map(s => ({ value: s.id, label: s.name, hint: s.family }))

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* DECISIONS — what should I buy/sell */}
        <Card className="border-2 border-primary/30 bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              What should I do right now?
              <Badge variant="outline" className="text-xs font-normal">Live consensus from 56 strategies</Badge>
              {decLoading && <Loader2 className="h-4 w-4 animate-spin ml-auto" />}
            </CardTitle>
            <CardDescription>
              Based on current signals + each strategy's recent OOS Sharpe, weighted to favor strategies that actually work.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {decisions.length === 0 && !decLoading && (
              <p className="text-sm text-muted-foreground">Add tickers above to see today's decisions.</p>
            )}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {decisions.map(d => {
                const Icon = DECISION_ICONS[d.decision]
                return (
                  <div key={d.ticker} className={`rounded-lg border-2 p-3 ${DECISION_COLORS[d.decision]}`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-sm">{d.ticker}</span>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-bold mb-1">{d.decision}</div>
                    <div className="text-xs opacity-90 mb-2">{d.confidence.toFixed(0)}% confidence</div>
                    <div className="text-xs space-y-0.5 opacity-80">
                      <div>↑ Long: {d.long_pct.toFixed(0)}% ({d.n_long})</div>
                      <div>↓ Short: {d.short_pct.toFixed(0)}% ({d.n_short})</div>
                    </div>
                    {d.long_strategies.length > 0 && d.decision === "BUY" && (
                      <div className="mt-2 pt-2 border-t border-white/30 text-xs opacity-90">
                        <div className="font-semibold mb-1">Why BUY:</div>
                        {d.long_strategies.slice(0, 3).map(s => (
                          <div key={s} className="truncate">• {strategyName(s, strategies)}</div>
                        ))}
                      </div>
                    )}
                    {d.short_strategies.length > 0 && d.decision === "SELL" && (
                      <div className="mt-2 pt-2 border-t border-white/30 text-xs opacity-90">
                        <div className="font-semibold mb-1">Why SELL:</div>
                        {d.short_strategies.slice(0, 3).map(s => (
                          <div key={s} className="truncate">• {strategyName(s, strategies)}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
              {decisions.length === 0 && decLoading && (
                <div className="col-span-full text-center py-8 text-muted-foreground">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                  Analyzing 56 strategies across {selectedTickers.length} tickers...
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* TICKER + PERIOD BAR */}
        <Card>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
              <div className="md:col-span-7 space-y-2 relative">
                <Label className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    Tickers ({selectedTickers.length}/25)
                    <TooltipUI>
                      <TooltipTrigger asChild><HelpCircle className="h-3 w-3 text-muted-foreground" /></TooltipTrigger>
                      <TooltipContent>Search any global ticker: Nifty (.NS), US stocks (AAPL), crypto (BTC-USD), FX (EURUSD=X)</TooltipContent>
                    </TooltipUI>
                  </span>
                  <span className="text-xs text-muted-foreground font-normal">Yahoo Finance</span>
                </Label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={tickerSearch}
                    onChange={e => { setTickerSearch(e.target.value); setShowSearch(true) }}
                    onFocus={() => setShowSearch(true)}
                    onKeyDown={e => {
                      if (e.key === "Enter" && tickerSearch) {
                        e.preventDefault()
                        const match = searchResults.find(r => r.symbol.toUpperCase() === tickerSearch.toUpperCase())
                        addTicker(match ? match.symbol : tickerSearch)
                      }
                    }}
                    placeholder="Search ticker (RELIANCE, AAPL, TSLA, BTC-USD...)"
                    className="pl-9"
                  />
                  {showSearch && searchResults.length > 0 && (
                    <div className="absolute z-50 mt-1 w-full border-2 rounded-md bg-card text-card-foreground shadow-lg max-h-72 overflow-y-auto">
                      {searchResults.map(r => (
                        <button
                          key={r.symbol}
                          type="button"
                          onClick={() => addTicker(r.symbol)}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-accent border-b last:border-0"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-medium">{r.symbol}</span>
                            <Badge variant="outline" className="text-xs">{r.exchange || r.quoteType}</Badge>
                          </div>
                          <div className="text-xs text-muted-foreground truncate">{r.shortname}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap gap-1">
                  {selectedTickers.map(t => (
                    <Badge key={t} variant="secondary" className="cursor-pointer text-xs" onClick={() => removeTicker(t)}>
                      {t} ×
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="md:col-span-3 space-y-2">
                <Label className="flex items-center gap-2">
                  Period
                  <TooltipUI>
                    <TooltipTrigger asChild><HelpCircle className="h-3 w-3 text-muted-foreground" /></TooltipTrigger>
                    <TooltipContent>How much historical data to backtest over</TooltipContent>
                  </TooltipUI>
                </Label>
                <Select value={period} onValueChange={setPeriod}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"].map(p => (
                      <SelectItem key={p} value={p}>{p === "max" ? "Max available" : p.toUpperCase()}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="md:col-span-2">
                <Button onClick={onRun} disabled={loading} className="w-full">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  <span className="ml-2">{loading && progress ? `${progress.done}/${progress.total}` : "Run"}</span>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* LEFT: STRATEGY + PRESETS */}
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-base">Strategies ({strategies.length})</CardTitle>
              <CardDescription>Pick one or many, or use a preset.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Combobox
                options={strategyOptions}
                value={selectedStrategies}
                onChange={setSelectedStrategies}
                placeholder="Search strategies..."
                multi
              />
              <div className="space-y-1">
                <Label className="text-xs">Quick presets</Label>
                <div className="grid grid-cols-1 gap-1">
                  {PRESETS.map(p => {
                    const Icon = p.icon
                    return (
                      <Button
                        key={p.id}
                        variant="outline"
                        size="sm"
                        onClick={() => runPreset(p)}
                        disabled={loading || selectedTickers.length === 0}
                        className="justify-start h-auto py-2"
                      >
                        <Icon className="h-3 w-3 mr-2 shrink-0" />
                        <div className="flex flex-col items-start text-left">
                          <span className="text-xs font-medium">{p.name}</span>
                          <span className="text-xs text-muted-foreground">{p.desc}</span>
                        </div>
                      </Button>
                    )
                  })}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* RIGHT: RECOMMENDATIONS + RESULTS */}
          <div className="lg:col-span-2 space-y-4">
            {/* RECOMMENDATIONS WITH REASONS */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  Best strategies by recent OOS Sharpe
                  {recLoading && <Loader2 className="h-3 w-3 animate-spin ml-auto" />}
                </CardTitle>
                <CardDescription>Out-of-sample performance on your tickers. Hover for reasoning.</CardDescription>
              </CardHeader>
              <CardContent>
                {recommendations.length === 0 && !recLoading && (
                  <p className="text-sm text-muted-foreground">Add tickers to see recommendations.</p>
                )}
                <div className="space-y-1 max-h-80 overflow-y-auto">
                  {recommendations.slice(0, 15).map(r => {
                    const sharpe = r.oos_sharpe ?? -99
                    const positive = sharpe > 0
                    const strat = strategies.find(s => s.id === r.strategy_id)
                    return (
                      <TooltipUI key={r.strategy_id}>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            onClick={() => {
                              if (!selectedStrategies.includes(r.strategy_id)) {
                                setSelectedStrategies([...selectedStrategies, r.strategy_id])
                              }
                            }}
                            className={`w-full flex items-center justify-between gap-2 px-3 py-2 rounded-md border hover:bg-accent transition-colors ${selectedStrategies.includes(r.strategy_id) ? "bg-accent" : ""}`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <Badge variant="outline" className={FAMILY_COLORS[r.family] || FAMILY_COLORS.Other}>
                                {r.family}
                              </Badge>
                              <span className="text-sm font-medium truncate">{strat?.name ?? r.strategy_id}</span>
                            </div>
                            <div className="flex items-center gap-3 text-xs tabular-nums shrink-0">
                              {r.error ? (
                                <span className="text-red-600">err</span>
                              ) : (
                                <>
                                  <span className={`font-semibold ${positive ? "text-emerald-600" : "text-red-600"}`}>
                                    {sharpe.toFixed(2)}
                                  </span>
                                  <span className="text-muted-foreground w-16 text-right">
                                    {((r.total_return ?? 0) * 100).toFixed(1)}%
                                  </span>
                                </>
                              )}
                            </div>
                          </button>
                        </TooltipTrigger>
                        {r.reason && (
                          <TooltipContent className="max-w-sm bg-card text-card-foreground border-2 shadow-lg">
                            <p className="text-xs">{r.reason}</p>
                          </TooltipContent>
                        )}
                      </TooltipUI>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {/* RESULTS */}
            {results.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">
                    Results ({results.length}) — {selectedTickers.join(", ")} · {period.toUpperCase()}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={combinedChart}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                      <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: 11 }} />
                      {results.map((r, i) => (
                        <Line key={r.id} type="monotone" dataKey={r.id} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={false} />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="max-h-72 overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-card">
                        <tr className="border-b">
                          <th className="text-left p-2">Strategy</th>
                          <th className="text-left p-2">Family</th>
                          <th className="text-right p-2">Total</th>
                          <th className="text-right p-2">CAGR</th>
                          <th className="text-right p-2">Sharpe</th>
                          <th className="text-right p-2">Max DD</th>
                          <th className="text-right p-2">Trades</th>
                        </tr>
                      </thead>
                      <tbody>
                        {results.map(r => {
                          const strat = strategies.find(s => s.id === r.id)
                          const sharpe = r.result.metrics.sharpe ?? -99
                          return (
                            <tr key={r.id} className="border-b">
                              <td className="p-2 font-medium">{strat?.name ?? r.id}</td>
                              <td className="p-2">{strat && <Badge variant="outline" className={FAMILY_COLORS[strat.family]}>{strat.family}</Badge>}</td>
                              <td className="p-2 text-right tabular-nums">{fmt(r.result.metrics.total_return)}</td>
                              <td className="p-2 text-right tabular-nums">{fmt(r.result.metrics.cagr)}</td>
                              <td className={`p-2 text-right tabular-nums font-semibold ${sharpe > 0 ? "text-emerald-600" : "text-red-600"}`}>{sharpe.toFixed(2)}</td>
                              <td className="p-2 text-right tabular-nums text-destructive">{fmt(r.result.metrics.max_drawdown)}</td>
                              <td className="p-2 text-right tabular-nums">{r.result.info.n_trades}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {!results.length && !loading && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Pick a preset or strategies above</CardTitle>
                  <CardDescription>
                    "What should I do right now?" above shows today's BUY/SELL signals. Presets run pre-built comparisons.
                  </CardDescription>
                </CardHeader>
              </Card>
            )}
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}

function strategyName(id: string, strategies: Strategy[]): string {
  return strategies.find(s => s.id === id)?.name ?? id
}

function fmt(v: number | undefined): string {
  if (v == null || Number.isNaN(v)) return "—"
  return `${(v * 100).toFixed(2)}%`
}
