"""
portfolio.py  (Weekly Strategy)
---------------------------------
Tracks open positions, computes live P&L, and calculates XIRR.
"""

import math
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

POSITIONS_FILE = Path("weekly_positions.csv")


def load_positions() -> pd.DataFrame:
    if POSITIONS_FILE.exists():
        return pd.read_csv(POSITIONS_FILE)
    return pd.DataFrame(columns=["Ticker", "Shares", "Entry_Price", "Entry_Date", "Notes"])


def save_positions(df: pd.DataFrame):
    df.to_csv(POSITIONS_FILE, index=False)


def add_position(ticker: str, shares: float, entry_price: float,
                 entry_date: str, notes: str = "") -> pd.DataFrame:
    df = load_positions()
    new = pd.DataFrame([{"Ticker": ticker, "Shares": shares,
                          "Entry_Price": entry_price, "Entry_Date": entry_date, "Notes": notes}])
    df = pd.concat([df, new], ignore_index=True)
    save_positions(df)
    return df


def remove_position(ticker: str) -> pd.DataFrame:
    df = load_positions()
    df = df[df["Ticker"] != ticker].reset_index(drop=True)
    save_positions(df)
    return df


def get_current_prices(tickers: list[str]) -> dict[str, float]:
    prices = {}
    for t in tickers:
        try:
            data = yf.download(t, period="2d", interval="1d", progress=False, auto_adjust=True)
            if not data.empty:
                prices[t] = float(data["Close"].iloc[-1])
        except Exception:
            pass
    return prices


def enrich_positions(df: pd.DataFrame) -> pd.DataFrame:
    """Add current price, P&L columns."""
    if df.empty:
        return df
    prices = get_current_prices(df["Ticker"].tolist())
    df = df.copy()
    df["Current_Price"] = df["Ticker"].map(prices)
    df["PnL_pct"] = ((df["Current_Price"] - df["Entry_Price"]) / df["Entry_Price"] * 100).round(2)
    df["PnL_INR"] = ((df["Current_Price"] - df["Entry_Price"]) * df["Shares"]).round(2)
    return df


def xirr(cashflows: list[tuple[date, float]], guess: float = 0.1) -> float | None:
    """Newton-Raphson XIRR. cashflows: list of (date, amount)."""
    if len(cashflows) < 2:
        return None
    dates   = [c[0] for c in cashflows]
    amounts = [c[1] for c in cashflows]
    t0      = dates[0]
    years   = [(d - t0).days / 365.25 for d in dates]

    def npv(r):
        return sum(a / (1 + r) ** y for a, y in zip(amounts, years))
    def dnpv(r):
        return sum(-y * a / (1 + r) ** (y + 1) for a, y in zip(amounts, years))

    r = guess
    for _ in range(200):
        n = npv(r)
        if abs(n) < 1e-7:
            break
        d = dnpv(r)
        if d == 0:
            break
        r -= n / d
        if r <= -1:
            r = -0.999
    return round(r * 100, 2) if not math.isnan(r) else None
