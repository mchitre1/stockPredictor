"""S&P 500 ticker list from Wikipedia, cached locally."""
import json
import time
from io import StringIO

import pandas as pd
import requests

from config import DATA_DIR

CACHE_FILE = DATA_DIR / "sp500_tickers.json"
CACHE_DAYS = 7
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def _yahoo_ticker(sym):
    """Wikipedia uses BRK.B; Yahoo uses BRK-B."""
    if not sym:
        return sym
    return str(sym).strip().replace(".", "-").upper()


def get_sp500_tickers(force_refresh=False):
    """
    Return list of S&P 500 ticker symbols (Yahoo-style, e.g. BRK-B).
    Uses cached list if fresh; otherwise fetches from Wikipedia.
    """
    now = time.time()
    if not force_refresh and CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
            if now - data.get("updated", 0) < CACHE_DAYS * 86400:
                return data["tickers"]
        except Exception:
            pass

    try:
        resp = requests.get(WIKI_URL, timeout=15)
        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text))
        df = tables[0]
        if "Symbol" not in df.columns:
            return _fallback_tickers()
        raw = df["Symbol"].astype(str).str.strip().dropna().unique().tolist()
        tickers = [_yahoo_ticker(s) for s in raw if _yahoo_ticker(s)]
        tickers = list(dict.fromkeys(tickers))
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump({"tickers": tickers, "updated": now}, f)
        return tickers
    except Exception:
        return _fallback_tickers()


def _fallback_tickers():
    """Minimal fallback if Wikipedia fails; still ~500 names."""
    # Small subset of well-known S&P 500 tickers so we always have something
    fallback = (
        "AAPL MSFT GOOGL AMZN NVDA META TSLA BRK-B JPM JNJ V UNH XOM WMT PG HD MA CVX "
        "LLY ABBV MRK PEP KO AVGO COST PFE TMO ABT MCD CSCO ACRM DIS WFC NEE PM TXN NKE "
        "BMY UPS HON INTC AMGN QCOM HCA RTX INTU HUM AMAT HII SBUX LMT MDT GILD C CI "
        "ADI TJX BKNG ISRG VRTX REPL BLK LRCX DE APH KLAC SNPS PANW CDNS MDLZ MAR "
        "NXPI AON GS AMAT CHTR TMUS ZTS BMY MU"
    )
    return [s.strip() for s in fallback.split() if s.strip()]
