"""
ssf.py
------
Ehlers 2-Pole Super Smoother Filter (SSF).

Formula (exact from spec):
    a1 = exp(-1.414 * pi / period)
    b1 = 2 * a1 * cos(1.414 * pi / period)
    c2 = b1
    c3 = -a1^2
    c1 = 1 - c2 - c3

    SSF[i] = c1*(price[i] + price[i-1])/2 + c2*SSF[i-1] + c3*SSF[i-2]
"""

import math
import numpy as np
import pandas as pd


def _ssf_coefficients(period: int) -> tuple[float, float, float]:
    """Compute SSF filter coefficients for a given period."""
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -(a1 ** 2)
    c1 = 1.0 - c2 - c3
    return c1, c2, c3


def ssf(prices: pd.Series, period: int) -> pd.Series:
    """
    Compute the Ehlers Super Smoother Filter on a price series.

    Parameters
    ----------
    prices : pd.Series
        Price series (must be ordered oldest → newest, no NaNs ideal).
    period : int
        Filter period (e.g. 50, 200, 250).

    Returns
    -------
    pd.Series
        SSF values, same index as `prices`. First 2 values are NaN.
    """
    if len(prices) < 3:
        return pd.Series(np.nan, index=prices.index)

    c1, c2, c3 = _ssf_coefficients(period)
    price_arr = prices.to_numpy(dtype=float)
    n = len(price_arr)
    out = np.full(n, np.nan)

    # Seed first two values with the price itself (no filter yet)
    out[0] = price_arr[0]
    out[1] = price_arr[1]

    for i in range(2, n):
        mid = (price_arr[i] + price_arr[i - 1]) / 2.0
        out[i] = c1 * mid + c2 * out[i - 1] + c3 * out[i - 2]

    return pd.Series(out, index=prices.index, name=f"SSF{period}")


def ssf_batch(prices: pd.Series, periods: list[int]) -> pd.DataFrame:
    """
    Compute multiple SSF periods at once.

    Returns a DataFrame with columns SSF{period} for each period.
    """
    results = {f"SSF{p}": ssf(prices, p) for p in periods}
    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import yfinance as yf

    print("Downloading TCS.NS monthly data for SSF self-test...")
    raw = yf.download("TCS.NS", period="10y", interval="1mo", progress=False)
    closes = raw["Close"].squeeze().dropna()

    df = ssf_batch(closes, [50, 200, 250])
    df["Close"] = closes
    print(df.tail(10))
    print("\n✅  SSF module OK")
