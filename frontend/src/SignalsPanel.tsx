import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2 } from "lucide-react"
import { fetchSignals, fetchTickers, fetchStrategies } from "@/api"
import type { Signal } from "@/api"

const SIGNAL_COLORS: Record<string, string> = {
  long: "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
  short: "bg-red-500/20 text-red-700 dark:text-red-300 border-red-500/30",
  flat: "bg-gray-500/20 text-gray-700 dark:text-gray-300 border-gray-500/30",
}

export default function SignalsPanel() {
  const [tickers, setTickers] = useState<string[]>([])
  const [strategies, setStrategies] = useState<{ id: string; family: string }[]>([])
  const [signals, setSignals] = useState<Signal[]>([])
  const [asOf, setAsOf] = useState<string>("")
  const [search, setSearch] = useState("")
  const [familyFilter, setFamilyFilter] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTickers().then(setTickers).catch(e => setError(e.message))
    fetchStrategies().then(s => setStrategies(s.map(x => ({ id: x.id, family: x.family })))).catch(e => setError(e.message))
  }, [])

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      // Use NIFTY15 subset (first 15) for speed
      const subset = tickers.slice(0, 10)
      const r = await fetchSignals(subset)
      setSignals(r.signals)
      setAsOf(r.as_of)
    } catch (e: any) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (tickers.length > 0) refresh() }, [tickers])

  // Group by strategy
  const byStrategy: Record<string, Signal[]> = {}
  for (const s of signals) {
    if (!byStrategy[s.strategy_id]) byStrategy[s.strategy_id] = []
    byStrategy[s.strategy_id].push(s)
  }
  const filtered = Object.entries(byStrategy).filter(([sid]) => {
    if (familyFilter) {
      const s = strategies.find(x => x.id === sid)
      if (!s || s.family !== familyFilter) return false
    }
    if (search && !sid.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const families = Array.from(new Set(strategies.map(s => s.family))).sort()

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Today's Signals</CardTitle>
          <CardDescription>
            Latest signal per strategy × ticker. {asOf && `As of ${asOf}.`} Refreshed on demand. Coverage: {tickers.slice(0, 10).length} tickers × {strategies.length} strategies.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col md:flex-row gap-2">
            <Input
              placeholder="Search strategies..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="md:max-w-sm"
            />
            <div className="flex flex-wrap gap-1">
              <Badge variant={familyFilter === "" ? "default" : "outline"} className="cursor-pointer" onClick={() => setFamilyFilter("")}>All</Badge>
              {families.map(f => (
                <Badge key={f} variant="outline" className="cursor-pointer" onClick={() => setFamilyFilter(f)}>{f}</Badge>
              ))}
            </div>
            <Button onClick={refresh} disabled={loading}>
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Refresh
            </Button>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="text-xs text-muted-foreground">
            {signals.length} signals across {Object.keys(byStrategy).length} strategies
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map(([sid, sigs]) => (
          <Card key={sid} className="overflow-hidden">
            <CardHeader className="py-3">
              <CardTitle className="text-sm font-medium">{sid}</CardTitle>
            </CardHeader>
            <CardContent className="py-2">
              <div className="space-y-1">
                {sigs.map(s => (
                  <div key={s.ticker} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground text-xs">{s.ticker}</span>
                    <Badge variant="outline" className={SIGNAL_COLORS[s.signal] || SIGNAL_COLORS.flat}>
                      {s.signal}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
