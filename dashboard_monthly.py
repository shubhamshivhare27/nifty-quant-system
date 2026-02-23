"""
dashboard.py
------------
Streamlit dashboard for the Monthly Structural Reversal System.

Run with:
    streamlit run dashboard.py
"""

import math
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty 500 Quant System",
    page_icon="📈",
    layout="wide",
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_signals(signal_type: str) -> pd.DataFrame:
    """Load latest signal CSV for buy/sell/hold."""
    signal_dir = Path("signals")
    files = sorted(signal_dir.glob(f"signals_{signal_type}_*.csv"))
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[-1])


def _load_positions() -> pd.DataFrame:
    pos_file = Path("positions.csv")
    if pos_file.exists():
        return pd.read_csv(pos_file)
    return pd.DataFrame(columns=["Ticker", "Shares", "Entry_Price", "Entry_Date", "Notes"])


def _save_positions(df: pd.DataFrame):
    df.to_csv("positions.csv", index=False)


def _xirr(cashflows: list[tuple[date, float]], guess: float = 0.1) -> float | None:
    """
    Compute XIRR via Newton-Raphson.
    cashflows: list of (date, amount) — negative = outflow, positive = inflow.
    """
    if len(cashflows) < 2:
        return None

    dates = [c[0] for c in cashflows]
    amounts = [c[1] for c in cashflows]
    t0 = dates[0]
    years = [(d - t0).days / 365.25 for d in dates]

    def _npv(rate):
        return sum(a / (1 + rate) ** y for a, y in zip(amounts, years))

    def _dnpv(rate):
        return sum(-y * a / (1 + rate) ** (y + 1) for a, y in zip(amounts, years))

    rate = guess
    for _ in range(200):
        npv = _npv(rate)
        if abs(npv) < 1e-6:
            break
        dnpv = _dnpv(rate)
        if dnpv == 0:
            break
        rate -= npv / dnpv
        if rate <= -1:
            rate = -0.999

    return round(rate * 100, 2) if not math.isnan(rate) else None


