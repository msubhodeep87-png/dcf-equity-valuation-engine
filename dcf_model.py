"""
Automated DCF Equity Valuation Engine
---------------------------------------
Pulls a company's financials (live via yfinance, with an offline sample
fallback so the project always runs), projects free cash flows, discounts
them at WACC, and outputs:
    1. Intrinsic value per share vs current market price
    2. A WACC x Terminal Growth sensitivity grid
    3. A 5-year FCF projection chart (PNG)
    4. A full valuation workbook (Excel)

Author: Subho | Built for finance-role portfolio
"""

import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# 1. CONFIG — change the ticker and assumptions here
# ----------------------------------------------------------------------
TICKER = "RELIANCE.NS"      # any NSE ticker, e.g. "TCS.NS", "INFY.NS", or US "AAPL"
PROJECTION_YEARS = 5
WACC = 0.11                 # discount rate (weighted avg cost of capital)
TERMINAL_GROWTH = 0.04      # perpetuity growth rate after year 5
REVENUE_GROWTH = 0.10       # assumed YoY revenue growth for projection
FCF_MARGIN = 0.14           # assumed free cash flow margin on revenue
CURRENCY = "INR"


def fetch_live_financials(ticker: str):
    """Attempt to pull real financials from Yahoo Finance via yfinance."""
    import yfinance as yf
    tk = yf.Ticker(ticker)
    info = tk.info
    revenue = info.get("totalRevenue")
    shares_out = info.get("sharesOutstanding")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    net_debt = (info.get("totalDebt") or 0) - (info.get("totalCash") or 0)
    if not all([revenue, shares_out, price]):
        raise ValueError("Incomplete data from API")
    return {
        "company": info.get("shortName", ticker),
        "revenue": revenue,
        "shares_out": shares_out,
        "price": price,
        "net_debt": net_debt,
    }


def sample_financials(ticker: str):
    """Offline fallback so this script ALWAYS runs end-to-end (used when
    there's no internet access, e.g. in a sandboxed environment, or when
    the API rate-limits you). Swap in real numbers any time."""
    return {
        "company": f"{ticker} — ILLUSTRATIVE DEMO DATA (no internet / API limit hit, replace with live pull)",
        "revenue": 500_000_000_000,      # ₹50,000 Cr
        "shares_out": 500_000_000,       # 50 Cr shares
        "price": 2_200.0,
        "net_debt": 50_000_000_000,      # ₹5,000 Cr
    }


def get_financials(ticker: str):
    try:
        data = fetch_live_financials(ticker)
        data["source"] = "LIVE (Yahoo Finance via yfinance)"
        return data
    except Exception as e:
        print(f"[INFO] Live fetch failed ({e}). Using bundled sample data so the model still runs.")
        data = sample_financials(ticker)
        data["source"] = "SAMPLE / OFFLINE"
        return data


def project_free_cash_flows(base_revenue, growth, fcf_margin, years):
    revenues = [base_revenue * ((1 + growth) ** i) for i in range(1, years + 1)]
    fcfs = [r * fcf_margin for r in revenues]
    return revenues, fcfs


def discount_cash_flows(fcfs, wacc):
    return [fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcfs)]


def terminal_value(last_fcf, wacc, terminal_growth):
    tv = last_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    return tv / ((1 + wacc) ** PROJECTION_YEARS)


def run_dcf(data):
    revenues, fcfs = project_free_cash_flows(
        data["revenue"], REVENUE_GROWTH, FCF_MARGIN, PROJECTION_YEARS
    )
    discounted_fcfs = discount_cash_flows(fcfs, WACC)
    pv_terminal = terminal_value(fcfs[-1], WACC, TERMINAL_GROWTH)
    enterprise_value = sum(discounted_fcfs) + pv_terminal
    equity_value = enterprise_value - data["net_debt"]
    intrinsic_value_per_share = equity_value / data["shares_out"]

    upside_pct = (intrinsic_value_per_share / data["price"] - 1) * 100
    verdict = "UNDERVALUED" if upside_pct > 0 else "OVERVALUED"

    return {
        "revenues": revenues,
        "fcfs": fcfs,
        "discounted_fcfs": discounted_fcfs,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "equity_value": equity_value,
        "intrinsic_value_per_share": intrinsic_value_per_share,
        "upside_pct": upside_pct,
        "verdict": verdict,
    }


