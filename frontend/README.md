# Frontend — stock-1

React + Vite + TypeScript + shadcn/ui + Tailwind CSS.

## Quickstart

```bash
# Terminal 1: backend (FastAPI)
pip install -r requirements-api.txt
cd .. && python3 -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend (Vite)
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

Vite proxies `/api/*` to the backend on `127.0.0.1:8000`.

## Build

```bash
npm run build       # production bundle in dist/
npm run preview     # preview production build
```

## Stack

- **React 18** + **TypeScript**
- **Vite** (dev server + bundler)
- **shadcn/ui** components (Button, Card, Input, Select, Tabs, Table, Badge, Label)
- **Tailwind CSS v3**
- **recharts** for equity curve
- **lucide-react** for icons

## What's in here

```
frontend/
  src/
    App.tsx                  # tab shell (Backtest | Library | About)
    BacktestPanel.tsx        # backtest config + equity curve + metrics + trades
    StrategyLibrary.tsx      # browse all 50 strategies with search + family filter
    api.ts                   # typed API client
    lib/utils.ts             # cn() helper
    components/ui/           # shadcn-style primitives
      button.tsx
      card.tsx
      input.tsx
      label.tsx
      select.tsx
      tabs.tsx
      table.tsx
      badge.tsx
    index.css                # tailwind + shadcn theme tokens
```

## Endpoints consumed

| Endpoint | Used by |
|----------|---------|
| GET /api/health | sanity check |
| GET /api/strategies | library list, dropdown options |
| GET /api/tickers | ticker hints in the input |
| GET /api/families | family filter chips |
| POST /api/backtest | the run button |

## Honest caveats

- All backtests are in-sample research. See backend runbook for known limits.
- yfinance is the only data source; some strategies use price-derived proxies for fundamentals (documented in ADR-005).
- Walk-forward + regime tests still v1.0.0 work.
