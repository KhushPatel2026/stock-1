import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2, TrendingUp, TrendingDown, Minus, Globe, Newspaper, RefreshCw, BarChart3, ExternalLink, MessageCircle, ArrowUpRight, ArrowDownRight, Activity, DollarSign } from "lucide-react"
import { fetchMacro, fetchLiveMacro, fetchNewsAggregate, fetchSentiment } from "@/api"
import type { MacroData, LiveMacro, NewsItem } from "@/api"

const REGIME_COLORS: Record<string, string> = {
  bullish: "bg-emerald-500 text-white",
  bearish: "bg-rose-500 text-white",
  neutral: "bg-gray-500 text-white",
  "risk-on": "bg-emerald-500 text-white",
  "risk-off": "bg-rose-500 text-white",
  mixed: "bg-amber-500 text-white",
}

const SOURCE_BADGES: Record<string, string> = {
  "Google News": "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30",
  "yfinance": "bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/30",
  "StockTwits": "bg-orange-500/10 text-orange-700 dark:text-orange-300 border-orange-500/30",
}

export default function MacroPanel() {
  const [data, setData] = useState<MacroData | null>(null)
  const [live, setLive] = useState<LiveMacro | null>(null)
  const [loading, setLoading] = useState(false)
  const [liveLoading, setLiveLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newsTicker, setNewsTicker] = useState("RELIANCE.NS")
  const [newsAgg, setNewsAgg] = useState<any | null>(null)
  const [sentiment, setSentiment] = useState<any | null>(null)
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

  const loadLive = async () => {
    setLiveLoading(true)
    try {
      const l = await fetchLiveMacro()
      setLive(l)
    } catch {
      // silent
    } finally {
      setLiveLoading(false)
    }
  }

  const loadNewsAgg = async (t: string) => {
    setNewsLoading(true)
    try {
      const r = await fetchNewsAggregate(t, 5)
      setNewsAgg(r)
    } catch {
      setNewsAgg(null)
    } finally {
      setNewsLoading(false)
    }
  }

  const loadSentiment = async (t: string) => {
    try {
      const r = await fetchSentiment(t)
      setSentiment(r)
    } catch {
      setSentiment(null)
    }
  }

  useEffect(() => { load(); loadLive() }, [])
  useEffect(() => {
    if (newsTicker) {
      loadNewsAgg(newsTicker)
      loadSentiment(newsTicker)
    }
  }, [newsTicker])

  const allRefresh = async () => {
    setLoading(true)
    setLiveLoading(true)
    await Promise.all([load(), loadLive(), loadNewsAgg(newsTicker), loadSentiment(newsTicker)])
    setLoading(false)
    setLiveLoading(false)
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Macro Context
                {live?.fetched_at && (
                  <Badge variant="outline" className="text-xs font-mono">
                    <Activity className="h-3 w-3 mr-1 animate-pulse text-emerald-500" />
                    live
                  </Badge>
                )}
              </CardTitle>
              <CardDescription>
                yfinance (sectors/commodities/FX) + NSE live (sectors) + Google News + StockTwits + yfinance news
              </CardDescription>
            </div>
            <Button variant="outline" size="icon" onClick={allRefresh} disabled={loading || liveLoading}>
              {(loading || liveLoading) ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {error && <p className="text-sm text-destructive">{error}</p>}
          {!data && loading && <Loader2 className="h-6 w-6 animate-spin mx-auto" />}
          {data?.regime && <RegimePanel regime={data.regime} nifty={data.nifty50} />}
        </CardContent>
      </Card>

      {/* NSE LIVE sectors (live data from NSE India) */}
      {live && live.nse_sectors.length > 0 && (
        <SectionCard title="NSE Sectors (live)" icon={<BarChart3 className="h-4 w-4 text-emerald-500" />}>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
            {live.nse_sectors.slice(0, 16).map(s => <NseSectorCell key={s.symbol} s={s} />)}
          </div>
        </SectionCard>
      )}

      {data && (
        <>
          <SectionCard title="Sectors (yfinance)" icon={<BarChart3 className="h-4 w-4" />}>
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
            <SectionCard title="Commodities" icon={<DollarSign className="h-4 w-4" />}>
              <div className="space-y-1">
                {data.commodities.map(s => <MacroRow key={s.symbol} item={s} />)}
              </div>
            </SectionCard>

            <SectionCard title="FX + Volatility" icon={<DollarSign className="h-4 w-4" />}>
              <div className="space-y-1">
                {data.fx.map(s => <MacroRow key={s.symbol} item={s} />)}
                {data.volatility.map(s => <MacroRow key={s.symbol} item={s} />)}
              </div>
            </SectionCard>
          </div>
        </>
      )}

      {/* Multi-source news aggregator */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Newspaper className="h-4 w-4" />
            Multi-Source News & Sentiment
          </CardTitle>
          <CardDescription>
            Google News RSS (free, no API key) + yfinance + StockTwits retail sentiment for one ticker.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={newsTicker}
              onChange={e => setNewsTicker(e.target.value.toUpperCase())}
              onKeyDown={e => { if (e.key === "Enter") { loadNewsAgg(newsTicker); loadSentiment(newsTicker) } }}
              placeholder="Ticker (e.g. RELIANCE.NS, AAPL, TSLA)"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <Button onClick={() => { loadNewsAgg(newsTicker); loadSentiment(newsTicker) }} disabled={newsLoading}>
              {newsLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Fetch
            </Button>
          </div>

          {/* Sentiment bar */}
          {sentiment && sentiment.total > 0 && (
            <div className="bg-muted/30 p-3 rounded-md border">
              <div className="flex items-center gap-2 text-xs">
                <MessageCircle className="h-4 w-4" />
                <span className="font-semibold">StockTwits retail sentiment:</span>
                <span className="text-emerald-600 flex items-center"><ArrowUpRight className="h-3 w-3" />{sentiment.sentiment.bullish} bullish</span>
                <span className="text-rose-600 flex items-center"><ArrowDownRight className="h-3 w-3" />{sentiment.sentiment.bearish} bearish</span>
                <span className="text-muted-foreground ml-auto">{sentiment.total} messages</span>
              </div>
              <div className="flex h-2 mt-2 rounded-full overflow-hidden bg-muted">
                <div className="bg-emerald-500" style={{ width: `${(sentiment.sentiment.bullish / sentiment.total * 100) || 0}%` }} />
                <div className="bg-rose-500" style={{ width: `${(sentiment.sentiment.bearish / sentiment.total * 100) || 0}%` }} />
              </div>
            </div>
          )}

          {/* News from all sources */}
          {newsAgg && (
            <div className="space-y-3">
              {(["google_news", "yfinance", "stocktwits"] as const).map(source => {
                const items: NewsItem[] = (newsAgg as any)[source] || []
                const displayItems = source === "stocktwits" ? items : items
                return (
                  <div key={source}>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className={SOURCE_BADGES[source] || ""}>{source}</Badge>
                      <span className="text-xs text-muted-foreground">{items.length} items</span>
                    </div>
                    <div className="space-y-1 max-h-72 overflow-y-auto">
                      {displayItems.length === 0 && (
                        <p className="text-xs text-muted-foreground italic">No data from this source.</p>
                      )}
                      {displayItems.slice(0, 5).map((n, i) => (
                        <NewsCard key={i} item={n} source={source} />
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Google News India headlines (live market context) */}
      {live && live.google_news_india.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Newspaper className="h-4 w-4 text-blue-500" />
              India Market News (Google News RSS, live)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {live.google_news_india.slice(0, 8).map((n, i) => (
                <NewsCard key={i} item={n} source="Google News" />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function NewsCard({ item }: { item: NewsItem; source: string }) {
  const title = item.title || item.body || ""
  const url = item.link
  const user = item.user
  const sentiment = item.sentiment
  const Wrapper = url ? "a" : "div"
  const wrapperProps = url ? { href: url, target: "_blank", rel: "noreferrer" } : {}
  return (
    <Wrapper {...(wrapperProps as any)} className="block p-2 rounded-md border hover:bg-accent transition-colors">
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium leading-snug">{title.slice(0, 150)}{title.length > 150 ? "..." : ""}</div>
          <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
            {user && <span>@{user}</span>}
            {item.published && <span>{new Date(item.published).toLocaleDateString()}</span>}
            {item.source && <span>• {item.source}</span>}
          </div>
        </div>
        {sentiment === "Bullish" && <Badge className="bg-emerald-500 text-white">Bullish</Badge>}
        {sentiment === "Bearish" && <Badge className="bg-rose-500 text-white">Bearish</Badge>}
        {url && <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0" />}
      </div>
    </Wrapper>
  )
}

function RegimePanel({ regime, nifty }: { regime: any; nifty: any }) {
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
          <div className="text-xs mt-1">{regime.strongest_sectors.map((s: string) => s?.replace("Nifty ", "")).join(", ") || "n/a"}</div>
        </div>
        <div className="bg-card border rounded-md p-2">
          <div className="text-muted-foreground">Weakest sectors</div>
          <div className="text-xs mt-1">{regime.weakest_sectors.map((s: string) => s?.replace("Nifty ", "")).join(", ") || "n/a"}</div>
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

function MacroCell({ item }: { item: any }) {
  const chg = item.chg_20d_pct
  const Icon = item.trend === "up" ? TrendingUp : item.trend === "down" ? TrendingDown : Minus
  const color = item.trend === "up" ? "text-emerald-600" : item.trend === "down" ? "text-rose-600" : "text-gray-500"
  return (
    <div className="bg-card border rounded-md p-2">
      <div className="text-xs text-muted-foreground truncate">{item.name}</div>
      <div className="flex items-center justify-between mt-1">
        <span className="font-mono font-semibold text-sm">{typeof item.last === "number" ? item.last.toLocaleString() : "—"}</span>
        <Icon className={`h-3 w-3 ${color}`} />
      </div>
      <div className={`text-xs font-mono ${chg >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
        {chg >= 0 ? "+" : ""}{chg.toFixed(2)}% 20d
      </div>
    </div>
  )
}

function NseSectorCell({ s }: { s: any }) {
  const pct = s.pct_change ?? 0
  const last = s.last ?? 0
  return (
    <div className={`bg-card border rounded-md p-2 ${pct >= 0 ? "border-l-2 border-l-emerald-500" : "border-l-2 border-l-rose-500"}`}>
      <div className="text-xs text-muted-foreground truncate" title={s.name}>{s.name?.replace("NIFTY ", "")}</div>
      <div className="flex items-center justify-between mt-1">
        <span className="font-mono font-semibold text-sm">{last.toLocaleString()}</span>
        {pct >= 0 ? <TrendingUp className="h-3 w-3 text-emerald-600" /> : <TrendingDown className="h-3 w-3 text-rose-600" />}
      </div>
      <div className={`text-xs font-mono ${pct >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
        {pct >= 0 ? "+" : ""}{pct.toFixed(2)}%
      </div>
    </div>
  )
}

function MacroRow({ item }: { item: any }) {
  const chg = item.chg_20d_pct
  return (
    <div className="flex items-center justify-between text-sm py-1 border-b last:border-0">
      <span>{item.name}</span>
      <div className="flex items-center gap-3 tabular-nums">
        <span className="font-mono">{typeof item.last === "number" ? item.last.toLocaleString() : "—"}</span>
        <span className={`text-xs ${chg >= 0 ? "text-emerald-600" : "text-rose-600"} w-16 text-right`}>
          {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
        </span>
      </div>
    </div>
  )
}
