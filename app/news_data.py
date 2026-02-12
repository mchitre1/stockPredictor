"""Fetch market/company news (optional, requires Finnhub API key)."""
import os
from datetime import datetime, timedelta
import requests

FINNHUB_BASE = "https://finnhub.io/api/v1"

def get_company_news(api_key, symbol, days=3):
    """Fetch recent company news with headline, url, summary. Returns list of dicts or []."""
    if not api_key:
        return []
    to_date = datetime.now()
    from_date = to_date - timedelta(days=days)
    url = f"{FINNHUB_BASE}/company-news"
    params = {
        "symbol": symbol,
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
        "token": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        items = r.json()
    except Exception:
        return []
    out = []
    for item in (items or [])[:15]:
        out.append({
            "headline": item.get("headline") or "",
            "url": item.get("url") or "",
            "summary": (item.get("summary") or "")[:300],
            "datetime": item.get("datetime"),
        })
    return out


def get_news_sentiment(api_key, symbol, from_date=None, to_date=None):
    """Fetch company news and derive a simple sentiment score (-1 to 1)."""
    if not api_key:
        return None
    to_date = to_date or datetime.now()
    from_date = from_date or (to_date - timedelta(days=2))
    url = f"{FINNHUB_BASE}/company-news"
    params = {
        "symbol": symbol,
        "from": from_date.strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
        "token": api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        items = r.json()
    except Exception:
        return None
    if not items:
        return 0.0
    # Simple heuristic: use headline + summary for sentiment (no NLP; could add later)
    total = 0.0
    count = 0
    for item in items[:15]:
        text = (item.get("headline") or "") + " " + (item.get("summary") or "")
        text = text.lower()
        pos = sum(1 for w in ("surge", "gain", "rise", "beat", "growth", "bull") if w in text)
        neg = sum(1 for w in ("fall", "drop", "loss", "miss", "decline", "bear") if w in text)
        if pos or neg:
            total += (pos - neg) / max(pos + neg, 1)
            count += 1
    if count == 0:
        return 0.0
    score = total / count
    return max(-1.0, min(1.0, score))
