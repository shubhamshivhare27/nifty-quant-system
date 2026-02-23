"""
strategy.py  (Monthly Strategy) — FINAL
-----------------------------------------
ENTRY (ALL required):
  Phase 1 — Deep Correction (within last 12 months):
      Close < SSF200 AND Close < SSF250

  Phase 2 — Structural Recovery (current month):
      Close > SSF50 AND SSF50 > SSF200

  Phase 3 — Momentum Confirmation:
      Previous month: RSI14 < RSI_MA14
      Current month:  RSI14 > RSI_MA14
      AND both RSI14 > 0 AND RSI_MA14 > 0

EXIT (ANY):
  1. RSI14 crosses BELOW RSI_MA14
  2. Close < SSF200

Execution: next month open.
"""

import logging
import pandas as pd
import numpy as np
from indicators_monthly import compute_indicators, fetch_monthly_closes

logger = logging.getLogger(__name__)
DEEP_CORRECTION_LOOKBACK = 12


def _rsi_cross_above(prev, curr) -> bool:
    """
    RSI14 crossed above RSI_MA14.
    Previous: RSI14 < RSI_MA14
    Current:  RSI14 > RSI_MA14
    Both RSI14 > 0 AND RSI_MA14 > 0
    """
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


def _had_deep_correction(df: pd.DataFrame, current_i: int) -> bool:
    """Check if within last 12 months there was Close < SSF200 AND Close < SSF250."""
    start  = max(0, current_i - DEEP_CORRECTION_LOOKBACK)
    window = df.iloc[start:current_i]
    if window.empty:
        return False
    mask = (window["Close"] < window["SSF200"]) & (window["Close"] < window["SSF250"])
    return mask.any()


def _structural_recovery(row) -> bool:
    """Phase 2: Close > SSF50 AND SSF50 > SSF200."""
    return (
        row["Close"] > row["SSF50"]  and
        row["SSF50"] > row["SSF200"] and
        not pd.isna(row["SSF50"])    and
        not pd.isna(row["SSF200"])
    )


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)
    buy_sig  = [False] * n
    exit_sig = [False] * n

    required = ["Close", "SSF50", "SSF200", "SSF250", "RSI14", "RSI_MA14"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    for i in range(2, n):
        curr = df.iloc[i]
        prev = df.iloc[i - 1]

        if any(pd.isna(curr[c]) for c in required):
            continue

        # ── ENTRY ─────────────────────────────────────────────────────────
        phase1 = _had_deep_correction(df, i)          # deep correction in past 12M
        phase2 = _structural_recovery(curr)            # structural recovery this month
        phase3 = _rsi_cross_above(prev, curr)          # RSI crossover with both > 0

        if phase1 and phase2 and phase3:
            buy_sig[i] = True

        # ── EXIT ──────────────────────────────────────────────────────────
        rsi_exit   = _rsi_cross_below(prev, curr)
        price_exit = curr["Close"] < curr["SSF200"]

        if rsi_exit or price_exit:
            exit_sig[i] = True

    df["buy_signal"]  = buy_sig
    df["exit_signal"] = exit_sig
    return df


def scan_universe(master_tickers, start="2008-01-01", end=None):
    results = []
    for ticker in master_tickers:
        monthly = fetch_monthly_closes(ticker, start=start, end=end)
        if monthly is None:
            continue
        ind_df = compute_indicators(monthly)
        sig_df = generate_signals(ind_df)
        last   = sig_df.iloc[-1]

        def _safe(val):
            return round(float(val), 2) if not pd.isna(val) else None

        results.append({
            "Ticker":     ticker,
            "Date":       sig_df.index[-1].strftime("%Y-%m"),
            "Close":      _safe(last["Close"]),
            "SSF50":      _safe(last["SSF50"]),
            "SSF200":     _safe(last["SSF200"]),
            "SSF250":     _safe(last["SSF250"]),
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
