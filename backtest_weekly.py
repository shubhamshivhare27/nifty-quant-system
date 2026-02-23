"""
backtest.py  (Weekly Strategy)
--------------------------------
Event-driven weekly backtest — 2010 to present.

Assumptions:
  - Execution at NEXT week open (no lookahead bias)
  - Slippage: 0.2% per leg
  - Brokerage: 0.1% per leg
  - Equal-weight, max 10 positions
  - Capital reinvested after exits
  - Monthly master list applied week-by-week
"""

import logging
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from indicators import compute_indicators, fetch_weekly_closes
from strategy import generate_signals, rank_buy_signals

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

SLIPPAGE   = 0.002
BROKERAGE  = 0.001
BUY_COST   = 1 + SLIPPAGE + BROKERAGE
SELL_YIELD = 1 - SLIPPAGE - BROKERAGE
MAX_POS    = 10
START_DATE = "2010-01-01"
DATA_START = "2008-01-01"


def _load_all_weekly_data(tickers: list[str]) -> dict[str, pd.DataFrame]:
    """Download + compute indicators for all tickers. Returns ticker → DataFrame."""
    logger.info("Loading weekly data for %d tickers...", len(tickers))
    cache = {}
    for ticker in tickers:
        weekly = fetch_weekly_closes(ticker, start=DATA_START)
        if weekly is None:
            continue
        ind = compute_indicators(weekly)
        sig = generate_signals(ind)
        cache[ticker] = sig
    logger.info("Loaded %d / %d tickers", len(cache), len(tickers))
    return cache


def _get_open_price(ticker: str, target_date: pd.Timestamp) -> float | None:
    """Fetch open price of the first trading day of the week containing target_date."""
    week_start = (target_date - pd.Timedelta(days=target_date.weekday())).strftime("%Y-%m-%d")
    week_end   = (target_date + pd.Timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        raw = yf.download(ticker, start=week_start, end=week_end,
                          interval="1d", progress=False, auto_adjust=True)
        if raw.empty:
            return None
        return float(raw["Open"].iloc[0])
    except Exception:
        return None


def _get_master_tickers_for_date(date: pd.Timestamp) -> set[str] | None:
    """Load the appropriate monthly master list for a given date."""
    from pathlib import Path
    master_dir = Path("master_lists")
    year, month = date.year, date.month

    # Try current month, then walk backward up to 6 months
    for m_offset in range(7):
        m = month - m_offset
        y = year
        while m <= 0:
            m += 12
            y -= 1
        path = master_dir / f"master_list_{y:04d}_{m:02d}.csv"
        if path.exists():
            df = pd.read_csv(path)
            return set(df["Ticker"].tolist())

    return None  # No master list found — no filter applied


def run_backtest(
    tickers: list[str],
    initial_capital: float = 1_000_000.0,
    start: str = START_DATE,
) -> dict:
    """
    Run full weekly backtest.

    Returns dict: equity_curve, drawdown, trades, metrics
    """
    all_data = _load_all_weekly_data(tickers)
    if not all_data:
        raise RuntimeError("No data loaded.")

    # Build unified weekly date index from START_DATE onwards
    all_dates = sorted(set(
        d for df in all_data.values() for d in df.index
        if d >= pd.Timestamp(start)
    ))

    capital   = initial_capital
    positions = {}   # ticker → {shares, entry_price, entry_date}
    equity_curve = {}
    trades = []
    weeks_with_positions = 0

    for date in all_dates:
        master_set = _get_master_tickers_for_date(date)
        next_date  = date + pd.Timedelta(weeks=1)

        exit_list = []
        buy_candidates = []

        for ticker, df in all_data.items():
            if date not in df.index:
                continue

            in_master = (master_set is None) or (ticker in master_set)
            row = df.loc[date]

            # Force exit if dropped from master list
            if ticker in positions and not in_master:
                exit_list.append(ticker)
                continue

            if not in_master:
                continue

            if row.get("exit_signal", False) and ticker in positions:
                exit_list.append(ticker)
            if row.get("buy_signal", False) and ticker not in positions:
                rsi_val = float(row["RSI14"]) if not pd.isna(row["RSI14"]) else 0
                buy_candidates.append((ticker, rsi_val))

        # ── Process exits at next week open ──────────────────────────────
        for ticker in exit_list:
            pos   = positions.pop(ticker)
            open_ = _get_open_price(ticker, next_date)
            if open_ is None:
                open_ = float(all_data[ticker].loc[date, "Close"])

            proceeds = pos["shares"] * open_ * SELL_YIELD
            capital += proceeds

            hold_weeks = max(1, round((next_date - pos["entry_date"]).days / 7))
            gain_pct   = (open_ * SELL_YIELD - pos["entry_price"] * BUY_COST) / (pos["entry_price"] * BUY_COST) * 100

            trades.append({
                "Ticker":       ticker,
                "Entry_Date":   pos["entry_date"].strftime("%Y-%m-%d"),
                "Exit_Date":    next_date.strftime("%Y-%m-%d"),
                "Entry_Price":  round(pos["entry_price"], 2),
                "Exit_Price":   round(open_, 2),
                "Shares":       round(pos["shares"], 4),
                "Gain_pct":     round(gain_pct, 2),
                "Hold_Weeks":   hold_weeks,
            })

        # ── Process entries — rank by RSI, take top slots ─────────────────
        open_slots = MAX_POS - len(positions)
        if buy_candidates and open_slots > 0:
            buy_candidates.sort(key=lambda x: x[1], reverse=True)
            selected = [t for t, _ in buy_candidates[:open_slots]]
            alloc    = capital / max(open_slots, 1)

            for ticker in selected:
                open_ = _get_open_price(ticker, next_date)
                if open_ is None or open_ <= 0:
                    continue
                shares  = alloc / (open_ * BUY_COST)
                cost    = shares * open_ * BUY_COST
                capital -= cost
                positions[ticker] = {
                    "shares":      shares,
                    "entry_price": open_,
                    "entry_date":  next_date,
                }

        # ── Mark-to-market ─────────────────────────────────────────────────
        pos_value = 0.0
        for ticker, pos in positions.items():
            df = all_data[ticker]
            if date in df.index:
                pos_value += pos["shares"] * float(df.loc[date, "Close"])

        equity_curve[date] = capital + pos_value
        if positions:
            weeks_with_positions += 1

    # ── Performance metrics ───────────────────────────────────────────────────
    eq = pd.Series(equity_curve).sort_index()
    eq_ret = eq.pct_change().dropna()

    rolling_max = eq.cummax()
    dd = (eq - rolling_max) / rolling_max * 100

    n_years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr    = (eq.iloc[-1] / eq.iloc[0]) ** (1 / n_years) - 1 if n_years > 0 else 0

    rf_weekly   = 0.06 / 52
    weekly_ret  = eq_ret.mean()
    weekly_std  = eq_ret.std()
    sharpe      = ((weekly_ret - rf_weekly) / weekly_std * np.sqrt(52)) if weekly_std > 0 else 0

    trades_df  = pd.DataFrame(trades)
    win_rate   = (trades_df["Gain_pct"] > 0).mean() * 100 if not trades_df.empty else 0
    avg_hold   = trades_df["Hold_Weeks"].mean() if not trades_df.empty else 0
    exposure   = weeks_with_positions / len(all_dates) * 100 if all_dates else 0

    metrics = {
        "CAGR_%":             round(cagr * 100, 2),
        "Max_Drawdown_%":     round(dd.min(), 2),
        "Sharpe_Ratio":       round(sharpe, 2),
        "Win_Rate_%":         round(win_rate, 2),
        "Avg_Hold_Weeks":     round(avg_hold, 1),
        "Exposure_%":         round(exposure, 1),
        "Total_Trades":       len(trades_df),
        "Final_Capital_INR":  round(eq.iloc[-1], 2),
    }

    return {"equity_curve": eq, "drawdown": dd, "trades": trades_df, "metrics": metrics}


def plot_results(results: dict, out_dir: Path = Path(".")) -> Path:
    """Save equity + drawdown chart."""
    eq = results["equity_curve"]
    dd = results["drawdown"]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                              gridspec_kw={"height_ratios": [3, 1]})

    ax1 = axes[0]
    ax1.plot(eq.index, eq / 1e6, color="#27ae60", lw=2)
    ax1.set_ylabel("Portfolio (₹ Mn)")
    ax1.set_title("Weekly Structural Trend Reversal — Equity Curve", fontweight="bold")
    ax1.grid(alpha=0.3)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"₹{x:.1f}M"))

    ax2 = axes[1]
    ax2.fill_between(dd.index, dd, 0, color="#e74c3c", alpha=0.5)
    ax2.set_ylabel("Drawdown %")
    ax2.set_xlabel("Date")
    ax2.grid(alpha=0.3)

    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()

    out = out_dir / "weekly_backtest.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Chart saved → %s", out)
    return out


