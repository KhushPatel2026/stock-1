import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Loader2, Sparkles, Brain, MessageSquare } from "lucide-react"
import { fetchAIStatus, aiPersonalized, aiExplainStrategy, fetchPortfolio } from "@/api"

export default function AIInsights() {
  const [status, setStatus] = useState<{ available: boolean } | null>(null)
  const [personalized, setPersonalized] = useState<{ text: string; ai_enabled: boolean; stats: any } | null>(null)
  const [question, setQuestion] = useState("")
  const [explanation, setExplanation] = useState<{ text: string; ai_enabled: boolean } | null>(null)
  const [strategyId, setStrategyId] = useState("magic_formula")
  const [portfolioInsight, setPortfolioInsight] = useState<{ text: string; ai_enabled: boolean } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAIStatus().then(setStatus).catch(() => setStatus({ available: false }))
    loadPersonalized()
  }, [])

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

  const askQuestion = async () => {
    if (!strategyId) return
    setLoading(true)
    setError(null)
    try {
      const r = await aiExplainStrategy(strategyId, { sharpe: 1.2, total_return: 0.18, max_drawdown: -0.08, n_bars: 252 }, question)
      setExplanation(r)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const analyzePortfolio = async () => {
    setLoading(true)
    try {
      const p = await fetchPortfolio()
      if (p.authenticated && p.holdings && p.summary) {
        const r = await fetch("/api/ai/explain-portfolio", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ holdings: p.holdings, summary: p.summary }),
        }).then(r => r.json())
        setPortfolioInsight(r)
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            AI Insights
            <Badge variant={status?.available ? "default" : "outline"} className="ml-2">
              {status?.available ? "Gemini enabled" : "Gemini fallback"}
            </Badge>
          </CardTitle>
          <CardDescription>
            Powered by Gemini Flash Lite. Provides plain-English explanations of strategies and personalized next-action recommendations.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* PERSONALIZED */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            Your next steps
            <Button variant="ghost" size="sm" onClick={loadPersonalized} disabled={loading} className="ml-auto">
              {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : "Refresh"}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {personalized?.text ? (
            <pre className="text-sm whitespace-pre-wrap font-sans">{personalized.text}</pre>
          ) : (
            <p className="text-sm text-muted-foreground">Loading...</p>
          )}
          {personalized?.stats && (
            <div className="text-xs text-muted-foreground mt-3 pt-3 border-t">
              <div>Most-used strategies: {personalized.stats.most_used?.join(", ") || "none yet"}</div>
              <div>Recent runs: {personalized.stats.recent_runs?.length || 0}</div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* STRATEGY EXPLANATION */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <MessageSquare className="h-4 w-4" />
            Ask about a strategy
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={strategyId}
              onChange={e => setStrategyId(e.target.value)}
              placeholder="strategy_id (e.g. magic_formula, rsi2)"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
          </div>
          <Textarea
            value={question}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setQuestion(e.target.value)}
            placeholder="Ask anything (e.g. 'Why did this strategy underperform in 2022?' or 'What market regime favors this?')"
            rows={3}
          />
          <Button onClick={askQuestion} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {loading ? "Thinking..." : "Ask"}
          </Button>
          {explanation && (
            <div className="mt-3 p-3 bg-muted rounded-md text-sm whitespace-pre-wrap">{explanation.text}</div>
          )}
        </CardContent>
      </Card>

      {/* PORTFOLIO AI */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Brain className="h-4 w-4" />
            Analyze my portfolio
          </CardTitle>
          <CardDescription>Connect Upstox first, then click below for AI analysis of your actual holdings.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button onClick={analyzePortfolio} disabled={loading} variant="outline">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Analyze portfolio with Gemini
          </Button>
          {portfolioInsight && (
            <div className="mt-3 p-3 bg-muted rounded-md text-sm whitespace-pre-wrap">{portfolioInsight.text}</div>
          )}
          {error && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
    </div>
  )
}
