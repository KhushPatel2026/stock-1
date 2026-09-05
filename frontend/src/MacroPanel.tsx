import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2, TrendingUp, TrendingDown, Minus, Globe, Newspaper, RefreshCw, BarChart3 } from "lucide-react"
import { fetchMacro, fetchTickerNews } from "@/api"
import type { MacroData, MacroItem, MacroRegime } from "@/api"

const REGIME_COLORS: Record<string, string> = {
  bullish: "bg-emerald-500 text-white",
  bearish: "bg-rose-500 text-white",
  neutral: "bg-gray-500 text-white",
  "risk-on": "bg-emerald-500 text-white",
  "risk-off": "bg-rose-500 text-white",
  mixed: "bg-amber-500 text-white",
}

export default function MacroPanel() {
  const [data, setData] = useState<MacroData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newsTicker, setNewsTicker] = useState("RELIANCE.NS")
  const [news, setNews] = useState<any[]>([])
  const [newsLoading, setNewsLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await fetchMacro()
      setData(d)
    } catch (e: any) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  const loadNews = async (t: string) => {
    setNewsLoading(true)
    try {
      const r = await fetchTickerNews(t, 5)
      setNews(r.news || [])
    } catch {
      setNews([])
    } finally {
      setNewsLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  useEffect(() => { if (newsTicker) loadNews(newsTicker) }, [newsTicker])

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Macro Context
              </CardTitle>
              <CardDescription>
                Nifty sectors + global indices + commodities + FX + India VIX. Regime classification adjusts AI recommendations.
              </CardDescription>
            </div>
            <Button variant="outline" size="icon" onClick={load} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {!data && loading && <Loader2 className="h-6 w-6 animate-spin mx-auto" />}
          {data?.regime && <RegimePanel regime={data.regime} nifty={data.nifty50} />}
        </CardContent>
      </Card>

      {data && (
        <>
          <SectionCard title="Sectors (Nifty)" icon={<BarChart3 className="h-4 w-4" />}>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
              {data.sectors.map(s => <MacroCell key={s.symbol} item={s} />)}
            </div>
          </SectionCard>

          <SectionCard title="Global Indices" icon={<Globe className="h-4 w-4" />}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {data.global.map(s => <MacroCell key={s.symbol} item={s} />)}
            </div>
          </SectionCard>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SectionCard title="Commodities" icon={<TrendingUp className="h-4 w-4" />}>
              <div className="space-y-1">
                {data.commodities.map(s => <MacroRow key={s.symbol} item={s} />)}
              </div>
            </SectionCard>

            <SectionCard title="FX + Volatility" icon={<TrendingUp className="h-4 w-4" />}>
              <div className="space-y-1">
                {data.fx.map(s => <MacroRow key={s.symbol} item={s} />)}
                {data.volatility.map(s => <MacroRow key={s.symbol} item={s} />)}
              </div>
            </SectionCard>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Newspaper className="h-4 w-4" />
                News Headlines
              </CardTitle>
              <CardDescription>Yahoo Finance news for the selected ticker.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newsTicker}
                  onChange={e => setNewsTicker(e.target.value.toUpperCase())}
                  onKeyDown={e => { if (e.key === "Enter") loadNews(newsTicker) }}
                  placeholder="Ticker (e.g. RELIANCE.NS)"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
                <Button onClick={() => loadNews(newsTicker)} disabled={newsLoading}>
                  {newsLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Fetch
                </Button>
              </div>
              {news.length === 0 && !newsLoading && (
                <p className="text-sm text-muted-foreground">No news for this ticker (or yfinance has none).</p>
              )}
              <div className="space-y-2">
                {news.map((n, i) => (
                  <a key={i} href={n.link} target="_blank" rel="noreferrer" className="block p-2 rounded-md border hover:bg-accent transition-colors">
                    <div className="font-medium text-sm">{n.title}</div>
                    <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                      <span>{n.publisher}</span>
                      {n.published && <span>•</span>}
                      {n.published && <span>{new Date(n.published * 1000).toLocaleDateString()}</span>}
                    </div>
                  </a>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

function RegimePanel({ regime, nifty }: { regime: MacroRegime; nifty: MacroItem }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2 items-center">
        <Badge className={REGIME_COLORS[regime.india_regime] || ""}>India: {regime.india_regime}</Badge>
        <Badge className={REGIME_COLORS[regime.global_regime] || ""}>Global: {regime.global_regime}</Badge>
        <Badge className={REGIME_COLORS[regime.commodities_bias] || ""}>{regime.commodities_bias}</Badge>
        <Badge className={REGIME_COLORS[regime.risk_on_off] || ""}>{regime.risk_on_off}</Badge>
        <span className="text-sm font-mono ml-2">India VIX: {regime.vix.toFixed(1)}</span>
      </div>
      <p className="text-sm bg-muted/40 p-3 rounded-md border">{regime.summary}</p>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="bg-card border rounded-md p-2">
          <div className="text-muted-foreground">Nifty 50</div>
          <div className="font-mono font-semibold text-lg">{nifty.last.toLocaleString()}</div>
          <div className={`text-xs ${nifty.chg_20d_pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
            {nifty.chg_20d_pct >= 0 ? "+" : ""}{nifty.chg_20d_pct.toFixed(2)}% 20d
          </div>
        </div>
        <div className="bg-card border rounded-md p-2">
          <div className="text-muted-foreground">Strongest sectors</div>
          <div className="text-xs mt-1">{regime.strongest_sectors.map(s => s?.replace("Nifty ", "")).join(", ") || "n/a"}</div>
        </div>
        <div className="bg-card border rounded-md p-2">
          <div className="text-muted-foreground">Weakest sectors</div>
          <div className="text-xs mt-1">{regime.weakest_sectors.map(s => s?.replace("Nifty ", "")).join(", ") || "n/a"}</div>
        </div>
      </div>
    </div>
  )
}

function SectionCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium flex items-center gap-2">{icon} {title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function MacroCell({ item }: { item: MacroItem }) {
  const chg = item.chg_20d_pct
  const Icon = item.trend === "up" ? TrendingUp : item.trend === "down" ? TrendingDown : Minus
  const color = item.trend === "up" ? "text-emerald-600" : item.trend === "down" ? "text-rose-600" : "text-gray-500"
  return (
    <div className="bg-card border rounded-md p-2">
      <div className="text-xs text-muted-foreground truncate">{item.name}</div>
      <div className="flex items-center justify-between mt-1">
        <span className="font-mono font-semibold text-sm">{item.last.toLocaleString()}</span>
        <Icon className={`h-3 w-3 ${color}`} />
      </div>
      <div className={`text-xs font-mono ${chg >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
        {chg >= 0 ? "+" : ""}{chg.toFixed(2)}% 20d
      </div>
    </div>
  )
}

function MacroRow({ item }: { item: MacroItem }) {
  const chg = item.chg_20d_pct
  return (
    <div className="flex items-center justify-between text-sm py-1 border-b last:border-0">
      <span>{item.name}</span>
      <div className="flex items-center gap-3 tabular-nums">
        <span className="font-mono">{item.last.toLocaleString()}</span>
        <span className={`text-xs ${chg >= 0 ? "text-emerald-600" : "text-rose-600"} w-16 text-right`}>
          {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
        </span>
      </div>
    </div>
  )
}
