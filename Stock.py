# NIFTY50 Mini-Terminal (Educational) – Streamlit + yfinance
# -----------------------------------------------------------
# Requirements (install once):
#   pip install streamlit yfinance pandas numpy
# Run:
#   streamlit run app.py

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date, timedelta

st.set_page_config(page_title="📊 NIFTY50 Mini-Terminal (2023)", layout="wide")

# -----------------------------
# Fixed Date Range for 2023
# -----------------------------
START = date(2023, 1, 1)
# yfinance's 'end' is exclusive; use first day of 2024 to include all of 2023
END_EXCLUSIVE = date(2024, 1, 1)

# -----------------------------
# Universe
# -----------------------------
NIFTY_SYMBOL = "^NSEI"  # NIFTY 50 index on Yahoo
NIFTY50 = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","LICI.NS","ITC.NS",
    "BHARTIARTL.NS","SBIN.NS","LT.NS","HINDUNILVR.NS","KOTAKBANK.NS","BAJFINANCE.NS",
    "HCLTECH.NS","AXISBANK.NS","MARUTI.NS","SUNPHARMA.NS","ASIANPAINT.NS","TITAN.NS",
    "ONGC.NS","ULTRACEMCO.NS","WIPRO.NS","NTPC.NS","ADANIENT.NS","ADANIPORTS.NS",
    "POWERGRID.NS","HDFCLIFE.NS","LTIM.NS","TATASTEEL.NS","M&M.NS","NESTLEIND.NS",
    "BAJAJFINSV.NS","JSWSTEEL.NS","BRITANNIA.NS","TECHM.NS","COALINDIA.NS","HEROMOTOCO.NS",
    "CIPLA.NS","HINDALCO.NS","DRREDDY.NS","SBILIFE.NS","APOLLOHOSP.NS","DIVISLAB.NS",
    "EICHERMOT.NS","TATACONSUM.NS","BPCL.NS","GRASIM.NS","BAJAJ-AUTO.NS","HAVELLS.NS",
    "BAJAJHLDNG.NS"
]

# -----------------------------
# Helpers
# -----------------------------
@st.cache_data(show_spinner=False)
def fetch_prices(tickers, start: date, end_exclusive: date, interval="1d", auto_adjust=True):
    """Return dict[ticker] -> tidy DataFrame with OHLCV.
    Uses yfinance.download; ensures index is Date and ascending.
    """
    if isinstance(tickers, str):
        tickers = [tickers]
    df = yf.download(
        tickers=tickers,
        start=start,
        end=end_exclusive,  # exclusive
        interval=interval,
        group_by="ticker",
        auto_adjust=auto_adjust,
        threads=True,
        progress=False,
    )
    out = {}
    if len(tickers) == 1:
        t = tickers[0]
        # Single ticker sometimes returns single-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.droplevel(0)
        tidy = df.reset_index().sort_values("Date").rename_axis(None, axis=1)
        out[t] = tidy
    else:
        for t in tickers:
            if t in df.columns.get_level_values(0):
                tidy = df[t].reset_index().sort_values("Date").rename_axis(None, axis=1)
                out[t] = tidy
    return out


def add_indicators(df: pd.DataFrame, ma_windows=(20, 50), vol_window=20) -> pd.DataFrame:
    d = df.copy()
    d["Returns"] = d["Close"].pct_change()
    # Moving averages
    for w in ma_windows:
        d[f"SMA{w}"] = d["Close"].rolling(w).mean()
    # Drawdown
    d["CumMax"] = d["Close"].cummax()
    d["Drawdown"] = (d["Close"] - d["CumMax"]) / d["CumMax"]
    # Rolling Volatility (annualized)
    d["VolAnnual"] = d["Returns"].rolling(vol_window).std() * np.sqrt(252)
    return d


def norm_to_first(series: pd.Series) -> pd.Series:
    if series.empty or series.iloc[0] == 0 or pd.isna(series.iloc[0]):
        return series * np.nan
    return series / series.iloc[0]

# -----------------------------
# Sidebar Controls
# -----------------------------
st.sidebar.title("Controls")

# 1) Ticker selection from NIFTY50
ticker = st.sidebar.selectbox("Select NIFTY 50 Stock", sorted(NIFTY50))

# 2) Indicator parameters via dropdowns
ma_choice = st.sidebar.multiselect(
    "Moving Averages (select 1–3)",
    options=[10, 20, 30, 50, 100, 200],
    default=[20, 50],
    help="Choose the SMA windows to overlay on price chart."
)
if len(ma_choice) == 0:
    ma_choice = [20]

