import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import BacktestPanel from "@/BacktestPanel"
import StrategyLibrary from "@/StrategyLibrary"

export default function App() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container py-6">
          <h1 className="text-3xl font-bold tracking-tight">stock-1</h1>
          <p className="text-sm text-muted-foreground">
            Nifty 50 systematic trading — 50+ strategies, all in your browser.
          </p>
        </div>
      </header>

      <main className="container py-6">
        <Tabs defaultValue="backtest">
          <TabsList>
            <TabsTrigger value="backtest">Backtest</TabsTrigger>
            <TabsTrigger value="library">Strategy Library</TabsTrigger>
            <TabsTrigger value="about">About</TabsTrigger>
          </TabsList>
          <TabsContent value="backtest">
            <BacktestPanel />
          </TabsContent>
          <TabsContent value="library">
            <StrategyLibrary />
          </TabsContent>
          <TabsContent value="about">
            <Card>
              <CardHeader><CardTitle>About stock-1</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  Systematic trading research platform for Nifty 50 large-caps. 50+ named strategies
                  across 16+ families: trend, mean reversion, momentum, factor, volume, pattern,
                  volatility, options, event, stat-arb, hedge, ML, allocation, carry.
                </p>
                <p>
                  All backtests run via the FastAPI backend at <code className="bg-muted px-1 rounded">/api/backtest</code>.
                  Data is fetched via yfinance and cached. Walk-forward + regime tests are still v1.0.0 work.
                </p>
                <p>
                  Honest caveat: in-sample research, not a production strategy. Real edges need
                  out-of-sample validation before any live capital.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>

      <footer className="container py-6 text-xs text-muted-foreground border-t">
        stock-1 v0.6.0 · <a href="https://github.com/KhushPatel2026/stock-1" className="underline">github.com/KhushPatel2026/stock-1</a>
      </footer>
    </div>
  )
}
