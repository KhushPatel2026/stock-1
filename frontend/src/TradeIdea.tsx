import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Compass,
  Search,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  Briefcase,
  Clock,
  Globe,
  Newspaper,
  AlertTriangle,
  ExternalLink,
} from "lucide-react"
import { fetchDecisions, fetchContext } from "@/api"
import type { Decision, MarketContext } from "@/api"

const QUICK_PICKS = [
  "RELIANCE.NS",
  "HDFCBANK.NS",
  "INFY.NS",
  "TCS.NS",
  "ITC.NS",
  "CANBK.NS",
  "ADANIENSOL.NS",
  "SBIN.NS",
]

function fmtSigned(v: number | undefined): string {
  if (v == null || Number.isNaN(v)) return "—"
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`
}

function fmtRs(v: number | undefined): string {
  if (v == null || Number.isNaN(v)) return "—"
  return `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`
}

export default function TradeIdea({ onTrade }: { onTrade: (ticker: string, side: "buy" | "sell") => void }) {
  const [ticker, setTicker] = useState("")
  const [verdict, setVerdict] = useState<Decision | null>(null)
  const [context, setContext] = useState<MarketContext | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ask = async (raw: string) => {
    const sym = raw.trim().toUpperCase()
    if (!sym) return
    setLoading(true)
    setError(null)
    setVerdict(null)
    setContext(null)
    try {
      const [r, c] = await Promise.all([
        fetchDecisions([sym], "3mo"),
        fetchContext(sym).catch(() => null),
      ])
      const d = r.decisions?.[0]
      if (!d) throw new Error("No verdict returned — try again in a minute.")
      setVerdict(d)
      if (c) setContext(c)
    } catch (e: any) {
      setError(e?.message ? String(e.message).slice(0, 180) : "Scan failed — backend may be warming up. Retry shortly.")
    } finally {
      setLoading(false)
    }
  }

  const isBuy = verdict?.decision === "BUY"
  const isSell = verdict?.decision === "SELL"
  const plan = verdict?.plan ?? null

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      {/* ASK */}
      <Card className="border-border/70 shadow-sm bg-card/90">
        <CardHeader className="pb-3 pt-4 px-5">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Compass className="h-4 w-4 text-primary" />
            What should I do with this stock?
          </CardTitle>
        </CardHeader>
        <CardContent className="px-5 pb-5 space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                placeholder="Type a stock — e.g. RELIANCE.NS"
                value={ticker}
                onChange={e => setTicker(e.target.value)}
                onKeyDown={e => e.key === "Enter" && ask(ticker)}
                className="pl-8 h-10 text-sm font-mono"
              />
            </div>
            <Button onClick={() => ask(ticker)} disabled={loading || !ticker.trim()} className="h-10 px-5">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Get Verdict"}
            </Button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {QUICK_PICKS.map(q => (
              <button
                key={q}
                type="button"
                onClick={() => {
                  setTicker(q)
                  ask(q)
                }}
                className="text-[11px] px-2 py-1 rounded-md border border-border/60 font-mono text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              >
                {q.replace(".NS", "")}
              </button>
            ))}
          </div>
          {error && (
            <p className="text-xs text-rose-400 border border-rose-500/30 bg-rose-500/5 rounded-lg p-2.5">{error}</p>
          )}
        </CardContent>
      </Card>

      {/* ANSWER */}
      {loading && (
        <Card className="border-border/70 bg-card/80">
          <CardContent className="py-10 flex flex-col items-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span>Asking all strategies about {ticker.trim().toUpperCase()}…</span>
          </CardContent>
        </Card>
      )}

      {verdict && !loading && (
        <Card
          className={`border shadow-sm overflow-hidden ${
            isBuy
              ? "border-emerald-500/40 bg-gradient-to-b from-emerald-500/10 via-emerald-500/5 to-transparent"
              : isSell
              ? "border-rose-500/40 bg-gradient-to-b from-rose-500/10 via-rose-500/5 to-transparent"
              : "border-border/70 bg-card/80"
          }`}
        >
          <CardContent className="p-5 space-y-4">
            {/* Verdict header */}
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="font-mono font-bold text-lg">{verdict.ticker.replace(".NS", "")}</div>
                <div className="text-xs text-muted-foreground font-mono">
                  {plan ? `${fmtRs(plan.price)}${plan.live_entry ? ` · Live ${plan.entry_label}` : ` · as of ${plan.as_of}`}` : verdict.ticker}
                </div>
              </div>
              <div className="text-right">
                <span
                  className={`inline-flex items-center gap-1.5 text-sm px-4 py-1.5 rounded-full font-bold ${
                    isBuy
                      ? "bg-emerald-500 text-white"
                      : isSell
                      ? "bg-rose-500 text-white"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {isBuy ? <TrendingUp className="h-4 w-4" /> : isSell ? <TrendingDown className="h-4 w-4" /> : <Minus className="h-4 w-4" />}
                  {verdict.decision}
                </span>
                <div className="text-[11px] text-muted-foreground font-mono mt-1">
                  Confidence {verdict.confidence.toFixed(0)}%
                </div>
              </div>
            </div>

            {/* Entry / Stop / Target */}
            {plan ? (
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded-xl border border-border/60 bg-background/50 p-3 text-center">
                  <div className="text-[10px] uppercase font-mono text-muted-foreground mb-1">
                    {plan.live_entry ? "Enter at (live)" : "Enter at"}
                  </div>
                  <div className="text-lg font-mono font-bold">{fmtRs(plan.entry)}</div>
                </div>
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 p-3 text-center">
                  <div className="text-[10px] uppercase font-mono text-rose-400 mb-1">Stop loss</div>
                  <div className="text-lg font-mono font-bold text-rose-400">{fmtRs(plan.stop_loss)}</div>
                  <div className="text-[11px] font-mono text-rose-400/80">{fmtSigned(plan.stop_pct)}</div>
                </div>
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-3 text-center">
                  <div className="text-[10px] uppercase font-mono text-emerald-400 mb-1">Target</div>
                  <div className="text-lg font-mono font-bold text-emerald-400">{fmtRs(plan.target)}</div>
                  <div className="text-[11px] font-mono text-emerald-400/80">{fmtSigned(plan.target_pct)}</div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground border border-dashed border-border/60 rounded-xl p-3">
                Price levels unavailable for this scan — the vote below still stands. Hit Get Verdict again to retry levels.
              </p>
            )}

            {/* Timeframe + risk */}
            {plan && (
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-primary/10 text-primary border border-primary/20 font-medium">
                  <Clock className="h-3 w-3" />
                  {plan.timeframe} · {plan.timeframe_detail}
                </span>
                <span className="font-mono text-muted-foreground">Risk : Reward = 1 : {plan.risk_reward}</span>
              </div>
            )}

            {/* Why */}
            {plan && <p className="text-[13px] leading-relaxed text-foreground/90">{plan.insight}</p>}

            {/* Votes */}
            <div className="space-y-1.5">
              <div className="w-full h-2 rounded-full overflow-hidden flex bg-muted/60">
                <div className="bg-emerald-500 h-full" style={{ width: `${verdict.long_pct}%` }} />
                <div className="bg-rose-500 h-full" style={{ width: `${verdict.short_pct}%` }} />
              </div>
              <div className="flex justify-between text-[11px] font-mono text-muted-foreground">
                <span className="text-emerald-500">↑ {verdict.n_long} say buy</span>
                <span>→ {verdict.n_flat} neutral</span>
                <span className="text-rose-500">↓ {verdict.n_short} say sell</span>
              </div>
            </div>

            {/* Macro: how the market weather moved the verdict */}
            {verdict.macro && (
              <div className="rounded-xl border border-sky-500/25 bg-sky-500/5 p-3 space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold flex items-center gap-1.5">
                    <Globe className="h-3.5 w-3.5 text-sky-500" />
                    Market says {verdict.macro.score > 0 ? "go" : verdict.macro.score < 0 ? "wait" : "neutral"}
                  </span>
                  <span className="font-mono text-muted-foreground">
                    vote {verdict.base_score.toFixed(0)} → macro {verdict.macro.score >= 0 ? "+" : ""}{verdict.macro.score} → final {verdict.score.toFixed(0)}
                  </span>
                </div>
                {verdict.macro.reasons.length > 0 && (
                  <ul className="text-[11px] text-muted-foreground space-y-0.5">
                    {verdict.macro.reasons.map((r, i) => (
                      <li key={i}>· {r}</li>
                    ))}
                  </ul>
                )}
                <div className="flex items-center justify-between text-[11px] pt-0.5">
                  <span className="font-mono text-foreground/80">
                    Size: {verdict.macro.sizing_note}
                  </span>
                  {verdict.macro.capped && (
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 font-medium">
                      confidence capped — macro disagrees
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Act */}
            <div className="flex items-center gap-2 pt-1">
              {(isBuy || isSell) && (
                <Button
                  onClick={() => onTrade(verdict.ticker, isBuy ? "buy" : "sell")}
                  className={`gap-2 ${isBuy ? "bg-emerald-600 hover:bg-emerald-500" : "bg-rose-600 hover:bg-rose-500"} text-white`}
                >
                  <Briefcase className="h-4 w-4" />
                  Paper-trade {isBuy ? "BUY" : "SELL"}
                </Button>
              )}
              <span className="text-[10px] text-muted-foreground/70">
                {verdict.n_long + verdict.n_short + verdict.n_flat} strategies voted · levels from 14-day ATR · paper-trade first
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* MARKET WEATHER — news, global, sector, commodity */}
      {context && !loading && (
        <Card className="border-border/70 shadow-sm bg-card/80">
          <CardContent className="p-5 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Globe className="h-4 w-4 text-sky-500" />
              Market weather
              <span className="text-[10px] font-mono font-normal text-muted-foreground">news + global + sector</span>
            </div>

            {context.summary && <p className="text-xs font-mono text-foreground/90">{context.summary}</p>}

            <div className="flex flex-wrap gap-1.5">
              <WxChip label="VIX" value={context.market.vix} suffix={` ${context.market.vix_state ?? ""}`} invert />
              {context.market.fii_5d_cr != null && (
                <span
                  title={`DII 5d ₹${(context.market.dii_5d_cr ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`}
                  className={`text-[11px] px-2 py-1 rounded-md border font-mono ${
                    context.market.fii_5d_cr >= 0
                      ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5"
                      : "text-rose-400 border-rose-500/30 bg-rose-500/5"
                  }`}
                >
                  FII 5d {context.market.fii_5d_cr >= 0 ? "+" : ""}₹{(context.market.fii_5d_cr / 1000).toFixed(1)}k Cr
                </span>
              )}
              {context.market.ad_ratio != null && (
                <span
                  title="Advance-decline ratio (Nifty 50 today)"
                  className="text-[11px] px-2 py-1 rounded-md border border-border/50 font-mono text-muted-foreground"
                >
                  A/D {context.market.ad_ratio.toFixed(2)}
                </span>
              )}
              {Object.entries(context.global).map(([name, g]) =>
                g.day_pct != null ? (
                  <WxChip key={name} label={name} value={g.day_pct} suffix="%" signed />
                ) : null
              )}
              {context.sector?.name && context.sector.day_pct != null && (
                <WxChip label={`${context.sector.name} sector`} value={context.sector.day_pct} suffix="%" signed />
              )}
              {context.commodity?.name && context.commodity.day_pct != null && (
                <WxChip label={`${context.commodity.name} (linked)`} value={context.commodity.day_pct} suffix="%" signed />
              )}
            </div>

            {context.cautions.length > 0 && (
              <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-2.5 space-y-1">
                {context.cautions.map((c, i) => (
                  <p key={i} className="text-[11px] text-amber-600 dark:text-amber-400 flex gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-px" />
                    {c}
                  </p>
                ))}
              </div>
            )}

            {context.news.items.length > 0 && (
              <NewsList title="Fresh headlines" source={context.news.source} items={context.news.items} />
            )}

            {context.market_news && context.market_news.items.length > 0 && (
              <NewsList title="Market headlines" source={context.market_news.source} items={context.market_news.items} />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function NewsList({ title, source, items }: { title: string; source: string; items: { title: string; source: string; time: string; link: string; tone: string }[] }) {
  return (
    <div className="space-y-1.5 pt-1">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground">
        <Newspaper className="h-3.5 w-3.5" />
        {title} · {source}
      </div>
      {items.map((a, i) => (
        <a
          key={i}
          href={a.link || undefined}
          target="_blank"
          rel="noreferrer"
          className="flex items-start gap-2 text-xs p-2 rounded-lg border border-border/40 hover:bg-muted/30 transition-colors"
        >
          <span
            title={`tone: ${a.tone}`}
            className={`mt-1 h-2 w-2 rounded-full shrink-0 ${
              a.tone === "positive"
                ? "bg-emerald-500"
                : a.tone === "negative"
                ? "bg-rose-500"
                : "bg-muted-foreground/40"
            }`}
          />
          <span className="flex-1">
            <span className="text-foreground/90">{a.title}</span>
            <span className="text-muted-foreground">
              {" "}
              — {a.source}
              {a.time ? ` · ${a.time}` : ""}
            </span>
          </span>
          {a.link && <ExternalLink className="h-3 w-3 text-muted-foreground shrink-0 mt-0.5" />}
        </a>
      ))}
    </div>
  )
}

function WxChip({ label, value, suffix = "", signed = false, invert = false }: {
  label: string
  value: number | undefined
  suffix?: string
  signed?: boolean
  invert?: boolean
}) {
  if (value == null) return null
  const up = value > 0
  const down = value < 0
  const cls = invert
    ? up
      ? "text-rose-400 border-rose-500/30 bg-rose-500/5"
      : down
      ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5"
      : "text-muted-foreground border-border/50"
    : up
    ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/5"
    : down
    ? "text-rose-400 border-rose-500/30 bg-rose-500/5"
    : "text-muted-foreground border-border/50"
  const txt = signed ? `${up ? "+" : ""}${value.toFixed(2)}${suffix}` : `${value}${suffix}`
  return (
    <span className={`text-[11px] px-2 py-1 rounded-md border font-mono ${cls}`}>
      {label} {txt}
    </span>
  )
}
