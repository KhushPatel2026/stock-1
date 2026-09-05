import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Loader2, RefreshCw, ExternalLink, AlertTriangle, Info, Wallet } from "lucide-react"
import { fetchPortfolio, setUpstoxToken, fetchUpstoxStatus, fetchInsightsPortfolio, fetchIndiaVix } from "@/api"
import type { PortfolioData, UpstoxHolding } from "@/api"

export default function Portfolio() {
  const [token, setToken] = useState("")
  const [authStatus, setAuthStatus] = useState<boolean | null>(null)
  const [data, setData] = useState<PortfolioData | null>(null)
  const [loading, setLoading] = useState(false)
  const [insights, setInsights] = useState<any | null>(null)
  const [vix, setVix] = useState<any | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showTokenForm, setShowTokenForm] = useState(false)

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      const status = await fetchUpstoxStatus()
      setAuthStatus(status.authenticated)
      if (status.authenticated) {
        const p = await fetchPortfolio()
        setData(p)
        if (p.authenticated) {
          try { const i = await fetchInsightsPortfolio(); setInsights(i) } catch {}
          try { const v = await fetchIndiaVix(); setVix(v) } catch {}
        }
      } else {
        setData(null)
      }
    } catch (e: any) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  const saveToken = async () => {
    if (!token) return
    setError(null)
    try {
      await setUpstoxToken(token)
      setShowTokenForm(false)
      setToken("")
      await refresh()
    } catch (e: any) {
      setError(e.message || String(e))
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Wallet className="h-5 w-5" />
                Your Upstox Portfolio
              </CardTitle>
              <CardDescription>
                {authStatus === null ? "Checking..." : authStatus
                  ? "Connected — refreshes every 60s"
                  : "Not connected. Add your Upstox access token below."}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowTokenForm(!showTokenForm)}>
                {authStatus ? "Update token" : "Connect Upstox"}
              </Button>
              <Button variant="outline" size="icon" onClick={refresh} disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              </Button>
            </div>
          </div>
        </CardHeader>
        {showTokenForm && (
          <CardContent className="border-t pt-4 space-y-3">
            <div className="space-y-2">
              <Label>Upstox Access Token</Label>
              <Input
                type="password"
                value={token}
                onChange={e => setToken(e.target.value)}
                placeholder="Paste your Upstox OAuth access token"
              />
              <p className="text-xs text-muted-foreground">
                Get one via Upstox OAuth flow at{" "}
                <a href="https://upstox.com/developer/api-documentation/authentication" target="_blank" className="underline inline-flex items-center gap-1">
                  upstox.com/developer <ExternalLink className="h-3 w-3" />
                </a>{" "}
                — tokens last ~24h.
              </p>
            </div>
            <Button onClick={saveToken} disabled={!token}>Save token</Button>
          </CardContent>
        )}
      </Card>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {authStatus && data?.authenticated && (
        <>
          {/* SUMMARY */}
          {data.summary && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <Stat label="Holdings" value={String(data.summary.n_holdings)} />
              <Stat label="Invested" value={`₹${data.summary.total_invested.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
              <Stat label="Current" value={`₹${data.summary.total_current.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} />
              <Stat label="P&L" value={`₹${data.summary.total_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}`} positive={data.summary.total_pnl >= 0} />
              <Stat label="Return" value={`${data.summary.total_pnl_pct.toFixed(2)}%`} positive={data.summary.total_pnl_pct >= 0} />
            </div>
          )}

          {/* INSIGHTS */}
          {insights && insights.authenticated && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  Insights
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {insights.concentration && (
                  <div className="text-sm">
                    <span className="font-semibold">Concentration: </span>
                    <Badge variant={insights.concentration.concentration === "high" ? "destructive" : "secondary"}>
                      {insights.concentration.concentration}
                    </Badge>
                    <span className="text-muted-foreground ml-2">
                      HHI {insights.concentration.score} · top 3 = {insights.concentration.top3_pct}% of portfolio
                    </span>
                  </div>
                )}
                {insights.suggestions && (
                  <ul className="space-y-1">
                    {insights.suggestions.map((s: string, i: number) => (
                      <li key={i} className="text-sm">{s}</li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}

          {/* VIX */}
          {vix && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-muted-foreground">India VIX (market fear gauge)</div>
                    <div className="text-3xl font-bold tabular-nums">
                      {typeof vix === "object" ? JSON.stringify(vix).slice(0, 100) : String(vix)}
                    </div>
                  </div>
                  <AlertTriangle className="h-8 w-8 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
          )}

          {/* HOLDINGS TABLE */}
          {data.holdings && data.holdings.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Holdings ({data.holdings.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="max-h-96 overflow-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-card">
                      <tr className="border-b">
                        <th className="text-left p-2">Ticker</th>
                        <th className="text-right p-2">Qty</th>
                        <th className="text-right p-2">Avg</th>
                        <th className="text-right p-2">LTP</th>
                        <th className="text-right p-2">Invested</th>
                        <th className="text-right p-2">Current</th>
                        <th className="text-right p-2">P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.holdings.map((h: UpstoxHolding) => (
                        <tr key={h.ticker} className="border-b">
                          <td className="p-2 font-medium">{h.ticker}</td>
                          <td className="p-2 text-right tabular-nums">{h.quantity}</td>
                          <td className="p-2 text-right tabular-nums">₹{h.avg_price.toFixed(0)}</td>
                          <td className="p-2 text-right tabular-nums">{h.current_price ? `₹${h.current_price.toFixed(0)}` : "—"}</td>
                          <td className="p-2 text-right tabular-nums">₹{h.invested.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                          <td className="p-2 text-right tabular-nums">₹{h.current_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                          <td className={`p-2 text-right tabular-nums font-semibold ${h.pnl >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                            ₹{h.pnl.toFixed(0)} ({h.pnl_pct.toFixed(1)}%)
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {data.holdings && data.holdings.length === 0 && (
            <Card>
              <CardContent className="pt-6">
                <p className="text-muted-foreground text-center">No long-term holdings found.</p>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {authStatus === false && !loading && (
        <Card>
          <CardContent className="pt-6 space-y-3 text-sm">
            <p className="font-semibold">How to connect your Upstox account:</p>
            <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
              <li>Go to <a href="https://upstox.com/developer/api-documentation/authentication" target="_blank" className="underline">upstox.com/developer/api-documentation/authentication</a></li>
              <li>Run the OAuth flow (or use the API playground) to get an access token</li>
              <li>Paste the token above and click "Save token"</li>
              <li>This app fetches your holdings + computes P&L + generates insights</li>
            </ol>
            <p className="text-xs text-muted-foreground pt-2 border-t">
              IP for Upstox whitelist: API calls go from this backend server, not your browser.
              If Upstox requires IP whitelisting, use your server's public IP (find at ipify.org).
              For local dev, 0.0.0.0/0 works.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function Stat({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className={`text-2xl font-bold tabular-nums ${positive === undefined ? "" : positive ? "text-emerald-600" : "text-red-600"}`}>{value}</div>
      </CardContent>
    </Card>
  )
}
