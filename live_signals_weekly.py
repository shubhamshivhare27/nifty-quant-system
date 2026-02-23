"""
live_signals.py  (Weekly Strategy)
------------------------------------
Scans master list tickers for current week's Buy / Sell / Hold signals.
Output: signals/weekly_buy_YYYY_MM_DD.csv etc.
"""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from master_list import get_latest_master_list
from strategy_weekly import scan_universe, rank_buy_signals

logger = logging.getLogger(__name__)
OUTPUT_DIR = Path("signals")


def run_live_signals(max_positions: int = 10, save: bool = True) -> dict[str, pd.DataFrame]:
    master = get_latest_master_list()
    if master is None or master.empty:
        raise RuntimeError("No master list found. Run master_list.py first.")

    tickers = master["Ticker"].tolist()
    logger.info("Scanning %d tickers for weekly signals...", len(tickers))

    all_signals = scan_universe(tickers)
    if all_signals.empty:
        logger.warning("No signals returned.")
        return {"buy": pd.DataFrame(), "sell": pd.DataFrame(), "hold": pd.DataFrame()}

    buy_df  = rank_buy_signals(all_signals, max_positions)
    sell_df = all_signals[all_signals["Signal"] == "SELL"].reset_index(drop=True)
    hold_df = all_signals[all_signals["Signal"] == "HOLD"].reset_index(drop=True)

    result = {"buy": buy_df, "sell": sell_df, "hold": hold_df}

    if save:
        OUTPUT_DIR.mkdir(exist_ok=True)
        stamp = datetime.today().strftime("%Y_%m_%d")
        for name, df in result.items():
            path = OUTPUT_DIR / f"weekly_{name}_{stamp}.csv"
            df.to_csv(path, index=False)
            logger.info("Saved %s → %s", name.upper(), path)

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s",
                        datefmt="%H:%M:%S")
    print("\n🔍  Running weekly live signal engine...\n")
    signals = run_live_signals()

    print(f"\n🟢  BUY  ({len(signals['buy'])} stocks):")
    print(signals["buy"][["Ticker","Close","RSI14","EMA200"]].to_string(index=False) if not signals["buy"].empty else "  None")

    print(f"\n🔴  SELL ({len(signals['sell'])} stocks):")
    print(signals["sell"][["Ticker","Close","RSI14"]].to_string(index=False) if not signals["sell"].empty else "  None")

    print(f"\n⚪  HOLD ({len(signals['hold'])} stocks)")
    print("\n✅  Done.")
