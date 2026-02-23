"""
email_report.py
----------------
Sends a formatted HTML email with Buy/Sell/Hold signals.
Uses Gmail SMTP with App Password (no OAuth needed).

Environment variables required (set as GitHub Secrets):
  GMAIL_USER      — your Gmail address (e.g. yourname@gmail.com)
  GMAIL_PASS      — Gmail App Password (16-char, not your login password)
  RECIPIENT       — email to send report to
  REPORT_TYPE     — 'weekly' or 'monthly'
"""

import os
import sys
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ── Skip if flagged by month_end_check.py ─────────────────────────────────────
if Path("skip_email.flag").exists():
    logger.info("Skip flag found — not a month-end Friday. No email sent.")
    Path("skip_email.flag").unlink()
    sys.exit(0)

# ── Config ────────────────────────────────────────────────────────────────────
GMAIL_USER   = os.environ.get("GMAIL_USER", "")
GMAIL_PASS   = os.environ.get("GMAIL_PASS", "")
RECIPIENT    = os.environ.get("RECIPIENT", GMAIL_USER)
REPORT_TYPE  = os.environ.get("REPORT_TYPE", "weekly")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL",
                "https://your-app.streamlit.app")  # set after Streamlit deploy

STREAMLIT_URL = os.environ.get("STREAMLIT_URL", DASHBOARD_URL)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_latest_signal(kind: str, prefix: str) -> pd.DataFrame:
    """Load the most recent signal CSV."""
    files = sorted(Path("signals").glob(f"{prefix}_{kind}_*.csv"))
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[-1])


def _df_to_html_table(df: pd.DataFrame, color: str = "#ffffff") -> str:
    """Convert a DataFrame to a styled HTML table."""
    if df.empty:
        return "<p style='color:#888'>None</p>"

    rows = ""
    for _, row in df.iterrows():
        cells = "".join(f"<td style='padding:6px 12px;border-bottom:1px solid #eee'>{v}</td>"
                        for v in row.values)
        rows += f"<tr>{cells}</tr>"

    headers = "".join(
        f"<th style='padding:8px 12px;background:{color};color:white;text-align:left'>{c}</th>"
        for c in df.columns
    )

    return f"""
    <table style='border-collapse:collapse;width:100%;font-size:13px;font-family:monospace'>
      <thead><tr>{headers}</tr></thead>
      <tbody>{rows}</tbody>
    </table>"""


def _build_html(report_type: str, buy: pd.DataFrame, sell: pd.DataFrame,
                hold: pd.DataFrame, date_str: str) -> str:
    """Build the full HTML email body."""

    label  = "Weekly" if report_type == "weekly" else "Monthly"
    prefix = "weekly" if report_type == "weekly" else "monthly"

    buy_cols  = ["Ticker", "Close", "EMA200", "RSI14", "RSI_MA14"] if report_type == "weekly" \
                else ["Ticker", "Close", "SSF50", "SSF200", "RSI14"]
    sell_cols = ["Ticker", "Close", "RSI14", "RSI_MA14"]
    hold_cols = ["Ticker", "Close", "RSI14"]

    def _trim(df, cols):
        available = [c for c in cols if c in df.columns]
        return df[available].head(20) if not df.empty else df

    buy_table  = _df_to_html_table(_trim(buy, buy_cols),   color="#27ae60")
    sell_table = _df_to_html_table(_trim(sell, sell_cols), color="#e74c3c")
    hold_table = _df_to_html_table(_trim(hold, hold_cols), color="#7f8c8d")

    return f"""
    <html><body style='font-family:Arial,sans-serif;max-width:800px;margin:auto;color:#2c3e50'>

    <div style='background:#2c3e50;padding:24px;border-radius:8px 8px 0 0'>
      <h1 style='color:white;margin:0'>📊 {label} Signal Report</h1>
      <p style='color:#bdc3c7;margin:4px 0'>{date_str} | Nifty 500 | Indian Markets</p>
    </div>

    <div style='background:#f8f9fa;padding:16px;border-left:4px solid #3498db'>
      <p style='margin:0'>
        🔗 <strong>Live Dashboard:</strong>
        <a href='{STREAMLIT_URL}'>{STREAMLIT_URL}</a>
      </p>
      <p style='margin:4px 0;font-size:12px;color:#888'>
        ⚠️ Execution: Enter/exit at <strong>next {label.lower()[:-2]} open</strong>.
        This is not financial advice.
      </p>
    </div>

    <!-- BUY -->
    <div style='padding:20px 0'>
      <h2 style='color:#27ae60'>🟢 BUY Signals ({len(buy)} stocks)</h2>
      <p style='color:#555;font-size:13px'>
        Enter at <strong>next {label.lower()[:-2]} open</strong>.
        Ranked by RSI14 (highest momentum first).
      </p>
      {buy_table}
    </div>

    <!-- SELL -->
    <div style='padding:20px 0;border-top:1px solid #eee'>
      <h2 style='color:#e74c3c'>🔴 SELL Signals ({len(sell)} stocks)</h2>
      <p style='color:#555;font-size:13px'>
        Exit at <strong>next {label.lower()[:-2]} open</strong>.
      </p>
      {sell_table}
    </div>

    <!-- HOLD -->
    <div style='padding:20px 0;border-top:1px solid #eee'>
      <h2 style='color:#7f8c8d'>⚪ HOLD ({len(hold)} stocks)</h2>
      <p style='color:#555;font-size:13px'>No action required this {label.lower()[:-2]}.</p>
      {hold_table if len(hold) <= 30 else
       f"<p style='color:#888'>{len(hold)} stocks on hold — see dashboard for full list.</p>"}
    </div>

    <!-- FOOTER -->
    <div style='background:#ecf0f1;padding:16px;border-radius:0 0 8px 8px;
                font-size:11px;color:#888;border-top:1px solid #ddd'>
      <p style='margin:0'>Generated automatically by your Nifty 500 Quant System.</p>
      <p style='margin:4px 0'>Data: yfinance (free) | Universe: Nifty 500 | No paid APIs</p>
      <p style='margin:0'>This report is for informational purposes only. Not financial advice.</p>
    </div>

    </body></html>
    """


def send_email(subject: str, html_body: str):
    """Send HTML email via Gmail SMTP."""
    if not GMAIL_USER or not GMAIL_PASS:
        logger.error("GMAIL_USER or GMAIL_PASS not set. Check GitHub Secrets.")
        sys.exit(1)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, RECIPIENT, msg.as_string())

    logger.info("Email sent to %s", RECIPIENT)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    prefix   = "weekly" if REPORT_TYPE == "weekly" else "monthly"
    date_str = datetime.today().strftime("%d %B %Y")

    buy  = _load_latest_signal("buy",  prefix)
    sell = _load_latest_signal("sell", prefix)
    hold = _load_latest_signal("hold", prefix)

    label   = "Weekly" if REPORT_TYPE == "weekly" else "Monthly"
    subject = (f"📊 {label} Signals — {date_str} | "
               f"BUY: {len(buy)} | SELL: {len(sell)} | HOLD: {len(hold)}")

    html = _build_html(REPORT_TYPE, buy, sell, hold, date_str)
    send_email(subject, html)
