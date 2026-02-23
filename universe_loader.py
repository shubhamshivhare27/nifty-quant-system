"""
universe_loader.py
------------------
Loads Nifty 500 universe from local CSV and formats tickers for yfinance.

Expected CSV columns (NSE official format):
    'Symbol' — e.g. RELIANCE  →  RELIANCE.NS
"""

import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

UNIVERSE_FILE = Path("nifty500_universe.csv")
NS_SUFFIX = ".NS"


def load_universe(filepath: Path = UNIVERSE_FILE) -> list[str]:
    """
    Load Nifty 500 tickers from local CSV.

    Returns
    -------
    list[str]
        yfinance-formatted tickers, e.g. ['RELIANCE.NS', 'TCS.NS', ...]

    Raises
    ------
    FileNotFoundError
        If the universe CSV is missing.
    ValueError
        If the CSV has no recognisable Symbol column.
    """
    if not filepath.exists():
        raise FileNotFoundError(
            f"Universe file not found: {filepath}\n"
            "Download from: https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500\n"
            "Save as 'nifty500_universe.csv' in the project root."
        )

    df = pd.read_csv(filepath)

    # Normalise column names — NSE CSVs can vary slightly
    df.columns = df.columns.str.strip().str.title()

    symbol_col = None
    for candidate in ["Symbol", "Ticker", "Scrip Code", "Nse Symbol"]:
        if candidate in df.columns:
            symbol_col = candidate
            break

    if symbol_col is None:
        raise ValueError(
            f"Could not find a Symbol column in {filepath}. "
            f"Available columns: {list(df.columns)}"
        )

    raw_symbols = df[symbol_col].dropna().str.strip().str.upper().tolist()

    # Append .NS suffix (skip if already present)
    tickers = [
        s if s.endswith(NS_SUFFIX) else f"{s}{NS_SUFFIX}"
        for s in raw_symbols
        if s  # drop blanks
    ]

    logger.info("Universe loaded: %d tickers from %s", len(tickers), filepath)
    return tickers


def load_universe_symbols(filepath: Path = UNIVERSE_FILE) -> list[str]:
    """
    Return bare NSE symbols (without .NS) — useful for display / lookups.
    """
    return [t.replace(NS_SUFFIX, "") for t in load_universe(filepath)]


# ---------------------------------------------------------------------------
# CLI helper — run directly to verify your CSV
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    tickers = load_universe()
    print(f"\n✅  Loaded {len(tickers)} tickers")
    print("First 10:", tickers[:10])
    print("Last  10:", tickers[-10:])
