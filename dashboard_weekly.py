"""
dashboard.py — Nifty 500 Quant System
World-class trading dashboard with:
  - Luxury dark theme with gold accents
  - Live signals (Buy/Sell/Hold)
  - Upstox holdings integration
  - Watchlist manager
  - Strategy rules reference panel
  - Portfolio analytics
  - XIRR calculator
  - Backtest results
"""

import math
import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty 500 Quant System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — Luxury Dark Theme ────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@400;600&family=DM+Sans:wght@300;400;500;600&display=swap');

  /* Global reset */
  .stApp { background: #0a0c10; color: #e8e6e0; font-family: 'DM Sans', sans-serif; }
  .main .block-container { padding: 1.5rem 2rem; max-width: 1600px; }

  /* Hide Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }
  .stDeployButton { display: none; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #0d0f14 !important;
    border-right: 1px solid #1e2130;
  }
  [data-testid="stSidebar"] .stMarkdown { color: #8892a4; }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #111420;
    border: 1px solid #1e2130;
    border-radius: 12px;
    padding: 1rem;
  }
  [data-testid="metric-container"] label { color: #8892a4 !important; font-size: 11px !important; letter-spacing: 1.5px; text-transform: uppercase; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #f0c060 !important; font-family: 'JetBrains Mono'; font-size: 1.6rem !important; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { background: #111420; border-radius: 10px; padding: 4px; gap: 4px; }
  .stTabs [data-baseweb="tab"] { color: #8892a4; border-radius: 8px; font-size: 13px; font-weight: 500; letter-spacing: 0.3px; }
  .stTabs [aria-selected="true"] { background: #1a2240 !important; color: #f0c060 !important; }

  /* DataFrames */
  [data-testid="stDataFrame"] { border: 1px solid #1e2130; border-radius: 10px; overflow: hidden; }
  .dvn-scroller { background: #0d0f14 !important; }

  /* Buttons */
  .stButton > button {
    background: linear-gradient(135deg, #1a2240, #1e2850);
    color: #f0c060;
    border: 1px solid #2a3560;
    border-radius: 8px;
    font-family: 'DM Sans';
    font-weight: 500;
    letter-spacing: 0.5px;
    transition: all 0.2s;
  }
  .stButton > button:hover { background: linear-gradient(135deg, #1e2850, #243070); border-color: #f0c060; }

  /* Input fields */
  .stTextInput input, .stNumberInput input, .stSelectbox select {
    background: #111420 !important;
    border: 1px solid #1e2130 !important;
    border-radius: 8px !important;
    color: #e8e6e0 !important;
    font-family: 'JetBrains Mono';
  }

  /* Custom card component */
  .quant-card {
    background: #111420;
    border: 1px solid #1e2130;
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 16px;
  }
  .quant-card-gold { border-left: 3px solid #f0c060; }
  .quant-card-green { border-left: 3px solid #2ecc71; }
  .quant-card-red   { border-left: 3px solid #e74c3c; }
  .quant-card-blue  { border-left: 3px solid #3498db; }

  /* Signal badges */
  .badge-buy  { background:#0d2a1a; color:#2ecc71; border:1px solid #2ecc71; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; letter-spacing:1px; }
  .badge-sell { background:#2a0d0d; color:#e74c3c; border:1px solid #e74c3c; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; letter-spacing:1px; }
  .badge-hold { background:#1a1a2a; color:#8892a4; border:1px solid #2a2a4a; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; letter-spacing:1px; }

  /* Section headers */
  .section-title {
    font-family: 'DM Serif Display';
    font-size: 1.4rem;
    color: #f0c060;
    margin-bottom: 4px;
    letter-spacing: -0.3px;
  }
  .section-sub { font-size: 12px; color: #8892a4; margin-bottom: 16px; letter-spacing: 0.3px; }

  /* Rule pills */
  .rule-pill {
    display: inline-block;
    background: #1a2240;
    border: 1px solid #2a3560;
    color: #a0b4d0;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-family: 'JetBrains Mono';
    margin: 3px;
  }
  .rule-pill-gold { border-color: #f0c060; color: #f0c060; }
  .rule-pill-green { border-color: #2ecc71; color: #2ecc71; }
  .rule-pill-red { border-color: #e74c3c; color: #e74c3c; }

  /* Top header bar */
  .top-header {
    background: linear-gradient(135deg, #0d0f14 0%, #111420 50%, #0d1220 100%);
    border: 1px solid #1e2130;
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  /* Divider */
  hr { border-color: #1e2130 !important; margin: 20px 0; }

  /* Info boxes */
  .stInfo, .stSuccess, .stWarning, .stError { border-radius: 10px; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #0a0c10; }
  ::-webkit-scrollbar-thumb { background: #1e2130; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #2a3560; }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────────────

def _load_signal(kind: str, prefix: str = "weekly") -> pd.DataFrame:
    files = sorted(Path("signals").glob(f"{prefix}_{kind}_*.csv"))
    return pd.read_csv(files[-1]) if files else pd.DataFrame()


def _load_positions() -> pd.DataFrame:
    p = Path("positions.csv")
    if p.exists():
        return pd.read_csv(p)
    return pd.DataFrame(columns=["Ticker", "Shares", "Entry_Price", "Entry_Date", "Source", "Notes"])


def _save_positions(df: pd.DataFrame):
    df.to_csv("positions.csv", index=False)


def _load_watchlist() -> list:
    p = Path("watchlist.json")
    if p.exists():
        return json.loads(p.read_text())
    return []


def _save_watchlist(lst: list):
    Path("watchlist.json").write_text(json.dumps(lst))


def _xirr(cashflows, guess=0.1):
    if len(cashflows) < 2:
        return None
    dates   = [c[0] for c in cashflows]
    amounts = [c[1] for c in cashflows]
    t0      = dates[0]
    years   = [(d - t0).days / 365.25 for d in dates]
    def npv(r): return sum(a / (1+r)**y for a, y in zip(amounts, years))
    def dnpv(r): return sum(-y*a/(1+r)**(y+1) for a, y in zip(amounts, years))
    r = guess
    for _ in range(200):
        n = npv(r)
        if abs(n) < 1e-7: break
        d = dnpv(r)
        if d == 0: break
        r -= n / d
        if r <= -1: r = -0.999
    return round(r * 100, 2) if not math.isnan(r) else None


def _get_prices(tickers):
    prices = {}
    try:
        import yfinance as yf
        for t in tickers:
            d = yf.download(t, period="2d", interval="1d", progress=False, auto_adjust=False)
            if not d.empty:
                prices[t] = round(float(d["Close"].iloc[-1]), 2)
    except Exception:
        pass
    return prices


def _fmt(val, prefix="₹", decimals=2):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return "—"
    return f"{prefix}{val:,.{decimals}f}"


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 8px'>
      <div style='font-family:DM Serif Display;font-size:1.3rem;color:#f0c060'>⬡ QUANT</div>
      <div style='font-size:10px;color:#8892a4;letter-spacing:2px'>NIFTY 500 SYSTEM</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown("<div style='font-size:11px;color:#8892a4;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px'>Navigation</div>", unsafe_allow_html=True)

    page = st.radio("", [
        "📡  Live Signals",
        "💼  Portfolio",
        "👁️  Watchlist",
        "📋  Strategy Rules",
        "💰  XIRR Calculator",
        "📊  Backtest",
        "🔗  Upstox Link",
    ], label_visibility="collapsed")

    st.divider()

    # Quick stats in sidebar
    buy_df  = _load_signal("buy")
    sell_df = _load_signal("sell")
    hold_df = _load_signal("hold")

    st.markdown("<div style='font-size:11px;color:#8892a4;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px'>This Week</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("🟢 BUY",  len(buy_df))
    c2.metric("🔴 SELL", len(sell_df))
    st.metric("⚪ HOLD", len(hold_df))

    st.divider()
    st.caption(f"🕐 {datetime.now().strftime('%d %b %Y  %H:%M')}")
    st.caption("Data: yfinance (free) | NSE")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class='top-header'>
  <div>
    <div style='font-family:DM Serif Display;font-size:2rem;color:#f0c060;line-height:1'>
      Nifty 500 Quant System
    </div>
    <div style='font-size:13px;color:#8892a4;margin-top:4px'>
      Monthly Structural Reversal &nbsp;·&nbsp; Weekly EMA Trend &nbsp;·&nbsp; Indian Markets
    </div>
  </div>
  <div style='text-align:right'>
    <div style='font-family:JetBrains Mono;font-size:1.1rem;color:#f0c060'>{datetime.now().strftime("%d %b %Y")}</div>
    <div style='font-size:11px;color:#8892a4'>NSE · {datetime.now().strftime("%A")}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: LIVE SIGNALS
# ══════════════════════════════════════════════════════════════════════════════
if "Signals" in page:

    # System selector
    system = st.radio("System", ["📊 Weekly", "📅 Monthly"], horizontal=True)
    prefix = "weekly" if "Weekly" in system else "monthly"

    buy_df  = _load_signal("buy",  prefix)
    sell_df = _load_signal("sell", prefix)
    hold_df = _load_signal("hold", prefix)

    # Summary row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🟢 BUY Signals",  len(buy_df),  help="Enter at next open")
    col2.metric("🔴 SELL Signals", len(sell_df), help="Exit at next open")
    col3.metric("⚪ HOLD",         len(hold_df))
    col4.metric("🗓️ Universe Scanned", len(buy_df)+len(sell_df)+len(hold_df))

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── BUY SIGNALS ──────────────────────────────────────────────────────────
    st.markdown("<div class='section-title'>🟢 Buy Signals</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Execute at NEXT week/month open · Ranked by RSI14 (highest momentum first)</div>", unsafe_allow_html=True)

    if buy_df.empty:
        st.markdown("<div class='quant-card quant-card-green'><span style='color:#8892a4'>No BUY signals this period. The strategy requires all 3 entry conditions to be met simultaneously.</span></div>", unsafe_allow_html=True)
    else:
        # Add signal badges
        display_buy = buy_df.copy()
        display_buy.insert(0, "Signal", "BUY")
        st.dataframe(
            display_buy,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Signal":   st.column_config.TextColumn("Signal", width=80),
                "Ticker":   st.column_config.TextColumn("Ticker", width=120),
                "Close":    st.column_config.NumberColumn("Close ₹",   format="₹%.2f"),
                "EMA200":   st.column_config.NumberColumn("EMA200 ₹",  format="₹%.2f"),
                "RSI14":    st.column_config.ProgressColumn("RSI14",   min_value=0, max_value=100, format="%.1f"),
                "RSI_MA14": st.column_config.NumberColumn("RSI_MA14",  format="%.1f"),
            }
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── SELL SIGNALS ─────────────────────────────────────────────────────────
    st.markdown("<div class='section-title'>🔴 Sell Signals</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Execute at NEXT week/month open · RSI crossed below RSI_MA</div>", unsafe_allow_html=True)

    if sell_df.empty:
        st.markdown("<div class='quant-card quant-card-red'><span style='color:#8892a4'>No SELL signals this period.</span></div>", unsafe_allow_html=True)
    else:
        st.dataframe(sell_df, use_container_width=True, hide_index=True,
                     column_config={
                         "Close":  st.column_config.NumberColumn("Close ₹",  format="₹%.2f"),
                         "RSI14":  st.column_config.ProgressColumn("RSI14",  min_value=0, max_value=100, format="%.1f"),
                     })

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── HOLD ─────────────────────────────────────────────────────────────────
    with st.expander(f"⚪ Hold List ({len(hold_df)} stocks) — click to expand"):
        if not hold_df.empty:
            st.dataframe(hold_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
elif "Portfolio" in page:

    st.markdown("<div class='section-title'>💼 Portfolio</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Live P&L · Open positions · Equal-weight quant portfolio</div>", unsafe_allow_html=True)

    pos = _load_positions()

    if not pos.empty:
        prices = _get_prices(pos["Ticker"].tolist())
        pos = pos.copy()
        pos["Current_Price"] = pos["Ticker"].map(prices)
        pos["PnL_%"]  = ((pos["Current_Price"] - pos["Entry_Price"]) / pos["Entry_Price"] * 100).round(2)
        pos["PnL_₹"]  = ((pos["Current_Price"] - pos["Entry_Price"]) * pos["Shares"]).round(2)
        pos["Value_₹"] = (pos["Current_Price"] * pos["Shares"]).round(2)

        total_invested = (pos["Entry_Price"] * pos["Shares"]).sum()
        total_value    = pos["Value_₹"].sum()
        total_pnl      = pos["PnL_₹"].sum()
        total_pnl_pct  = (total_pnl / total_invested * 100) if total_invested > 0 else 0

        # Summary metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Positions",       len(pos))
        c2.metric("Portfolio Value",  _fmt(total_value))
        c3.metric("Total P&L",        _fmt(total_pnl),
                  delta=f"{total_pnl_pct:+.2f}%")
        c4.metric("Invested",         _fmt(total_invested))

        st.markdown("<hr>", unsafe_allow_html=True)

        st.dataframe(
            pos,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Entry_Price":   st.column_config.NumberColumn("Entry ₹",   format="₹%.2f"),
                "Current_Price": st.column_config.NumberColumn("Current ₹", format="₹%.2f"),
                "Value_₹":       st.column_config.NumberColumn("Value ₹",   format="₹%.0f"),
                "PnL_%":         st.column_config.NumberColumn("P&L %",     format="%+.2f%%"),
                "PnL_₹":         st.column_config.NumberColumn("P&L ₹",     format="₹%+.0f"),
            }
        )
    else:
        st.markdown("<div class='quant-card'>No positions yet. Add them below or link your Upstox account.</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Manual position entry ─────────────────────────────────────────────────
    st.markdown("<div class='section-title' style='font-size:1.1rem'>✏️ Manage Positions</div>", unsafe_allow_html=True)

    action = st.radio("Action", ["➕ Add", "❌ Remove"], horizontal=True)
    c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 1.5, 2])
    ticker  = c1.text_input("Ticker", placeholder="RELIANCE.NS").upper().strip()
    shares  = c2.number_input("Shares", min_value=0.0, step=1.0)
    price   = c3.number_input("Entry Price ₹", min_value=0.0, step=0.5)
    edate   = c4.date_input("Entry Date", value=date.today())
    source  = c5.selectbox("Source", ["Manual", "Upstox", "Zerodha", "Groww", "Other"])
    notes   = st.text_input("Notes (optional)", placeholder="e.g. Weekly BUY signal")

    if st.button("✅ Submit Position", use_container_width=False):
        if ticker:
            pos = _load_positions()
            if "Add" in action:
                new = pd.DataFrame([{"Ticker": ticker, "Shares": shares,
                                     "Entry_Price": price, "Entry_Date": str(edate),
                                     "Source": source, "Notes": notes}])
                pos = pd.concat([pos, new], ignore_index=True)
                st.success(f"✅ Added {ticker}")
            else:
                pos = pos[pos["Ticker"] != ticker]
                st.warning(f"Removed {ticker}")
            _save_positions(pos)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
elif "Watchlist" in page:

    st.markdown("<div class='section-title'>👁️ Watchlist</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Track stocks you're monitoring — live prices + indicator snapshot</div>", unsafe_allow_html=True)

    watchlist = _load_watchlist()

    # Add to watchlist
    c1, c2 = st.columns([3, 1])
    new_ticker = c1.text_input("Add ticker", placeholder="e.g. TITAN.NS").upper().strip()
    if c2.button("➕ Add", use_container_width=True) and new_ticker:
        if new_ticker not in watchlist:
            watchlist.append(new_ticker)
            _save_watchlist(watchlist)
            st.rerun()

    if not watchlist:
        st.markdown("<div class='quant-card'>Your watchlist is empty. Add tickers above.</div>", unsafe_allow_html=True)
    else:
        # Fetch live data for watchlist
        prices = _get_prices(watchlist)

        # Check if any watchlist stocks have signals
        all_signals = pd.concat([
            _load_signal("buy"),
            _load_signal("sell"),
            _load_signal("hold"),
        ], ignore_index=True) if not _load_signal("buy").empty else pd.DataFrame()

        rows = []
        for t in watchlist:
            price = prices.get(t, None)
            signal = "—"
            if not all_signals.empty and "Ticker" in all_signals.columns:
                match = all_signals[all_signals["Ticker"] == t]
                if not match.empty:
                    signal = match.iloc[0].get("Signal", "—")
            rows.append({"Ticker": t, "Price ₹": price, "Signal": signal})

        wl_df = pd.DataFrame(rows)

        st.dataframe(
            wl_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Price ₹": st.column_config.NumberColumn("Price ₹", format="₹%.2f"),
                "Signal":  st.column_config.TextColumn("Signal", width=100),
            }
        )

        # Remove from watchlist
        to_remove = st.selectbox("Remove from watchlist", ["—"] + watchlist)
        if st.button("❌ Remove") and to_remove != "—":
            watchlist.remove(to_remove)
            _save_watchlist(watchlist)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: STRATEGY RULES
# ══════════════════════════════════════════════════════════════════════════════
elif "Strategy" in page:

    st.markdown("<div class='section-title'>📋 Strategy Rules Reference</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Complete entry & exit criteria for both systems — always visible, never forget a rule</div>", unsafe_allow_html=True)

    tab_w, tab_m = st.tabs(["📊 Weekly System", "📅 Monthly System"])

    with tab_w:
        st.markdown("""
        <div class='quant-card quant-card-gold'>
          <div style='font-family:DM Serif Display;font-size:1.2rem;color:#f0c060;margin-bottom:12px'>
            Weekly Structural Trend Reversal
          </div>
          <div style='font-size:12px;color:#8892a4;margin-bottom:16px'>
            Timeframe: Weekly (Friday close) · Universe: Nifty 500 Fundamentally Filtered
          </div>

          <div style='font-size:13px;font-weight:600;color:#2ecc71;margin-bottom:8px'>🟢 ENTRY — All 3 conditions required</div>

          <div style='margin-bottom:6px'>
            <span class='rule-pill rule-pill-gold'>1</span>
            <span style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0'>
              Previous week: Close &lt; EMA200
            </span>
          </div>
          <div style='margin-bottom:6px'>
            <span class='rule-pill rule-pill-gold'>2</span>
            <span style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0'>
              Current week: Close &gt; EMA200 &nbsp;←&nbsp; True EMA crossover
            </span>
          </div>
          <div style='margin-bottom:6px'>
            <span class='rule-pill rule-pill-gold'>3</span>
            <span style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0'>
              Previous week: RSI14 &lt; RSI_MA14
            </span>
          </div>
          <div style='margin-bottom:6px'>
            <span class='rule-pill rule-pill-gold'>3</span>
            <span style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0'>
              Current week: RSI14 &gt; RSI_MA14 &nbsp;AND&nbsp; RSI14 &gt; 0 &nbsp;AND&nbsp; RSI_MA14 &gt; 0
            </span>
          </div>

          <div style='background:#0a1020;border-radius:8px;padding:10px 14px;margin:14px 0;font-family:JetBrains Mono;font-size:11px;color:#f0c060'>
            ⚡ Execution: Enter at NEXT WEEK OPEN
          </div>

          <div style='font-size:13px;font-weight:600;color:#e74c3c;margin:16px 0 8px'>🔴 EXIT — Either condition triggers exit</div>
          <div style='margin-bottom:6px'>
            <span class='rule-pill rule-pill-red'>A</span>
            <span style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0'>
              RSI14 crosses BELOW RSI_MA14
            </span>
          </div>
          <div style='background:#0a1020;border-radius:8px;padding:10px 14px;margin:14px 0;font-family:JetBrains Mono;font-size:11px;color:#e74c3c'>
            ⚡ Execution: Exit at NEXT WEEK OPEN
          </div>
        </div>

        <div class='quant-card quant-card-blue'>
          <div style='font-size:13px;font-weight:600;color:#3498db;margin-bottom:10px'>📐 Indicators</div>
          <div style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0;line-height:2'>
            EMA200 &nbsp;=&nbsp; Exponential MA (200 weeks) on unadjusted close → matches TradingView<br>
            RSI14 &nbsp;&nbsp;=&nbsp; Wilder RSI, 14-period weekly<br>
            RSI_MA14 =&nbsp; 14-period SMA of RSI14
          </div>
        </div>
        """, unsafe_allow_html=True)

    with tab_m:
        st.markdown("""
        <div class='quant-card quant-card-gold'>
          <div style='font-family:DM Serif Display;font-size:1.2rem;color:#f0c060;margin-bottom:12px'>
            Monthly Structural Reversal System
          </div>
          <div style='font-size:12px;color:#8892a4;margin-bottom:16px'>
            Timeframe: Monthly · Universe: Nifty 500 Fundamentally Filtered
          </div>

          <div style='font-size:13px;font-weight:600;color:#2ecc71;margin-bottom:8px'>🟢 ENTRY — All 3 phases required</div>

          <div style='background:#0a1020;border-radius:8px;padding:12px 16px;margin-bottom:10px'>
            <div style='color:#f0c060;font-size:12px;font-weight:600;margin-bottom:6px'>Phase 1 — Deep Correction (within last 12 months)</div>
            <div style='font-family:JetBrains Mono;font-size:11px;color:#a0b4d0'>
              Close &lt; SSF200 &nbsp;AND&nbsp; Close &lt; SSF250
            </div>
          </div>

          <div style='background:#0a1020;border-radius:8px;padding:12px 16px;margin-bottom:10px'>
            <div style='color:#f0c060;font-size:12px;font-weight:600;margin-bottom:6px'>Phase 2 — Structural Recovery (current month)</div>
            <div style='font-family:JetBrains Mono;font-size:11px;color:#a0b4d0'>
              Close &gt; SSF50 &nbsp;AND&nbsp; SSF50 &gt; SSF200
            </div>
          </div>

          <div style='background:#0a1020;border-radius:8px;padding:12px 16px;margin-bottom:10px'>
            <div style='color:#f0c060;font-size:12px;font-weight:600;margin-bottom:6px'>Phase 3 — Momentum Confirmation</div>
            <div style='font-family:JetBrains Mono;font-size:11px;color:#a0b4d0;line-height:2'>
              Previous month: RSI14 &lt; RSI_MA14<br>
              Current month:  RSI14 &gt; RSI_MA14<br>
              AND RSI14 &gt; 0 &nbsp;AND&nbsp; RSI_MA14 &gt; 0
            </div>
          </div>

          <div style='background:#0a1020;border-radius:8px;padding:10px 14px;margin:14px 0;font-family:JetBrains Mono;font-size:11px;color:#f0c060'>
            ⚡ Execution: Enter at NEXT MONTH OPEN
          </div>

          <div style='font-size:13px;font-weight:600;color:#e74c3c;margin:16px 0 8px'>🔴 EXIT — Either condition triggers exit</div>
          <div style='margin-bottom:6px'>
            <span class='rule-pill rule-pill-red'>A</span>
            <span style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0'> RSI14 crosses BELOW RSI_MA14</span>
          </div>
          <div style='margin-bottom:6px'>
            <span class='rule-pill rule-pill-red'>B</span>
            <span style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0'> Close &lt; SSF200</span>
          </div>
          <div style='background:#0a1020;border-radius:8px;padding:10px 14px;margin:14px 0;font-family:JetBrains Mono;font-size:11px;color:#e74c3c'>
            ⚡ Execution: Exit at NEXT MONTH OPEN
          </div>
        </div>

        <div class='quant-card quant-card-blue'>
          <div style='font-size:13px;font-weight:600;color:#3498db;margin-bottom:10px'>📐 Indicators (Ehlers SSF)</div>
          <div style='font-family:JetBrains Mono;font-size:12px;color:#a0b4d0;line-height:2'>
            SSF50 &nbsp; = Ehlers 2-pole Super Smoother, period=50<br>
            SSF200 &nbsp;= Ehlers 2-pole Super Smoother, period=200<br>
            SSF250 &nbsp;= Ehlers 2-pole Super Smoother, period=250<br>
            RSI14 &nbsp; = Wilder RSI, 14-period monthly<br>
            RSI_MA14 = 14-period SMA of RSI14
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Portfolio rules (shared)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("""
    <div class='quant-card'>
      <div style='font-size:13px;font-weight:600;color:#f0c060;margin-bottom:10px'>⚖️ Portfolio Rules (Both Systems)</div>
      <div style='display:flex;flex-wrap:wrap;gap:8px'>
        <span class='rule-pill'>Max 10 positions</span>
        <span class='rule-pill'>Equal weight allocation</span>
        <span class='rule-pill'>Rank by RSI14 if &gt;10 signals</span>
        <span class='rule-pill'>Capital reinvested after exits</span>
        <span class='rule-pill'>0.2% slippage</span>
        <span class='rule-pill'>0.1% brokerage</span>
      </div>
    </div>

    <div class='quant-card'>
      <div style='font-size:13px;font-weight:600;color:#f0c060;margin-bottom:10px'>🔍 Fundamental Filter (Monthly Master List)</div>
      <div style='display:flex;flex-wrap:wrap;gap:8px'>
        <span class='rule-pill rule-pill-gold'>Market Cap &gt; ₹5000 Cr</span>
        <span class='rule-pill rule-pill-gold'>EPS &gt; 0</span>
        <span class='rule-pill rule-pill-gold'>EPS CAGR 5Y &gt; 0</span>
        <span class='rule-pill rule-pill-gold'>Revenue CAGR 3Y &gt; 0</span>
        <span class='rule-pill rule-pill-gold'>Dividend Yield &gt; 0</span>
        <span class='rule-pill rule-pill-gold'>ROE &gt; 12%</span>
        <span class='rule-pill rule-pill-gold'>OPM &gt; 10%</span>
        <span class='rule-pill rule-pill-gold'>Free Cash Flow &gt; 0</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: XIRR CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════
elif "XIRR" in page:

    st.markdown("<div class='section-title'>💰 XIRR / IRR Calculator</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Calculate annualised returns on irregular cash flows · Investments = negative · Receipts = positive</div>", unsafe_allow_html=True)

    if "cf_rows" not in st.session_state:
        st.session_state.cf_rows = [
            {"date": date(2024, 1, 1), "amount": -100000.0, "label": "Initial investment"},
            {"date": date.today(),     "amount":  150000.0, "label": "Current value"},
        ]

    for i, row in enumerate(st.session_state.cf_rows):
        c1, c2, c3, c4 = st.columns([2, 2, 3, 1])
        st.session_state.cf_rows[i]["date"]   = c1.date_input(f"Date {i+1}",  value=row["date"],   key=f"d{i}")
        st.session_state.cf_rows[i]["amount"] = c2.number_input(f"Amount ₹ {i+1}", value=float(row["amount"]), key=f"a{i}", step=1000.0)
        st.session_state.cf_rows[i]["label"]  = c3.text_input(f"Label {i+1}", value=row.get("label",""), key=f"l{i}", placeholder="e.g. SIP, Withdrawal")
        if c4.button("❌", key=f"del{i}") and len(st.session_state.cf_rows) > 2:
            st.session_state.cf_rows.pop(i); st.rerun()

    col1, col2 = st.columns([1, 4])
    if col1.button("➕ Add Cash Flow"):
        st.session_state.cf_rows.append({"date": date.today(), "amount": 0.0, "label": ""}); st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    if st.button("📐 Calculate XIRR", type="primary", use_container_width=False):
        cfs = [(r["date"], r["amount"]) for r in st.session_state.cf_rows]
        result = _xirr(cfs)
        if result is not None:
            color  = "#2ecc71" if result > 0 else "#e74c3c"
            emoji  = "🚀" if result > 20 else ("✅" if result > 10 else "⚠️")
            st.markdown(f"""
            <div class='quant-card quant-card-gold' style='text-align:center;padding:32px'>
              <div style='font-size:14px;color:#8892a4;letter-spacing:2px;text-transform:uppercase'>XIRR Result</div>
              <div style='font-family:DM Serif Display;font-size:3.5rem;color:{color};margin:8px 0'>{result}%</div>
              <div style='font-size:14px;color:#8892a4'>per annum &nbsp;{emoji}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error("Could not converge. Check your cash flows — ensure at least one negative and one positive value.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: BACKTEST
# ══════════════════════════════════════════════════════════════════════════════
elif "Backtest" in page:

    st.markdown("<div class='section-title'>📊 Backtest Results</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>2010 → Present · Monthly master list · No lookahead bias · 0.2% slippage + 0.1% brokerage</div>", unsafe_allow_html=True)

    tab_w, tab_m = st.tabs(["📊 Weekly", "📅 Monthly"])

    for tab, prefix, chart_file, metrics_file, trades_file in [
        (tab_w, "weekly",  "weekly_backtest.png",  "weekly_metrics.csv",  "weekly_trades.csv"),
        (tab_m, "monthly", "backtest_results.png", "backtest_metrics.csv","trades_log.csv"),
    ]:
        with tab:
            if Path(chart_file).exists():
                st.image(chart_file, use_column_width=True)
            else:
                st.markdown(f"<div class='quant-card'>Run <code>python backtest.py</code> to generate the {prefix} backtest chart.</div>", unsafe_allow_html=True)

            if Path(metrics_file).exists():
                m = pd.read_csv(metrics_file).set_index("Metric")["Value"]
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("CAGR",         f"{m.get('CAGR_%','—')}%")
                c2.metric("Max Drawdown",  f"{m.get('Max_Drawdown_%','—')}%")
                c3.metric("Sharpe Ratio",  m.get("Sharpe_Ratio","—"))
                c4.metric("Win Rate",      f"{m.get('Win_Rate_%','—')}%")
                c1.metric("Avg Hold",      f"{m.get('Avg_Hold_Weeks', m.get('Avg_Hold_Months','—'))} periods")
                c2.metric("Exposure",      f"{m.get('Exposure_%','—')}%")
                c3.metric("Total Trades",  m.get("Total_Trades","—"))
                c4.metric("Final Capital", _fmt(float(m.get("Final_Capital_INR",0))))

            if Path(trades_file).exists():
                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown("<div style='font-size:13px;font-weight:600;color:#f0c060;margin-bottom:8px'>📋 Trade Log</div>", unsafe_allow_html=True)
                trades = pd.read_csv(trades_file)
                st.dataframe(trades, use_container_width=True, hide_index=True,
                             column_config={
                                 "Gain_pct":    st.column_config.NumberColumn("Gain %",    format="%+.2f%%"),
                                 "Entry_Price": st.column_config.NumberColumn("Entry ₹",   format="₹%.2f"),
                                 "Exit_Price":  st.column_config.NumberColumn("Exit ₹",    format="₹%.2f"),
                             })


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: UPSTOX LINK
# ══════════════════════════════════════════════════════════════════════════════
elif "Upstox" in page:

    st.markdown("<div class='section-title'>🔗 Upstox Integration</div>", unsafe_allow_html=True)
    st.markdown("<div class='section-sub'>Import your holdings directly from Upstox into the portfolio tracker</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class='quant-card quant-card-blue'>
      <div style='font-size:13px;font-weight:600;color:#3498db;margin-bottom:12px'>📥 Method 1 — Upload Holdings CSV (Recommended)</div>
      <div style='font-size:12px;color:#8892a4;line-height:1.8'>
        1. Open Upstox app → Portfolio → Holdings<br>
        2. Click <strong style='color:#e8e6e0'>Download / Export</strong> (top right)<br>
        3. Save the CSV file<br>
        4. Upload it below ↓
      </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload Upstox Holdings CSV", type=["csv"])

    if uploaded:
        try:
            upstox_df = pd.read_csv(uploaded)
            st.markdown("**Preview of uploaded file:**")
            st.dataframe(upstox_df.head(10), use_container_width=True, hide_index=True)

            # Try to map common Upstox CSV column names
            col_map = {}
            cols_lower = {c.lower().strip(): c for c in upstox_df.columns}

            for candidate in ["symbol", "scrip", "stock", "instrument"]:
                if candidate in cols_lower: col_map["Ticker"] = cols_lower[candidate]; break
            for candidate in ["quantity", "qty", "shares"]:
                if candidate in cols_lower: col_map["Shares"] = cols_lower[candidate]; break
            for candidate in ["avg price", "average price", "avg. price", "buy price"]:
                if candidate in cols_lower: col_map["Entry_Price"] = cols_lower[candidate]; break

            if len(col_map) >= 2:
                mapped = upstox_df.rename(columns={v: k for k, v in col_map.items()})
                # Add .NS suffix if missing
                if "Ticker" in mapped.columns:
                    mapped["Ticker"] = mapped["Ticker"].astype(str).apply(
                        lambda x: x.strip().upper() + ".NS" if not x.strip().upper().endswith(".NS") else x.strip().upper()
                    )
                mapped["Entry_Date"] = str(date.today())
                mapped["Source"]     = "Upstox"
                mapped["Notes"]      = "Imported from Upstox"

                if st.button("✅ Import to Portfolio", type="primary"):
                    existing = _load_positions()
                    keep_cols = ["Ticker","Shares","Entry_Price","Entry_Date","Source","Notes"]
                    import_df = mapped[[c for c in keep_cols if c in mapped.columns]]
                    combined  = pd.concat([existing, import_df], ignore_index=True)
                    _save_positions(combined)
                    st.success(f"✅ Imported {len(import_df)} holdings from Upstox!")
                    st.balloons()
            else:
                st.warning("Could not auto-map columns. Please check your CSV format and map manually below.")
                st.write("Available columns:", list(upstox_df.columns))

        except Exception as e:
            st.error(f"Error reading file: {e}")

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown("""
    <div class='quant-card'>
      <div style='font-size:13px;font-weight:600;color:#f0c060;margin-bottom:12px'>🔌 Method 2 — Upstox API (Advanced)</div>
      <div style='font-size:12px;color:#8892a4;line-height:1.8'>
        For real-time auto-sync, you can connect via the Upstox API v2.<br>
        This requires generating an API key from your Upstox Developer Console.<br><br>
        <strong style='color:#e8e6e0'>Steps:</strong><br>
        1. Go to <a href='https://developer.upstox.com' target='_blank' style='color:#3498db'>developer.upstox.com</a><br>
        2. Create an App → get API Key + Secret<br>
        3. Add them as GitHub Secrets: <code style='color:#f0c060'>UPSTOX_API_KEY</code>, <code style='color:#f0c060'>UPSTOX_SECRET</code><br>
        4. The signal engine will then auto-check your holdings before each run<br><br>
        <em style='color:#555'>Note: Upstox API is free for personal use.</em>
      </div>
    </div>
    """, unsafe_allow_html=True)
