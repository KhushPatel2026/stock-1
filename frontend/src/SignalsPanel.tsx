import { useEffect, useState, useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
  Radio,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Search,
  Grid,
  LayoutGrid,
  Zap,
  Briefcase,
} from "lucide-react"
import { fetchSignals, fetchTickers, fetchStrategies } from "@/api"
import type { Signal } from "@/api"

const FAMILY_COLORS: Record<string, string> = {
  Trend: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  MR: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  Momentum: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  Factor: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  Volume: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  Pattern: "bg-pink-500/10 text-pink-400 border-pink-500/30",
  Volatility: "bg-red-500/10 text-red-400 border-red-500/30",
  Options: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
  Event: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
  Stat_arb: "bg-teal-500/10 text-teal-400 border-teal-500/30",
  Cross_sect: "bg-lime-500/10 text-lime-400 border-lime-500/30",
  Hedge: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  ML: "bg-fuchsia-500/10 text-fuchsia-400 border-fuchsia-500/30",
  Allocation: "bg-violet-500/10 text-violet-400 border-violet-500/30",
  Carry: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
  Intraday: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  Other: "bg-gray-500/10 text-gray-400 border-gray-500/30",
}

interface SignalsPanelProps {
  onSelectSignalOrder?: (ticker: string, side: "buy" | "sell") => void
  onBacktestStrategy?: (strategyId: string, ticker?: string) => void
}

