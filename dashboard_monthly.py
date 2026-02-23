"""
dashboard_monthly.py — Monthly Structural Reversal System
Clean professional dark dashboard | Blue + Slate theme
"""
import math, json
from datetime import date, datetime
from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Monthly Signals · Nifty 500", page_icon="📅", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
html,body,.stApp{background:#0f1117;color:#e2e8f0;font-family:'Inter',sans-serif;}
.main .block-container{padding:1.5rem 2.5rem 3rem;max-width:1400px;}
#MainMenu,footer,header,.stDeployButton{visibility:hidden;display:none;}
[data-testid="stSidebar"]{background:#080b10 !important;border-right:1px solid #1e2433 !important;}
[data-testid="metric-container"]{background:#131926;border:1px solid #1e2433;border-radius:10px;padding:16px 20px;}
[data-testid="metric-container"] label{color:#64748b !important;font-size:11px !important;letter-spacing:1px;text-transform:uppercase;font-weight:600;}
[data-testid="metric-container"] [data-testid="stMetricValue"]{color:#f1f5f9 !important;font-family:'IBM Plex Mono';font-size:1.8rem !important;font-weight:500;}
.stTabs [data-baseweb="tab-list"]{background:#131926;border-radius:8px;padding:3px;gap:2px;border:1px solid #1e2433;}
.stTabs [data-baseweb="tab"]{color:#64748b;border-radius:6px;font-size:13px;font-weight:500;padding:8px 18px;}
.stTabs [aria-selected="true"]{background:#3b82f6 !important;color:#fff !important;}
.stButton>button{background:#3b82f6;color:#fff;border:none;border-radius:8px;font-weight:600;font-size:13px;padding:8px 20px;transition:all 0.2s;}
.stButton>button:hover{background:#2563eb;color:#fff;}
.stTextInput input,.stNumberInput input{background:#131926 !important;border:1px solid #1e2433 !important;border-radius:8px !important;color:#e2e8f0 !important;font-family:'IBM Plex Mono';font-size:13px;}
.stSelectbox>div>div{background:#131926 !important;border:1px solid #1e2433 !important;border-radius:8px !important;color:#e2e8f0 !important;}
[data-testid="stDataFrame"]{border:1px solid #1e2433 !important;border-radius:10px;overflow:hidden;}
hr{border-color:#1e2433 !important;margin:1.5rem 0;}
.card{background:#131926;border:1px solid #1e2433;border-radius:12px;padding:20px 24px;margin-bottom:12px;}
.card-green{border-left:3px solid #10b981;}
.card-red{border-left:3px solid #ef4444;}
.card-blue{border-left:3px solid #3b82f6;}
.card-yellow{border-left:3px solid #f59e0b;}
.card-slate{border-left:3px solid #475569;}
.ptitle{font-size:1.4rem;font-weight:700;color:#f1f5f9;margin-bottom:2px;}
.psub{font-size:12px;color:#475569;margin-bottom:20px;}
.tag{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:0.5px;margin:2px;}
.tag-green{background:#052e16;color:#10b981;border:1px solid #10b981;}
.tag-red{background:#1c0505;color:#ef4444;border:1px solid #ef4444;}
.tag-blue{background:#0c1a3d;color:#3b82f6;border:1px solid #3b82f6;}
.tag-yellow{background:#1c1205;color:#f59e0b;border:1px solid #f59e0b;}
.tag-slate{background:#0f172a;color:#64748b;border:1px solid #334155;}
.tag-purple{background:#1a0a2e;color:#a855f7;border:1px solid #a855f7;}
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:#080b10;}
::-webkit-scrollbar-thumb{background:#1e2433;border-radius:3px;}
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def _sig(kind):
    files = sorted(Path("signals").glob(f"monthly_{kind}_*.csv"))
    return pd.read_csv(files[-1]) if files else pd.DataFrame()

def _pos():
    p = Path("positions_monthly.csv")
    return pd.read_csv(p) if p.exists() else pd.DataFrame(
        columns=["Ticker","Shares","Entry_Price","Entry_Date","Source","Notes"])

def _save_pos(df): df.to_csv("positions_monthly.csv", index=False)

def _wl():
    p = Path("watchlist_monthly.json")
    return json.loads(p.read_text()) if p.exists() else []

def _save_wl(lst): Path("watchlist_monthly.json").write_text(json.dumps(lst))

def _xirr(cfs, guess=0.1):
    if len(cfs)<2: return None
    dates=[c[0] for c in cfs]; amounts=[c[1] for c in cfs]
    t0=dates[0]; yrs=[(d-t0).days/365.25 for d in dates]
    def npv(r): return sum(a/(1+r)**y for a,y in zip(amounts,yrs))
    def dnpv(r): return sum(-y*a/(1+r)**(y+1) for a,y in zip(amounts,yrs))
    r=guess
    for _ in range(200):
        n=npv(r)
        if abs(n)<1e-7: break
        d=dnpv(r)
        if d==0: break
        r-=n/d
        if r<=-1: r=-0.999
    return round(r*100,2) if not math.isnan(r) else None

def _prices(tickers):
    out={}
    try:
        import yfinance as yf
        for t in tickers:
            d=yf.download(t,period="2d",interval="1d",progress=False,auto_adjust=False)
            if not d.empty: out[t]=round(float(d["Close"].iloc[-1]),2)
    except: pass
    return out

def _fmt(v): return f"₹{v:,.2f}" if v and not (isinstance(v,float) and math.isnan(v)) else "—"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:16px 0 12px'>
      <div style='font-size:18px;font-weight:700;color:#3b82f6'>📅 Monthly System</div>
      <div style='font-size:10px;color:#334155;letter-spacing:2px;margin-top:3px'>SSF · STRUCTURAL REVERSAL</div>
    </div>""", unsafe_allow_html=True)
    st.divider()
    page = st.radio("", ["📡  Live Signals","💼  Portfolio","👁️  Watchlist",
                         "📋  Strategy Rules","💰  XIRR","📊  Backtest","🔗  Upstox"],
                    label_visibility="collapsed")
    st.divider()
    buy_s=_sig("buy"); sell_s=_sig("sell"); hold_s=_sig("hold")
    st.markdown("<div style='font-size:10px;color:#334155;letter-spacing:2px;margin-bottom:10px'>THIS MONTH</div>", unsafe_allow_html=True)
    c1,c2=st.columns(2)
    c1.metric("🟢 BUY", len(buy_s)); c2.metric("🔴 SELL", len(sell_s))
    st.metric("⚪ HOLD", len(hold_s))
    st.divider()
    st.caption(f"{datetime.now().strftime('%d %b %Y  %H:%M IST')}")
    st.caption("NSE · yfinance · Nifty 500")
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear(); st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class='card' style='display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding:18px 28px'>
  <div>
    <div style='font-size:1.5rem;font-weight:700;color:#f1f5f9'>Monthly Structural Reversal System</div>
    <div style='margin-top:6px'>
      <span class='tag tag-blue'>Ehlers SSF Filters</span>
      <span class='tag tag-green'>RSI Momentum</span>
      <span class='tag tag-yellow'>Nifty 500</span>
      <span class='tag tag-slate'>Month-End Close</span>
      <span class='tag tag-purple'>3-Phase Entry</span>
    </div>
  </div>
  <div style='text-align:right'>
    <div style='font-family:IBM Plex Mono;font-size:1.1rem;color:#3b82f6;font-weight:500'>{datetime.now().strftime("%b %Y")}</div>
    <div style='font-size:11px;color:#475569;margin-top:3px'>{datetime.now().strftime("%d %B")} · NSE</div>
  </div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LIVE SIGNALS
# ══════════════════════════════════════════════════════════════════════════════
if "Signals" in page:
    buy_df=_sig("buy"); sell_df=_sig("sell"); hold_df=_sig("hold")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("BUY Signals",  len(buy_df),  help="Enter at next month open")
    c2.metric("SELL Signals", len(sell_df), help="Exit at next month open")
    c3.metric("HOLD",         len(hold_df))
    c4.metric("Universe Scanned", len(buy_df)+len(sell_df)+len(hold_df))
    st.divider()

    if len(buy_df)+len(sell_df)+len(hold_df)==0:
        st.markdown("""
        <div class='card card-yellow'>
          <div style='font-size:14px;font-weight:600;color:#f59e0b;margin-bottom:6px'>⏳ Signals not yet generated</div>
          <div style='font-size:13px;color:#94a3b8;line-height:1.9'>
            Monthly signals auto-generate on the <strong style='color:#e2e8f0'>last Friday of each month at 9pm IST</strong> via GitHub Actions.<br>
            To generate now: run <code style='background:#0f172a;padding:2px 8px;border-radius:4px;color:#3b82f6'>python live_signals_monthly.py</code>
            on your laptop and push the CSV files to GitHub.
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div class='ptitle'>🟢 Buy Signals</div>", unsafe_allow_html=True)
    st.markdown("<div class='psub'>Enter at NEXT MONTH OPEN · All 3 phases must be satisfied · Ranked by RSI14</div>", unsafe_allow_html=True)
    if buy_df.empty:
        st.markdown("<div class='card card-green'><span style='color:#475569;font-size:13px'>No BUY signals — all 3 phases (Deep Correction + Structural Recovery + RSI Crossover) must trigger simultaneously.</span></div>", unsafe_allow_html=True)
    else:
        st.dataframe(buy_df, use_container_width=True, hide_index=True,
            column_config={
                "Close":    st.column_config.NumberColumn("Close ₹",   format="₹%.2f"),
                "SSF50":    st.column_config.NumberColumn("SSF50 ₹",   format="₹%.2f"),
                "SSF200":   st.column_config.NumberColumn("SSF200 ₹",  format="₹%.2f"),
                "SSF250":   st.column_config.NumberColumn("SSF250 ₹",  format="₹%.2f"),
                "RSI14":    st.column_config.ProgressColumn("RSI14",   min_value=0, max_value=100, format="%.1f"),
                "RSI_MA14": st.column_config.NumberColumn("RSI_MA14",  format="%.1f"),
                "Date":     st.column_config.TextColumn("Month"),
            })
    st.divider()

    st.markdown("<div class='ptitle'>🔴 Sell Signals</div>", unsafe_allow_html=True)
    st.markdown("<div class='psub'>Exit at NEXT MONTH OPEN · RSI14 crossed below RSI_MA14 OR Close dropped below SSF200</div>", unsafe_allow_html=True)
    if sell_df.empty:
        st.markdown("<div class='card card-red'><span style='color:#475569;font-size:13px'>No SELL signals this month.</span></div>", unsafe_allow_html=True)
    else:
        st.dataframe(sell_df, use_container_width=True, hide_index=True,
            column_config={
                "Close":    st.column_config.NumberColumn("Close ₹",  format="₹%.2f"),
                "SSF200":   st.column_config.NumberColumn("SSF200 ₹", format="₹%.2f"),
                "RSI14":    st.column_config.ProgressColumn("RSI14",  min_value=0, max_value=100, format="%.1f"),
                "RSI_MA14": st.column_config.NumberColumn("RSI_MA14", format="%.1f"),
            })
    with st.expander(f"⚪ Hold List — {len(hold_df)} stocks"):
        if not hold_df.empty: st.dataframe(hold_df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
elif "Portfolio" in page:
    st.markdown("<div class='ptitle'>💼 Portfolio</div>", unsafe_allow_html=True)
    st.markdown("<div class='psub'>Live P&L · Monthly system positions · Equal-weight allocation</div>", unsafe_allow_html=True)
    pos=_pos()
    if not pos.empty:
        prices=_prices(pos["Ticker"].tolist()); pos=pos.copy()
        pos["Current"]=pos["Ticker"].map(prices)
        pos["P&L %"]=((pos["Current"]-pos["Entry_Price"])/pos["Entry_Price"]*100).round(2)
        pos["P&L ₹"]=((pos["Current"]-pos["Entry_Price"])*pos["Shares"]).round(2)
        pos["Value"]=(pos["Current"]*pos["Shares"]).round(2)
        inv=(pos["Entry_Price"]*pos["Shares"]).sum(); val=pos["Value"].sum(); pnl=pos["P&L ₹"].sum()
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Positions",len(pos)); c2.metric("Value",_fmt(val))
        c3.metric("P&L",_fmt(pnl),delta=f"{pnl/inv*100:+.2f}%" if inv>0 else None)
        c4.metric("Invested",_fmt(inv))
        st.divider()
        st.dataframe(pos, use_container_width=True, hide_index=True,
            column_config={
                "Entry_Price": st.column_config.NumberColumn("Entry ₹",   format="₹%.2f"),
                "Current":     st.column_config.NumberColumn("Current ₹", format="₹%.2f"),
                "Value":       st.column_config.NumberColumn("Value ₹",   format="₹%.0f"),
                "P&L %":       st.column_config.NumberColumn("P&L %",     format="%+.2f%%"),
                "P&L ₹":       st.column_config.NumberColumn("P&L ₹",     format="₹%+.0f"),
            })
    else:
        st.markdown("<div class='card'>No positions yet. Add below or import from Upstox.</div>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<div style='font-size:14px;font-weight:600;color:#f1f5f9;margin-bottom:12px'>✏️ Manage Positions</div>", unsafe_allow_html=True)
    action=st.radio("",["➕ Add","❌ Remove"],horizontal=True)
    c1,c2,c3,c4,c5=st.columns([2,1.5,1.5,1.5,2])
    ticker=c1.text_input("Ticker",placeholder="RELIANCE.NS").upper().strip()
    shares=c2.number_input("Shares",min_value=0.0,step=1.0)
    price=c3.number_input("Entry ₹",min_value=0.0,step=0.5)
    edate=c4.date_input("Date",value=date.today())
    source=c5.selectbox("Source",["Manual","Upstox","Zerodha","Groww","Other"])
    notes=st.text_input("Notes",placeholder="e.g. Monthly BUY signal Feb-2026")
    if st.button("Submit"):
        if ticker:
            pos=_pos()
            if "Add" in action:
                new=pd.DataFrame([{"Ticker":ticker,"Shares":shares,"Entry_Price":price,
                                   "Entry_Date":str(edate),"Source":source,"Notes":notes}])
                pos=pd.concat([pos,new],ignore_index=True); st.success(f"Added {ticker}")
            else:
                pos=pos[pos["Ticker"]!=ticker]; st.warning(f"Removed {ticker}")
            _save_pos(pos); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# WATCHLIST
# ══════════════════════════════════════════════════════════════════════════════
elif "Watchlist" in page:
    st.markdown("<div class='ptitle'>👁️ Watchlist</div>", unsafe_allow_html=True)
    st.markdown("<div class='psub'>Monitor stocks with live prices and monthly signal status</div>", unsafe_allow_html=True)
    wl=_wl()
    c1,c2=st.columns([3,1])
    nt=c1.text_input("Add ticker",placeholder="TITAN.NS").upper().strip()
    if c2.button("➕ Add") and nt and nt not in wl:
        wl.append(nt); _save_wl(wl); st.rerun()
    if not wl:
        st.markdown("<div class='card'>Watchlist empty. Add tickers above.</div>", unsafe_allow_html=True)
    else:
        prices=_prices(wl)
        all_sig=pd.concat([_sig("buy"),_sig("sell"),_sig("hold")],ignore_index=True)
        rows=[]
        for t in wl:
            sig="—"
            if not all_sig.empty and "Ticker" in all_sig.columns:
                m=all_sig[all_sig["Ticker"]==t]
                if not m.empty: sig=m.iloc[0].get("Signal","—")
            rows.append({"Ticker":t,"Price ₹":prices.get(t),"Monthly Signal":sig})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
            column_config={"Price ₹":st.column_config.NumberColumn("Price ₹",format="₹%.2f")})
        rm=st.selectbox("Remove",["—"]+wl)
        if st.button("Remove") and rm!="—":
            wl.remove(rm); _save_wl(wl); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY RULES
# ══════════════════════════════════════════════════════════════════════════════
elif "Strategy" in page:
    st.markdown("<div class='ptitle'>📋 Monthly Strategy Rules</div>", unsafe_allow_html=True)
    st.markdown("<div class='psub'>Complete entry & exit criteria — 3-phase structural reversal system</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='card card-blue'>
      <div style='font-size:15px;font-weight:700;color:#f1f5f9;margin-bottom:4px'>Monthly Structural Reversal System</div>
      <div style='font-size:11px;color:#475569;margin-bottom:18px'>Timeframe: Monthly close · Universe: Nifty 500 — Fundamentally filtered · Ehlers SSF indicators</div>

      <div style='font-size:12px;font-weight:700;color:#10b981;letter-spacing:0.5px;margin-bottom:12px'>🟢 ENTRY — All 3 phases required simultaneously</div>

      <div style='background:#080b10;border-radius:8px;padding:14px 18px;margin-bottom:8px'>
        <div style='font-size:11px;font-weight:700;color:#3b82f6;letter-spacing:1px;margin-bottom:8px'>PHASE 1 — Deep Correction (within last 12 months)</div>
        <div style='font-family:IBM Plex Mono;font-size:12px;color:#94a3b8;line-height:2'>
          Close &lt; SSF200 &nbsp;<span style='color:#475569'>AND</span>&nbsp; Close &lt; SSF250<br>
          <span style='color:#475569;font-size:11px'>← Stock must have been deeply corrected below both long-term SSF filters</span>
        </div>
      </div>

      <div style='background:#080b10;border-radius:8px;padding:14px 18px;margin-bottom:8px'>
        <div style='font-size:11px;font-weight:700;color:#3b82f6;letter-spacing:1px;margin-bottom:8px'>PHASE 2 — Structural Recovery (current month)</div>
        <div style='font-family:IBM Plex Mono;font-size:12px;color:#94a3b8;line-height:2'>
          Close &gt; SSF50 &nbsp;<span style='color:#475569'>AND</span>&nbsp; SSF50 &gt; SSF200<br>
          <span style='color:#475569;font-size:11px'>← Price must be above short-term filter, and trend must be turning up</span>
        </div>
      </div>

      <div style='background:#080b10;border-radius:8px;padding:14px 18px;margin-bottom:8px'>
        <div style='font-size:11px;font-weight:700;color:#3b82f6;letter-spacing:1px;margin-bottom:8px'>PHASE 3 — Momentum Confirmation (current month)</div>
        <div style='font-family:IBM Plex Mono;font-size:12px;color:#94a3b8;line-height:2.4'>
          Previous month: RSI14 &lt; RSI_MA14<br>
          Current month:&nbsp; RSI14 &gt; RSI_MA14 &nbsp;<span style='color:#475569'>← RSI crosses above its MA</span><br>
          <span style='color:#f59e0b;font-weight:600'>AND RSI14 &gt; 0 AND RSI_MA14 &gt; 0</span>
        </div>
      </div>

      <div style='background:#052e16;border-radius:6px;padding:9px 16px;margin-bottom:20px;font-size:12px;color:#10b981;font-family:IBM Plex Mono;font-weight:500'>
        ⚡ Execution: Enter at NEXT MONTH OPEN (no lookahead bias)
      </div>

      <div style='font-size:12px;font-weight:700;color:#ef4444;letter-spacing:0.5px;margin-bottom:10px'>🔴 EXIT — Either condition triggers exit</div>
      <div style='background:#080b10;border-radius:8px;padding:14px 18px;margin-bottom:8px;font-family:IBM Plex Mono;font-size:12px;color:#94a3b8;line-height:2.4'>
        <span style='color:#ef4444;font-weight:700'>A.</span> RSI14 crosses BELOW RSI_MA14<br>
        &nbsp;&nbsp;&nbsp;&nbsp;<span style='color:#475569'>(momentum deteriorating)</span><br>
        <span style='color:#ef4444;font-weight:700'>B.</span> Close &lt; SSF200<br>
        &nbsp;&nbsp;&nbsp;&nbsp;<span style='color:#475569'>(structural breakdown — price falls back below long-term filter)</span>
      </div>
      <div style='background:#1c0505;border-radius:6px;padding:9px 16px;font-size:12px;color:#ef4444;font-family:IBM Plex Mono;font-weight:500'>
        ⚡ Execution: Exit at NEXT MONTH OPEN
      </div>
    </div>

    <div class='card card-blue'>
      <div style='font-size:13px;font-weight:600;color:#3b82f6;margin-bottom:12px'>📐 Indicators — Monthly System (Ehlers SSF)</div>
      <div style='font-family:IBM Plex Mono;font-size:12px;color:#64748b;line-height:2.4'>
        <span style='color:#94a3b8'>SSF50</span> &nbsp;&nbsp;= Ehlers 2-pole Super Smoother Filter, period=50 months<br>
        <span style='color:#94a3b8'>SSF200</span> &nbsp;= Ehlers 2-pole Super Smoother Filter, period=200 months<br>
        <span style='color:#94a3b8'>SSF250</span> &nbsp;= Ehlers 2-pole Super Smoother Filter, period=250 months<br>
        <span style='color:#94a3b8'>RSI14</span> &nbsp;&nbsp;= Wilder RSI, 14-period, on monthly closes<br>
        <span style='color:#94a3b8'>RSI_MA14</span> = Simple Moving Average of RSI14, 14-period
      </div>
    </div>

    <div class='card'>
      <div style='font-size:13px;font-weight:600;color:#f1f5f9;margin-bottom:12px'>⚖️ Portfolio Rules</div>
      <div style='display:flex;flex-wrap:wrap;gap:6px'>
        <span class='tag tag-slate'>Max 10 positions</span>
        <span class='tag tag-slate'>Equal weight allocation</span>
        <span class='tag tag-slate'>Rank by RSI14 if &gt;10 signals</span>
        <span class='tag tag-slate'>Capital reinvested after exits</span>
        <span class='tag tag-slate'>0.2% slippage per trade</span>
        <span class='tag tag-slate'>0.1% brokerage per trade</span>
      </div>
    </div>

    <div class='card'>
      <div style='font-size:13px;font-weight:600;color:#f1f5f9;margin-bottom:12px'>🔍 Fundamental Filter (Monthly Master List rebuild)</div>
      <div style='display:flex;flex-wrap:wrap;gap:6px'>
        <span class='tag tag-yellow'>Market Cap &gt; ₹5000 Cr</span>
        <span class='tag tag-yellow'>EPS &gt; 0</span>
        <span class='tag tag-yellow'>EPS CAGR 5Y &gt; 0</span>
        <span class='tag tag-yellow'>Revenue CAGR 3Y &gt; 0</span>
        <span class='tag tag-yellow'>Dividend Yield &gt; 0</span>
        <span class='tag tag-yellow'>ROE &gt; 12%</span>
        <span class='tag tag-yellow'>OPM &gt; 10%</span>
        <span class='tag tag-yellow'>Free Cash Flow &gt; 0</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# XIRR
# ══════════════════════════════════════════════════════════════════════════════
elif "XIRR" in page:
    st.markdown("<div class='ptitle'>💰 XIRR Calculator</div>", unsafe_allow_html=True)
    st.markdown("<div class='psub'>Annualised return on irregular cash flows · Investments = negative · Receipts = positive</div>", unsafe_allow_html=True)
    if "cf_m" not in st.session_state:
        st.session_state.cf_m=[{"date":date(2024,1,1),"amount":-100000.0,"label":"Initial investment"},
                                {"date":date.today(),"amount":150000.0,"label":"Current value"}]
    for i,row in enumerate(st.session_state.cf_m):
        c1,c2,c3,c4=st.columns([2,2,3,1])
        st.session_state.cf_m[i]["date"]=c1.date_input(f"Date {i+1}",value=row["date"],key=f"md{i}")
        st.session_state.cf_m[i]["amount"]=c2.number_input(f"Amount {i+1}",value=float(row["amount"]),key=f"ma{i}",step=1000.0)
        st.session_state.cf_m[i]["label"]=c3.text_input(f"Label {i+1}",value=row.get("label",""),key=f"ml{i}")
        if c4.button("✕",key=f"mdel{i}") and len(st.session_state.cf_m)>2:
            st.session_state.cf_m.pop(i); st.rerun()
    if st.button("➕ Add row"):
        st.session_state.cf_m.append({"date":date.today(),"amount":0.0,"label":""}); st.rerun()
    st.divider()
    if st.button("Calculate XIRR →",type="primary"):
        res=_xirr([(r["date"],r["amount"]) for r in st.session_state.cf_m])
        if res is not None:
            col="#10b981" if res>0 else "#ef4444"
            st.markdown(f"""<div class='card' style='text-align:center;padding:40px'>
              <div style='font-size:11px;color:#475569;letter-spacing:2px;text-transform:uppercase'>XIRR Result</div>
              <div style='font-size:4rem;font-weight:700;color:{col};font-family:IBM Plex Mono;margin:12px 0'>{res}%</div>
              <div style='font-size:13px;color:#475569'>per annum</div></div>""", unsafe_allow_html=True)
        else:
            st.error("Could not converge. Ensure at least one negative and one positive value.")

# ══════════════════════════════════════════════════════════════════════════════
# BACKTEST
# ══════════════════════════════════════════════════════════════════════════════
elif "Backtest" in page:
    st.markdown("<div class='ptitle'>📊 Monthly Backtest Results</div>", unsafe_allow_html=True)
    st.markdown("<div class='psub'>2010 → Present · 3-phase structural reversal strategy · No lookahead bias · 0.2% slippage + 0.1% brokerage</div>", unsafe_allow_html=True)
    if Path("backtest_results.png").exists(): st.image("backtest_results.png",use_column_width=True)
    else: st.markdown("<div class='card'>Run <code>python backtest_monthly.py</code> to generate backtest chart.</div>",unsafe_allow_html=True)
    if Path("backtest_metrics.csv").exists():
        m=pd.read_csv("backtest_metrics.csv").set_index("Metric")["Value"]
        c1,c2,c3,c4=st.columns(4)
        c1.metric("CAGR",f"{m.get('CAGR_%','—')}%")
        c2.metric("Max Drawdown",f"{m.get('Max_Drawdown_%','—')}%")
        c3.metric("Sharpe",m.get("Sharpe_Ratio","—"))
        c4.metric("Win Rate",f"{m.get('Win_Rate_%','—')}%")
        c1.metric("Avg Hold (months)",m.get("Avg_Hold_Months","—"))
        c2.metric("Exposure",f"{m.get('Exposure_%','—')}%")
        c3.metric("Total Trades",m.get("Total_Trades","—"))
        c4.metric("Final Capital",f"₹{float(m.get('Final_Capital_INR',0)):,.0f}")
    if Path("trades_log.csv").exists():
        st.divider()
        st.markdown("<div style='font-size:13px;font-weight:600;color:#f1f5f9;margin-bottom:8px'>Trade Log</div>",unsafe_allow_html=True)
        st.dataframe(pd.read_csv("trades_log.csv"),use_container_width=True,hide_index=True,
            column_config={"Gain_pct":st.column_config.NumberColumn("Gain %",format="%+.2f%%"),
                           "Entry_Price":st.column_config.NumberColumn("Entry ₹",format="₹%.2f"),
                           "Exit_Price":st.column_config.NumberColumn("Exit ₹",format="₹%.2f")})

# ══════════════════════════════════════════════════════════════════════════════
# UPSTOX
# ══════════════════════════════════════════════════════════════════════════════
elif "Upstox" in page:
    st.markdown("<div class='ptitle'>🔗 Upstox Integration</div>",unsafe_allow_html=True)
    st.markdown("<div class='psub'>Import your holdings directly from Upstox into the monthly portfolio tracker</div>",unsafe_allow_html=True)
    st.markdown("""<div class='card card-blue'>
      <div style='font-size:13px;font-weight:600;color:#3b82f6;margin-bottom:10px'>📥 How to export from Upstox</div>
      <div style='font-size:13px;color:#94a3b8;line-height:2.2'>
        1. Open Upstox app → <strong style='color:#e2e8f0'>Portfolio</strong> → <strong style='color:#e2e8f0'>Holdings</strong><br>
        2. Tap the <strong style='color:#e2e8f0'>Download / Export icon</strong> (top right corner)<br>
        3. Save the CSV file to your device<br>
        4. Upload it below ↓
      </div></div>""",unsafe_allow_html=True)
    uploaded=st.file_uploader("Upload Upstox Holdings CSV",type=["csv"])
    if uploaded:
        try:
            df=pd.read_csv(uploaded); st.dataframe(df.head(10),use_container_width=True,hide_index=True)
            cols={c.lower().strip():c for c in df.columns}; col_map={}
            for k,candidates in [("Ticker",["symbol","scrip","stock","instrument"]),
                                   ("Shares",["quantity","qty","shares"]),
                                   ("Entry_Price",["avg price","average price","buy price","avg. price"])]:
                for c in candidates:
                    if c in cols: col_map[k]=cols[c]; break
            if len(col_map)>=2:
                mapped=df.rename(columns={v:k for k,v in col_map.items()})
                if "Ticker" in mapped.columns:
                    mapped["Ticker"]=mapped["Ticker"].astype(str).apply(
                        lambda x: x.strip().upper()+".NS" if not x.strip().upper().endswith(".NS") else x.strip().upper())
                mapped["Entry_Date"]=str(date.today()); mapped["Source"]="Upstox"; mapped["Notes"]="Imported from Upstox"
                if st.button("✅ Import to Portfolio",type="primary"):
                    existing=_pos()
                    keep=["Ticker","Shares","Entry_Price","Entry_Date","Source","Notes"]
                    imp=mapped[[c for c in keep if c in mapped.columns]]
                    _save_pos(pd.concat([existing,imp],ignore_index=True))
                    st.success(f"✅ Imported {len(imp)} holdings!"); st.balloons()
            else:
                st.warning("Could not auto-map columns. Available: "+str(list(df.columns)))
        except Exception as e: st.error(f"Error reading file: {e}")