def _portfolio_cagr(equity_csv: Path | None) -> tuple[float, pd.DataFrame] | None:
    if equity_csv is None or not equity_csv.exists():
        return None
    eq = pd.read_csv(equity_csv, index_col=0, parse_dates=True).squeeze()
    n  = (eq.index[-1] - eq.index[0]).days / 365.25
    if n <= 0:
        return None
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / n) - 1
    return round(cagr * 100, 2), eq


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/combo-chart.png", width=60)
    st.title("⚙️ Controls")

    if st.button("🔄 Refresh Signals", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("Data: yfinance (free) · Universe: Nifty 500")
    st.caption(f"Last refresh: {datetime.now().strftime('%d %b %Y %H:%M')}")


# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 Nifty 500 Monthly Structural Reversal System")
st.markdown("*Long-term quant system — monthly signals, SSF-based trend + RSI momentum*")
st.divider()


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_signals, tab_positions, tab_xirr, tab_backtest = st.tabs(
    ["📡 Live Signals", "📂 Open Positions", "💰 IRR / XIRR", "📊 Backtest"]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — LIVE SIGNALS
# ══════════════════════════════════════════════════════════════════════════════
with tab_signals:
    col1, col2 = st.columns(2)

    # BUY
    with col1:
        st.subheader("🟢 BUY Signals")
        buy_df = _load_signals("buy")
        if buy_df.empty:
            st.info("No BUY signals — run live_signals.py first.")
        else:
            st.dataframe(
                buy_df[["Ticker", "Close", "RSI14", "SSF50", "SSF200"]].style.format({
                    "Close": "₹{:.2f}", "RSI14": "{:.1f}", "SSF50": "₹{:.2f}", "SSF200": "₹{:.2f}"
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.success(f"**{len(buy_df)} BUY signals** — Execute at next month open")

    # SELL
    with col2:
        st.subheader("🔴 SELL Signals")
        sell_df = _load_signals("sell")
        if sell_df.empty:
            st.info("No SELL signals currently.")
        else:
            st.dataframe(
                sell_df[["Ticker", "Close", "RSI14", "SSF200"]].style.format({
                    "Close": "₹{:.2f}", "RSI14": "{:.1f}", "SSF200": "₹{:.2f}"
                }),
                use_container_width=True,
                hide_index=True,
            )
            st.error(f"**{len(sell_df)} SELL signals** — Execute at next month open")

    st.divider()
    st.subheader("⚪ HOLD List")
    hold_df = _load_signals("hold")
    if hold_df.empty:
        st.info("No HOLD data.")
    else:
        st.dataframe(
            hold_df[["Ticker", "Close", "RSI14", "SSF50", "SSF200", "SSF250"]],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"{len(hold_df)} stocks on HOLD")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — OPEN POSITIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_positions:
    st.subheader("📂 Open Positions")

    positions = _load_positions()

    if not positions.empty:
        # Try to fetch current prices
        tickers = positions["Ticker"].tolist()
        try:
            import yfinance as yf
            prices = {}
            for t in tickers:
                data = yf.download(t, period="2d", interval="1d", progress=False, auto_adjust=True)
                if not data.empty:
                    prices[t] = float(data["Close"].iloc[-1])
        except Exception:
            prices = {}

        positions["Current_Price"] = positions["Ticker"].map(prices)
        positions["P&L_%"] = (
            (positions["Current_Price"] - positions["Entry_Price"]) / positions["Entry_Price"] * 100
        ).round(2)
        positions["P&L_₹"] = (
            (positions["Current_Price"] - positions["Entry_Price"]) * positions["Shares"]
        ).round(2)

        st.dataframe(
            positions.style.format({
                "Entry_Price": "₹{:.2f}",
                "Current_Price": "₹{:.2f}",
                "P&L_%": "{:+.2f}%",
                "P&L_₹": "₹{:,.0f}",
            }).applymap(
                lambda x: "color: green" if isinstance(x, (int, float)) and x > 0
                          else ("color: red" if isinstance(x, (int, float)) and x < 0 else ""),
                subset=["P&L_%", "P&L_₹"],
            ),
            use_container_width=True,
            hide_index=True,
        )

        total_pl = positions["P&L_₹"].sum()
        st.metric("Total Unrealised P&L", f"₹{total_pl:,.0f}", f"{total_pl/1e5:.2f} L")

    st.divider()

    # Manual trade entry
    st.subheader("✏️ Add / Remove Position")
    with st.form("trade_form"):
        c1, c2, c3, c4 = st.columns(4)
        ticker_in   = c1.text_input("Ticker (e.g. RELIANCE.NS)").strip().upper()
        shares_in   = c2.number_input("Shares", min_value=0.0, step=1.0)
        price_in    = c3.number_input("Entry Price (₹)", min_value=0.0, step=0.05)
        edate_in    = c4.date_input("Entry Date", value=date.today())
        notes_in    = st.text_input("Notes (optional)")
        action      = st.radio("Action", ["Add", "Remove"], horizontal=True)
        submitted   = st.form_submit_button("✅ Submit")

        if submitted and ticker_in:
            if action == "Add":
                new_row = pd.DataFrame([{
                    "Ticker": ticker_in, "Shares": shares_in,
                    "Entry_Price": price_in, "Entry_Date": str(edate_in), "Notes": notes_in,
                }])
                positions = pd.concat([positions, new_row], ignore_index=True)
                _save_positions(positions)
                st.success(f"Added {ticker_in}")
            else:
                positions = positions[positions["Ticker"] != ticker_in]
                _save_positions(positions)
                st.warning(f"Removed {ticker_in}")
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — IRR / XIRR
# ══════════════════════════════════════════════════════════════════════════════
with tab_xirr:
    st.subheader("💰 IRR / XIRR Calculator")
    st.markdown("Enter your cash flows (investments = negative, receipts = positive).")

    if "cf_rows" not in st.session_state:
        st.session_state.cf_rows = [{"date": date.today(), "amount": -100000.0}]

    for i, row in enumerate(st.session_state.cf_rows):
        c1, c2, c3 = st.columns([2, 2, 1])
        st.session_state.cf_rows[i]["date"]   = c1.date_input(f"Date {i+1}", value=row["date"], key=f"d_{i}")
        st.session_state.cf_rows[i]["amount"] = c2.number_input(f"Amount ₹ {i+1}", value=float(row["amount"]), key=f"a_{i}")
        if c3.button("❌", key=f"del_{i}") and len(st.session_state.cf_rows) > 1:
            st.session_state.cf_rows.pop(i)
            st.rerun()

    if st.button("➕ Add Cash Flow"):
        st.session_state.cf_rows.append({"date": date.today(), "amount": 0.0})
        st.rerun()

    st.divider()
    if st.button("📐 Calculate XIRR", type="primary"):
        cfs = [(row["date"], row["amount"]) for row in st.session_state.cf_rows]
        xirr_val = _xirr(cfs)
        if xirr_val is not None:
            color = "green" if xirr_val > 0 else "red"
            st.markdown(f"### XIRR: <span style='color:{color}'>{xirr_val}%</span> per annum", unsafe_allow_html=True)
        else:
            st.error("Could not converge. Please check your cash flows.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — BACKTEST RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_backtest:
    st.subheader("📊 Backtest Results")

    chart_path = Path("backtest_results.png")
    if chart_path.exists():
        st.image(str(chart_path), use_column_width=True)
    else:
        st.info("Run `python backtest.py` to generate backtest results and charts.")

    trades_path = Path("trades_log.csv")
    if trades_path.exists():
        trades_df = pd.read_csv(trades_path)
        st.subheader("📋 Trade Log")
        st.dataframe(
            trades_df.style.format({"Gain_pct": "{:+.2f}%", "Entry_Price": "₹{:.2f}", "Exit_Price": "₹{:.2f}"}),
            use_container_width=True,
        )

    metrics_path = Path("backtest_metrics.csv")
    if metrics_path.exists():
        m = pd.read_csv(metrics_path).set_index("Metric")
        st.subheader("📐 Performance Metrics")
        col1, col2, col3 = st.columns(3)
        if "CAGR_%" in m.index:
            col1.metric("CAGR", f"{m.loc['CAGR_%', 'Value']}%")
        if "Max_Drawdown_%" in m.index:
            col2.metric("Max Drawdown", f"{m.loc['Max_Drawdown_%', 'Value']}%")
        if "Sharpe_Ratio" in m.index:
            col3.metric("Sharpe Ratio", m.loc["Sharpe_Ratio", "Value"])
