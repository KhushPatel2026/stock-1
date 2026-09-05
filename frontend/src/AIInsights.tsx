import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, Sparkles, Brain, Wallet, Send } from "lucide-react"
import { fetchAIStatus, aiPersonalized, aiExplainStrategy, fetchPortfolio, fetchDecisions } from "@/api"

export default function AIInsights() {
  const [status, setStatus] = useState<{ available: boolean } | null>(null)
  const [portfolio, setPortfolio] = useState<any>(null)
  const [holdingTickers, setHoldingTickers] = useState<string[]>([])

  // Tab states
  const [personalized, setPersonalized] = useState<{ text: string; stats: any } | null>(null)
  const [analyzeTickers, setAnalyzeTickers] = useState<string[]>(["RELIANCE.NS", "TCS.NS"])
  const [tickerInput, setTickerInput] = useState("")
  const [analyzeQuestion, setAnalyzeQuestion] = useState("What should I do with these? Entry, stop loss, target.")
  const [analyzeResult, setAnalyzeResult] = useState<string | null>(null)
  const [strategyId, setStrategyId] = useState("magic_formula")
  const [strategyQuestion, setStrategyQuestion] = useState("")
  const [strategyResult, setStrategyResult] = useState<string | null>(null)
  const [decisions, setDecisions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load on mount — status + portfolio + recent decisions (NO AI calls yet)
  useEffect(() => {
    fetchAIStatus().then(setStatus).catch(() => setStatus({ available: false }))
    fetchPortfolio().then(p => {
      setPortfolio(p)
      if (p?.holdings) {
        setHoldingTickers(p.holdings.map((h: any) => h.ticker))
      }
    }).catch(() => {})
    if (analyzeTickers.length > 0) {
      fetchDecisions(analyzeTickers, "3mo").then(r => setDecisions(r.decisions || [])).catch(() => {})
    }
  }, [])

  const addTicker = (t: string) => {
    const sym = t.trim().toUpperCase()
    if (!sym) return
    if (analyzeTickers.includes(sym)) return
    if (analyzeTickers.length >= 20) return
    setAnalyzeTickers([...analyzeTickers, sym])
    setTickerInput("")
    // refresh decisions
    fetchDecisions([...analyzeTickers, sym], "3mo").then(r => setDecisions(r.decisions || [])).catch(() => {})
  }

  const removeTicker = (t: string) => {
    const next = analyzeTickers.filter(x => x !== t)
    setAnalyzeTickers(next)
    fetchDecisions(next, "3mo").then(r => setDecisions(r.decisions || [])).catch(() => {})
  }

  const loadPersonalized = async () => {
    setLoading(true)
    try {
      const r = await aiPersonalized()
      setPersonalized(r)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const runAnalyze = async () => {
    if (analyzeTickers.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const r = await fetch("/api/ai/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tickers: analyzeTickers,
          holdings: holdingTickers.length ? holdingTickers.map(t => ({ ticker: t })) : [],
          question: analyzeQuestion,
        }),
      }).then(r => r.json())
      setAnalyzeResult(r.text)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const askStrategy = async () => {
    if (!strategyId) return
    setLoading(true)
    try {
      const r = await aiExplainStrategy(strategyId, { sharpe: 1.2, total_return: 0.18, max_drawdown: -0.08, n_bars: 252 }, strategyQuestion)
      setStrategyResult(r.text)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const hasPortfolio = portfolio?.authenticated && portfolio?.holdings?.length > 0

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            AI Insights
            <Badge variant={status?.available ? "default" : "outline"} className="ml-2">
              {status?.available ? "Gemini enabled" : "Fallback mode"}
            </Badge>
            {hasPortfolio && <Badge variant="secondary" className="ml-2">
              <Wallet className="h-3 w-3 mr-1" /> {portfolio.holdings.length} holdings loaded
            </Badge>}
          </CardTitle>
          <CardDescription>
            All Gemini calls are on-demand only. AI uses your actual watchlist + portfolio + recent backtests.
          </CardDescription>
        </CardHeader>
      </Card>

      <Tabs defaultValue="analyze">
        <TabsList>
          <TabsTrigger value="analyze">Analyze Tickers</TabsTrigger>
          <TabsTrigger value="strategy">Ask About Strategy</TabsTrigger>
          <TabsTrigger value="next">My Next Steps</TabsTrigger>
        </TabsList>

        {/* ANALYZE TICKERS */}
        <TabsContent value="analyze">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Analyze my tickers / portfolio</CardTitle>
              <CardDescription>
                Enter tickers below (or use your Upstox portfolio) → click Analyze → Gemini gives BUY/SELL/HOLD per ticker.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Tickers to analyze</Label>
                <div className="flex gap-2">
                  <Input
                    value={tickerInput}
                    onChange={e => setTickerInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addTicker(tickerInput) } }}
                    placeholder="Type ticker (RELIANCE.NS, AAPL...) and Enter"
                  />
                  <Button onClick={() => addTicker(tickerInput)} variant="outline">Add</Button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {analyzeTickers.map(t => (
                    <Badge key={t} variant="secondary" className="cursor-pointer" onClick={() => removeTicker(t)}>
                      {t} ×
                    </Badge>
                  ))}
                </div>
                {hasPortfolio && (
                  <Button
                    variant="link"
                    size="sm"
                    onClick={() => {
                      setAnalyzeTickers(holdingTickers.slice(0, 15))
                      fetchDecisions(holdingTickers.slice(0, 15), "3mo").then(r => setDecisions(r.decisions || [])).catch(() => {})
                    }}
                  >
                    <Wallet className="h-3 w-3 mr-1" />
                    Use my portfolio ({holdingTickers.length} holdings)
                  </Button>
                )}
              </div>

              <div className="space-y-2">
                <Label>Question for Gemini</Label>
                <Textarea
                  value={analyzeQuestion}
                  onChange={e => setAnalyzeQuestion(e.target.value)}
                  rows={2}
                  placeholder="What should I do with these? Include entry, stop loss, target."
                />
              </div>

              <Button onClick={runAnalyze} disabled={loading || analyzeTickers.length === 0}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Sparkles className="h-4 w-4 mr-2" />}
                Analyze with Gemini
              </Button>

              {decisions.length > 0 && (
                <Card className="bg-muted/30">
                  <CardHeader className="pb-2"><CardTitle className="text-sm">Live signals (no AI)</CardTitle></CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {decisions.map((d: any) => {
                        const p = d.plan || {}
                        return (
                          <div key={d.ticker} className={`p-2 rounded border text-xs ${d.decision === "BUY" ? "border-emerald-500/30 bg-emerald-500/5" : d.decision === "SELL" ? "border-rose-500/30 bg-rose-500/5" : "border-border"}`}>
                            <div className="flex justify-between">
                              <span className="font-bold">{d.ticker}</span>
                              <Badge variant={d.decision === "BUY" ? "default" : d.decision === "SELL" ? "destructive" : "secondary"} className="text-[10px] px-1 py-0">{d.decision}</Badge>
                            </div>
                            {p.entry && (
                              <div className="text-muted-foreground mt-1">
                                ₹{p.entry} → SL ₹{p.stop_loss} → TP ₹{p.target} ({p.timeframe})
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </CardContent>
                </Card>
              )}

              {analyzeResult && (
                <div className="p-4 bg-muted rounded-md text-sm whitespace-pre-wrap">{analyzeResult}</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* STRATEGY Q&A */}
        <TabsContent value="strategy">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Ask about a specific strategy</CardTitle>
              <CardDescription>
                Gemini gets the strategy result + your actual watchlist + holdings + recent runs.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                value={strategyId}
                onChange={e => setStrategyId(e.target.value)}
                placeholder="strategy_id (e.g. magic_formula, rsi2, gap_fade)"
              />
              <Textarea
                value={strategyQuestion}
                onChange={e => setStrategyQuestion(e.target.value)}
                placeholder="Why did this underperform in 2022? Or: What tickers in my watchlist should I run this on?"
                rows={3}
              />
              <Button onClick={askStrategy} disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Send className="h-4 w-4 mr-2" />}
                Ask Gemini
              </Button>
              {strategyResult && (
                <div className="p-4 bg-muted rounded-md text-sm whitespace-pre-wrap">{strategyResult}</div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* PERSONALIZED NEXT STEPS */}
        <TabsContent value="next">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Sparkles className="h-4 w-4" />
                My next steps
              </CardTitle>
              <CardDescription>
                Gemini reads your Upstox holdings + tickers you've been researching + strategies you've run.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {!personalized?.text && !loading && (
                <Button onClick={loadPersonalized} disabled={loading}>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Get my personalized next steps
                </Button>
              )}
              {loading && <Loader2 className="h-5 w-5 animate-spin" />}
              {personalized?.text && (
                <>
                  <pre className="text-sm whitespace-pre-wrap font-sans">{personalized.text}</pre>
                  {personalized?.stats && (
                    <div className="text-xs text-muted-foreground mt-3 pt-3 border-t space-y-1">
                      {personalized.stats.watchlist?.length > 0 && (
                        <div>Watchlist: {personalized.stats.watchlist.join(", ")}</div>
                      )}
                      {personalized.stats.user_holdings?.length > 0 && (
                        <div>Holdings: {personalized.stats.user_holdings.length} positions, total ₹{personalized.stats.portfolio_summary?.total_current?.toLocaleString() ?? "?"}</div>
                      )}
                      {personalized.stats.most_used?.length > 0 && (
                        <div>Most-used: {personalized.stats.most_used.join(", ")}</div>
                      )}
                      <div>Recent runs: {personalized.stats.recent_runs?.length || 0}</div>
                    </div>
                  )}
                  <Button variant="outline" size="sm" onClick={loadPersonalized} disabled={loading} className="mt-3">
                    {loading ? <Loader2 className="h-3 w-3 animate-spin mr-2" /> : null}
                    Regenerate
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