def sensitivity_table(data, wacc_range, growth_range):
    rows = []
    for w in wacc_range:
        row = []
        for g in growth_range:
            revenues, fcfs = project_free_cash_flows(
                data["revenue"], REVENUE_GROWTH, FCF_MARGIN, PROJECTION_YEARS
            )
            disc = discount_cash_flows(fcfs, w)
            tv = fcfs[-1] * (1 + g) / (w - g) / ((1 + w) ** PROJECTION_YEARS)
            ev = sum(disc) + tv
            eq = ev - data["net_debt"]
            per_share = eq / data["shares_out"]
            row.append(round(per_share, 1))
        rows.append(row)
    df = pd.DataFrame(
        rows,
        index=[f"WACC {w*100:.1f}%" for w in wacc_range],
        columns=[f"g {g*100:.1f}%" for g in growth_range],
    )
    return df


def make_chart(data, result, outpath):
    years = [f"Y{i+1}" for i in range(PROJECTION_YEARS)]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(years, [f / 1e9 for f in result["fcfs"]], color="#1f6f4a", label="Projected FCF (₹ Bn)")
    ax.plot(years, [d / 1e9 for d in result["discounted_fcfs"]], color="#d4af37",
            marker="o", linewidth=2, label="Discounted FCF (₹ Bn)")
    ax.set_title(f"{data['company']} — 5-Year FCF Projection & Discounting", fontsize=12)
    ax.set_ylabel("₹ Billions")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def export_excel(data, result, sens_df, outpath):
    with pd.ExcelWriter(outpath, engine="openpyxl") as writer:
        summary = pd.DataFrame({
            "Metric": ["Company", "Data Source", "Current Price", "Intrinsic Value / Share",
                       "Upside / Downside %", "Verdict", "Enterprise Value", "Equity Value",
                       "WACC", "Terminal Growth"],
            "Value": [data["company"], data["source"], round(data["price"], 2),
                      round(result["intrinsic_value_per_share"], 2),
                      f"{result['upside_pct']:.1f}%", result["verdict"],
                      round(result["enterprise_value"], 0), round(result["equity_value"], 0),
                      f"{WACC*100:.1f}%", f"{TERMINAL_GROWTH*100:.1f}%"]
        })
        summary.to_excel(writer, sheet_name="Summary", index=False)

        proj = pd.DataFrame({
            "Year": [f"Y{i+1}" for i in range(PROJECTION_YEARS)],
            "Revenue": result["revenues"],
            "FCF": result["fcfs"],
            "Discounted FCF": result["discounted_fcfs"],
        })
        proj.to_excel(writer, sheet_name="Projections", index=False)
        sens_df.to_excel(writer, sheet_name="Sensitivity (WACC x g)")


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else TICKER
    data = get_financials(ticker)
    result = run_dcf(data)
    sens_df = sensitivity_table(
        data,
        wacc_range=[0.09, 0.10, 0.11, 0.12, 0.13],
        growth_range=[0.02, 0.03, 0.04, 0.05],
    )

    make_chart(data, result, "fcf_projection_chart.png")
    export_excel(data, result, sens_df, "dcf_valuation_output.xlsx")

    print("=" * 60)
    print(f"DCF VALUATION REPORT — {data['company']}")
    print(f"Data source: {data['source']}")
    print("=" * 60)
    print(f"Current Market Price       : {CURRENCY} {data['price']:,.2f}")
    print(f"Intrinsic Value / Share    : {CURRENCY} {result['intrinsic_value_per_share']:,.2f}")
    print(f"Upside / Downside          : {result['upside_pct']:.1f}%")
    print(f"Verdict                    : {result['verdict']}")
    print(f"Enterprise Value           : {CURRENCY} {result['enterprise_value']/1e9:,.1f} Bn")
    print(f"Equity Value               : {CURRENCY} {result['equity_value']/1e9:,.1f} Bn")
    print("-" * 60)
    print("Sensitivity Table (Intrinsic Value/Share — WACC vs Terminal Growth):")
    print(sens_df.to_string())
    print("-" * 60)
    print("Outputs written: fcf_projection_chart.png, dcf_valuation_output.xlsx")


if __name__ == "__main__":
    main()
