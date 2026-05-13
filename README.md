# Macro Regime Dashboard

A local-first macro regime and portfolio sizing overlay for a discretionary global growth equity investor running a leveraged IBKR portfolio.

**The dashboard answers exactly 3 questions:**
1. Is the environment supportive of risk?
2. How aligned are the signals?
3. How aggressively should I size?

---

## Philosophy

```
SIGNAL → COMPOSITE SCORE → CONVICTION FILTER → VETO CHECK → SIZING
```

- **Signals** describe the environment. They never prescribe trades.
- **Conviction** measures agreement across 8 layers. Low conviction caps sizing at Neutral even if the composite is high.
- **Vetoes** override averages when market fragility rises. Hard vetoes are non-negotiable.

---

## Setup

### 1. Install dependencies

```bash
cd macro_dashboard
pip install -r requirements.txt
```

### 2. (Optional) Add FRED API key

Create a `.env` file in the project root:

```
FRED_API_KEY=your_key_here
```

Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html

Without a key, the dashboard uses `pandas_datareader` as a fallback (no key required for most FRED series).

### 3. Run the dashboard

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Project Structure

```
macro_dashboard/
├── app.py              # Streamlit entry point
├── config.py           # All thresholds, weights, sizing bands
├── requirements.txt
├── README.md
├── data/
│   ├── market_data.py  # yfinance data fetcher
│   ├── fred_data.py    # FRED macro data fetcher
│   └── cache.py        # Local CSV cache (4hr TTL)
├── signals/
│   ├── base.py         # SignalResult dataclass + helpers
│   ├── trend.py        # SPY/QQQ/ACWI vs moving averages
│   ├── momentum.py     # ROC + acceleration
│   ├── volatility.py   # VIX level + term structure
│   ├── credit.py       # HY/IG spreads + KRE/SPY
│   ├── liquidity.py    # DXY + Fed balance sheet + RRP
│   ├── rates.py        # Real yields + curve shape
│   ├── risk_appetite.py# BTC + GLD/SPY + SMH/XLU + XLY/XLP
│   └── breadth.py      # RSP/SPY + IWM/SPY
├── engine/
│   ├── scoring.py      # Weighted composite score
│   ├── conviction.py   # Signal agreement meter
│   ├── veto.py         # Hard + soft veto rules
│   ├── sizing.py       # Portfolio sizing bands
│   └── regime.py       # 7 macro regime classifier
├── ui/
│   ├── layout.py       # Panel orchestration
│   ├── charts.py       # Plotly chart functions
│   └── cards.py        # Signal card rendering
└── tests/
    └── test_scoring.py # Unit tests for scoring + sizing
```

---

## Signal Layers

| Signal | Weight | Key Inputs |
|--------|--------|-----------|
| Trend | 20% | SPY/QQQ/ACWI vs 20/50/200DMA |
| Momentum | 15% | 1M/3M ROC + acceleration |
| Volatility | 15% | VIX level + term structure |
| Credit | 15% | HY/IG spreads + KRE/SPY |
| Liquidity | 10% | DXY (UUP) + Fed balance sheet |
| Rates | 10% | 10Y real yield + curve shape |
| Risk Appetite | 10% | BTC + GLD/SPY + SMH/XLU |
| Breadth | 5% | RSP/SPY + IWM/SPY |

---

## Sizing Bands

| Score | Posture | Target Gross | Action |
|-------|---------|-------------|--------|
| 80–100 | Full Risk-On | 1.35x–1.40x | Add |
| 60–79 | Lean Risk-On | 1.30x–1.35x | Add (selective) |
| 40–59 | Neutral | 1.25x–1.30x | Hold |
| 20–39 | Defensive | 1.15x–1.20x | Trim |
| 0–19 | Risk-Off | <1.10x | Deleverage |

**Overrides:**
- Low conviction → cap at Neutral regardless of composite score
- Any active hard veto → max gross cannot exceed veto ceiling

---

## Hard Veto Rules

| Condition | Max Gross |
|-----------|-----------|
| SPY below 200DMA | 1.15x |
| VIX backwardation | 1.20x |
| HY spreads +75bps in 20 days | 1.20x |
| Real yields + DXY both rising sharply | 1.25x |
| Composite < 40 | 1.20x |
| Composite < 20 | 1.10x |

---

## Macro Regimes

1. **Goldilocks Risk-On** — High trend + momentum + low vol + broad breadth
2. **AI/Liquidity Melt-Up** — Large-cap driven, semis leading, breadth narrow
3. **Inflation Scare** — Rising real yields + strong DXY + falling breadth
4. **Growth Scare** — Widening credit + falling yields + rising VIX
5. **Crisis Deleveraging** — VIX backwardation + HY widening + SPY below 200DMA
6. **Late-Cycle Narrow Rally** — SPY/QQQ fine but weak RSP + IWM
7. **Neutral/Transition** — Mixed signals, no dominant regime

---

## Configuration

All scoring thresholds, weights, and sizing bands are in `config.py`. No need to touch signal code to adjust:
- Signal weights (`SIGNAL_WEIGHTS`)
- VIX thresholds (`VIX_LOW`, `VIX_ELEVATED`)
- HY spread thresholds (`HY_SPREAD_NORMAL`, `HY_SPREAD_WIDE`)
- Veto rules (`HARD_VETO_RULES`, `SOFT_VETO_RULES`)
- Sizing bands (`SIZING_BANDS`)

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Data Sources

- **Market prices**: yfinance (free, no key required)
- **FRED macro series**: fredapi (key optional) or pandas_datareader (no key)
- **Cache**: Local CSV files in `data/cache/` directory, refreshed every 4 hours

---

## Phase 2 / Phase 3 Roadmap

**Phase 2** (planned):
- Alert history and weekly change detection
- Manual override inputs
- IBKR CSV portfolio exposure import

**Phase 3** (planned):
- LLM-generated narrative summary via Anthropic API
- Historical backtesting of composite score vs SPY/QQQ forward returns
- Telegram/email alerts for regime changes

---

## Important Notes

- This dashboard is a **signal overlay**, not a trading system
- All outputs are informational and require discretionary judgment
- Past signal quality does not guarantee future regime predictability
- Default gross exposure targets assume a leveraged IBKR account with ~1.25x–1.40x normal operating range
