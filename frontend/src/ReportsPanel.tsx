import { useEffect, useState, useMemo } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
  Legend,
  ScatterChart,
  Scatter,
  ZAxis,
  ReferenceLine,
} from "recharts"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Loader2,
  FileText,
  Download,
  Search,
  ArrowUpDown,
  ShieldAlert,
  Zap,
  RotateCw,
  TrendingUp,
  Award,
  BarChart3,
  SlidersHorizontal,
  Activity,
  Layers,
  Sparkles,
} from "lucide-react"

export interface WalkForwardRecord {
  strategy_id: string
  n_windows: number
  mean_oos_sharpe: number
  total_oos_return: number
  max_dd: number
}

export interface RegimeRecord {
  strategy_id: string
  regime: string
  sharpe: number
  total_return: number
  max_dd: number
  n_bars: number
}

interface ReportsPanelProps {
  onBacktestStrategy?: (strategyId: string) => void
}

type TabMode = "walk_forward" | "regime_stress" | "risk_return" | "executive_md"
type QuickFilter = "all" | "positive" | "high_sharpe" | "capital_pres"


export default function ReportsPanel({ onBacktestStrategy }: ReportsPanelProps) {
  const [activeTab, setActiveTab] = useState<TabMode>("walk_forward")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Data states
  const [wfData, setWfData] = useState<WalkForwardRecord[]>([])
  const [rgData, setRgData] = useState<RegimeRecord[]>([])
  const [markdownContent, setMarkdownContent] = useState<string>("")

  // Filter & search states
  const [search, setSearch] = useState("")
  const [quickFilter, setQuickFilter] = useState<QuickFilter>("all")
  const [sortCol, setSortCol] = useState<keyof WalkForwardRecord>("mean_oos_sharpe")
  const [sortAsc, setSortAsc] = useState(false)
  const [regimeMetric, setRegimeMetric] = useState<"sharpe" | "total_return">("sharpe")
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null)

  // Fetch all real validation data
  const loadAllReports = async () => {
    setLoading(true)
    setError(null)
    try {
      // 1. Try API endpoints first, fallback to static CSVs
      let parsedWf: WalkForwardRecord[] = []
      let parsedRg: RegimeRecord[] = []
      let mdText = ""

      // Walk Forward
      try {
        const wfRes = await fetch("/api/reports/walk-forward")
        if (wfRes.ok) {
          parsedWf = await wfRes.json()
        } else {
          throw new Error("API fallback")
        }
      } catch {
        const staticRes = await fetch("/reports/walk_forward.csv")
        if (!staticRes.ok) throw new Error("Could not load walk_forward.csv")
        const text = await staticRes.text()
        parsedWf = parseWalkForwardCsv(text)
      }

      // Regimes
      try {
        const rgRes = await fetch("/api/reports/regimes")
        if (rgRes.ok) {
          const body = await rgRes.json()
          parsedRg = body.rows || []
        } else {
          throw new Error("API fallback")
        }
      } catch {
        const staticRes = await fetch("/reports/regime_tests.csv")
        if (staticRes.ok) {
          const text = await staticRes.text()
          parsedRg = parseRegimesCsv(text)
        }
      }

      // Markdown report
      try {
        const mdRes = await fetch("/reports/regime_tests.md")
        if (mdRes.ok) {
          mdText = await mdRes.text()
        }
      } catch {
        // optional
      }

      setWfData(parsedWf)
      setRgData(parsedRg)
      setMarkdownContent(mdText)
    } catch (e: any) {
      setError(e.message || "Failed to load validation reports")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadAllReports()
  }, [])

  // Summary Metrics
  const summary = useMemo(() => {
    if (!wfData.length) {
      return {
        total: 0,
        positiveRatio: 0,
        medianSharpe: 0,
        topStrat: null as WalkForwardRecord | null,
        lowestDdStrat: null as WalkForwardRecord | null,
      }
    }

    const sharpes = wfData.map(r => r.mean_oos_sharpe).sort((a, b) => a - b)
    const positiveCount = sharpes.filter(s => s > 0).length
    const median = sharpes[Math.floor(sharpes.length / 2)] ?? 0
    const top = [...wfData].sort((a, b) => b.mean_oos_sharpe - a.mean_oos_sharpe)[0]
    const lowestDd = [...wfData]
      .filter(r => r.mean_oos_sharpe > 0)
      .sort((a, b) => Math.abs(a.max_dd) - Math.abs(b.max_dd))[0] || top

    return {
      total: wfData.length,
      positiveRatio: positiveCount / wfData.length,
      medianSharpe: median,
      topStrat: top,
      lowestDdStrat: lowestDd,
    }
  }, [wfData])

  // Filtered and sorted walk-forward records
  const filteredWfData = useMemo(() => {
    let list = [...wfData]

    // Quick filters
    if (quickFilter === "positive") {
      list = list.filter(r => r.mean_oos_sharpe > 0)
    } else if (quickFilter === "high_sharpe") {
      list = list.filter(r => r.mean_oos_sharpe >= 0.7)
    } else if (quickFilter === "capital_pres") {
      list = list.filter(r => Math.abs(r.max_dd) <= 0.10 && r.mean_oos_sharpe > 0)
    }

    // Search
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(r => r.strategy_id.toLowerCase().includes(q))
    }

    // Sorting
    list.sort((a, b) => {
      const valA = a[sortCol]
      const valB = b[sortCol]
      if (typeof valA === "number" && typeof valB === "number") {
        return sortAsc ? valA - valB : valB - valA
      }
      return sortAsc
        ? String(valA).localeCompare(String(valB))
        : String(valB).localeCompare(String(valA))
    })

    return list
  }, [wfData, quickFilter, search, sortCol, sortAsc])

  // Chart data for top 12 strategies by OOS Sharpe
  const barChartData = useMemo(() => {
    const sorted = [...wfData].sort((a, b) => b.mean_oos_sharpe - a.mean_oos_sharpe)
    return sorted.slice(0, 14).map(r => ({
      strategy_id: r.strategy_id,
      name: formatStrategyName(r.strategy_id),
      sharpe: Number(r.mean_oos_sharpe.toFixed(2)),
      returnPct: Number((r.total_oos_return * 100).toFixed(1)),
      maxDdPct: Number((r.max_dd * 100).toFixed(1)),
      windows: r.n_windows,
    }))
  }, [wfData])

  // Pivot matrix for regime stress tests
  const regimeMatrix = useMemo(() => {
    const map = new Map<string, Record<string, RegimeRecord>>()
    rgData.forEach(r => {
      if (!map.has(r.strategy_id)) {
        map.set(r.strategy_id, {})
      }
      map.get(r.strategy_id)![r.regime] = r
    })

    const rows = Array.from(map.entries()).map(([strategy_id, regimes]) => {
      const r2018 = regimes["2018_crash"]
      const r2020 = regimes["2020_covid"]
      const r2022 = regimes["2022_chop"]
      const rFull = regimes["full"]

      // Resilience classification
      let status: "All-Weather" | "Crisis-Resilient" | "Chop-Resilient" | "Bull-Dependent" | "High-Risk" = "High-Risk"
      const is2018Pos = (r2018?.sharpe || 0) > 0
      const is2020Pos = (r2020?.sharpe || 0) > 0
      const is2022Pos = (r2022?.sharpe || 0) > 0

      if (is2018Pos && is2020Pos && is2022Pos) {
        status = "All-Weather"
      } else if (is2020Pos) {
        status = "Crisis-Resilient"
      } else if (is2022Pos) {
        status = "Chop-Resilient"
      } else if ((rFull?.sharpe || 0) > 0) {
        status = "Bull-Dependent"
      }

      return {
        strategy_id,
        regimes,
        status,
        fullSharpe: rFull?.sharpe ?? 0,
        fullReturn: rFull?.total_return ?? 0,
      }
    })

    // Sort by full Sharpe descending
    rows.sort((a, b) => b.fullSharpe - a.fullSharpe)
    return rows
  }, [rgData])

  // Grouped bar chart data for top 8 strategies across regimes
  const regimeChartData = useMemo(() => {
    const topStrategies = regimeMatrix.slice(0, 8)
    return topStrategies.map(row => {
      const r2018 = row.regimes["2018_crash"]
      const r2020 = row.regimes["2020_covid"]
      const r2022 = row.regimes["2022_chop"]
      const rFull = row.regimes["full"]

      if (regimeMetric === "sharpe") {
        return {
          name: formatStrategyName(row.strategy_id),
          strategy_id: row.strategy_id,
          "2018 NBFC": Number((r2018?.sharpe || 0).toFixed(2)),
          "2020 COVID": Number((r2020?.sharpe || 0).toFixed(2)),
          "2022 Chop": Number((r2022?.sharpe || 0).toFixed(2)),
          "Full Sample": Number((rFull?.sharpe || 0).toFixed(2)),
        }
      } else {
        return {
          name: formatStrategyName(row.strategy_id),
          strategy_id: row.strategy_id,
          "2018 NBFC": Number(((r2018?.total_return || 0) * 100).toFixed(1)),
          "2020 COVID": Number(((r2020?.total_return || 0) * 100).toFixed(1)),
          "2022 Chop": Number(((r2022?.total_return || 0) * 100).toFixed(1)),
          "Full Sample": Number(((rFull?.total_return || 0) * 100).toFixed(1)),
        }
      }
    })
  }, [regimeMatrix, regimeMetric])

  // Scatter plot data for Risk vs Return
  const scatterData = useMemo(() => {
    return wfData.map(r => ({
      strategy_id: r.strategy_id,
      name: formatStrategyName(r.strategy_id),
      drawdown: Number((Math.abs(r.max_dd) * 100).toFixed(1)),
      returnPct: Number((r.total_oos_return * 100).toFixed(1)),
      sharpe: Number(r.mean_oos_sharpe.toFixed(2)),
    }))
  }, [wfData])

  const handleSort = (col: keyof WalkForwardRecord) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc)
    } else {
      setSortCol(col)
      setSortAsc(false)
    }
  }

  const downloadCsv = (filename: string, content: string) => {
    const blob = new Blob([content], { type: "text/csv;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const exportCurrentWfCsv = () => {
    if (!wfData.length) return
    const headers = ["strategy_id", "n_windows", "mean_oos_sharpe", "total_oos_return", "max_dd"]
    const rows = wfData.map(r => [
      r.strategy_id,
      r.n_windows,
      r.mean_oos_sharpe,
      r.total_oos_return,
      r.max_dd,
    ].join(","))
    downloadCsv("walk_forward_validation.csv", [headers.join(","), ...rows].join("\n"))
  }

  return (
    <div className="space-y-5 animate-in fade-in duration-300">
      {/* EXECUTIVE HEADER & SUMMARY METRICS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* KPI 1: Top OOS Sharpe */}
        <Card className="border-border/70 bg-card/85 backdrop-blur shadow-sm relative overflow-hidden group hover:border-primary/40 transition-all">
          <div className="absolute top-0 right-0 p-3 opacity-15 group-hover:opacity-25 transition-opacity">
            <Award className="h-10 w-10 text-primary" />
          </div>
          <CardHeader className="pb-1 pt-3.5 px-4">
            <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              Top Out-Of-Sample Sharpe
            </span>
          </CardHeader>
          <CardContent className="px-4 pb-3.5">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono tracking-tight text-emerald-400">
                {summary.topStrat ? summary.topStrat.mean_oos_sharpe.toFixed(2) : "—"}
              </span>
              <Badge variant="outline" className="font-mono text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/20 px-1.5 py-0">
                {summary.topStrat?.strategy_id || "None"}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              CAGR:{" "}
              <span className="text-emerald-400 font-mono font-medium">
                {summary.topStrat ? `+${(summary.topStrat.total_oos_return * 100).toFixed(1)}%` : "0%"}
              </span>{" "}
              · Max DD:{" "}
              <span className="text-rose-400 font-mono">
                {summary.topStrat ? `${(summary.topStrat.max_dd * 100).toFixed(2)}%` : "0%"}
              </span>
            </p>
          </CardContent>
        </Card>

        {/* KPI 2: Positive Alpha Ratio */}
        <Card className="border-border/70 bg-card/85 backdrop-blur shadow-sm relative overflow-hidden group hover:border-primary/40 transition-all">
          <div className="absolute top-0 right-0 p-3 opacity-15 group-hover:opacity-25 transition-opacity">
            <Activity className="h-10 w-10 text-emerald-500" />
          </div>
          <CardHeader className="pb-1 pt-3.5 px-4">
            <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
              Positive Alpha Ratio
            </span>
          </CardHeader>
          <CardContent className="px-4 pb-3.5">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono tracking-tight text-foreground">
                {(summary.positiveRatio * 100).toFixed(1)}%
              </span>
              <span className="text-xs text-muted-foreground font-mono">
                ({Math.round(summary.positiveRatio * summary.total)} / {summary.total} models)
              </span>
            </div>
            <div className="w-full bg-muted/60 rounded-full h-1.5 mt-2.5 overflow-hidden">
              <div
                className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, summary.positiveRatio * 100))}%` }}
              />
            </div>
          </CardContent>
        </Card>

        {/* KPI 3: Median OOS Sharpe */}
        <Card className="border-border/70 bg-card/85 backdrop-blur shadow-sm relative overflow-hidden group hover:border-primary/40 transition-all">
          <div className="absolute top-0 right-0 p-3 opacity-15 group-hover:opacity-25 transition-opacity">
            <SlidersHorizontal className="h-10 w-10 text-cyan-500" />
          </div>
          <CardHeader className="pb-1 pt-3.5 px-4">
            <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <BarChart3 className="h-3.5 w-3.5 text-cyan-500" />
              Median OOS Sharpe
            </span>
          </CardHeader>
          <CardContent className="px-4 pb-3.5">
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold font-mono tracking-tight ${summary.medianSharpe >= 0 ? "text-cyan-400" : "text-rose-400"}`}>
                {summary.medianSharpe.toFixed(2)}
              </span>
              <Badge variant="outline" className="font-mono text-[10px] px-1.5 py-0 bg-muted/40">
                Cross-Fold Median
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              Evaluated across 12 to 39 rolling OOS test chunks
            </p>
          </CardContent>
        </Card>

        {/* KPI 4: Lowest Crisis Drawdown */}
        <Card className="border-border/70 bg-card/85 backdrop-blur shadow-sm relative overflow-hidden group hover:border-primary/40 transition-all">
          <div className="absolute top-0 right-0 p-3 opacity-15 group-hover:opacity-25 transition-opacity">
            <ShieldAlert className="h-10 w-10 text-primary" />
          </div>
          <CardHeader className="pb-1 pt-3.5 px-4">
            <span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <ShieldAlert className="h-3.5 w-3.5 text-primary" />
              Capital Preservation Peak
            </span>
          </CardHeader>
          <CardContent className="px-4 pb-3.5">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold font-mono tracking-tight text-emerald-400">
                {summary.lowestDdStrat ? `${(summary.lowestDdStrat.max_dd * 100).toFixed(2)}%` : "—"}
              </span>
              <Badge variant="outline" className="font-mono text-[10px] bg-primary/10 text-primary border-primary/20 px-1.5 py-0">
                {summary.lowestDdStrat?.strategy_id || "None"}
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">
              Lowest maximum drawdown among positive alpha strategies
            </p>
          </CardContent>
        </Card>
      </div>

      {/* REGIME CONTEXT ACCORDION/PILLS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-xl border border-rose-500/20 bg-rose-500/5 backdrop-blur space-y-1">
          <div className="flex items-center gap-1.5 text-rose-400 font-semibold text-xs font-mono">
            <ShieldAlert className="h-3.5 w-3.5" />
            2018 NBFC Liquidity Freeze
          </div>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            IL&amp;FS default trigger, severe mid-cap liquidity drain. Validates automated cash de-risking during credit freeze.
          </p>
        </div>

        <div className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5 backdrop-blur space-y-1">
          <div className="flex items-center gap-1.5 text-amber-400 font-semibold text-xs font-mono">
            <ShieldAlert className="h-3.5 w-3.5" />
            2020 COVID Flash Crash &amp; V-Spike
          </div>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            38% Nifty collapse in 4 weeks, India VIX hit 86. Evaluates rapid volatility stop-losses and aggressive mean-reversion re-entry.
          </p>
        </div>

        <div className="p-3.5 rounded-xl border border-blue-500/20 bg-blue-500/5 backdrop-blur space-y-1">
          <div className="flex items-center gap-1.5 text-blue-400 font-semibold text-xs font-mono">
            <ShieldAlert className="h-3.5 w-3.5" />
            2022 Global Rate-Hike Chop
          </div>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            +250 bps central bank rate hikes with zero persistent trend. Tests algorithm discipline to avoid overtrading whipsaws.
          </p>
        </div>
      </div>

      {/* MAIN CONTENT CARD */}
      <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur">
        {/* Navigation Tabs Header */}
        <CardHeader className="pb-3 pt-4 px-5 border-b border-border/50">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            {/* Tab navigation pills */}
            <div className="flex flex-wrap items-center gap-1.5 bg-muted/40 p-1 rounded-xl border border-border/70">
              <button
                type="button"
                onClick={() => setActiveTab("walk_forward")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === "walk_forward"
                    ? "bg-card text-foreground shadow-sm font-semibold border border-border/50"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Layers className="h-3.5 w-3.5 text-primary" />
                <span>Walk-Forward OOS</span>
                <Badge variant="outline" className="text-[10px] font-mono py-0 px-1 ml-0.5">
                  {wfData.length}
                </Badge>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("regime_stress")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === "regime_stress"
                    ? "bg-card text-foreground shadow-sm font-semibold border border-border/50"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                <span>Regime Stress-Matrix</span>
                <Badge variant="outline" className="text-[10px] font-mono py-0 px-1 ml-0.5">
                  {regimeMatrix.length}
                </Badge>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("risk_return")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === "risk_return"
                    ? "bg-card text-foreground shadow-sm font-semibold border border-border/50"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Activity className="h-3.5 w-3.5 text-cyan-400" />
                <span>Risk vs. Return Frontier</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("executive_md")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  activeTab === "executive_md"
                    ? "bg-card text-foreground shadow-sm font-semibold border border-border/50"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                <span>Committee Dossier</span>
              </button>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={loadAllReports}
                disabled={loading}
                className="h-8 text-xs gap-1.5 border-border/80"
              >
                <RotateCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-primary" : ""}`} />
                <span>Refresh</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={exportCurrentWfCsv}
                disabled={!wfData.length}
                className="h-8 text-xs gap-1.5 border-border/80"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Export CSV</span>
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-5">
          {loading && (
            <div className="py-24 text-center text-muted-foreground text-xs flex flex-col items-center justify-center gap-2">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span>Loading institutional validation models...</span>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/10 text-destructive text-xs space-y-1">
              <p className="font-semibold flex items-center gap-1.5">
                <ShieldAlert className="h-4 w-4" /> Validation Data Error
              </p>
              <p>{error}</p>
            </div>
          )}

          {!loading && !error && (
            <>
              {/* TAB 1: WALK-FORWARD OOS */}
              {activeTab === "walk_forward" && (
                <div className="space-y-6">
                  {/* Visual Chart: Top Strategies by OOS Sharpe */}
                  <div className="p-4 rounded-2xl border border-border/60 bg-muted/20 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground font-mono flex items-center gap-2">
                          <BarChart3 className="h-3.5 w-3.5 text-primary" />
                          Out-Of-Sample Sharpe Alpha Ranking (Top 14)
                        </h4>
                        <p className="text-[11px] text-muted-foreground">
                          Rolling 63-bar out-of-sample forward slices across Nifty large-cap equities.
                        </p>
                      </div>

                      <div className="flex items-center gap-3 text-[11px] font-mono text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <span className="h-2 w-2 rounded-full bg-emerald-400"></span> Sharpe &ge; 1.0
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="h-2 w-2 rounded-full bg-cyan-400"></span> 0.5 – 1.0
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="h-2 w-2 rounded-full bg-blue-400"></span> 0.0 – 0.5
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="h-2 w-2 rounded-full bg-rose-500"></span> &lt; 0.0
                        </span>
                      </div>
                    </div>

                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={barChartData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
                          <XAxis
                            dataKey="name"
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "monospace" }}
                            angle={-30}
                            textAnchor="end"
                            interval={0}
                          />
                          <YAxis
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "monospace" }}
                          />
                          <RechartsTooltip
                            content={({ active, payload }) => {
                              if (!active || !payload?.length) return null
                              const d = payload[0].payload
                              return (
                                <div className="rounded-xl border border-border/80 bg-popover/95 p-3 shadow-xl backdrop-blur text-xs font-mono space-y-1.5">
                                  <p className="font-semibold text-foreground text-sm flex items-center justify-between gap-4">
                                    <span>{d.name}</span>
                                    <Badge variant="outline" className="text-[10px] font-mono uppercase">
                                      {d.strategy_id}
                                    </Badge>
                                  </p>
                                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-muted-foreground pt-1 border-t border-border/50 text-[11px]">
                                    <span>Mean OOS Sharpe:</span>
                                    <span className="font-bold text-foreground text-right">{d.sharpe}</span>
                                    <span>Cumulative Return:</span>
                                    <span className={`font-semibold text-right ${d.returnPct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                                      {d.returnPct >= 0 ? `+${d.returnPct}%` : `${d.returnPct}%`}
                                    </span>
                                    <span>Max Drawdown:</span>
                                    <span className="text-rose-400 font-semibold text-right">{d.maxDdPct}%</span>
                                    <span>Rolling Windows:</span>
                                    <span className="text-foreground text-right">{d.windows}</span>
                                  </div>
                                </div>
                              )
                            }}
                          />
                          <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" opacity={0.6} />
                          <Bar
                            dataKey="sharpe"
                            radius={[4, 4, 0, 0]}
                            onClick={(entry: any) => {
                              const sid = entry?.strategy_id || entry?.payload?.strategy_id
                              if (sid && onBacktestStrategy) {
                                onBacktestStrategy(sid)
                              }
                            }}
                            className="cursor-pointer"
                          >
                            {barChartData.map((entry, idx) => {
                              let color = "#3b82f6" // blue
                              if (entry.sharpe >= 1.0) color = "#10b981" // emerald
                              else if (entry.sharpe >= 0.5) color = "#06b6d4" // cyan
                              else if (entry.sharpe < 0) color = "#f43f5e" // rose
                              return <Cell key={`cell-${idx}`} fill={color} />
                            })}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Filter & Search Bar */}
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Button
                        variant={quickFilter === "all" ? "secondary" : "ghost"}
                        size="sm"
                        onClick={() => setQuickFilter("all")}
                        className="h-7 text-xs font-mono"
                      >
                        All ({wfData.length})
                      </Button>
                      <Button
                        variant={quickFilter === "positive" ? "secondary" : "ghost"}
                        size="sm"
                        onClick={() => setQuickFilter("positive")}
                        className="h-7 text-xs font-mono text-emerald-400"
                      >
                        OOS Sharpe &gt; 0 ({wfData.filter(r => r.mean_oos_sharpe > 0).length})
                      </Button>
                      <Button
                        variant={quickFilter === "high_sharpe" ? "secondary" : "ghost"}
                        size="sm"
                        onClick={() => setQuickFilter("high_sharpe")}
                        className="h-7 text-xs font-mono text-cyan-400"
                      >
                        Institutional (&ge; 0.7)
                      </Button>
                      <Button
                        variant={quickFilter === "capital_pres" ? "secondary" : "ghost"}
                        size="sm"
                        onClick={() => setQuickFilter("capital_pres")}
                        className="h-7 text-xs font-mono text-primary"
                      >
                        Low DD (&le; 10%)
                      </Button>
                    </div>

                    <div className="relative max-w-xs">
                      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                      <Input
                        placeholder="Filter strategies..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="pl-8 h-8 text-xs bg-background/60 font-mono"
                      />
                    </div>
                  </div>

                  {/* Walk Forward Data Table */}
                  <div className="rounded-2xl border border-border/60 overflow-hidden overflow-x-auto shadow-sm">
                    <table className="w-full text-xs font-mono">
                      <thead className="bg-muted/40 border-b border-border/70 sticky top-0 bg-card z-10">
                        <tr>
                          <th className="py-2.5 px-3 text-left font-semibold text-muted-foreground w-12">#</th>
                          <th
                            onClick={() => handleSort("strategy_id")}
                            className="py-2.5 px-3 text-left font-semibold cursor-pointer hover:text-foreground text-muted-foreground transition-colors"
                          >
                            <div className="flex items-center gap-1">
                              <span>Strategy Identifier</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                          <th
                            onClick={() => handleSort("n_windows")}
                            className="py-2.5 px-3 text-center font-semibold cursor-pointer hover:text-foreground text-muted-foreground transition-colors"
                          >
                            <div className="flex items-center justify-center gap-1">
                              <span>Folds (Windows)</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                          <th
                            onClick={() => handleSort("mean_oos_sharpe")}
                            className="py-2.5 px-3 text-right font-semibold cursor-pointer hover:text-foreground text-muted-foreground transition-colors"
                          >
                            <div className="flex items-center justify-end gap-1">
                              <span>Mean OOS Sharpe</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                          <th
                            onClick={() => handleSort("total_oos_return")}
                            className="py-2.5 px-3 text-right font-semibold cursor-pointer hover:text-foreground text-muted-foreground transition-colors"
                          >
                            <div className="flex items-center justify-end gap-1">
                              <span>Cumulative OOS Return</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                          <th
                            onClick={() => handleSort("max_dd")}
                            className="py-2.5 px-3 text-right font-semibold cursor-pointer hover:text-foreground text-muted-foreground transition-colors"
                          >
                            <div className="flex items-center justify-end gap-1">
                              <span>Max Drawdown</span>
                              <ArrowUpDown className="h-3 w-3 opacity-60" />
                            </div>
                          </th>
                          <th className="py-2.5 px-3 text-center font-semibold text-muted-foreground">Resilience Grade</th>
                          {onBacktestStrategy && (
                            <th className="py-2.5 px-3 text-center font-semibold text-muted-foreground">Action</th>
                          )}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {filteredWfData.map((row, idx) => {
                          const isTopTier = row.mean_oos_sharpe >= 0.7
                          const isPos = row.mean_oos_sharpe > 0
                          return (
                            <tr
                              key={row.strategy_id}
                              className={`hover:bg-accent/30 transition-colors ${
                                selectedStrategy === row.strategy_id ? "bg-primary/10" : ""
                              }`}
                              onClick={() => setSelectedStrategy(row.strategy_id)}
                            >
                              <td className="py-2.5 px-3 text-muted-foreground text-center">{idx + 1}</td>
                              <td className="py-2.5 px-3 font-semibold text-foreground">
                                <div className="flex items-center gap-2">
                                  <span>{row.strategy_id}</span>
                                  {row.mean_oos_sharpe >= 1.5 && (
                                    <Badge variant="outline" className="text-[9px] font-mono px-1 py-0 bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                                      Alpha Leader
                                    </Badge>
                                  )}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-center text-muted-foreground tabular-nums">
                                {row.n_windows} windows
                              </td>
                              <td className="py-2.5 px-3 text-right tabular-nums">
                                <span
                                  className={`inline-block px-2 py-0.5 rounded font-bold ${
                                    row.mean_oos_sharpe >= 1.0
                                      ? "bg-emerald-500/15 text-emerald-400"
                                      : isPos
                                      ? "text-emerald-500"
                                      : "text-rose-500"
                                  }`}
                                >
                                  {row.mean_oos_sharpe.toFixed(2)}
                                </span>
                              </td>
                              <td
                                className={`py-2.5 px-3 text-right tabular-nums font-medium ${
                                  row.total_oos_return >= 0 ? "text-emerald-400" : "text-rose-400"
                                }`}
                              >
                                {row.total_oos_return >= 0 ? `+${(row.total_oos_return * 100).toFixed(2)}%` : `${(row.total_oos_return * 100).toFixed(2)}%`}
                              </td>
                              <td className="py-2.5 px-3 text-right tabular-nums font-mono text-rose-400">
                                {(row.max_dd * 100).toFixed(2)}%
                              </td>
                              <td className="py-2.5 px-3 text-center">
                                {isTopTier ? (
                                  <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] font-mono">
                                    Grade A
                                  </Badge>
                                ) : isPos ? (
                                  <Badge variant="outline" className="text-[10px] font-mono text-blue-400 border-blue-500/20">
                                    Grade B
                                  </Badge>
                                ) : (
                                  <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground border-border">
                                    Decayed
                                  </Badge>
                                )}
                              </td>
                              {onBacktestStrategy && (
                                <td className="py-2.5 px-3 text-center">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={e => {
                                      e.stopPropagation()
                                      onBacktestStrategy(row.strategy_id)
                                    }}
                                    className="h-6 px-2 text-[10px] text-muted-foreground hover:text-primary gap-1"
                                    title={`Launch full backtest for ${row.strategy_id}`}
                                  >
                                    <Zap className="h-3 w-3 text-primary" />
                                    <span>Backtest</span>
                                  </Button>
                                </td>
                              )}
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 2: REGIME STRESS-MATRIX */}
              {activeTab === "regime_stress" && (
                <div className="space-y-6">
                  {/* Regime Comparison Chart */}
                  <div className="p-4 rounded-2xl border border-border/60 bg-muted/20 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground font-mono flex items-center gap-2">
                          <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                          Multi-Regime Performance Comparison (Top 8 Models)
                        </h4>
                        <p className="text-[11px] text-muted-foreground">
                          Evaluates how strategy metrics performed across crisis flash-crashes versus full bull runs.
                        </p>
                      </div>

                      {/* Metric Toggle */}
                      <div className="flex items-center bg-card p-1 rounded-lg border border-border/70 text-xs font-mono">
                        <button
                          type="button"
                          onClick={() => setRegimeMetric("sharpe")}
                          className={`px-2.5 py-1 rounded transition-all ${
                            regimeMetric === "sharpe" ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground"
                          }`}
                        >
                          Sharpe Ratio
                        </button>
                        <button
                          type="button"
                          onClick={() => setRegimeMetric("total_return")}
                          className={`px-2.5 py-1 rounded transition-all ${
                            regimeMetric === "total_return" ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground"
                          }`}
                        >
                          Total Return %
                        </button>
                      </div>
                    </div>

                    <div className="h-72 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={regimeChartData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
                          <XAxis
                            dataKey="name"
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "monospace" }}
                            angle={-25}
                            textAnchor="end"
                            interval={0}
                          />
                          <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "monospace" }} />
                          <RechartsTooltip
                            content={({ active, payload, label }) => {
                              if (!active || !payload?.length) return null
                              return (
                                <div className="rounded-xl border border-border/80 bg-popover/95 p-3 shadow-xl backdrop-blur text-xs font-mono space-y-1.5">
                                  <p className="font-semibold text-foreground text-sm">{label}</p>
                                  <div className="space-y-1 pt-1 border-t border-border/50 text-[11px]">
                                    {payload.map((item, i) => (
                                      <div key={i} className="flex items-center justify-between gap-4">
                                        <span className="flex items-center gap-1.5" style={{ color: item.color }}>
                                          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
                                          {item.name}:
                                        </span>
                                        <span className="font-bold text-foreground">
                                          {regimeMetric === "sharpe" ? Number(item.value).toFixed(2) : `${Number(item.value).toFixed(1)}%`}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )
                            }}
                          />
                          <Legend
                            wrapperStyle={{ fontSize: "11px", fontFamily: "monospace", paddingTop: "8px" }}
                          />
                          <ReferenceLine y={0} stroke="hsl(var(--muted-foreground))" strokeDasharray="3 3" opacity={0.5} />
                          <Bar dataKey="2018 NBFC" fill="#f43f5e" radius={[3, 3, 0, 0]} />
                          <Bar dataKey="2020 COVID" fill="#f59e0b" radius={[3, 3, 0, 0]} />
                          <Bar dataKey="2022 Chop" fill="#3b82f6" radius={[3, 3, 0, 0]} />
                          <Bar dataKey="Full Sample" fill="#10b981" radius={[3, 3, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Regime Matrix Table */}
                  <div className="rounded-2xl border border-border/60 overflow-hidden overflow-x-auto shadow-sm">
                    <table className="w-full text-xs font-mono">
                      <thead className="bg-muted/40 border-b border-border/70 sticky top-0 bg-card z-10">
                        <tr>
                          <th className="py-2.5 px-3 text-left font-semibold text-muted-foreground">Strategy</th>
                          <th className="py-2.5 px-3 text-center font-semibold text-rose-400">2018 Crash (Sharpe / Ret)</th>
                          <th className="py-2.5 px-3 text-center font-semibold text-amber-400">2020 COVID (Sharpe / Ret)</th>
                          <th className="py-2.5 px-3 text-center font-semibold text-blue-400">2022 Chop (Sharpe / Ret)</th>
                          <th className="py-2.5 px-3 text-center font-semibold text-emerald-400">Full Cycle Sharpe</th>
                          <th className="py-2.5 px-3 text-center font-semibold text-muted-foreground">Resilience Verdict</th>
                          {onBacktestStrategy && (
                            <th className="py-2.5 px-3 text-center font-semibold text-muted-foreground">Action</th>
                          )}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/40">
                        {regimeMatrix.map((row, idx) => {
                          const r2018 = row.regimes["2018_crash"]
                          const r2020 = row.regimes["2020_covid"]
                          const r2022 = row.regimes["2022_chop"]
                          const rFull = row.regimes["full"]

                          let verdictBadge = (
                            <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
                              High Risk
                            </Badge>
                          )
                          if (row.status === "All-Weather") {
                            verdictBadge = (
                              <Badge className="bg-emerald-500/15 text-emerald-400 border-emerald-500/30 text-[10px] font-mono">
                                All-Weather
                              </Badge>
                            )
                          } else if (row.status === "Crisis-Resilient") {
                            verdictBadge = (
                              <Badge className="bg-blue-500/15 text-blue-400 border-blue-500/30 text-[10px] font-mono">
                                Crisis Resilient
                              </Badge>
                            )
                          } else if (row.status === "Chop-Resilient") {
                            verdictBadge = (
                              <Badge className="bg-cyan-500/15 text-cyan-400 border-cyan-500/30 text-[10px] font-mono">
                                Chop Proof
                              </Badge>
                            )
                          } else if (row.status === "Bull-Dependent") {
                            verdictBadge = (
                              <Badge className="bg-amber-500/15 text-amber-400 border-amber-500/30 text-[10px] font-mono">
                                Bull Only
                              </Badge>
                            )
                          }

                          return (
                            <tr key={idx} className="hover:bg-accent/30 transition-colors">
                              <td className="py-2.5 px-3 font-semibold text-foreground">{row.strategy_id}</td>
                              <td className="py-2.5 px-3 text-center tabular-nums">
                                <span className={Number(r2018?.sharpe || 0) > 0 ? "text-emerald-400 font-medium" : "text-rose-400"}>
                                  {r2018 ? `${r2018.sharpe.toFixed(2)} (${(r2018.total_return * 100).toFixed(1)}%)` : "—"}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-center tabular-nums">
                                <span className={Number(r2020?.sharpe || 0) > 0 ? "text-emerald-400 font-medium" : "text-rose-400"}>
                                  {r2020 ? `${r2020.sharpe.toFixed(2)} (${(r2020.total_return * 100).toFixed(1)}%)` : "—"}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-center tabular-nums">
                                <span className={Number(r2022?.sharpe || 0) > 0 ? "text-emerald-400 font-medium" : "text-rose-400"}>
                                  {r2022 ? `${r2022.sharpe.toFixed(2)} (${(r2022.total_return * 100).toFixed(1)}%)` : "—"}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-center tabular-nums font-bold">
                                <span className={Number(rFull?.sharpe || 0) > 0 ? "text-emerald-400" : "text-rose-400"}>
                                  {rFull ? rFull.sharpe.toFixed(2) : "—"}
                                </span>
                              </td>
                              <td className="py-2.5 px-3 text-center">{verdictBadge}</td>
                              {onBacktestStrategy && (
                                <td className="py-2.5 px-3 text-center">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => onBacktestStrategy(row.strategy_id)}
                                    className="h-6 px-1.5 text-[10px] text-muted-foreground hover:text-primary gap-1"
                                  >
                                    <Zap className="h-3 w-3 text-primary" />
                                    <span>Test</span>
                                  </Button>
                                </td>
                              )}
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* TAB 3: RISK VS RETURN SCATTER */}
              {activeTab === "risk_return" && (
                <div className="space-y-4">
                  <div className="p-4 rounded-2xl border border-border/60 bg-muted/20 space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground font-mono flex items-center gap-2">
                          <Activity className="h-3.5 w-3.5 text-cyan-400" />
                          Risk-Return Efficient Frontier (Max Drawdown vs. OOS Return)
                        </h4>
                        <p className="text-[11px] text-muted-foreground">
                          Optimal institutional strategies cluster in the top-left quadrant (Low Max Drawdown, High Positive Return).
                        </p>
                      </div>
                    </div>

                    <div className="h-80 w-full pt-2">
                      <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
                          <XAxis
                            type="number"
                            dataKey="drawdown"
                            name="Max Drawdown"
                            unit="%"
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "monospace" }}
                            label={{
                              value: "Max Drawdown (%) → Higher Risk",
                              position: "insideBottom",
                              offset: -10,
                              fill: "hsl(var(--muted-foreground))",
                              fontSize: 11,
                              fontFamily: "monospace",
                            }}
                          />
                          <YAxis
                            type="number"
                            dataKey="returnPct"
                            name="Cumulative Return"
                            unit="%"
                            tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "monospace" }}
                            label={{
                              value: "OOS Return (%) → Higher Alpha",
                              angle: -90,
                              position: "insideLeft",
                              offset: 15,
                              fill: "hsl(var(--muted-foreground))",
                              fontSize: 11,
                              fontFamily: "monospace",
                            }}
                          />
                          <ZAxis range={[60, 60]} />
                          <RechartsTooltip
                            content={({ active, payload }) => {
                              if (!active || !payload?.length) return null
                              const d = payload[0].payload
                              return (
                                <div className="rounded-xl border border-border/80 bg-popover/95 p-3 shadow-xl backdrop-blur text-xs font-mono space-y-1">
                                  <p className="font-bold text-foreground text-sm">{d.name}</p>
                                  <div className="space-y-0.5 pt-1 text-[11px] text-muted-foreground">
                                    <p>
                                      OOS Sharpe: <span className="font-bold text-foreground">{d.sharpe}</span>
                                    </p>
                                    <p>
                                      OOS Return:{" "}
                                      <span className={d.returnPct >= 0 ? "text-emerald-400 font-bold" : "text-rose-400"}>
                                        {d.returnPct}%
                                      </span>
                                    </p>
                                    <p>
                                      Max Drawdown: <span className="text-rose-400 font-bold">{d.drawdown}%</span>
                                    </p>
                                  </div>
                                </div>
                              )
                            }}
                          />
                          <Scatter
                            name="Strategies"
                            data={scatterData}
                            onClick={(entry: any) => {
                              const sid = entry?.strategy_id || entry?.payload?.strategy_id
                              if (sid && onBacktestStrategy) {
                                onBacktestStrategy(sid)
                              }
                            }}
                            className="cursor-pointer"
                          >
                            {scatterData.map((entry, index) => {
                              const fill = entry.sharpe >= 1.0 ? "#10b981" : entry.sharpe > 0 ? "#06b6d4" : "#f43f5e"
                              return <Cell key={`cell-${index}`} fill={fill} />
                            })}
                          </Scatter>
                        </ScatterChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 4: EXECUTIVE MARKDOWN REPORT */}
              {activeTab === "executive_md" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-foreground font-mono">
                        Institutional Review Committee Dossier
                      </h4>
                      <p className="text-[11px] text-muted-foreground">
                        Offline generated markdown artifact from scripts/run_validation.py.
                      </p>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => downloadCsv("regime_tests.md", markdownContent)}
                      disabled={!markdownContent}
                      className="h-7 text-xs gap-1"
                    >
                      <Download className="h-3 w-3" />
                      <span>Download .md</span>
                    </Button>
                  </div>

                  {markdownContent ? (
                    <pre className="text-xs font-mono whitespace-pre overflow-auto max-h-[600px] bg-muted/30 p-4 rounded-2xl border border-border/60 text-muted-foreground leading-relaxed">
                      {markdownContent}
                    </pre>
                  ) : (
                    <div className="py-12 text-center text-muted-foreground text-xs">
                      No markdown summary currently found on disk.
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function parseWalkForwardCsv(text: string): WalkForwardRecord[] {
  const lines = text.trim().split("\n").filter(Boolean)
  if (lines.length < 2) return []

  const records: WalkForwardRecord[] = []
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",").map(p => p.trim().replace(/^"/, "").replace(/"$/, ""))
    if (parts.length < 5) continue
    records.push({
      strategy_id: parts[0],
      n_windows: parseInt(parts[1], 10) || 0,
      mean_oos_sharpe: parseFloat(parts[2]) || 0,
      total_oos_return: parseFloat(parts[3]) || 0,
      max_dd: parseFloat(parts[4]) || 0,
    })
  }
  return records.sort((a, b) => b.mean_oos_sharpe - a.mean_oos_sharpe)
}

function parseRegimesCsv(text: string): RegimeRecord[] {
  const lines = text.trim().split("\n").filter(Boolean)
  if (lines.length < 2) return []

  const records: RegimeRecord[] = []
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",").map(p => p.trim().replace(/^"/, "").replace(/"$/, ""))
    if (parts.length < 6) continue
    records.push({
      strategy_id: parts[0],
      regime: parts[1],
      sharpe: parseFloat(parts[2]) || 0,
      total_return: parseFloat(parts[3]) || 0,
      max_dd: parseFloat(parts[4]) || 0,
      n_bars: parseInt(parts[5], 10) || 0,
    })
  }
  return records
}

function formatStrategyName(sid: string): string {
  return sid
    .replace(/_/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase())
}