vol_window = st.sidebar.selectbox(
    "Volatility Window (days)", options=[10, 20, 30, 60], index=1,
    help="Rolling window used to compute annualized volatility."
)

# 3) Chart toggles
chart_choices = st.sidebar.multiselect(
    "Show Charts",
    options=["Price + MAs", "Drawdown", "Rolling Volatility", "Excess Return vs NIFTY"],
    default=["Price + MAs", "Drawdown", "Rolling Volatility"],
)

st.sidebar.info("Data fixed to 01 Jan 2023 – 31 Dec 2023 (EOD)")

# -----------------------------
# Fetch Data (selected stock + NIFTY)
# -----------------------------
with st.spinner("Fetching prices from Yahoo Finance…"):
    data = fetch_prices([ticker, NIFTY_SYMBOL], START, END_EXCLUSIVE)

if ticker not in data or NIFTY_SYMBOL not in data:
    st.error("Could not fetch data. Try another ticker or check your internet connection.")
    st.stop()

stock = data[ticker].copy()
nifty = data[NIFTY_SYMBOL].copy()

# Safety: ensure required columns exist
required_cols = {"Date", "Close"}
if not required_cols.issubset(stock.columns) or not required_cols.issubset(nifty.columns):
    st.error("Downloaded data is missing required columns. Please retry.")
    st.stop()

# Add indicators
stock = add_indicators(stock, ma_windows=tuple(ma_choice), vol_window=vol_window)

# Join NIFTY (for excess returns)
stock = stock.merge(
    nifty[["Date", "Close"]].rename(columns={"Close": "NIFTY"}),
    on="Date", how="left"
)
stock["NIFTY_Returns"] = stock["NIFTY"].pct_change()
stock["Excess_Returns"] = stock["Returns"] - stock["NIFTY_Returns"]
stock["Excess_Cum"] = stock["Excess_Returns"].fillna(0).cumsum()

# -----------------------------
# Header & Summary
# -----------------------------
st.title("📊 NIFTY50 Stock Mini-Terminal — 2023")
st.caption("Educational dashboard pulling EOD data from Yahoo Finance via yfinance.")

# Summary KPIs
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("First Date", stock["Date"].min().strftime("%d-%b-%Y"))
with c2:
    st.metric("Last Date", stock["Date"].max().strftime("%d-%b-%Y"))
with c3:
    perf = (stock["Close"].iloc[-1] / stock["Close"].iloc[0] - 1.0) * 100
    st.metric("Price Change (2023)", f"{perf:,.2f}%")
with c4:
    max_dd = stock["Drawdown"].min() * 100
    st.metric("Max Drawdown", f"{max_dd:,.2f}%")

st.divider()

# -----------------------------
# CHARTS
# -----------------------------
# 1) Price + MAs
if "Price + MAs" in chart_choices:
    st.subheader(f"{ticker} — Price with Moving Averages")
    show_cols = ["Close"] + [f"SMA{w}" for w in ma_choice]
    price_df = stock.set_index("Date")[show_cols]
    st.line_chart(price_df, use_container_width=True)

# 2) Drawdown
if "Drawdown" in chart_choices:
    st.subheader("Drawdown (relative to running peak)")
    st.line_chart(stock.set_index("Date")["Drawdown"], use_container_width=True)

# 3) Rolling Volatility
if "Rolling Volatility" in chart_choices:
    st.subheader(f"Rolling Volatility (Annualized, window={vol_window}d)")
    st.line_chart(stock.set_index("Date")["VolAnnual"], use_container_width=True)

# 4) Excess Return vs NIFTY
if "Excess Return vs NIFTY" in chart_choices:
    st.subheader("Excess Cumulative Return vs NIFTY (Stock − Index)")
    st.line_chart(stock.set_index("Date")["Excess_Cum"], use_container_width=True)

st.divider()

# -----------------------------
# Data View & Downloads
# -----------------------------
with st.expander("Data Preview (first 50 rows)"):
    st.dataframe(stock.head(50), use_container_width=True)

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        label="Download Enriched Stock Data (CSV)",
        data=stock.to_csv(index=False),
        file_name=f"{ticker.replace('.','_')}_2023_enriched.csv",
        mime="text/csv",
    )
with c2:
    # Provide a simple normalized comparison vs NIFTY for quick teaching
    comp = pd.DataFrame({
        "Date": stock["Date"],
        f"{ticker}_Norm": norm_to_first(stock["Close"]),
        "NIFTY_Norm": norm_to_first(stock["NIFTY"]) if "NIFTY" in stock else np.nan,
    }).set_index("Date")
    st.caption("Normalized price (start=1.0) — quick comparison vs NIFTY")
    st.line_chart(comp, use_container_width=True)
