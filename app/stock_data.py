"""Fetch historical stock data using yfinance."""
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd


def get_stock_name(symbol):
    """Return full company name for symbol, or symbol if unavailable."""
    try:
        t = yf.Ticker(symbol.upper())
        info = t.info
        return (info.get("longName") or info.get("shortName") or symbol).strip() or symbol
    except Exception:
        return symbol.upper()


def _fetch_one(symbol, days=90):
    """Fetch one symbol; more reliable than batch when market is closed or for few symbols."""
    sym = symbol.upper()
    try:
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


def get_chart_data(symbol, days=90):
    """Return list of {date: 'YYYY-MM-DD', close: float} for charting (full time series)."""
    sym = symbol.upper()
    end = datetime.now()
    start = end - timedelta(days=days + 30)
    try:
        data = yf.download(
            sym,
            start=start.strftime("%Y-%m-%d"),
            end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception:
        return []
    if data is None or data.empty:
        return []
    # Flatten: yfinance can return MultiIndex columns for single ticker
    if isinstance(data.columns, pd.MultiIndex):
        if sym in data.columns.get_level_values(0):
            close = data[sym]["Close"].copy()
        else:
            close = data["Close"].copy() if "Close" in data.columns else None
    else:
        close = data["Close"].copy() if "Close" in data.columns else None
    if close is None or close.empty:
        return []
    close = close.dropna().sort_index()
    if close.index.duplicated().any():
        close = close.groupby(level=0).last()
    # Build list by position so every value is scalar
    out = []
    for i in range(len(close)):
        d = close.index[i]
        v = close.iloc[i]
        try:
            date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        except Exception:
            date_str = str(d)[:10]
        try:
            scalar = float(v)
        except (TypeError, ValueError):
            scalar = float(pd.Series(v).iloc[0])
        out.append({"date": date_str, "close": round(scalar, 2)})
    return out


def fetch_prices_until(symbol, end_date_str, days=60):
    """Fetch price series for one symbol ending on or before end_date_str (for ML training)."""
    end = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
    start = end - timedelta(days=days + 30)
    try:
        data = yf.download(
            symbol.upper(),
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
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


def fetch_prices_batched(symbols, days=60, chunk_size=80):
    """
    Fetch prices for many symbols in chunks (for S&P 500). Returns same dict as fetch_prices.
    """
    if not symbols:
        return {}
    symbols = [s.upper() if isinstance(s, str) else s for s in symbols]
    result = {}
    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i : i + chunk_size]
        result.update(fetch_prices(chunk, days=days))
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


def volatility_annualized(series: pd.Series, window=10):
    """Annualized volatility (std of daily returns) in percent."""
    if series is None or len(series) < window + 1:
        return None
    rets = series.pct_change().dropna()
    if len(rets) < window:
        return None
    std = rets.iloc[-window:].std() * 100
    return float(std * (252 ** 0.5))


def get_ml_features(series: pd.Series):
    """
    Feature vector for ML model: return_1d, return_5d, return_20d, volatility_10d.
    Returns dict or None if insufficient data. Used for training and prediction.
    """
    if series is None or len(series) < 21:
        return None
    r1 = compute_returns(series, 1)
    r5 = compute_returns(series, 5)
    r20 = compute_returns(series, 20)
    vol = volatility_annualized(series, 10)
    if r1 is None and r5 is None and r20 is None:
        return None
    return {
        "return_1d": r1 if r1 is not None else 0.0,
        "return_5d": r5 if r5 is not None else 0.0,
        "return_20d": r20 if r20 is not None else 0.0,
        "volatility_10d": vol if vol is not None else 0.0,
    }