export default function SignalsPanel({ onSelectSignalOrder, onBacktestStrategy }: SignalsPanelProps) {
  const [tickers, setTickers] = useState<string[]>([])
  const [strategies, setStrategies] = useState<{ id: string; name: string; family: string }[]>([])
  const [signals, setSignals] = useState<Signal[]>([])
  const [asOf, setAsOf] = useState<string>("")
  const [search, setSearch] = useState("")
  const [familyFilter, setFamilyFilter] = useState<string>("")
  const [directionFilter, setDirectionFilter] = useState<"all" | "long" | "short" | "flat">("all")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<"cards" | "matrix">("cards")

  useEffect(() => {
    fetchTickers().then(setTickers).catch(e => setError(e.message))
    fetchStrategies()
      .then(s => setStrategies(s.map(x => ({ id: x.id, name: x.name, family: x.family }))))
      .catch(e => setError(e.message))
  }, [])

  const refresh = useMemo(() => {
    return async () => {
      setLoading(true)
      setError(null)
      try {
        const subset = tickers.slice(0, 15)
        const r = await fetchSignals(subset.length > 0 ? subset : undefined)
        setSignals(r.signals)
        setAsOf(r.as_of)
      } catch (e: any) {
        setError(e.message || String(e))
      } finally {
        setLoading(false)
      }
    }
  }, [tickers])

  useEffect(() => {
    if (tickers.length > 0) refresh()
  }, [tickers, refresh])

  // Summary statistics
  const stats = useMemo(() => {
    const longs = signals.filter(s => s.signal === "long").length
    const shorts = signals.filter(s => s.signal === "short").length
    const flats = signals.filter(s => s.signal === "flat").length
    const total = signals.length
    const longPct = total > 0 ? (longs / total) * 100 : 0
    const shortPct = total > 0 ? (shorts / total) * 100 : 0

    return { longs, shorts, flats, total, longPct, shortPct }
  }, [signals])

  // Group signals by strategy
  const byStrategy = useMemo(() => {
    const m: Record<string, Signal[]> = {}
    for (const s of signals) {
      if (!m[s.strategy_id]) m[s.strategy_id] = []
      m[s.strategy_id].push(s)
    }
    return m
  }, [signals])

  // Group signals by ticker (for matrix)
  const activeTickers = useMemo(() => {
    const tSet = new Set<string>()
    signals.forEach(s => tSet.add(s.ticker))
    return Array.from(tSet).sort()
  }, [signals])

  // Filtered strategies for card view
  const filteredStrategies = useMemo(() => {
    return Object.entries(byStrategy).filter(([sid, sigs]) => {
      const strat = strategies.find(x => x.id === sid)
      if (familyFilter && strat?.family !== familyFilter) return false
      if (search) {
        const matchName = strat?.name.toLowerCase().includes(search.toLowerCase())
        const matchId = sid.toLowerCase().includes(search.toLowerCase())
        if (!matchName && !matchId) return false
      }
      if (directionFilter !== "all") {
        const hasDir = sigs.some(s => s.signal === directionFilter)
        if (!hasDir) return false
      }
      return true
    })
  }, [byStrategy, strategies, familyFilter, search, directionFilter])

  const families = useMemo(() => {
    return Array.from(new Set(strategies.map(s => s.family))).sort()
  }, [strategies])

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* SUMMARY STATS & RADAR METRICS */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card className="border-border/70 bg-card/90 shadow-sm p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
              Total Signals Computed
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-foreground">{stats.total}</span>
              <span className="text-[11px] text-muted-foreground">across {Object.keys(byStrategy).length} strats</span>
            </div>
          </Card>

          <Card className="border-border/70 bg-card/90 shadow-sm p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
              Long (Bullish) Alpha
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-emerald-500">{stats.longs}</span>
              <span className="text-[11px] text-emerald-500/80 font-mono">({stats.longPct.toFixed(0)}%)</span>
            </div>
          </Card>

          <Card className="border-border/70 bg-card/90 shadow-sm p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
              <TrendingDown className="h-3.5 w-3.5 text-rose-500" />
              Short (Bearish) Alpha
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-rose-500">{stats.shorts}</span>
              <span className="text-[11px] text-rose-500/80 font-mono">({stats.shortPct.toFixed(0)}%)</span>
            </div>
          </Card>

          <Card className="border-border/70 bg-card/90 shadow-sm p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
              <Minus className="h-3.5 w-3.5 text-muted-foreground" />
              Neutral / Flat
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-muted-foreground">{stats.flats}</span>
              <span className="text-[11px] text-muted-foreground">in cash/sidelines</span>
            </div>
          </Card>
        </div>

        {/* FILTER & RADAR CONTROLS */}
        <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur">
          <CardHeader className="pb-3 pt-4 px-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Radio className="h-4 w-4 text-emerald-500" />
                  <span>Real-Time Signal Radar</span>
                </CardTitle>
                <CardDescription className="text-xs">
                  Cross-sectional snapshot of indicators across active universe. {asOf && `As of ${asOf}.`}
                </CardDescription>
              </div>

              {/* View Switcher & Refresh */}
              <div className="flex items-center gap-2">
                <div className="flex items-center bg-muted/50 p-1 rounded-lg border border-border/70">
                  <button
                    type="button"
                    onClick={() => setViewMode("cards")}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                      viewMode === "cards"
                        ? "bg-card text-foreground shadow-sm font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <LayoutGrid className="h-3.5 w-3.5" />
                    <span>Cards</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("matrix")}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                      viewMode === "matrix"
                        ? "bg-card text-foreground shadow-sm font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Grid className="h-3.5 w-3.5" />
                    <span>Heatmap</span>
                  </button>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={refresh}
                  disabled={loading}
                  className="h-8 text-xs gap-1.5 border-border/80"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-primary" : ""}`} />
                  <span>Scan</span>
                </Button>
              </div>
            </div>
          </CardHeader>

          <CardContent className="px-5 pb-5 pt-0 space-y-3">
            <div className="flex flex-col md:flex-row gap-2.5 items-center justify-between">
              {/* Search input */}
              <div className="relative w-full md:max-w-xs">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  placeholder="Filter strategies..."
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="pl-8 h-8 text-xs bg-background/60"
                />
              </div>

              {/* Direction Filter */}
              <div className="flex items-center gap-1 w-full md:w-auto overflow-x-auto">
                <span className="text-[10px] uppercase font-mono text-muted-foreground mr-1">Signal:</span>
                {(["all", "long", "short", "flat"] as const).map(d => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDirectionFilter(d)}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize transition-all border ${
                      directionFilter === d
                        ? d === "long"
                          ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400 font-semibold"
                          : d === "short"
                          ? "bg-rose-500/20 border-rose-500/40 text-rose-400 font-semibold"
                          : "bg-card border-border text-foreground font-semibold"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            {/* Family Chips */}
            <div className="flex flex-wrap gap-1 pt-1 border-t border-border/40">
              <button
                type="button"
                onClick={() => setFamilyFilter("")}
                className={`text-[10px] px-2 py-0.5 rounded-md border font-mono transition-all ${
                  familyFilter === "" ? "bg-primary text-primary-foreground border-primary" : "border-border/60 hover:bg-muted text-muted-foreground"
                }`}
              >
                All Families
              </button>
              {families.map(f => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFamilyFilter(familyFilter === f ? "" : f)}
                  className={`text-[10px] px-2 py-0.5 rounded-md border font-mono transition-all ${
                    familyFilter === f
                      ? "bg-primary text-primary-foreground border-primary"
                      : `${FAMILY_COLORS[f] || FAMILY_COLORS.Other} hover:opacity-80`
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            {error && <p className="text-xs text-rose-500">{error}</p>}
          </CardContent>
        </Card>

        {/* VIEW 1: STRATEGY CARDS */}
        {viewMode === "cards" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredStrategies.map(([sid, sigs]) => {
              const strat = strategies.find(x => x.id === sid)
              return (
                <Card key={sid} className="border-border/70 shadow-sm bg-card/80 backdrop-blur hover:border-border transition-all flex flex-col justify-between">
                  <CardHeader className="py-3 px-4 border-b border-border/40">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <CardTitle className="text-xs font-semibold text-foreground truncate">
                          {strat?.name ?? sid}
                        </CardTitle>
                        <span className="text-[10px] text-muted-foreground font-mono">{sid}</span>
                      </div>
                      {strat && (
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded border font-mono shrink-0 ${
                            FAMILY_COLORS[strat.family] || FAMILY_COLORS.Other
                          }`}
                        >
                          {strat.family}
                        </span>
                      )}
                    </div>
                  </CardHeader>

                  <CardContent className="p-3 space-y-1.5 flex-1">
                    <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                      {sigs.map(s => {
                        const isLong = s.signal === "long"
                        const isShort = s.signal === "short"

                        return (
                          <div
                            key={s.ticker}
                            className="flex items-center justify-between p-1.5 rounded-lg border border-border/40 hover:bg-muted/30 transition-colors text-xs"
                          >
                            <span className="font-mono font-medium text-foreground">{s.ticker}</span>

                            <div className="flex items-center gap-1.5">
                              <span
                                className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold uppercase ${
                                  isLong
                                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                                    : isShort
                                    ? "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                                    : "bg-muted text-muted-foreground border border-border/60"
                                }`}
                              >
                                {s.signal}
                              </span>

                              {onSelectSignalOrder && (isLong || isShort) && (
                                <button
                                  type="button"
                                  onClick={() => onSelectSignalOrder(s.ticker, isLong ? "buy" : "sell")}
                                  className="p-1 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
                                  title={`Paper Trade ${isLong ? "BUY" : "SELL"} ${s.ticker}`}
                                >
                                  <Briefcase className="h-3 w-3 text-purple-400" />
                                </button>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </CardContent>

                  {/* Card footer with test shortcut */}
                  {onBacktestStrategy && (
                    <div className="px-3 py-2 border-t border-border/40 bg-muted/20 flex justify-end">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onBacktestStrategy(sid)}
                        className="h-6 text-[11px] text-muted-foreground hover:text-foreground gap-1 px-2"
                      >
                        <Zap className="h-3 w-3 text-primary" />
                        <span>Backtest</span>
                      </Button>
                    </div>
                  )}
                </Card>
              )
            })}
          </div>
        )}

        {/* VIEW 2: HEATMAP 2D MATRIX (TICKER × STRATEGY) */}
        {viewMode === "matrix" && (
          <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur overflow-hidden">
            <CardHeader className="py-3 px-5 border-b border-border/60">
              <CardTitle className="text-sm font-semibold">
                Cross-Sectional Alpha Matrix ({activeTickers.length} Tickers × {filteredStrategies.length} Algorithms)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead className="bg-muted/40 border-b border-border/70 text-muted-foreground">
                  <tr>
                    <th className="py-2.5 px-3 text-left font-semibold sticky left-0 bg-card z-10">Ticker</th>
                    {filteredStrategies.map(([sid]) => {
                      const strat = strategies.find(s => s.id === sid)
                      return (
                        <th key={sid} className="py-2.5 px-2 text-center font-medium max-w-[100px] truncate" title={strat?.name || sid}>
                          <div className="truncate max-w-[90px]">{strat?.name || sid}</div>
                        </th>
                      )
                    })}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {activeTickers.map(ticker => (
                    <tr key={ticker} className="hover:bg-accent/30 transition-colors">
                      <td className="py-2 px-3 font-semibold text-foreground sticky left-0 bg-card z-10 border-r border-border/40">
                        {ticker}
                      </td>
                      {filteredStrategies.map(([sid, sigs]) => {
                        const sig = sigs.find(s => s.ticker === ticker)
                        const signalType = sig?.signal || "flat"
                        const isLong = signalType === "long"
                        const isShort = signalType === "short"

                        return (
                          <td key={sid} className="py-2 px-2 text-center">
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span
                                  className={`inline-block h-4 w-4 rounded-full border cursor-pointer transition-transform hover:scale-125 ${
                                    isLong
                                      ? "bg-emerald-500 border-emerald-400 shadow-sm shadow-emerald-500/50"
                                      : isShort
                                      ? "bg-rose-500 border-rose-400 shadow-sm shadow-rose-500/50"
                                      : "bg-muted border-border/70"
                                  }`}
                                />
                              </TooltipTrigger>
                              <TooltipContent className="text-xs p-2">
                                <p className="font-semibold">{ticker}</p>
                                <p className="text-muted-foreground">
                                  {sid}: <span className="uppercase font-bold text-foreground">{signalType}</span>
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </div>
    </TooltipProvider>
  )
}
