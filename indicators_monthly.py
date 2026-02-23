"""
indicators.py
-------------
All technical indicators used by the strategy — computed on MONTHLY data.

Indicators:
  - SSF50, SSF200, SSF250  (Ehlers Super Smoother Filter)
  - RSI14
  - RSI_MA14 (14-period SMA of RSI14)
"""

import numpy as np
import pandas as pd
import yfinance as yf
import logging

from ssf import ssf_batch

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
SSF_PERIODS = [50, 200, 250]
RSI_PERIOD = 14
RSI_MA_PERIOD = 14


# ── RSI ──────────────────────────────────────────────────────────────────────

def rsi(prices: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """
    Wilder's RSI.

    Parameters
    ----------
    prices : pd.Series   (monthly close, oldest → newest)
    period : int

    Returns
    -------
    pd.Series  — RSI values in [0, 100], NaN for first `period` bars.
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # First average using simple mean
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Wilder smoothing for subsequent values
    for i in range(period, len(prices)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_vals = 100 - (100 / (1 + rs))
    return rsi_vals.rename("RSI14")


def rsi_ma(rsi_series: pd.Series, period: int = RSI_MA_PERIOD) -> pd.Series:
    """Simple moving average of RSI."""
    return rsi_series.rolling(window=period, min_periods=period).mean().rename("RSI_MA14")


# ── Monthly price fetch ───────────────────────────────────────────────────────

def fetch_monthly_closes(
    ticker: str,
    start: str = "2008-01-01",   # extra history for indicator warm-up
    end: str | None = None,
) -> pd.Series | None:
    """
    Download daily data for `ticker` and resample to monthly closes.

    Returns None if download fails or has < 60 bars.
    """
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=end,
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        if raw.empty:
            logger.warning("No data for %s", ticker)
            return None

        closes = raw["Close"].squeeze()
        monthly = closes.resample("ME").last().dropna()

        if len(monthly) < 60:
            logger.warning("Insufficient monthly bars for %s (%d)", ticker, len(monthly))
            return None

        return monthly

    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", ticker, exc)
        return None


# ── Full indicator DataFrame ──────────────────────────────────────────────────

def compute_indicators(monthly_closes: pd.Series) -> pd.DataFrame:
    """
    Given a monthly close series, compute all strategy indicators.

    Returns
    -------
    pd.DataFrame with columns:
        Close, SSF50, SSF200, SSF250, RSI14, RSI_MA14
    """
    df = pd.DataFrame({"Close": monthly_closes})

    # SSF filters
    ssf_df = ssf_batch(monthly_closes, SSF_PERIODS)
    df = pd.concat([df, ssf_df], axis=1)

    # RSI + RSI_MA
    df["RSI14"] = rsi(monthly_closes)
    df["RSI_MA14"] = rsi_ma(df["RSI14"])

    return df


def get_indicators_for_ticker(
    ticker: str,
    start: str = "2008-01-01",
    end: str | None = None,
) -> pd.DataFrame | None:
    """
    Full pipeline: download → resample → compute indicators.

    Returns None if data is unavailable or insufficient.
    """
    monthly = fetch_monthly_closes(ticker, start=start, end=end)
    if monthly is None:
        return None

    df = compute_indicators(monthly)
    df["Ticker"] = ticker
    return df


# ---------------------------------------------------------------------------
# CLI self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    print("Computing indicators for RELIANCE.NS...")
    df = get_indicators_for_ticker("RELIANCE.NS")
    if df is not None:
        print(df[["Close", "SSF50", "SSF200", "SSF250", "RSI14", "RSI_MA14"]].tail(12))
        print(f"\n✅  Indicators OK — {len(df)} monthly bars")
    else:
        print("❌  Failed to compute indicators")
