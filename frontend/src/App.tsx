import { useState, useEffect } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Activity,
  Radio,
  Briefcase,
  FileBarChart2,
  BookOpen,
  Info,
  ExternalLink,
  ShieldCheck,
  Cpu,
  Layers,
  Database,
  Wallet,
  Brain,
  Globe,
  Compass,
} from "lucide-react"
import BacktestPanel from "@/BacktestPanel"
import StrategyLibrary from "@/StrategyLibrary"
import SignalsPanel from "@/SignalsPanel"
import PaperPanel from "@/PaperPanel"
import ReportsPanel from "@/ReportsPanel"
import Portfolio from "@/Portfolio"
import AIInsights from "@/AIInsights"
import TradeIdea from "@/TradeIdea"
import MacroPanel from "@/MacroPanel"
import Callback from "@/Callback"
import { ThemeToggle } from "@/components/ThemeToggle"

export default function App() {
  // OAuth callback route — render standalone page
  if (typeof window !== "undefined" && window.location.pathname === "/callback") {
    return <Callback />
  }

  const [activeTab, setActiveTab] = useState("idea")
  const [targetStrategy, setTargetStrategy] = useState<string | null>(null)
  const [targetTicker, setTargetTicker] = useState<string | null>(null)
  const [paperOrderPrefill, setPaperOrderPrefill] = useState<{ ticker: string; side: "buy" | "sell" } | null>(null)
  const [istTime, setIstTime] = useState("")
  const [isMarketOpen, setIsMarketOpen] = useState(false)
  const [strategyCount, setStrategyCount] = useState<number | null>(null)
  const [familyCount, setFamilyCount] = useState<number | null>(null)

  // Live strategy/family counts — never hardcode, the library keeps growing
  useEffect(() => {
    fetch(`${(import.meta as any).env?.VITE_API_URL || ""}/api/strategies`)
      .then(r => (r.ok ? r.json() : []))
      .then((s: unknown[]) => setStrategyCount(s.length))
      .catch(() => {})
    fetch(`${(import.meta as any).env?.VITE_API_URL || ""}/api/families`)
      .then(r => (r.ok ? r.json() : []))
      .then((f: unknown[]) => setFamilyCount(f.length))
      .catch(() => {})
  }, [])

  // Live IST market status clock (NSE: 9:15 AM - 3:30 PM IST, Mon-Fri)
  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      // Convert to IST (UTC + 5:30)
      const utc = now.getTime() + now.getTimezoneOffset() * 60000
      const istDate = new Date(utc + 3600000 * 5.5)

      const hours = istDate.getHours()
      const minutes = istDate.getMinutes()
      const seconds = istDate.getSeconds()
      const day = istDate.getDay() // 0 is Sunday, 6 is Saturday

      const timeStr = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")} IST`
      setIstTime(timeStr)

      // Weekday check (Mon=1 ... Fri=5)
      const isWeekday = day >= 1 && day <= 5
      const currentMin = hours * 60 + minutes
      const openMin = 9 * 60 + 15 // 09:15
      const closeMin = 15 * 60 + 30 // 15:30

      setIsMarketOpen(isWeekday && currentMin >= openMin && currentMin <= closeMin)
    }

    updateTime()
    const timer = setInterval(updateTime, 1000)
    return () => clearInterval(timer)
  }, [])

  const handleLaunchBacktest = (strategyId: string, ticker?: string) => {
    setTargetStrategy(strategyId)
    if (ticker) setTargetTicker(ticker)
    setActiveTab("backtest")
  }

  const handleLaunchPaperOrder = (ticker: string, side: "buy" | "sell") => {
    setPaperOrderPrefill({ ticker, side })
    setActiveTab("paper")
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-primary/20 selection:text-primary">
      {/* EXECUTIVE HEADER */}
      <header className="sticky top-0 z-40 border-b border-border/70 glass-panel">
        <div className="container flex flex-col md:flex-row items-center justify-between gap-3 py-3 px-4 sm:px-6">
          {/* Brand & Market Status */}
          <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-400 flex items-center justify-center shadow-lg shadow-blue-500/25 border border-white/20">
                <Activity className="h-5 w-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-foreground via-foreground/90 to-foreground/70 bg-clip-text text-transparent">
                    stock-1
                  </span>
                  <span className="text-[10px] uppercase font-mono tracking-wider px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20 font-semibold">
                    v1.0 Quant
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground hidden sm:block">
                  Nifty 50 Systematic Quantitative Engine
                </p>
              </div>
            </div>

            {/* NSE Live Indicator Pill */}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-full border border-border/80 bg-background/60 backdrop-blur text-xs">
              <span className="relative flex h-2 w-2">
                {isMarketOpen && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                )}
                <span
                  className={`relative inline-flex rounded-full h-2 w-2 ${
                    isMarketOpen ? "bg-emerald-500" : "bg-amber-500"
                  }`}
                ></span>
              </span>
              <span className="font-mono text-[11px] font-medium text-foreground/90">
                {isMarketOpen ? "NSE OPEN" : "NSE CLOSED"}
              </span>
              <span className="text-muted-foreground text-[10px] hidden sm:inline">·</span>
              <span className="font-mono text-[11px] text-muted-foreground hidden sm:inline">{istTime}</span>
            </div>
          </div>

          {/* Quick Stats & Utilities */}
          <div className="flex items-center gap-2.5 w-full md:w-auto justify-end">
            <div className="hidden lg:flex items-center gap-1.5 text-xs text-muted-foreground font-mono bg-muted/40 px-3 py-1 rounded-lg border border-border/60">
              <span className="font-semibold text-foreground">{strategyCount ?? "…"}</span> Strategies
              <span>·</span>
              <span className="font-semibold text-foreground">{familyCount ?? "…"}</span> Families
              <span>·</span>
              <span className="text-emerald-500 font-medium">Walk-Forward</span> Validated
            </div>

            <ThemeToggle />

            <a
              href="https://github.com/KhushPatel2026/stock-1"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg border border-border/80 bg-background/50 hover:bg-accent text-foreground/80 hover:text-foreground transition-colors"
            >
              <span>GitHub</span>
              <ExternalLink className="h-3 w-3 opacity-60" />
            </a>
          </div>
        </div>
      </header>

      {/* MAIN TRADING WORKSPACE */}
      <main className="container flex-1 py-5 px-4 sm:px-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-5">
          {/* TAB BAR */}
          <div className="flex items-center justify-between overflow-x-auto pb-1 border-b border-border/60">
            <TabsList className="bg-muted/40 p-1 rounded-xl border border-border/60 h-auto gap-1">
              <TabsTrigger
                value="idea"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <Compass className="h-3.5 w-3.5 text-primary" />
                Trade Idea
              </TabsTrigger>
              <TabsTrigger
                value="backtest"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <Activity className="h-3.5 w-3.5 text-blue-500" />
                Backtest Engine
              </TabsTrigger>
              <TabsTrigger
                value="portfolio"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <Wallet className="h-3.5 w-3.5 text-emerald-600" />
                Portfolio
              </TabsTrigger>
              <TabsTrigger
                value="ai"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <Brain className="h-3.5 w-3.5 text-purple-600" />
                AI Insights
              </TabsTrigger>
              <TabsTrigger
                value="macro"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <Globe className="h-3.5 w-3.5 text-cyan-600" />
                Macro
              </TabsTrigger>
              <TabsTrigger
                value="signals"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <Radio className="h-3.5 w-3.5 text-emerald-500" />
                Signals Radar
              </TabsTrigger>
              <TabsTrigger
                value="paper"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <Briefcase className="h-3.5 w-3.5 text-purple-500" />
                Paper Terminal
              </TabsTrigger>
              <TabsTrigger
                value="reports"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <FileBarChart2 className="h-3.5 w-3.5 text-amber-500" />
                Regime & Reports
              </TabsTrigger>
              <TabsTrigger
                value="library"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <BookOpen className="h-3.5 w-3.5 text-cyan-500" />
                Strategy Library
                <Badge variant="secondary" className="ml-1 px-1.5 py-0 text-[10px] font-mono h-4">
                  {strategyCount ?? "…"}
                </Badge>
              </TabsTrigger>
              <TabsTrigger
                value="about"
                className="gap-2 px-3.5 py-2 rounded-lg text-xs font-medium data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm transition-all"
              >
                <Info className="h-3.5 w-3.5 text-muted-foreground" />
                Architecture
              </TabsTrigger>
            </TabsList>
          </div>

          {/* TAB CONTENTS */}
          <TabsContent value="idea" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <TradeIdea onTrade={handleLaunchPaperOrder} />
          </TabsContent>

          <TabsContent value="backtest" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <BacktestPanel
              targetStrategy={targetStrategy}
              targetTicker={targetTicker}
              onNavigateToPaper={handleLaunchPaperOrder}
            />
          </TabsContent>

          <TabsContent value="portfolio" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <Portfolio />
          </TabsContent>

          <TabsContent value="ai" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <AIInsights />
          </TabsContent>

          <TabsContent value="signals" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <SignalsPanel
              onSelectSignalOrder={handleLaunchPaperOrder}
              onBacktestStrategy={handleLaunchBacktest}
            />
          </TabsContent>

          <TabsContent value="paper" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <PaperPanel prefilledOrder={paperOrderPrefill} />
          </TabsContent>

          <TabsContent value="reports" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <ReportsPanel onBacktestStrategy={handleLaunchBacktest} />
          </TabsContent>

          <TabsContent value="portfolio" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <Portfolio />
          </TabsContent>

          <TabsContent value="ai" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <AIInsights />
          </TabsContent>

          <TabsContent value="macro" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <MacroPanel />
          </TabsContent>

          <TabsContent value="library" className="focus-visible:outline-none focus-visible:ring-0 mt-0">
            <StrategyLibrary onBacktestStrategy={handleLaunchBacktest} />
          </TabsContent>

          <TabsContent value="about" className="focus-visible:outline-none focus-visible:ring-0 mt-0 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="border-border/70 shadow-sm bg-card/80 backdrop-blur">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2 text-primary font-semibold text-sm">
                    <Cpu className="h-4 w-4" />
                    Quantitative Core
                  </div>
                  <CardTitle className="text-lg">{strategyCount ?? "…"} Systematic Strategies</CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground space-y-2 leading-relaxed">
                  <p>
                    Covers {familyCount ?? "…"} mathematical families: Trend Following, Mean Reversion, Momentum, Factor
                    Investing (Magic Formula, Quality, Value), Volatility Breakouts, Options Modeling,
                    Statistical Arbitrage, Cross-Sectional Ranking, and Machine Learning overlays.
                  </p>
                  <p>
                    Vectorized execution engine computes indicator signals, target weights, friction, and
                    slippage across historical price matrices in milliseconds.
                  </p>
                </CardContent>
              </Card>

              <Card className="border-border/70 shadow-sm bg-card/80 backdrop-blur">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2 text-emerald-500 font-semibold text-sm">
                    <ShieldCheck className="h-4 w-4" />
                    Validation Framework
                  </div>
                  <CardTitle className="text-lg">Walk-Forward & Regime Tests</CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground space-y-2 leading-relaxed">
                  <p>
                    Rigorous Out-Of-Sample (OOS) walk-forward testing avoids data snooping and curve fitting.
                    Every strategy is continuously evaluated over rolling windows.
                  </p>
                  <p>
                    Regime stress-tests benchmark resilience against extreme market disruptions:
                    the 2018 NBFC credit crunch, the 2020 COVID crash, and the 2022 chop market.
                  </p>
                </CardContent>
              </Card>

              <Card className="border-border/70 shadow-sm bg-card/80 backdrop-blur">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2 text-purple-500 font-semibold text-sm">
                    <Database className="h-4 w-4" />
                    Data Sources
                  </div>
                  <CardTitle className="text-lg">yfinance + Upstox + Gemini</CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground space-y-2 leading-relaxed">
                  <p>
                    Default data: yfinance (daily + 60m intraday). Upstox Analytics adds option chain,
                    greeks, PCR, India VIX, OI when you supply an access token.
                  </p>
                  <p>
                    Upstox Portfolio API pulls your real holdings + computes P&amp;L + concentration risk.
                    Gemini Flash Lite provides plain-English strategy explanations.
                  </p>
                </CardContent>
              </Card>
            </div>

            <Card className="border-amber-500/30 bg-amber-500/5">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center gap-2 text-amber-600 dark:text-amber-400">
                  <Layers className="h-4 w-4" />
                  Institutional Notice & Production Caveats
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-1.5 leading-relaxed">
                <p>
                  <strong>Research Platform:</strong> stock-1 is designed as a rigorous quantitative research sandbox.
                  Past simulated backtest results do not guarantee live market alpha.
                </p>
                <p>
                  Live Zerodha Kite Connect integration, real-time M&amp;A/earnings event feeds, and intraday
                  short-selling capabilities are documented external extensions. Always perform independent
                  walk-forward verification prior to deploying proprietary capital.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      {/* TERMINAL FOOTER */}
      <footer className="border-t border-border/70 bg-card/40 py-3 text-xs text-muted-foreground">
        <div className="container flex flex-col sm:flex-row items-center justify-between gap-2 px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
            <span className="font-mono text-[11px]">System Ready · Latency &lt; 20ms</span>
            <span>·</span>
            <span>stock-1 v1.1.0</span>
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <span className="text-muted-foreground/80">Nifty 50 Systematic Trading Lab</span>
            <a
              href="https://github.com/KhushPatel2026/stock-1"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-foreground transition-colors"
            >
              Documentation
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
