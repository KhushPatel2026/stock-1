import { useEffect, useState, useMemo } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Search,
  BookOpen,
  LayoutGrid,
  Table as TableIcon,
  Zap,
} from "lucide-react"
import { fetchStrategies } from "@/api"
import type { Strategy } from "@/api"

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

interface StrategyLibraryProps {
  onBacktestStrategy?: (strategyId: string) => void
}

export default function StrategyLibrary({ onBacktestStrategy }: StrategyLibraryProps) {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [search, setSearch] = useState("")
  const [familyFilter, setFamilyFilter] = useState<string>("")
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchStrategies().then(setStrategies).catch(e => setError(e.message))
  }, [])

  const families = useMemo(() => {
    return Array.from(new Set(strategies.map(s => s.family))).sort()
  }, [strategies])

  const filtered = useMemo(() => {
    return strategies.filter(s => {
      if (familyFilter && s.family !== familyFilter) return false
      if (search) {
        const q = search.toLowerCase()
        const text = `${s.name} ${s.id} ${s.description} ${s.family} ${JSON.stringify(s.params)}`.toLowerCase()
        if (!text.includes(q)) return false
      }
      return true
    })
  }, [strategies, familyFilter, search])

  return (
    <div className="space-y-4">
      {/* HEADER & FILTER BAR */}
      <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur">
        <CardHeader className="pb-3 pt-4 px-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-cyan-400" />
                <span>Strategy Library ({filtered.length}/{strategies.length})</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Comprehensive catalog of mathematical formulas, statistical arbitrations, and quantitative alphas.
              </CardDescription>
            </div>

            {/* View switcher */}
            <div className="flex items-center gap-2 self-start sm:self-auto">
              <div className="flex items-center bg-muted/40 p-1 rounded-lg border border-border/70">
                <button
                  type="button"
                  onClick={() => setViewMode("grid")}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                    viewMode === "grid"
                      ? "bg-card text-foreground shadow-sm font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <LayoutGrid className="h-3.5 w-3.5" />
                  <span>Cards</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("table")}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 ${
                    viewMode === "table"
                      ? "bg-card text-foreground shadow-sm font-semibold"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <TableIcon className="h-3.5 w-3.5" />
                  <span>Table</span>
                </button>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="px-5 pb-5 pt-0 space-y-3">
          {/* Search */}
          <div className="relative max-w-sm">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              placeholder="Search by name, ID, or thesis..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="pl-8 h-8 text-xs bg-background/60"
            />
          </div>

          {/* Family pills */}
          <div className="flex flex-wrap gap-1 pt-1 border-t border-border/40">
            <button
              type="button"
              onClick={() => setFamilyFilter("")}
              className={`text-[10px] px-2.5 py-1 rounded-md border font-mono transition-all ${
                familyFilter === ""
                  ? "bg-primary text-primary-foreground border-primary font-bold shadow-sm"
                  : "border-border/60 hover:bg-muted text-muted-foreground"
              }`}
            >
              All Families ({strategies.length})
            </button>
            {families.map(f => {
              const count = strategies.filter(s => s.family === f).length
              const isActive = familyFilter === f
              return (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFamilyFilter(isActive ? "" : f)}
                  className={`text-[10px] px-2.5 py-1 rounded-md border font-mono transition-all flex items-center gap-1 ${
                    isActive
                      ? "bg-primary text-primary-foreground border-primary font-bold shadow-sm"
                      : `${FAMILY_COLORS[f] || FAMILY_COLORS.Other} hover:opacity-80`
                  }`}
                >
                  <span>{f}</span>
                  <span className="opacity-70 text-[9px]">({count})</span>
                </button>
              )
            })}
          </div>

          {error && <p className="text-xs text-rose-500">{error}</p>}
        </CardContent>
      </Card>

      {/* VIEW 1: INTERACTIVE CARD GRID */}
      {viewMode === "grid" && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
          {filtered.map(s => (
            <Card
              key={s.id}
              className="border-border/70 shadow-sm bg-card/85 backdrop-blur hover:border-primary/40 hover:shadow-md transition-all flex flex-col justify-between group"
            >
              <CardHeader className="py-3.5 px-4 pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                      {s.name}
                    </CardTitle>
                    <span className="text-[11px] font-mono text-muted-foreground">{s.id}</span>
                  </div>

                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full border font-mono shrink-0 ${
                      FAMILY_COLORS[s.family] || FAMILY_COLORS.Other
                    }`}
                  >
                    {s.family}
                  </span>
                </div>
              </CardHeader>

              <CardContent className="px-4 py-2 space-y-3 flex-1 flex flex-col justify-between">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {s.description}
                </p>

                {/* Parameters pills */}
                {Object.keys(s.params).length > 0 && (
                  <div className="pt-2 border-t border-border/40">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground block mb-1">
                      Parameters:
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(s.params).map(([k, v]) => (
                        <span
                          key={k}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground border border-border/60"
                        >
                          {k}: <strong className="text-foreground">{String(v)}</strong>
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>

              {/* Backtest shortcut button */}
              {onBacktestStrategy && (
                <div className="px-4 py-2.5 border-t border-border/40 bg-muted/20 flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground font-mono">Vectorized Engine</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onBacktestStrategy(s.id)}
                    className="h-7 text-xs font-medium text-primary hover:bg-primary/10 gap-1.5 px-2.5 rounded-lg"
                  >
                    <Zap className="h-3.5 w-3.5 fill-current" />
                    <span>Backtest</span>
                  </Button>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* VIEW 2: DENSE DATA TABLE */}
      {viewMode === "table" && (
        <Card className="border-border/70 shadow-sm bg-card/90 backdrop-blur overflow-hidden">
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader className="bg-muted/40 border-b border-border/70 text-muted-foreground text-xs">
                <TableRow>
                  <TableHead className="w-48 font-semibold">Algorithm</TableHead>
                  <TableHead className="w-32 font-semibold">Family</TableHead>
                  <TableHead className="font-semibold">Theoretical Thesis &amp; Description</TableHead>
                  <TableHead className="w-56 font-semibold">Parameters</TableHead>
                  {onBacktestStrategy && <TableHead className="w-24 text-center font-semibold">Execute</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody className="text-xs divide-y divide-border/40">
                {filtered.map(s => (
                  <TableRow key={s.id} className="hover:bg-accent/30 transition-colors">
                    <TableCell className="font-medium text-foreground py-3">
                      <div>{s.name}</div>
                      <div className="text-[10px] font-mono text-muted-foreground">{s.id}</div>
                    </TableCell>
                    <TableCell>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full border font-mono ${
                          FAMILY_COLORS[s.family] || FAMILY_COLORS.Other
                        }`}
                      >
                        {s.family}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground leading-relaxed py-3">
                      {s.description}
                    </TableCell>
                    <TableCell className="font-mono text-[11px] text-muted-foreground py-3">
                      <div className="max-w-[200px] truncate">{JSON.stringify(s.params)}</div>
                    </TableCell>
                    {onBacktestStrategy && (
                      <TableCell className="text-center py-3">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onBacktestStrategy(s.id)}
                          className="h-7 text-xs font-medium text-primary hover:bg-primary/10 gap-1 px-2"
                          title="Run Backtest"
                        >
                          <Zap className="h-3.5 w-3.5 fill-current" />
                          <span>Test</span>
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {filtered.length === 0 && (
        <div className="py-16 text-center text-xs text-muted-foreground">
          No algorithms match your query. Try searching for "momentum", "trend", or "bollinger".
        </div>
      )}
    </div>
  )
}
