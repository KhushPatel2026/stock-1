import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import BacktestPanel from "@/BacktestPanel"
import StrategyLibrary from "@/StrategyLibrary"
import SignalsPanel from "@/SignalsPanel"
import PaperPanel from "@/PaperPanel"
import ReportsPanel from "@/ReportsPanel"

export default function App() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container py-6">
          <h1 className="text-3xl font-bold tracking-tight">stock-1</h1>
          <p className="text-sm text-muted-foreground">
            Nifty 50 systematic trading — 56 strategies, validation, paper trading.
          </p>
        </div>
      </header>

      <main className="container py-6">
        <Tabs defaultValue="backtest">
          <TabsList>
            <TabsTrigger value="backtest">Backtest</TabsTrigger>
            <TabsTrigger value="signals">Signals</TabsTrigger>
            <TabsTrigger value="paper">Paper</TabsTrigger>
            <TabsTrigger value="reports">Reports</TabsTrigger>
            <TabsTrigger value="library">Library</TabsTrigger>
            <TabsTrigger value="about">About</TabsTrigger>
          </TabsList>
          <TabsContent value="backtest">
            <BacktestPanel />
          </TabsContent>
          <TabsContent value="signals">
            <SignalsPanel />
          </TabsContent>
          <TabsContent value="paper">
            <PaperPanel />
          </TabsContent>
          <TabsContent value="reports">
            <ReportsPanel />
          </TabsContent>
          <TabsContent value="library">
            <StrategyLibrary />
          </TabsContent>
          <TabsContent value="about">
            <Card>
              <CardHeader><CardTitle>About stock-1</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  Systematic trading research platform for Nifty 50 large-caps. 56 named strategies
                  across 16 families: trend, mean reversion, momentum, factor, volume, pattern,
                  volatility, options, event, stat-arb, hedge, ML, allocation, carry, intraday.
                </p>
                <p>
                  Validation: walk-forward OOS Sharpe + regime tests (2018/2020/2022) — see Reports tab.
                  Paper trading: mock broker with state persistence — see Paper tab.
                  Real fundamentals: yfinance .info for Greenblatt EBIT/EV/ROE.
                </p>
                <p>
                  Honest caveat: in-sample research, not a production strategy. Real edges need
                  out-of-sample validation before any live capital. Live Zerodha integration, M&amp;A
                  event feed, and short interest are documented as external blockers.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      <footer className="container py-6 text-xs text-muted-foreground border-t">
        stock-1 v1.0.0 · <a href="https://github.com/KhushPatel2026/stock-1" className="underline">github.com/KhushPatel2026/stock-1</a>
      </footer>
    </div>
  )
}
