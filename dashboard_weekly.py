"""
dashboard.py  (Weekly Strategy)
---------------------------------
Streamlit dashboard for the Weekly Structural Trend Reversal System.

Run: streamlit run dashboard.py
"""

import math
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Weekly Quant System", page_icon="📊", layout="wide")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_latest_signal(kind: str) -> pd.DataFrame:
    files = sorted(Path("signals").glob(f"weekly_{kind}_*.csv"))
    return pd.read_csv(files[-1]) if files else pd.DataFrame()


def _load_positions():
    from portfolio import load_positions, enrich_positions
    return enrich_positions(load_positions())


def _xirr_calc(cashflows):
    from portfolio import xirr
    return xirr(cashflows)


def _fmt_inr(val):
    if pd.isna(val): return "—"
    return f"₹{val:,.0f}"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Controls")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption("Weekly Structural Trend Reversal")
    st.caption(f"Updated: {datetime.now().strftime('%d %b %Y %H:%M')}")
    st.caption("Universe: Nifty 500 | Data: yfinance")


# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 Weekly Structural Trend Reversal System")
st.markdown("*EMA200 crossover + RSI momentum — weekly signals, Indian markets*")
st.divider()

tab_signals, tab_positions, tab_xirr, tab_backtest = st.tabs(
    ["📡 Live Signals", "📂 Positions", "💰 XIRR", "📈 Backtest"]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SIGNALS
# ══════════════════════════════════════════════════════════════════════════════
with tab_signals:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🟢 BUY Signals")
        buy = _load_latest_signal("buy")
        if buy.empty:
            st.info("No BUY signals — run live_signals.py first.")
        else:
            st.dataframe(buy[["Ticker","Close","EMA200","RSI14","RSI_MA14"]].style.format({
                "Close": "₹{:.2f}", "EMA200": "₹{:.2f}",
                "RSI14": "{:.1f}", "RSI_MA14": "{:.1f}",
            }), hide_index=True, use_container_width=True)
            st.success(f"**{len(buy)} BUY signals** — Execute at next week open")

    with col2:
        st.subheader("🔴 SELL Signals")
        sell = _load_latest_signal("sell")
        if sell.empty:
            st.info("No SELL signals.")
        else:
            st.dataframe(sell[["Ticker","Close","RSI14","RSI_MA14"]].style.format({
                "Close": "₹{:.2f}", "RSI14": "{:.1f}", "RSI_MA14": "{:.1f}",
            }), hide_index=True, use_container_width=True)
            st.error(f"**{len(sell)} SELL signals** — Execute at next week open")

    st.divider()
    st.subheader("⚪ HOLD List")
    hold = _load_latest_signal("hold")
    if not hold.empty:
        st.dataframe(hold[["Ticker","Close","EMA200","RSI14","RSI_MA14"]],
                     hide_index=True, use_container_width=True)
        st.caption(f"{len(hold)} stocks on HOLD")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — POSITIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_positions:
    st.subheader("📂 Open Positions")

    try:
        pos = _load_positions()
    except Exception:
        pos = pd.DataFrame()

    if not pos.empty:
        styled = pos.copy()
        if "PnL_pct" in styled.columns:
            st.dataframe(
                styled.style.format({
                    "Entry_Price": "₹{:.2f}",
                    "Current_Price": "₹{:.2f}",
                    "PnL_pct": "{:+.2f}%",
                    "PnL_INR": "₹{:,.0f}",
                }).applymap(
                    lambda x: "color:green" if isinstance(x,(int,float)) and x>0
                              else ("color:red" if isinstance(x,(int,float)) and x<0 else ""),
                    subset=["PnL_pct","PnL_INR"]
                ),
                hide_index=True, use_container_width=True
            )
            total = pos["PnL_INR"].sum() if "PnL_INR" in pos.columns else 0
            st.metric("Total Unrealised P&L", _fmt_inr(total))
    else:
        st.info("No open positions. Add them below.")

    st.divider()
    st.subheader("✏️ Manage Positions")

    action = st.radio("Action", ["Add", "Remove"], horizontal=True)
    c1, c2, c3, c4 = st.columns(4)
    t_in = c1.text_input("Ticker").upper().strip()
    sh   = c2.number_input("Shares", min_value=0.0, step=1.0)
    px   = c3.number_input("Entry Price ₹", min_value=0.0, step=0.05)
    dt   = c4.date_input("Entry Date", value=date.today())
    note = st.text_input("Notes")

    if st.button("✅ Submit") and t_in:
        from portfolio import add_position, remove_position
        if action == "Add":
            add_position(t_in, sh, px, str(dt), note)
            st.success(f"Added {t_in}")
        else:
            remove_position(t_in)
            st.warning(f"Removed {t_in}")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — XIRR
# ══════════════════════════════════════════════════════════════════════════════
with tab_xirr:
    st.subheader("💰 XIRR / IRR Calculator")
    st.markdown("Enter cash flows — investments as **negative**, receipts as **positive**.")

    if "cf" not in st.session_state:
        st.session_state.cf = [{"date": date.today(), "amount": -100000.0}]

    for i, row in enumerate(st.session_state.cf):
        ca, cb, cc = st.columns([2, 2, 1])
        st.session_state.cf[i]["date"]   = ca.date_input(f"Date {i+1}", row["date"], key=f"d{i}")
        st.session_state.cf[i]["amount"] = cb.number_input(f"Amount ₹ {i+1}", float(row["amount"]), key=f"a{i}")
        if cc.button("❌", key=f"del{i}") and len(st.session_state.cf) > 1:
            st.session_state.cf.pop(i); st.rerun()

    if st.button("➕ Add Cash Flow"):
        st.session_state.cf.append({"date": date.today(), "amount": 0.0}); st.rerun()

    st.divider()
    if st.button("📐 Calculate XIRR", type="primary"):
        cfs = [(r["date"], r["amount"]) for r in st.session_state.cf]
        result = _xirr_calc(cfs)
        if result is not None:
            color = "green" if result > 0 else "red"
            st.markdown(f"### XIRR: <span style='color:{color}'>{result}%</span> p.a.",
                        unsafe_allow_html=True)
        else:
            st.error("Could not converge. Check your cash flows.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — BACKTEST
# ══════════════════════════════════════════════════════════════════════════════
with tab_backtest:
    st.subheader("📈 Backtest Results")

    chart = Path("weekly_backtest.png")
    if chart.exists():
        st.image(str(chart), use_column_width=True)
    else:
        st.info("Run `python backtest.py` to generate the backtest chart.")

    m_path = Path("weekly_metrics.csv")
    if m_path.exists():
        m = pd.read_csv(m_path).set_index("Metric")["Value"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("CAGR",          f"{m.get('CAGR_%', '—')}%")
        c2.metric("Max Drawdown",   f"{m.get('Max_Drawdown_%', '—')}%")
        c3.metric("Sharpe",         m.get("Sharpe_Ratio", "—"))
        c4.metric("Win Rate",       f"{m.get('Win_Rate_%', '—')}%")
        c1.metric("Avg Hold (wks)", m.get("Avg_Hold_Weeks", "—"))
        c2.metric("Exposure",       f"{m.get('Exposure_%', '—')}%")
        c3.metric("Total Trades",   m.get("Total_Trades", "—"))
        c4.metric("Final Capital",  _fmt_inr(float(m.get("Final_Capital_INR", 0))))

    t_path = Path("weekly_trades.csv")
    if t_path.exists():
        st.subheader("📋 Trade Log")
        trades = pd.read_csv(t_path)
        st.dataframe(trades.style.format({
            "Gain_pct": "{:+.2f}%",
            "Entry_Price": "₹{:.2f}",
            "Exit_Price": "₹{:.2f}",
        }), use_container_width=True)