def save_results(results: dict, out_dir: Path = Path(".")):
    """Save trade log and metrics CSV."""
    if not results["trades"].empty:
        results["trades"].to_csv(out_dir / "weekly_trades.csv", index=False)
    metrics_df = pd.DataFrame(results["metrics"].items(), columns=["Metric", "Value"])
    metrics_df.to_csv(out_dir / "weekly_metrics.csv", index=False)
    results["equity_curve"].to_csv(out_dir / "weekly_equity.csv", header=["Value"])


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s",
                        datefmt="%H:%M:%S")

    # Try to load master list; fall back to test set
    try:
        import sys; sys.path.insert(0, ".")
        from master_list import get_latest_master_list
        master = get_latest_master_list()
        tickers = master["Ticker"].tolist() if master is not None else []
    except Exception:
        tickers = []

    if not tickers:
        logger.warning("No master list — using test set of 10 stocks")
        tickers = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
                   "WIPRO.NS", "HINDUNILVR.NS", "MARUTI.NS", "TITAN.NS", "BAJFINANCE.NS"]

    print(f"\n🚀  Running weekly backtest on {len(tickers)} tickers from {START_DATE}...\n")
    results = run_backtest(tickers)

    print("\n📊 Metrics:")
    for k, v in results["metrics"].items():
        print(f"   {k:25s}: {v}")

    save_results(results)
    chart = plot_results(results)
    print(f"\n📈 Chart: {chart}")
    if not results["trades"].empty:
        print(f"\n📋 Last 5 trades:\n{results['trades'].tail(5).to_string(index=False)}")
