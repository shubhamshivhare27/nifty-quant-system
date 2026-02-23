"""
live_signals.py
---------------
Live signal engine — generates Buy / Sell / Hold lists from latest data.

Output: signals_YYYY_MM.csv
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from master_list import get_latest_master_list
from strategy_monthly import scan_universe, rank_buy_signals

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("signals")


def run_live_signals(
    max_positions: int = 10,
    save: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    1. Load latest master list.
    2. Scan all qualifying tickers for current signals.
    3. Split into BUY / SELL / HOLD DataFrames.
    4. Rank BUY list by RSI14, limit to max_positions.
    5. Optionally save to CSV.

    Returns
    -------
    dict with keys: 'buy', 'sell', 'hold', 'all'
    """
    master = get_latest_master_list()
    if master is None or master.empty:
        raise RuntimeError(
            "No master list found. Run master_list.py first to build the fundamental filter."
        )

    tickers = master["Ticker"].tolist()
    logger.info("Scanning %d tickers from master list...", len(tickers))

    all_signals = scan_universe(tickers)

    if all_signals.empty:
        logger.warning("No signal data returned — check data availability.")
        return {"buy": pd.DataFrame(), "sell": pd.DataFrame(), "hold": pd.DataFrame(), "all": pd.DataFrame()}

    buy_df  = rank_buy_signals(all_signals, max_positions=max_positions)
    sell_df = all_signals[all_signals["Signal"] == "SELL"].reset_index(drop=True)
    hold_df = all_signals[all_signals["Signal"] == "HOLD"].reset_index(drop=True)

    result = {"buy": buy_df, "sell": sell_df, "hold": hold_df, "all": all_signals}

    if save:
        OUTPUT_DIR.mkdir(exist_ok=True)
        stamp = datetime.today().strftime("%Y_%m")
        for name, df in result.items():
            if name == "all":
                continue
            path = OUTPUT_DIR / f"signals_{name}_{stamp}.csv"
            df.to_csv(path, index=False)
            logger.info("Saved %s → %s", name.upper(), path)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    print("\n🔍  Running live signal engine...\n")
    signals = run_live_signals()

    print(f"\n🟢  BUY  ({len(signals['buy'])} stocks):")
    if not signals["buy"].empty:
        print(signals["buy"][["Ticker", "Close", "RSI14", "Signal"]].to_string(index=False))
    else:
        print("   None")

    print(f"\n🔴  SELL ({len(signals['sell'])} stocks):")
    if not signals["sell"].empty:
        print(signals["sell"][["Ticker", "Close", "RSI14", "Signal"]].to_string(index=False))
    else:
        print("   None")

    print(f"\n⚪  HOLD ({len(signals['hold'])} stocks)")
    print("\n✅  Signal engine complete.")
