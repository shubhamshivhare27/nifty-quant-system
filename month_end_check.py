"""
month_end_check.py
-------------------
Checks if today is the last Friday of the month.
If yes, runs master_list rebuild + monthly signal scan.
If no, exits silently (no email sent).

Called by GitHub Actions every Friday.
"""

import sys
import logging
from datetime import datetime, timedelta
import calendar

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def is_last_friday_of_month() -> bool:
    today = datetime.today()
    # Find the last day of the month
    last_day = calendar.monthrange(today.year, today.month)[1]
    last_date = datetime(today.year, today.month, last_day)

    # Walk back to find last Friday (weekday 4)
    while last_date.weekday() != 4:
        last_date -= timedelta(days=1)

    return today.date() == last_date.date()


if __name__ == "__main__":
    if not is_last_friday_of_month():
        logger.info("Not last Friday of month — skipping monthly run.")
        # Write a flag file so email_report.py knows to skip
        with open("skip_email.flag", "w") as f:
            f.write("skip")
        sys.exit(0)

    logger.info("✅ Last Friday of month — running monthly pipeline...")

    # 1. Rebuild master list
    from master_list import build_master_list
    df = build_master_list()
    logger.info("Master list built: %d stocks", len(df))

    # 2. Run monthly signals
    from live_signals_monthly import run_live_signals
    signals = run_live_signals()
    logger.info("Monthly signals complete — BUY: %d, SELL: %d, HOLD: %d",
                len(signals["buy"]), len(signals["sell"]), len(signals["hold"]))
