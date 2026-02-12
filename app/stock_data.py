"""Fetch historical stock data using yfinance."""
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd

def fetch_prices(symbols, days=60):
    """Fetch closing prices for the last `days` trading days."""
    if not symbols:
        return {}
    end = datetime.now()
    start = end - timedelta(days=days + 30)  # buffer for weekends/holidays
    try:
        data = yf.download(
            symbols,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
            group_by="ticker",
            auto_adjust=True,
            threads=False,
        )
    except Exception:
        return {}
    result = {}
    if isinstance(symbols, str):
        symbols = [symbols]
    # Single ticker: yfinance may return flat columns or MultiIndex
    if len(symbols) == 1:
        sym = symbols[0].upper()
        if isinstance(data.columns, pd.MultiIndex):
            if sym in data.columns.get_level_values(0):
                result[sym] = data[sym]["Close"].dropna()
        elif "Close" in data.columns:
            result[sym] = data["Close"].dropna()
        return result
    for sym in symbols:
        sym = sym.upper()
        if isinstance(data.columns, pd.MultiIndex) and sym in data.columns.get_level_values(0):
            result[sym] = data[sym]["Close"].dropna()
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
