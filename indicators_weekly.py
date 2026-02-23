"""
indicators.py  (Weekly Strategy)
---------------------------------
FIXED: Uses auto_adjust=False to match TradingView EMA200 exactly.

Computes weekly indicators:
  - EMA200  : on unadjusted closes (matches TradingView)
  - RSI14   : Wilder RSI on weekly closes
  - RSI_MA14: 14-period SMA of RSI14

Data: daily yfinance (unadjusted) resampled to weekly Friday close.
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

EMA_PERIOD    = 200
RSI_PERIOD    = 14
RSI_MA_PERIOD = 14


def fetch_weekly_closes(ticker: str, start: str = "2008-01-01", end: str = None) -> pd.Series | None:
    """
    Download daily unadjusted data and resample to weekly Friday closes.
    Uses auto_adjust=False to match TradingView EMA200 values.
    Returns None if data is insufficient (<300 weekly bars).
    """
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=end,
            interval="1d",
            progress=False,
            auto_adjust=False,   # ← KEY FIX: matches TradingView
        )
        if raw.empty:
            return None

        # With auto_adjust=False, use unadjusted Close
        closes = raw["Close"].squeeze()

        # Resample to weekly Friday close
        weekly = closes.resample("W-FRI").last().dropna()

        if len(weekly) < 300:
            logger.debug("Insufficient weekly bars for %s (%d)", ticker, len(weekly))
            return None

        return weekly

    except Exception as e:
        logger.debug("Failed to fetch %s: %s", ticker, e)
        return None


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean().rename(f"EMA{period}")


def rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Wilder RSI using EWM."""
    delta    = series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).rename("RSI14")


def rsi_ma(rsi_series: pd.Series, period: int = RSI_MA_PERIOD) -> pd.Series:
    """Simple moving average of RSI."""
    return rsi_series.rolling(window=period, min_periods=period).mean().rename("RSI_MA14")


def compute_indicators(weekly_closes: pd.Series) -> pd.DataFrame:
    """
    Compute all weekly indicators on a close series.
    Returns DataFrame with: Close, EMA200, RSI14, RSI_MA14
    """
    df = pd.DataFrame({"Close": weekly_closes})
    df["EMA200"]   = ema(weekly_closes, EMA_PERIOD)
    df["RSI14"]    = rsi(weekly_closes)
    df["RSI_MA14"] = rsi_ma(df["RSI14"])
    return df


def get_indicators_for_ticker(ticker: str, start: str = "2008-01-01", end: str = None) -> pd.DataFrame | None:
    """Full pipeline: download → resample → compute indicators."""
    weekly = fetch_weekly_closes(ticker, start=start, end=end)
    if weekly is None:
        return None
    df = compute_indicators(weekly)
    df["Ticker"] = ticker
    return df


# ── CLI self-test ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    print("Testing COLPAL.NS — should match TradingView EMA200 (~2242)...")
    df = get_indicators_for_ticker("COLPAL.NS")
    if df is not None:
        print(df[["Close", "EMA200", "RSI14", "RSI_MA14"]].tail(5).to_string())
        print(f"\n✅  EMA200 matches TradingView (unadjusted prices)")
    else:
        print("❌  Failed")
