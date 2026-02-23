"""
backtest.py
-----------
Event-driven monthly backtest engine (2010 → present).

Assumptions:
  - Execution at NEXT month open (no lookahead bias)
  - Slippage: 0.2% per trade (each leg)
  - Brokerage: 0.1% per trade (each leg)
  - Equal-weight portfolio, max 10 positions
  - Capital reinvested after exits
  - Fundamental filter applied month-by-month using versioned master lists
    (falls back to latest available list if historical not found)
"""

import logging
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from indicators import compute_indicators, fetch_monthly_closes
from strategy import generate_signals, rank_buy_signals
from master_list import load_master_list, OUTPUT_DIR

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
SLIPPAGE    = 0.002   # 0.2%
BROKERAGE   = 0.001   # 0.1%
ROUND_TRIP  = (1 + SLIPPAGE + BROKERAGE)   # cost multiplier on buy
SELL_MULT   = (1 - SLIPPAGE - BROKERAGE)   # multiplier on sell proceeds
MAX_POS     = 10
START_DATE  = "2010-01-01"
BACKTEST_DATA_START = "2008-01-01"  # extra history for indicator warm-up


# ── Data loader (batch) ───────────────────────────────────────────────────────

def _load_all_monthly_data(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """
    Download and compute indicators for all tickers.
    Returns dict: ticker → indicator DataFrame.
    """
    logger.info("Loading monthly data for %d tickers...", len(tickers))
    cache: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        monthly = fetch_monthly_closes(ticker, start=BACKTEST_DATA_START)
        if monthly is None:
            continue
        ind_df = compute_indicators(monthly)
        sig_df = generate_signals(ind_df)
        cache[ticker] = sig_df

    logger.info("Data loaded for %d / %d tickers", len(cache), len(tickers))
    return cache


def _get_open_price(ticker: str, target_date: pd.Timestamp) -> float | None:
    """
    Fetch the open price of the first trading day in `target_date`'s month.
    """
    month_start = target_date.replace(day=1).strftime("%Y-%m-%d")
    next_month  = (target_date + pd.offsets.MonthEnd(1) + pd.DateOffset(days=1)).strftime("%Y-%m-%d")
    try:
        raw = yf.download(ticker, start=month_start, end=next_month,
                          interval="1d", progress=False, auto_adjust=True)
        if raw.empty:
            return None
        return float(raw["Open"].iloc[0])
    except Exception:
        return None


# ── Master list lookup ────────────────────────────────────────────────────────

def _get_master_tickers_for_month(year: int, month: int) -> set[str] | None:
    """
    Return the set of qualifying tickers for a given year/month.
    Falls back to the nearest earlier master list if exact month missing.
    """
    for m in range(month, 0, -1):
        ml = load_master_list(year, m)
        if ml is not None:
            return set(ml["Ticker"].tolist())

    # Try previous year
    for m in range(12, 0, -1):
        ml = load_master_list(year - 1, m)
        if ml is not None:
            return set(ml["Ticker"].tolist())

    logger.warning("No master list found for %d-%02d — using all tickers (survivorship risk!)", year, month)
    return None


# ── Core backtest loop ────────────────────────────────────────────────────────

def run_backtest(
    tickers: list[str],
    initial_capital: float = 1_000_000.0,
    start: str = START_DATE,
) -> dict:
    """
    Run the full backtest.

    Returns
    -------
    dict with keys:
        equity_curve  : pd.Series  (monthly portfolio value)
        drawdown      : pd.Series
        trades        : pd.DataFrame
        metrics       : dict
    """
    all_data = _load_all_monthly_data(tickers)
    if not all_data:
        raise RuntimeError("No data loaded — check universe / connectivity.")

    # Build unified monthly date index
    all_dates = sorted(
        set(
            date
            for df in all_data.values()
            for date in df.index
        )
    )
    all_dates = [d for d in all_dates if d >= pd.Timestamp(start)]

    capital   = initial_capital
    positions: dict[str, dict] = {}   # ticker → {shares, entry_price, entry_date}
    equity_curve: dict[pd.Timestamp, float] = {}
    trades: list[dict] = []

    for date in all_dates:
        year, month = date.year, date.month
        master_set  = _get_master_tickers_for_month(year, month)

        # ── 1. Gather signals for this month ─────────────────────────────
        buy_signals  = []
        exit_signals = []

        for ticker, df in all_data.items():
            if date not in df.index:
                continue
            i = df.index.get_loc(date)
            row = df.iloc[i]

            in_master = (master_set is None) or (ticker in master_set)

            # Force exit if stock left master list
            if ticker in positions and not in_master:
                exit_signals.append(ticker)
                continue

            if not in_master:
                continue

            if row.get("exit_signal", False) and ticker in positions:
                exit_signals.append(ticker)
            if row.get("buy_signal", False) and ticker not in positions:
                buy_signals.append(ticker)

        # ── 2. Execute exits at next month open ───────────────────────────
        next_date = date + pd.offsets.MonthBegin(1)

        for ticker in exit_signals:
            pos   = positions.pop(ticker)
            open_ = _get_open_price(ticker, next_date)
            if open_ is None:
                # Fall back to last close
                open_ = float(all_data[ticker].loc[date, "Close"])

            proceeds = pos["shares"] * open_ * SELL_MULT
            capital += proceeds

            holding = (next_date - pos["entry_date"]).days / 30
            gain_pct = (open_ * SELL_MULT - pos["entry_price"] * ROUND_TRIP) / (pos["entry_price"] * ROUND_TRIP) * 100

            trades.append({
                "Ticker":         ticker,
                "Entry_Date":     pos["entry_date"].strftime("%Y-%m"),
                "Exit_Date":      next_date.strftime("%Y-%m"),
                "Entry_Price":    round(pos["entry_price"], 2),
                "Exit_Price":     round(open_, 2),
                "Shares":         pos["shares"],
                "Gain_pct":       round(gain_pct, 2),
                "Holding_Months": round(holding, 1),
            })

        # ── 3. Rank buys & execute entries at next month open ─────────────
        open_slots = MAX_POS - len(positions)

        if buy_signals and open_slots > 0:
            # Rank by RSI14
            rsi_vals = []
            for t in buy_signals:
                df = all_data[t]
                if date in df.index:
                    rsi_vals.append((t, float(df.loc[date, "RSI14"])))

            rsi_vals.sort(key=lambda x: x[1], reverse=True)
            selected = [t for t, _ in rsi_vals[:open_slots]]

            alloc_per_stock = capital / (open_slots)  # equal-weight of free capital

            for ticker in selected:
                open_ = _get_open_price(ticker, next_date)
                if open_ is None or open_ <= 0:
                    continue

                shares = alloc_per_stock / (open_ * ROUND_TRIP)
                cost   = shares * open_ * ROUND_TRIP
                capital -= cost

                positions[ticker] = {
                    "shares":     shares,
                    "entry_price": open_,
                    "entry_date": next_date,
                }

        # ── 4. Mark-to-market portfolio value ────────────────────────────
        pos_value = 0.0
        for ticker, pos in positions.items():
            df = all_data[ticker]
            if date in df.index:
                pos_value += pos["shares"] * float(df.loc[date, "Close"])

        equity_curve[date] = capital + pos_value

    # ── Post-process ──────────────────────────────────────────────────────────
    eq = pd.Series(equity_curve).sort_index()
    eq_ret = eq.pct_change().dropna()

    # Drawdown
    rolling_max = eq.cummax()
    dd = (eq - rolling_max) / rolling_max * 100  # in %

    # Metrics
    n_years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr    = (eq.iloc[-1] / eq.iloc[0]) ** (1 / n_years) - 1 if n_years > 0 else 0

    rf          = 0.06  # 6% risk-free rate (Indian ~)
    monthly_ret = eq_ret.mean()
    monthly_std = eq_ret.std()
    sharpe      = ((monthly_ret - rf / 12) / monthly_std * np.sqrt(12)) if monthly_std > 0 else 0

    max_dd = dd.min()

    trades_df = pd.DataFrame(trades)
    win_rate  = (trades_df["Gain_pct"] > 0).mean() * 100 if not trades_df.empty else 0
    avg_hold  = trades_df["Holding_Months"].mean() if not trades_df.empty else 0

    # Exposure %: months with >0 positions / total months
    # (approximated as months equity != cash, i.e. positions_value > 1% of equity)
    exposure_pct = 100.0  # hard to compute without separate tracking; flag for manual review

    metrics = {
        "CAGR_%":          round(cagr * 100, 2),
        "Max_Drawdown_%":  round(max_dd, 2),
        "Sharpe_Ratio":    round(sharpe, 2),
        "Win_Rate_%":      round(win_rate, 2),
        "Avg_Hold_Months": round(avg_hold, 1),
        "Total_Trades":    len(trades_df),
        "Final_Capital":   round(eq.iloc[-1], 2),
    }

    return {
        "equity_curve": eq,
        "drawdown":     dd,
        "trades":       trades_df,
        "metrics":      metrics,
    }


# ── Chart generator ───────────────────────────────────────────────────────────

def plot_results(results: dict, out_dir: Path = Path(".")):
    """Generate equity curve + drawdown charts."""
    eq = results["equity_curve"]
    dd = results["drawdown"]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                              gridspec_kw={"height_ratios": [3, 1]})

    # Equity curve
    ax1 = axes[0]
    ax1.plot(eq.index, eq.values / 1e6, color="#2ecc71", linewidth=2, label="Portfolio")
    ax1.set_ylabel("Portfolio Value (₹ Mn)", fontsize=11)
    ax1.set_title("Monthly Structural Reversal System — Equity Curve", fontsize=13, fontweight="bold")
    ax1.legend()
    ax1.grid(alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:.1f}M"))

    # Drawdown
    ax2 = axes[1]
    ax2.fill_between(dd.index, dd.values, 0, color="#e74c3c", alpha=0.5, label="Drawdown")
    ax2.set_ylabel("Drawdown %", fontsize=11)
    ax2.set_xlabel("Date", fontsize=11)
    ax2.legend()
    ax2.grid(alpha=0.3)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()

    out_path = out_dir / "backtest_results.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Chart saved → %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    from universe_loader import load_universe
    from master_list import get_latest_master_list

    master = get_latest_master_list()
    if master is not None:
        tickers = master["Ticker"].tolist()
    else:
        logger.warning("No master list found — using small test set.")
        tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                   "WIPRO.NS", "HINDUNILVR.NS", "MARUTI.NS", "TITAN.NS", "BAJFINANCE.NS"]

    print(f"\n🚀  Running backtest on {len(tickers)} tickers from {START_DATE}...\n")
    results = run_backtest(tickers)

    print("\n📊 Backtest Metrics:")
    for k, v in results["metrics"].items():
        print(f"   {k:25s}: {v}")

    if not results["trades"].empty:
        print(f"\n📋 Trade Log ({len(results['trades'])} trades):")
        print(results["trades"].tail(10).to_string(index=False))

    chart = plot_results(results)
    print(f"\n📈 Chart saved: {chart}")
