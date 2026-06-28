# Automated DCF Equity Valuation Engine

A Python tool that pulls a company's financials and runs a full Discounted Cash Flow (DCF) valuation — the same core methodology used in equity research, investment banking, and CFA Level 2 corporate finance/equity valuation curriculum.

## What it does
- Projects 5-year free cash flows from current revenue, growth rate, and FCF margin assumptions
- Discounts cash flows at WACC and adds a Gordon Growth terminal value
- Computes intrinsic value per share and compares it to the live market price
- Builds a **WACC × Terminal Growth sensitivity grid** (the table every equity analyst includes in a pitch)
- Exports an FCF projection chart and a full Excel valuation workbook

## Why this matters for a finance role
This is the exact framework used in equity research reports, IB pitch books, and CFA Level 2's Equity Valuation and Corporate Finance readings. It shows you can translate a financial model from theory into working code that produces an investable conclusion (undervalued/overvalued), not just a spreadsheet.

## Tech stack
Python · pandas · numpy · matplotlib · openpyxl · yfinance

## Setup
```bash
pip install -r requirements.txt
python dcf_model.py RELIANCE.NS
```
Replace `RELIANCE.NS` with any NSE ticker (`TCS.NS`, `INFY.NS`) or US ticker (`AAPL`). If you're offline or Yahoo Finance rate-limits you, the script automatically falls back to bundled illustrative data so it never crashes — you'll see `[INFO] Live fetch failed...` printed, and the rest of the pipeline still runs.

## Outputs
- `fcf_projection_chart.png` — 5-year FCF projection vs discounted FCF
- `dcf_valuation_output.xlsx` — Summary, Year-by-year projections, Sensitivity table

## Customize for a real pitch
Open `dcf_model.py` and change the assumptions at the top:
```python
TICKER = "TCS.NS"
WACC = 0.11
TERMINAL_GROWTH = 0.04
REVENUE_GROWTH = 0.10
FCF_MARGIN = 0.14
```

## How to talk about this in an interview
- "I built an automated DCF engine in Python that pulls live financials and outputs an intrinsic value vs market price comparison, with a full WACC/growth sensitivity table — the same structure I'd build manually for a CFA Level 2 equity valuation case."
- Be ready to explain: why WACC matters as a discount rate, why terminal value typically accounts for 60-80% of total DCF value, and the key limitation of DCF (extremely sensitive to terminal growth and WACC assumptions — which is exactly why the sensitivity table exists).
- If asked "what would you change for a real client pitch": multi-stage growth (high growth → fade → terminal), scenario-based (bull/base/bear) FCF margins, and a proper WACC build-up (CAPM cost of equity + after-tax cost of debt) instead of a flat assumption.
