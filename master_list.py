import logging, math
from datetime import datetime
from pathlib import Path
import pandas as pd
import yfinance as yf
from universe_loader import load_universe

logger = logging.getLogger(__name__)
MIN_MARKET_CAP_CR = 5000
MIN_ROE_PCT = 12.0
MIN_OPM_PCT = 10.0
MIN_CAGR_YEARS_EPS = 4
MIN_CAGR_YEARS_REV = 3
CRORE = 1e7
OUTPUT_DIR = Path("master_lists")

def _safe_get(info, *keys, default=None):
    for k in keys:
        v = info.get(k)
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            return v
    return default

def _cagr(e, s, y):
    try:
        if any(x is None or x <= 0 for x in [e, s]) or y <= 0:
            return None
        return (e / s) ** (1.0 / y) - 1.0
    except:
        return None

def _find_row(df, kws):
    if df is None or df.empty:
        return None
    for idx in df.index:
        s = str(idx).lower().replace(' ', '').replace('_', '')
        for kw in kws:
            if kw.lower().replace(' ', '') in s:
                row = df.loc[idx].dropna()
                if not row.empty:
                    return row.sort_index(ascending=False)
    return None

def evaluate_ticker(ticker):
    try:
        stk = yf.Ticker(ticker)
        info = stk.info or {}
        mc = _safe_get(info, "marketCap")
        if not mc or mc / CRORE <= MIN_MARKET_CAP_CR:
            return None
        eps = _safe_get(info, "trailingEps", "epsTrailingTwelveMonths")
        if not eps or eps <= 0:
            return None
        dy = _safe_get(info, "dividendYield") or 0
        dr = _safe_get(info, "dividendRate") or 0
        if dy <= 0 and dr <= 0:
            return None
        opm = _safe_get(info, "operatingMargins", "ebitdaMargins")
        if opm is None or opm * 100 <= MIN_OPM_PCT:
            return None
        try:
            inc = stk.financials
        except:
            inc = None
        try:
            cf = stk.cashflow
        except:
            cf = None
        rev = _find_row(inc, ['totalrevenue', 'total revenue', 'operatingrevenue'])
        if rev is None or len(rev) < MIN_CAGR_YEARS_REV:
            return None
        rc = _cagr(float(rev.iloc[0]), float(rev.iloc[MIN_CAGR_YEARS_REV - 1]), MIN_CAGR_YEARS_REV - 1)
        if not rc or rc <= 0:
            return None
        ni = _find_row(inc, ['netincome', 'net income', 'netincomefromcontinuingoperation'])
        if ni is None or len(ni) < MIN_CAGR_YEARS_EPS:
            return None
        ni_vals = [float(v) for v in ni.values[:MIN_CAGR_YEARS_EPS] if float(v) > 0]
        if len(ni_vals) < 2:
            return None
        ec = _cagr(ni_vals[0], ni_vals[-1], len(ni_vals) - 1)
        if not ec or ec <= 0:
            return None
        fcf_row = _find_row(cf, ['freecashflow', 'free cash flow'])
        if fcf_row is not None:
            fcf = float(fcf_row.iloc[0])
        else:
            ocf = _find_row(cf, ['operatingcashflow', 'cashfromoperations'])
            cap = _find_row(cf, ['capitalexpenditure', 'capital expenditure'])
            if ocf is None:
                return None
            ov = float(ocf.iloc[0])
            cv = float(cap.iloc[0]) if cap is not None else 0
            fcf = ov + cv if cv < 0 else ov - cv
        if fcf <= 0:
            return None
        roe = _safe_get(info, "returnOnEquity")
        if roe is None:
            try:
                bal = stk.balance_sheet
                tbv = _find_row(bal, ['tangiblebookvalue', 'tangible book value',
                                       'commonstockequity', 'stockholdersequity', 'totalequity'])
                if tbv is not None and float(tbv.iloc[0]) > 0:
                    roe = float(ni.iloc[0]) / float(tbv.iloc[0])
            except:
                roe = None
        if roe is None:
            roa = _safe_get(info, "returnOnAssets")
            if roa is not None:
                roe = roa * 1.5
        if roe is None or roe * 100 <= MIN_ROE_PCT:
            return None
        return {
            "Ticker": ticker,
            "MarketCap_Cr": round(mc / CRORE, 2),
            "EPS_TTM": round(eps, 4),
            "NI_CAGR_4Y_pct": round(ec * 100, 2),
            "Rev_CAGR_3Y_pct": round(rc * 100, 2),
            "DivYield_pct": round(dy * 100, 4),
            "ROE_pct": round(roe * 100, 2),
            "OPM_pct": round(opm * 100, 2),
            "FCF_Cr": round(fcf / CRORE, 2),
        }
    except Exception as ex:
        logger.debug("Skip %s: %s", ticker, ex)
        return None

def build_master_list(tickers=None, save=True, as_of=None):
    if tickers is None:
        tickers = load_universe()
    logger.info("Screening %d tickers...", len(tickers))
    qualified = []
    for i, t in enumerate(tickers, 1):
        r = evaluate_ticker(t)
        if r:
            qualified.append(r)
            logger.info("[%d/%d] YES %s", i, len(tickers), t)
        else:
            logger.debug("[%d/%d] NO  %s", i, len(tickers), t)
    df = pd.DataFrame(qualified)
    if df.empty:
        logger.warning("Master list is empty.")
        return df
    df = df.sort_values("MarketCap_Cr", ascending=False).reset_index(drop=True)
    if save:
        OUTPUT_DIR.mkdir(exist_ok=True)
        stamp = (as_of or datetime.today()).strftime("%Y_%m")
        out = OUTPUT_DIR / f"master_list_{stamp}.csv"
        df.to_csv(out, index=False)
        logger.info("Saved -> %s (%d stocks)", out, len(df))
    return df

def load_master_list(year, month):
    p = OUTPUT_DIR / f"master_list_{year:04d}_{month:02d}.csv"
    return pd.read_csv(p) if p.exists() else None

def get_latest_master_list():
    f = sorted(OUTPUT_DIR.glob("master_list_*.csv"))
    return pd.read_csv(f[-1]) if f else None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s",
                        datefmt="%H:%M:%S")
    print("\nBuilding master list...\n")
    df = build_master_list()
    if not df.empty:
        print(f"\n{len(df)} stocks qualified:")
        print(df.to_string(index=False))
    else:
        print("No stocks qualified.")
