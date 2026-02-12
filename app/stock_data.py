"""Fetch historical stock data using yfinance."""
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

def _fetch_one(symbol, days=90):
    """Fetch one symbol; more reliable than batch when market is closed or for few symbols."""
    sym = symbol.upper()
    try:
        # period includes up to last available trading day (works on weekends)
        data = yf.download(
            sym,
            period="3mo",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception:
        return None
    if data is None or data.empty or "Close" not in data.columns:
        return None
    close = data["Close"].dropna()
    if len(close) < 2:
        return None
    return close

def fetch_prices(symbols, days=60):
    """Fetch closing prices for the last several trading days. Works outside market hours."""
    if not symbols:
        return {}
    if isinstance(symbols, str):
        symbols = [symbols]
    symbols = [s.upper() for s in symbols]
    result = {}

    # Try batch first for efficiency
    end = datetime.now()
    start = end - timedelta(days=days + 40)
    try:
        data = yf.download(
            symbols,
            start=start.strftime("%Y-%m-%d"),
            end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
            progress=False,
            group_by="ticker",
            auto_adjust=True,
            threads=False,
        )
    except Exception:
        data = None

    if data is not None and not data.empty:
        if len(symbols) == 1:
            if isinstance(data.columns, pd.MultiIndex):
                if symbols[0] in data.columns.get_level_values(0):
                    result[symbols[0]] = data[symbols[0]]["Close"].dropna()
            elif "Close" in data.columns:
                result[symbols[0]] = data["Close"].dropna()
        else:
            for sym in symbols:
                if isinstance(data.columns, pd.MultiIndex) and sym in data.columns.get_level_values(0):
                    ser = data[sym]["Close"].dropna()
                    if len(ser) >= 2:
                        result[sym] = ser

    # Fallback: fetch each symbol individually (more reliable on weekends / outside market)
    for sym in symbols:
        if sym not in result or len(result[sym]) < 2:
            one = _fetch_one(sym, days=days)
            if one is not None:
                result[sym] = one

    return result

def compute_returns(series: pd.Series, periods=1):
    """Compute period-over-period return (e.g. 1 = one-day return)."""
    if series is None or len(series) < periods + 1:
        return None
    return (series.iloc[-1] / series.iloc[-1 - periods] - 1.0) * 100

def get_momentum_metrics(series: pd.Series):
    """Return dict with 1d, 5d, 20d returns and recent trend."""
    if series is None or len(series) < 2:
        return None
    return {
        "return_1d": compute_returns(series, 1),
        "return_5d": compute_returns(series, 5) if len(series) >= 6 else None,
        "return_20d": compute_returns(series, 20) if len(series) >= 21 else None,
        "last_close": float(series.iloc[-1]),
    }
