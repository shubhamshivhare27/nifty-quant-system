"""
strategy.py  (Weekly Strategy) — FINAL
----------------------------------------
ENTRY (ALL required):
  1. Previous week: Close < EMA200
  2. Current week:  Close > EMA200  (true crossover)
  3. Previous week: RSI14 < RSI_MA14
     Current week:  RSI14 > RSI_MA14
     AND both RSI14 > 0 AND RSI_MA14 > 0

EXIT:
  Previous week: RSI14 > RSI_MA14
  Current week:  RSI14 < RSI_MA14

Execution: next week open.
"""

import logging
import pandas as pd
import numpy as np
from indicators_weekly import compute_indicators, fetch_weekly_closes

logger = logging.getLogger(__name__)


def _rsi_cross_above(prev, curr) -> bool:
    """RSI14 crossed above RSI_MA14, with both values > 0."""
    return (
        prev["RSI14"]    < prev["RSI_MA14"] and  # prev: RSI below RSI_MA
        curr["RSI14"]    > curr["RSI_MA14"] and  # curr: RSI above RSI_MA
        curr["RSI14"]    > 0                and  # RSI14 must be positive
        curr["RSI_MA14"] > 0                     # RSI_MA14 must be positive
    )


def _rsi_cross_below(prev, curr) -> bool:
    """RSI14 crossed below RSI_MA14."""
    return (
        prev["RSI14"] > prev["RSI_MA14"] and
        curr["RSI14"] < curr["RSI_MA14"]
    )


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)
    buy_sig  = [False] * n
    exit_sig = [False] * n

    required = ["Close", "EMA200", "RSI14", "RSI_MA14"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    for i in range(1, n):
        curr = df.iloc[i]
        prev = df.iloc[i - 1]

        if any(pd.isna(curr[c]) for c in required) or any(pd.isna(prev[c]) for c in required):
            continue

        # ── ENTRY ─────────────────────────────────────────────────────────
        # Condition 1 & 2: EMA200 crossover
        ema_crossover = (
            prev["Close"] < prev["EMA200"] and   # prev below EMA200
            curr["Close"] > curr["EMA200"]        # curr above EMA200
        )
        # Condition 3: RSI cross above RSI_MA with both > 0
        rsi_crossover = _rsi_cross_above(prev, curr)

        if ema_crossover and rsi_crossover:
            buy_sig[i] = True

        # ── EXIT ──────────────────────────────────────────────────────────
        if _rsi_cross_below(prev, curr):
            exit_sig[i] = True

    df["buy_signal"]  = buy_sig
    df["exit_signal"] = exit_sig
    return df


def scan_universe(master_tickers, start="2008-01-01", end=None):
    results = []
    for ticker in master_tickers:
        weekly = fetch_weekly_closes(ticker, start=start, end=end)
        if weekly is None:
            continue
        ind_df = compute_indicators(weekly)
        sig_df = generate_signals(ind_df)
        last   = sig_df.iloc[-1]

        def _safe(val):
            return round(float(val), 2) if not pd.isna(val) else None

        results.append({
            "Ticker":     ticker,
            "Date":       sig_df.index[-1].strftime("%Y-%m-%d"),
            "Close":      _safe(last["Close"]),
            "EMA200":     _safe(last["EMA200"]),
            "RSI14":      _safe(last["RSI14"]),
            "RSI_MA14":   _safe(last["RSI_MA14"]),
            "buy_signal": bool(last["buy_signal"]),
            "exit_signal":bool(last["exit_signal"]),
        })

    df = pd.DataFrame(results)
    if df.empty:
        return df

    df["Signal"] = df.apply(
        lambda r: "BUY" if r["buy_signal"] else ("SELL" if r["exit_signal"] else "HOLD"),
        axis=1
    )
    return df


def rank_buy_signals(signals_df, max_positions=10):
    buys = signals_df[signals_df["Signal"] == "BUY"].copy()
    if buys.empty:
        return buys
    return buys.sort_values("RSI14", ascending=False).head(max_positions).reset_index(drop=True)
