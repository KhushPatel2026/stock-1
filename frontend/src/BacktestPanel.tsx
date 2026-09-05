import { useEffect, useState, useMemo } from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  AreaChart,
  Area,
} from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Tooltip as TooltipUI, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
  Loader2,
  Play,
  Sparkles,
  TrendingUp,
  TrendingDown,
  RotateCw,
  Search,
  CheckCircle2,
  HelpCircle,
  Download,
  ArrowUpDown,
  Briefcase,
  Zap,
  Layers,
  BarChart2,
  AlertCircle,
} from "lucide-react"
import { fetchStrategies, fetchTickers, searchTickers, runBacktest, fetchRecommendations, fetchDecisions } from "@/api"
import type { Strategy, BacktestResult, Recommendation, TickerSearchResult, Decision } from "@/api"
import { Combobox } from "@/Combobox"

const FAMILY_COLORS: Record<string, string> = {
  Trend: "bg-blue-500/10 text-blue-500 border-blue-500/30",
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

const CHART_COLORS = [
  "#3b82f6", // Blue
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#8b5cf6", // Purple
  "#ec4899", // Pink
  "#06b6d4", // Cyan
  "#f43f5e", // Rose
  "#84cc16", // Lime
]

const QUICK_CATEGORIES = [
  { name: "Nifty Giants", tickers: ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ITC.NS"] },
  { name: "Banking Titans", tickers: ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"] },
  { name: "Tech & Auto", tickers: ["INFY.NS", "TCS.NS", "WIPRO.NS", "TATAMOTORS.NS", "M&M.NS"] },
  { name: "US Megacaps", tickers: ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"] },
]

const PERIOD_OPTIONS = [
  { label: "1M", value: "1mo" },
  { label: "3M", value: "3mo" },
  { label: "6M", value: "6mo" },
  { label: "1Y", value: "1y" },
  { label: "2Y", value: "2y" },
  { label: "5Y", value: "5y" },
  { label: "MAX", value: "max" },
]

// Short-duration presets — yfinance accepts any human-readable period
const QUICK_PERIODS = [
  { label: "1D", value: "1d" },
  { label: "3D", value: "3d" },
  { label: "1W", value: "5d" },
  { label: "2W", value: "2wk" },
  { label: "1M", value: "1mo" },
]

const PRESETS = [
  { id: "smart", name: "Smart Alpha Picks", icon: Sparkles, desc: "Top 5 ranked by OOS Sharpe", action: "recommend" },
  { id: "decide", name: "Consensus Portfolio", icon: CheckCircle2, desc: "Backtest today's top BUY picks", action: "decisions" },
  { id: "compare", name: "Family Champions", icon: RotateCw, desc: "Best strategy from each family", action: "compare_families" },
  { id: "mom", name: "Trend & Momentum", icon: TrendingUp, desc: "Trend, Momentum & Breakout", action: "filter:Momentum,Trend" },
  { id: "mr", name: "Mean-Reversion", icon: TrendingDown, desc: "RSI, Bollinger & Volume", action: "filter:MR,Volume" },
  { id: "fac", name: "Factor & Allocation", icon: Layers, desc: "Magic Formula, Quality, Risk-Parity", action: "filter:Factor,Allocation" },
  { id: "all", name: "Universe Stress (All)", icon: BarChart2, desc: "Benchmark all registered algorithms", action: "all" },
]

interface BacktestPanelProps {
  targetStrategy?: string | null
  targetTicker?: string | null
  onNavigateToPaper?: (ticker: string, side: "buy" | "sell") => void
}

type SortField = "sharpe" | "cagr" | "total_return" | "max_drawdown" | "trades"

export default function BacktestPanel({ targetStrategy, targetTicker, onNavigateToPaper }: BacktestPanelProps) {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [, setTickers] = useState<string[]>([])
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>(["magic_formula"])
  const [selectedTickers, setSelectedTickers] = useState<string[]>([
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ITC.NS",
  ])
  const [tickerSearch, setTickerSearch] = useState("")
  const [searchResults, setSearchResults] = useState<TickerSearchResult[]>([])
  const [showSearch, setShowSearch] = useState(false)
  const [period, setPeriod] = useState("2y")
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState<{ done: number; total: number; label: string } | null>(null)
  const [results, setResults] = useState<{ id: string; result: BacktestResult }[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [recLoading, setRecLoading] = useState(false)
  const [decLoading, setDecLoading] = useState(false)
  const [decError, setDecError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [chartMode, setChartMode] = useState<"equity" | "drawdown">("equity")
  const [sortField, setSortField] = useState<SortField>("sharpe")
  const [sortAsc, setSortAsc] = useState(false)
  const [resultsFilter, setResultsFilter] = useState("")

  // Handle external triggers from StrategyLibrary or Signals tab
  useEffect(() => {
    if (targetStrategy && !selectedStrategies.includes(targetStrategy)) {
      setSelectedStrategies([targetStrategy])
    }
  }, [targetStrategy, selectedStrategies])

  useEffect(() => {
    if (targetTicker && !selectedTickers.includes(targetTicker)) {
      setSelectedTickers([targetTicker, ...selectedTickers.filter(t => t !== targetTicker)].slice(0, 15))
    }
  }, [targetTicker, selectedTickers])

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
    }, 200)
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

  const applyCategory = (tickers: string[]) => {
    const combined = Array.from(new Set([...selectedTickers, ...tickers])).slice(0, 20)
    setSelectedTickers(combined)
  }

  // Auto-load decisions & recommendations when tickers change
  useEffect(() => {
    if (selectedTickers.length === 0) {
      setDecisions([])
      setRecommendations([])
      return
    }
    setDecLoading(true)
    setDecError(null)
    fetchDecisions(selectedTickers, "3mo")
      .then(r => setDecisions(r.decisions))
      .catch(e => {
        setDecisions([])
        setDecError(e?.message ? String(e.message).slice(0, 160) : "Consensus scan failed — backend may still be warming up. Retry in a minute.")
      })
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
      return {
        id: sid,
        result: {
          equity_curve: [],
          metrics: {
            total_return: 0,
            cagr: 0,
            sharpe: -99,
            max_drawdown: 0,
            n_bars: 0,
            final_equity: 0,
          },
          trades: [],
          info: { strategy: sid, tickers: selectedTickers, params: {}, n_trades: 0 },
        },
        error: e.message || String(e),
      }
    }
  }

  const runPreset = async (preset: (typeof PRESETS)[number]) => {
    setError(null)
    setResults([])
    setLoading(true)
    setProgress({ done: 0, total: 1, label: preset.name })

    try {
      if (preset.action === "recommend") {
        const top = recommendations.filter(r => !r.error && (r.oos_sharpe ?? -99) > -99).slice(0, 5)
        const ids = top.map(r => r.strategy_id)
        if (ids.length === 0) {
          ids.push("magic_formula", "bollinger", "trend_following", "risk_parity")
        }
        setProgress({ done: 0, total: ids.length, label: "Top OOS Alpha" })
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < ids.length; i += 3) {
          const batch = ids.slice(i, i + 3)
          const batchResults = await Promise.all(batch.map(runOne))
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({ done: Math.min(i + batch.length, ids.length), total: ids.length, label: "Top OOS Alpha" })
        }
        setResults(out)
      } else if (preset.action === "all") {
        const total = strategies.length
        setProgress({ done: 0, total, label: `Running all ${total} algorithms` })
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < strategies.length; i += 6) {
          const batch = strategies.slice(i, i + 6).map(s => s.id)
          const batchResults = await Promise.all(batch.map(runOne))
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({ done: Math.min(i + batch.length, total), total, label: `All ${total} algorithms` })
        }
        setResults(out.sort((a, b) => (b.result.metrics.sharpe ?? -99) - (a.result.metrics.sharpe ?? -99)))
      } else if (preset.action === "compare_families") {
        const byFamily = new Map<string, Recommendation>()
        for (const r of recommendations) {
          if (r.error) continue
          const cur = byFamily.get(r.family)
          if (!cur || (r.oos_sharpe ?? -99) > (cur.oos_sharpe ?? -99)) byFamily.set(r.family, r)
        }
        let ids = Array.from(byFamily.values()).map(r => r.strategy_id)
        if (ids.length === 0) {
          ids = ["trend_following", "bollinger", "dual_momentum", "magic_formula", "risk_parity", "gap_fade"]
        }
        setProgress({ done: 0, total: ids.length, label: "Family Leaders" })
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < ids.length; i += 3) {
          const batch = ids.slice(i, i + 3)
          const batchResults = await Promise.all(batch.map(runOne))
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({ done: Math.min(i + batch.length, ids.length), total: ids.length, label: "Family Leaders" })
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
        const buys = decisions.filter(d => d.decision === "BUY").slice(0, 5)
        const topStrategies = recommendations
          .filter(r => !r.error && (r.oos_sharpe ?? -99) > 0.3)
          .slice(0, 4)
          .map(r => r.strategy_id)
        const stratIds = topStrategies.length > 0 ? topStrategies : ["magic_formula", "bollinger", "trend_following"]
        const tickersToRun = buys.length > 0 ? buys.map(b => b.ticker) : selectedTickers
        const out: { id: string; result: BacktestResult }[] = []
        for (let i = 0; i < stratIds.length; i += 3) {
          const batch = stratIds.slice(i, i + 3)
          const batchResults = await Promise.all(
            batch.map(async sid => {
              try {
                const r = await runBacktest(sid, tickersToRun, period, null)
                return { id: sid, result: r }
              } catch (e: any) {
                return {
                  id: sid,
                  result: {
                    equity_curve: [],
                    metrics: {} as any,
                    trades: [],
                    info: { strategy: sid, tickers: tickersToRun, params: {}, n_trades: 0 },
                  },
                  error: e.message || String(e),
                }
              }
            })
          )
          for (const r of batchResults) if (!r.error) out.push(r)
          setProgress({
            done: Math.min(i + batch.length, stratIds.length),
            total: stratIds.length,
            label: "Consensus picks",
          })
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

  const onRunCustom = async () => {
    if (selectedStrategies.length === 0 || selectedTickers.length === 0) return
    setError(null)
    setResults([])
    setLoading(true)
    setProgress({ done: 0, total: selectedStrategies.length, label: "Backtesting" })

    const out: { id: string; result: BacktestResult }[] = []
    for (let i = 0; i < selectedStrategies.length; i += 4) {
      const batch = selectedStrategies.slice(i, i + 4)
      const batchResults = await Promise.all(batch.map(runOne))
      for (const r of batchResults) if (!r.error) out.push(r)
      setProgress({
        done: Math.min(i + batch.length, selectedStrategies.length),
        total: selectedStrategies.length,
        label: "Backtesting",
      })
    }
    setResults(out)
    setLoading(false)
    setProgress(null)
  }

  // Combined chart for equity and drawdown curves
  const { combinedEquityChart, combinedDrawdownChart } = useMemo(() => {
    if (results.length === 0) return { combinedEquityChart: [], combinedDrawdownChart: [] }

    const dates = new Set<string>()
    results.forEach(r => r.result.equity_curve.forEach(p => dates.add(p.date)))
    const sortedDates = Array.from(dates).sort()

    // Precalculate drawdowns per strategy
    const ddMap = new Map<string, Map<string, number>>()
    results.forEach(r => {
      const m = new Map<string, number>()
      let peak = -Infinity
      r.result.equity_curve.forEach(p => {
        if (p.equity > peak) peak = p.equity
        const dd = peak > 0 ? ((p.equity - peak) / peak) * 100 : 0
        m.set(p.date, dd)
      })
      ddMap.set(r.id, m)
    })

    const eqRows = sortedDates.map(date => {
      const row: Record<string, number | string> = { date }
      results.forEach(r => {
        const point = r.result.equity_curve.find(p => p.date === date)
        if (point) row[r.id] = Number(point.equity.toFixed(2))
      })
      return row
    })

    const ddRows = sortedDates.map(date => {
      const row: Record<string, number | string> = { date }
      results.forEach(r => {
        const dd = ddMap.get(r.id)?.get(date)
        if (dd !== undefined) row[r.id] = Number(dd.toFixed(2))
      })
      return row
    })

    return { combinedEquityChart: eqRows, combinedDrawdownChart: ddRows }
  }, [results])

  // Top summary KPI metrics from current backtest
  const summaryKpi = useMemo(() => {
    if (results.length === 0) return null
    const valid = results.filter(r => r.result.metrics.sharpe != null)
    if (valid.length === 0) return null

    const bestSharpe = valid.reduce((prev, cur) => (cur.result.metrics.sharpe > prev.result.metrics.sharpe ? cur : prev))
    const bestReturn = valid.reduce((prev, cur) =>
      cur.result.metrics.total_return > prev.result.metrics.total_return ? cur : prev
    )
    const minDd = valid.reduce((prev, cur) =>
      Math.abs(cur.result.metrics.max_drawdown) < Math.abs(prev.result.metrics.max_drawdown) ? cur : prev
    )
    const avgSharpe = valid.reduce((acc, cur) => acc + (cur.result.metrics.sharpe || 0), 0) / valid.length

    return {
      bestSharpe,
      bestReturn,
      minDd,
      avgSharpe,
      count: valid.length,
    }
  }, [results])

  // Sorted and filtered results table
  const sortedResults = useMemo(() => {
    let list = [...results]
    if (resultsFilter) {
      const q = resultsFilter.toLowerCase()
      list = list.filter(r => {
        const strat = strategies.find(s => s.id === r.id)
        return r.id.toLowerCase().includes(q) || strat?.name.toLowerCase().includes(q) || strat?.family.toLowerCase().includes(q)
      })
    }

    list.sort((a, b) => {
      let valA = 0
      let valB = 0
      if (sortField === "sharpe") {
        valA = a.result.metrics.sharpe ?? -99
        valB = b.result.metrics.sharpe ?? -99
      } else if (sortField === "cagr") {
        valA = a.result.metrics.cagr ?? -99
        valB = b.result.metrics.cagr ?? -99
      } else if (sortField === "total_return") {
        valA = a.result.metrics.total_return ?? -99
        valB = b.result.metrics.total_return ?? -99
      } else if (sortField === "max_drawdown") {
        valA = a.result.metrics.max_drawdown ?? 0
        valB = b.result.metrics.max_drawdown ?? 0
      } else if (sortField === "trades") {
        valA = a.result.info.n_trades ?? 0
        valB = b.result.info.n_trades ?? 0
      }
      return sortAsc ? valA - valB : valB - valA
    })
    return list
  }, [results, sortField, sortAsc, resultsFilter, strategies])

  const exportCsv = () => {
    if (results.length === 0) return
    const headers = ["Strategy_ID", "Strategy_Name", "Family", "Total_Return", "CAGR", "Sharpe", "Max_Drawdown", "Trades", "Tickers", "Period"]
    const rows = results.map(r => {
      const s = strategies.find(x => x.id === r.id)
      return [
        r.id,
        `"${s?.name || r.id}"`,
        s?.family || "Other",
        r.result.metrics.total_return,
        r.result.metrics.cagr,
        r.result.metrics.sharpe,
        r.result.metrics.max_drawdown,
        r.result.info.n_trades,
        `"${selectedTickers.join(";")}"`,
        period,
      ].join(",")
    })
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n")
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    link.setAttribute("download", `stock1_backtest_${period}_${new Date().toISOString().slice(0, 10)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const strategyOptions = strategies.map(s => ({ value: s.id, label: s.name, hint: s.family }))

  return (
    <TooltipProvider>
      <div className="space-y-5">
        {/* HERO CONSENSUS RADAR ("WHAT SHOULD I DO RIGHT NOW?") */}
        <Card className="border border-border/80 shadow-md bg-gradient-to-b from-card/90 via-card/70 to-card/50 backdrop-blur-xl overflow-hidden relative">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-blue-500 via-emerald-500 to-cyan-500 opacity-80" />
          <CardHeader className="pb-3 pt-5 px-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="space-y-1">
                <CardTitle className="text-base sm:text-lg flex items-center gap-2 tracking-tight">
                  <div className="h-7 w-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
                    <Sparkles className="h-4 w-4 text-primary" />
                  </div>
                  <span>Real-Time Quantitative Consensus</span>
                  <Badge variant="outline" className="text-[11px] font-mono font-medium border-primary/30 text-primary">
                    {strategies.length > 0 ? `${strategies.length} Alpha Signals` : "Alpha Signals"}
                  </Badge>
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground">
                  Bayesian signal consensus weighted by each strategy's out-of-sample Sharpe ratio over rolling windows.
                </CardDescription>
              </div>

              {decLoading && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono bg-muted/40 px-3 py-1.5 rounded-lg border border-border/60">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                  <span>Scanning universe...</span>
                </div>
              )}
            </div>
          </CardHeader>

          <CardContent className="px-5 pb-5">
            {decError && (
              <div className="mb-3 p-2.5 rounded-xl border border-rose-500/30 bg-rose-500/5 text-xs text-rose-400">
                Consensus scan failed: {decError}
              </div>
            )}
            {decisions.length === 0 && !decLoading && !decError && (
              <div className="py-8 text-center border border-dashed border-border/70 rounded-xl bg-muted/10 text-xs text-muted-foreground">
                Add stock tickers below to run live consensus across quantitative algorithms.
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {decisions.map(d => {
                const isBuy = d.decision === "BUY"
                const isSell = d.decision === "SELL"

                const borderStyle = isBuy
                  ? "border-emerald-500/40 hover:border-emerald-500/80 bg-gradient-to-b from-emerald-500/10 via-emerald-500/5 to-transparent shadow-bullish"
                  : isSell
                  ? "border-rose-500/40 hover:border-rose-500/80 bg-gradient-to-b from-rose-500/10 via-rose-500/5 to-transparent shadow-bearish"
                  : "border-border/80 hover:border-border bg-card/60"

                const badgeStyle = isBuy
                  ? "bg-emerald-500 text-white font-bold"
                  : isSell
                  ? "bg-rose-500 text-white font-bold"
                  : "bg-muted text-muted-foreground font-semibold"

                return (
                  <div
                    key={d.ticker}
                    className={`group relative rounded-xl border p-3.5 transition-all duration-200 flex flex-col justify-between ${borderStyle}`}
                  >
                    <div>
                      {/* Ticker & Signal Header */}
                      <div className="flex items-center justify-between gap-1 mb-2">
                        <span className="font-mono font-bold text-sm text-foreground tracking-tight">{d.ticker}</span>
                        <span className={`text-[11px] px-2 py-0.5 rounded-full ${badgeStyle}`}>
                          {d.decision}
                        </span>
                      </div>

                      {/* Confidence & Score */}
                      <div className="space-y-1.5 mb-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground text-[11px]">Confidence</span>
                          <span className="font-mono font-semibold text-foreground text-xs">
                            {d.confidence.toFixed(0)}%
                          </span>
                        </div>
                        {/* Progress bar */}
                        <div className="w-full bg-muted/60 h-1.5 rounded-full overflow-hidden flex">
                          <div
                            className="bg-emerald-500 h-full transition-all duration-500"
                            style={{ width: `${d.long_pct}%` }}
                            title={`Long: ${d.long_pct.toFixed(0)}%`}
                          />
                          <div
                            className="bg-rose-500 h-full transition-all duration-500"
                            style={{ width: `${d.short_pct}%` }}
                            title={`Short: ${d.short_pct.toFixed(0)}%`}
                          />
                        </div>

                        <div className="flex justify-between text-[10px] text-muted-foreground font-mono pt-0.5">
                          <span className="text-emerald-500 font-medium">↑ {d.n_long} Long</span>
                          <span className="text-rose-500 font-medium">↓ {d.n_short} Short</span>
                        </div>
                      </div>

                      {/* Trade plan: entry / stop / target / timeframe */}
                      {d.plan && (
                        <div className="rounded-lg border border-border/50 bg-muted/20 p-2 space-y-1.5">
                          <div className="grid grid-cols-3 gap-1 text-center">
                            <div>
                              <div className="text-[9px] uppercase font-mono text-muted-foreground">
                                Entry{d.plan.live_entry ? " · Live" : ""}
                              </div>
                              <div className="text-xs font-mono font-bold text-foreground">
                                ₹{d.plan.entry.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                              </div>
                            </div>
                            <div>
                              <div className="text-[9px] uppercase font-mono text-rose-400">Stop</div>
                              <div className="text-xs font-mono font-bold text-rose-400">
                                ₹{d.plan.stop_loss.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                              </div>
                              <div className="text-[9px] font-mono text-rose-400/70">{fmtSigned(d.plan.stop_pct)}</div>
                            </div>
                            <div>
                              <div className="text-[9px] uppercase font-mono text-emerald-400">Target</div>
                              <div className="text-xs font-mono font-bold text-emerald-400">
                                ₹{d.plan.target.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                              </div>
                              <div className="text-[9px] font-mono text-emerald-400/70">{fmtSigned(d.plan.target_pct)}</div>
                            </div>
                          </div>
                          <div className="flex items-center justify-between text-[10px] font-mono">
                            <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                              {d.plan.timeframe}
                            </span>
                            <span className="text-muted-foreground" title="Reward-to-risk">
                              R:R {d.plan.risk_reward}
                            </span>
                          </div>
                          <p className="text-[10px] leading-relaxed text-muted-foreground" title={d.plan.insight}>
                            {d.plan.insight}
                          </p>
                          <p className="text-[9px] text-muted-foreground/60 font-mono">
                            {d.plan.live_entry ? `Live ${d.plan.entry_label} · ` : `As of ${d.plan.as_of} · `}
                            ATR ₹{d.plan.atr} ({d.plan.atr_pct}%)
                          </p>
                        </div>
                      )}
                      {!d.plan && (
                        <div className="rounded-lg border border-dashed border-border/50 p-2 text-[10px] text-muted-foreground">
                          Levels unavailable — feed skipped this ticker. Hit Scan to retry.
                        </div>
                      )}

                      {/* Top Strategies driving signal */}
                      {d.long_strategies.length > 0 && isBuy && (
                        <div className="pt-2 border-t border-border/50 space-y-1">
                          <span className="text-[10px] uppercase font-mono tracking-wider text-muted-foreground">
                            Top Signals:
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {d.long_strategies.slice(0, 2).map(s => (
                              <span
                                key={s}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 truncate max-w-[130px]"
                              >
                                {strategyName(s, strategies)}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {d.short_strategies.length > 0 && isSell && (
                        <div className="pt-2 border-t border-border/50 space-y-1">
                          <span className="text-[10px] uppercase font-mono tracking-wider text-muted-foreground">
                            Top Signals:
                          </span>
                          <div className="flex flex-wrap gap-1">
                            {d.short_strategies.slice(0, 2).map(s => (
                              <span
                                key={s}
                                className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 truncate max-w-[130px]"
                              >
                                {strategyName(s, strategies)}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Action shortcuts */}
                    <div className="mt-3 pt-2 border-t border-border/50 flex items-center justify-between gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          const sid = isBuy ? d.long_strategies[0] : isSell ? d.short_strategies[0] : "magic_formula"
                          if (sid) setSelectedStrategies([sid])
                          setSelectedTickers([d.ticker])
                          onRunCustom()
                        }}
                        className="h-6 px-2 text-[10px] font-medium text-muted-foreground hover:text-foreground gap-1"
                        title="Run individual backtest on this ticker"
                      >
                        <Zap className="h-3 w-3 text-primary" />
                        Test
                      </Button>

                      {onNavigateToPaper && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onNavigateToPaper(d.ticker, isSell ? "sell" : "buy")}
                          className="h-6 px-2 text-[10px] font-medium text-muted-foreground hover:text-foreground gap-1"
                          title="Open order in Paper Trading terminal"
                        >
                          <Briefcase className="h-3 w-3 text-purple-400" />
                          Trade
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* WORKBENCH CONTROLS (TICKERS + PERIOD + RUN) */}
        <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur">
          <CardContent className="pt-5 pb-5 px-5">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
              {/* Tickers Column */}
              <div className="lg:col-span-7 space-y-2.5">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2 text-xs font-semibold text-foreground/90">
                    Active Universe ({selectedTickers.length}/25)
                    <TooltipUI>
                      <TooltipTrigger asChild>
                        <HelpCircle className="h-3.5 w-3.5 text-muted-foreground cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-xs">
                        Supports global securities: Indian stocks (.NS, .BO), US equities (AAPL, NVDA), Crypto (BTC-USD), Commodities, & FX.
                      </TooltipContent>
                    </TooltipUI>
                  </Label>

                  {/* Quick Category Chips */}
                  <div className="hidden sm:flex items-center gap-1 text-[11px] text-muted-foreground">
                    <span className="text-[10px] uppercase font-mono mr-1">Quick Add:</span>
                    {QUICK_CATEGORIES.map(cat => (
                      <button
                        key={cat.name}
                        type="button"
                        onClick={() => applyCategory(cat.tickers)}
                        className="px-2 py-0.5 rounded-md border border-border/70 bg-background/60 hover:bg-accent text-[10px] transition-colors"
                      >
                        {cat.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Search Input with dropdown */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                  <Input
                    value={tickerSearch}
                    onChange={e => {
                      setTickerSearch(e.target.value)
                      setShowSearch(true)
                    }}
                    onFocus={() => setShowSearch(true)}
                    onKeyDown={e => {
                      if (e.key === "Enter" && tickerSearch) {
                        e.preventDefault()
                        const match = searchResults.find(
                          r => r.symbol.toUpperCase() === tickerSearch.toUpperCase()
                        )
                        addTicker(match ? match.symbol : tickerSearch)
                      }
                    }}
                    placeholder="Search ticker symbol (e.g. RELIANCE, AAPL, NVDA, BTC-USD)..."
                    className="pl-9 h-10 bg-background/70 font-mono text-xs border-border/80 focus-visible:ring-primary/30"
                  />

                  {showSearch && searchResults.length > 0 && (
                    <div className="absolute z-50 mt-1 w-full border border-border rounded-xl bg-popover/95 text-popover-foreground shadow-2xl backdrop-blur-md max-h-72 overflow-y-auto divide-y divide-border/40">
                      {searchResults.map(r => (
                        <button
                          key={r.symbol}
                          type="button"
                          onClick={() => addTicker(r.symbol)}
                          className="w-full text-left px-3.5 py-2.5 text-xs hover:bg-accent/60 transition-colors flex items-center justify-between"
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-semibold text-foreground text-sm">{r.symbol}</span>
                              <Badge variant="outline" className="text-[10px] font-mono px-1.5 py-0">
                                {r.exchange || r.quoteType}
                              </Badge>
                            </div>
                            <div className="text-muted-foreground text-[11px] truncate max-w-sm">{r.shortname}</div>
                          </div>
                          <span className="text-[11px] text-primary font-medium">+ Add</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Selected Tickers Badges */}
                <div className="flex flex-wrap gap-1.5 max-h-20 overflow-y-auto pt-1">
                  {selectedTickers.map(t => (
                    <Badge
                      key={t}
                      variant="secondary"
                      className="cursor-pointer text-[11px] font-mono px-2 py-0.5 rounded-md hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 border transition-all gap-1 group"
                      onClick={() => removeTicker(t)}
                    >
                      <span>{t}</span>
                      <span className="text-muted-foreground group-hover:text-destructive text-xs">×</span>
                    </Badge>
                  ))}
                  {selectedTickers.length === 0 && (
                    <span className="text-xs text-muted-foreground italic">No tickers selected.</span>
                  )}
                </div>
              </div>

              {/* Period Selector Column */}
              <div className="lg:col-span-3 space-y-2.5">
                <Label className="text-xs font-semibold text-foreground/90">Historical Backtest Horizon</Label>
                <div className="flex gap-1">
                  {QUICK_PERIODS.map(p => (
                    <button
                      key={p.value}
                      type="button"
                      onClick={() => setPeriod(p.value)}
                      title={`Last ${p.label}`}
                      className={`flex-1 h-7 rounded-lg text-[11px] font-mono font-medium transition-all border ${
                        period === p.value
                          ? "bg-primary/15 text-primary border-primary/40 font-semibold"
                          : "text-muted-foreground hover:text-foreground border-border/50"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <div className="grid grid-cols-4 sm:grid-cols-7 gap-1 bg-muted/30 p-1 rounded-xl border border-border/70">
                  {PERIOD_OPTIONS.map(p => (
                    <button
                      key={p.value}
                      type="button"
                      onClick={() => setPeriod(p.value)}
                      className={`h-8 rounded-lg text-xs font-mono font-medium transition-all ${
                        period === p.value
                          ? "bg-card text-foreground shadow-sm font-semibold border border-border/80"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>Selected: {period.toUpperCase()}</span>
                  <span>Friction: 10bps/trade</span>
                </div>
              </div>

              {/* Run Engine Button */}
              <div className="lg:col-span-2 space-y-2.5 lg:pt-6">
                <Button
                  onClick={onRunCustom}
                  disabled={loading || selectedTickers.length === 0 || selectedStrategies.length === 0}
                  className="w-full h-10 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-blue-500/20 transition-all gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>{progress ? `${progress.done}/${progress.total}` : "Simulating..."}</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 fill-current" />
                      <span>Execute Backtest</span>
                    </>
                  )}
                </Button>
                {progress && (
                  <div className="space-y-1">
                    <div className="w-full bg-muted/70 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-primary h-full transition-all duration-300"
                        style={{ width: `${(progress.done / progress.total) * 100}%` }}
                      />
                    </div>
                    <p className="text-[10px] text-muted-foreground text-center truncate">{progress.label}</p>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {error && (
          <div className="p-3.5 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* WORKSPACE GRID: STRATEGIES & PRESETS (LEFT) + CHARTS & METRICS (RIGHT) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* LEFT SIDEBAR: STRATEGY PICKER & QUANT PRESETS */}
          <div className="lg:col-span-4 space-y-4">
            <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur">
              <CardHeader className="pb-3 pt-4 px-4">
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span>Strategy Configuration</span>
                  <Badge variant="outline" className="text-[10px] font-mono">
                    {selectedStrategies.length} selected
                  </Badge>
                </CardTitle>
                <CardDescription className="text-xs">
                  Select algorithms or execute institutional quant presets.
                </CardDescription>
              </CardHeader>

              <CardContent className="space-y-4 px-4 pb-4">
                <Combobox
                  options={strategyOptions}
                  value={selectedStrategies}
                  onChange={setSelectedStrategies}
                  placeholder="Select strategies to backtest..."
                  multi
                  className="rounded-xl border-border/80 text-xs"
                />

                {/* Quick Presets */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between">
                    <Label className="text-[11px] uppercase tracking-wider font-mono text-muted-foreground">
                      Preset Comparisons
                    </Label>
                    <span className="text-[10px] text-muted-foreground">1-Click</span>
                  </div>

                  <div className="grid grid-cols-1 gap-1.5">
                    {PRESETS.map(p => {
                      const Icon = p.icon
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onClick={() => runPreset(p)}
                          disabled={loading || selectedTickers.length === 0}
                          className="w-full text-left p-2.5 rounded-xl border border-border/60 hover:border-primary/50 hover:bg-primary/5 bg-background/40 transition-all flex items-start gap-2.5 group disabled:opacity-50"
                        >
                          <div className="h-7 w-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 mt-0.5 group-hover:scale-105 transition-transform">
                            <Icon className="h-3.5 w-3.5 text-primary" />
                          </div>
                          <div className="flex flex-col min-w-0 flex-1">
                            <span className="text-xs font-semibold text-foreground group-hover:text-primary transition-colors">
                              {p.name}
                            </span>
                            <span className="text-[11px] text-muted-foreground truncate">{p.desc}</span>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* OOS RECOMMENDATIONS LIST */}
            <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur">
              <CardHeader className="pb-3 pt-4 px-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-emerald-500" />
                    <span>Top OOS Sharpe Alpha</span>
                  </CardTitle>
                  {recLoading && <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />}
                </div>
                <CardDescription className="text-xs">
                  Out-of-sample Sharpe over current ticker basket. Click to add.
                </CardDescription>
              </CardHeader>

              <CardContent className="px-4 pb-4">
                {recommendations.length === 0 && !recLoading && (
                  <p className="text-xs text-muted-foreground py-4 text-center">Add tickers to calculate OOS Sharpe.</p>
                )}

                <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
                  {recommendations.slice(0, 12).map(r => {
                    const sharpe = r.oos_sharpe ?? -99
                    const positive = sharpe > 0
                    const strat = strategies.find(s => s.id === r.strategy_id)
                    const isSelected = selectedStrategies.includes(r.strategy_id)

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
                            className={`w-full flex items-center justify-between gap-2 p-2 rounded-lg border transition-all text-left ${
                              isSelected
                                ? "border-primary bg-primary/10 text-primary"
                                : "border-border/60 hover:border-border hover:bg-accent/40 text-foreground"
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <span
                                className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${
                                  FAMILY_COLORS[r.family] || FAMILY_COLORS.Other
                                }`}
                              >
                                {r.family}
                              </span>
                              <span className="text-xs font-medium truncate">{strat?.name ?? r.strategy_id}</span>
                            </div>

                            <div className="flex items-center gap-2 font-mono text-xs tabular-nums shrink-0">
                              {r.error ? (
                                <span className="text-rose-500 text-[10px]">n/a</span>
                              ) : (
                                <>
                                  <span className={`font-semibold ${positive ? "text-emerald-500" : "text-rose-500"}`}>
                                    {sharpe.toFixed(2)}
                                  </span>
                                  <span className="text-muted-foreground text-[11px] w-12 text-right">
                                    {((r.total_return ?? 0) * 100).toFixed(0)}%
                                  </span>
                                </>
                              )}
                            </div>
                          </button>
                        </TooltipTrigger>
                        {r.reason && (
                          <TooltipContent className="max-w-sm bg-popover text-popover-foreground border shadow-xl p-2.5 text-xs">
                            <p className="font-semibold text-foreground mb-1">{strat?.name || r.strategy_id}</p>
                            <p className="text-muted-foreground leading-relaxed">{r.reason}</p>
                          </TooltipContent>
                        )}
                      </TooltipUI>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* RIGHT MAIN: KPI SUMMARY, INTERACTIVE CHARTS & SORTABLE RESULTS */}
          <div className="lg:col-span-8 space-y-4">
            {/* KPI METRIC CARDS (IF RESULTS AVAILABLE) */}
            {summaryKpi && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Card className="border-border/70 bg-card/90 shadow-sm p-3.5 space-y-1">
                  <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
                    Highest Sharpe
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold font-mono text-emerald-500">
                      {summaryKpi.bestSharpe.result.metrics.sharpe.toFixed(2)}
                    </span>
                    <span className="text-[11px] font-medium text-foreground truncate">
                      {strategyName(summaryKpi.bestSharpe.id, strategies)}
                    </span>
                  </div>
                </Card>

                <Card className="border-border/70 bg-card/90 shadow-sm p-3.5 space-y-1">
                  <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
                    Best Cumulative Return
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold font-mono text-blue-500">
                      {(summaryKpi.bestReturn.result.metrics.total_return * 100).toFixed(1)}%
                    </span>
                    <span className="text-[11px] font-medium text-foreground truncate">
                      {strategyName(summaryKpi.bestReturn.id, strategies)}
                    </span>
                  </div>
                </Card>

                <Card className="border-border/70 bg-card/90 shadow-sm p-3.5 space-y-1">
                  <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
                    Lowest Drawdown
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold font-mono text-amber-500">
                      {(summaryKpi.minDd.result.metrics.max_drawdown * 100).toFixed(1)}%
                    </span>
                    <span className="text-[11px] font-medium text-foreground truncate">
                      {strategyName(summaryKpi.minDd.id, strategies)}
                    </span>
                  </div>
                </Card>

                <Card className="border-border/70 bg-card/90 shadow-sm p-3.5 space-y-1">
                  <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
                    Mean Alpha Sharpe
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span
                      className={`text-xl font-bold font-mono ${
                        summaryKpi.avgSharpe > 0 ? "text-emerald-500" : "text-rose-500"
                      }`}
                    >
                      {summaryKpi.avgSharpe.toFixed(2)}
                    </span>
                    <span className="text-[11px] text-muted-foreground">across {summaryKpi.count} runs</span>
                  </div>
                </Card>
              </div>
            )}

            {/* PERFORMANCE CHART */}
            {results.length > 0 && (
              <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur">
                <CardHeader className="pb-2 pt-4 px-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-base font-semibold tracking-tight">
                        Comparative Trajectory · {selectedTickers.slice(0, 4).join(", ")}
                        {selectedTickers.length > 4 && ` +${selectedTickers.length - 4}`}
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Normalized cumulative growth starting from 1.0 baseline.
                      </CardDescription>
                    </div>

                    {/* Chart Mode Toggle */}
                    <div className="flex items-center gap-1 bg-muted/40 p-1 rounded-lg border border-border/70 self-start sm:self-auto">
                      <button
                        type="button"
                        onClick={() => setChartMode("equity")}
                        className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                          chartMode === "equity"
                            ? "bg-card text-foreground shadow-sm font-semibold"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        Equity Curve
                      </button>
                      <button
                        type="button"
                        onClick={() => setChartMode("drawdown")}
                        className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                          chartMode === "drawdown"
                            ? "bg-card text-foreground shadow-sm font-semibold"
                            : "text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        Drawdown %
                      </button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="px-5 pb-5 pt-2">
                  <div className="h-[340px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      {chartMode === "equity" ? (
                        <LineChart data={combinedEquityChart}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" vertical={false} />
                          <XAxis
                            dataKey="date"
                            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                            stroke="rgba(148, 163, 184, 0.3)"
                          />
                          <YAxis
                            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                            stroke="rgba(148, 163, 184, 0.3)"
                            domain={["auto", "auto"]}
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "rgba(15, 23, 42, 0.95)",
                              borderColor: "rgba(255, 255, 255, 0.1)",
                              borderRadius: "0.75rem",
                              boxShadow: "0 10px 25px -5px rgba(0,0,0,0.5)",
                              fontSize: "12px",
                              fontFamily: "JetBrains Mono, monospace",
                            }}
                          />
                          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                          {results.map((r, i) => (
                            <Line
                              key={r.id}
                              type="monotone"
                              name={strategyName(r.id, strategies)}
                              dataKey={r.id}
                              stroke={CHART_COLORS[i % CHART_COLORS.length]}
                              strokeWidth={2}
                              dot={false}
                              activeDot={{ r: 4 }}
                            />
                          ))}
                        </LineChart>
                      ) : (
                        <AreaChart data={combinedDrawdownChart}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.15)" vertical={false} />
                          <XAxis
                            dataKey="date"
                            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                            stroke="rgba(148, 163, 184, 0.3)"
                          />
                          <YAxis
                            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                            stroke="rgba(148, 163, 184, 0.3)"
                            domain={["auto", 0]}
                            unit="%"
                          />
                          <Tooltip
                            contentStyle={{
                              backgroundColor: "rgba(15, 23, 42, 0.95)",
                              borderColor: "rgba(255, 255, 255, 0.1)",
                              borderRadius: "0.75rem",
                              fontSize: "12px",
                              fontFamily: "JetBrains Mono, monospace",
                            }}
                            formatter={(value: any) => [`${value}%`, "Drawdown"]}
                          />
                          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                          {results.map((r, i) => (
                            <Area
                              key={r.id}
                              type="monotone"
                              name={strategyName(r.id, strategies)}
                              dataKey={r.id}
                              stroke={CHART_COLORS[i % CHART_COLORS.length]}
                              fill={CHART_COLORS[i % CHART_COLORS.length]}
                              fillOpacity={0.15}
                              strokeWidth={1.5}
                            />
                          ))}
                        </AreaChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* RESULTS DATA GRID */}
            {results.length > 0 && (
              <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur">
                <CardHeader className="pb-3 pt-4 px-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <CardTitle className="text-base font-semibold flex items-center gap-2">
                        <span>Performance Leaderboard ({sortedResults.length})</span>
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Metrics include transaction slippage & commission assumptions.
                      </CardDescription>
                    </div>

                    <div className="flex items-center gap-2">
                      <Input
                        value={resultsFilter}
                        onChange={e => setResultsFilter(e.target.value)}
                        placeholder="Filter results..."
                        className="h-8 text-xs w-36 sm:w-48 bg-background/50"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={exportCsv}
                        className="h-8 text-xs gap-1.5 border-border/80"
                      >
                        <Download className="h-3.5 w-3.5" />
                        <span>Export CSV</span>
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="px-5 pb-5 pt-0">
                  <div className="rounded-xl border border-border/60 overflow-hidden overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-muted/40 border-b border-border/70 text-muted-foreground">
                        <tr>
                          <th className="text-left py-2.5 px-3 font-semibold">Algorithm</th>
                          <th className="text-left py-2.5 px-3 font-semibold">Family</th>
                          <th
                            className="text-right py-2.5 px-3 font-semibold cursor-pointer hover:text-foreground transition-colors"
                            onClick={() => {
                              if (sortField === "total_return") setSortAsc(!sortAsc)
                              else {
                                setSortField("total_return")
                                setSortAsc(false)
                              }
                            }}
                          >
                            <div className="flex items-center justify-end gap-1">
                              <span>Total Return</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                          <th
                            className="text-right py-2.5 px-3 font-semibold cursor-pointer hover:text-foreground transition-colors"
                            onClick={() => {
                              if (sortField === "cagr") setSortAsc(!sortAsc)
                              else {
                                setSortField("cagr")
                                setSortAsc(false)
                              }
                            }}
                          >
                            <div className="flex items-center justify-end gap-1">
                              <span>CAGR</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                          <th
                            className="text-right py-2.5 px-3 font-semibold cursor-pointer hover:text-foreground transition-colors"
                            onClick={() => {
                              if (sortField === "sharpe") setSortAsc(!sortAsc)
                              else {
                                setSortField("sharpe")
                                setSortAsc(false)
                              }
                            }}
                          >
                            <div className="flex items-center justify-end gap-1 text-primary">
                              <span>Sharpe</span>
                              <ArrowUpDown className="h-3 w-3" />
                            </div>
                          </th>
                          <th
                            className="text-right py-2.5 px-3 font-semibold cursor-pointer hover:text-foreground transition-colors"
                            onClick={() => {
                              if (sortField === "max_drawdown") setSortAsc(!sortAsc)
                              else {
                                setSortField("max_drawdown")
                                setSortAsc(false)
                              }
                            }}
                          >
                            <div className="flex items-center justify-end gap-1">
                              <span>Max DD</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                          <th
                            className="text-right py-2.5 px-3 font-semibold cursor-pointer hover:text-foreground transition-colors"
                            onClick={() => {
                              if (sortField === "trades") setSortAsc(!sortAsc)
                              else {
                                setSortField("trades")
                                setSortAsc(false)
                              }
                            }}
                          >
                            <div className="flex items-center justify-end gap-1">
                              <span>Trades</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40 font-mono">
                        {sortedResults.map(r => {
                          const strat = strategies.find(s => s.id === r.id)
                          const sharpe = r.result.metrics.sharpe ?? -99
                          const isPositiveReturn = (r.result.metrics.total_return ?? 0) >= 0

                          return (
                            <tr key={r.id} className="hover:bg-accent/30 transition-colors">
                              <td className="py-2.5 px-3 font-sans font-medium text-foreground">
                                {strat?.name ?? r.id}
                              </td>
                              <td className="py-2.5 px-3">
                                {strat && (
                                  <span
                                    className={`text-[10px] px-1.5 py-0.5 rounded border font-mono ${
                                      FAMILY_COLORS[strat.family] || FAMILY_COLORS.Other
                                    }`}
                                  >
                                    {strat.family}
                                  </span>
                                )}
                              </td>
                              <td
                                className={`py-2.5 px-3 text-right tabular-nums font-semibold ${
                                  isPositiveReturn ? "text-emerald-500" : "text-rose-500"
                                }`}
                              >
                                {fmt(r.result.metrics.total_return)}
                              </td>
                              <td
                                className={`py-2.5 px-3 text-right tabular-nums ${
                                  (r.result.metrics.cagr ?? 0) >= 0 ? "text-emerald-500" : "text-rose-500"
                                }`}
                              >
                                {fmt(r.result.metrics.cagr)}
                              </td>
                              <td className="py-2.5 px-3 text-right tabular-nums">
                                <span
                                  className={`px-2 py-0.5 rounded-full font-bold text-[11px] ${
                                    sharpe >= 1.5
                                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                                      : sharpe > 0.5
                                      ? "bg-blue-500/20 text-blue-400 border border-blue-500/40"
                                      : sharpe > 0
                                      ? "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                                      : "bg-rose-500/20 text-rose-400 border border-rose-500/40"
                                  }`}
                                >
                                  {sharpe.toFixed(2)}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-right tabular-nums text-rose-500/90 font-medium">
                                {fmt(r.result.metrics.max_drawdown)}
                              </td>
                              <td className="py-2.5 px-3 text-right tabular-nums text-muted-foreground">
                                {r.result.info.n_trades}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* EMPTY STATE */}
            {!results.length && !loading && (
              <Card className="border-border/70 bg-card/60 border-dashed text-center py-16 px-4">
                <div className="max-w-md mx-auto space-y-3">
                  <div className="h-12 w-12 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto text-primary">
                    <Play className="h-6 w-6 ml-0.5 fill-current" />
                  </div>
                  <h3 className="text-base font-semibold text-foreground">Ready to simulate quantitative alpha</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Select algorithms from the left sidebar or launch one of our 1-click institutional presets (e.g. Smart Alpha Picks, Family Champions) to visualize risk-adjusted performance.
                  </p>
                </div>
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

function fmtSigned(v: number | undefined): string {
  if (v == null || Number.isNaN(v)) return "—"
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`
}
