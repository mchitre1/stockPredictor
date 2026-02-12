"""Score watchlist symbols and pick the best for the day."""
from datetime import datetime
from app.stock_data import fetch_prices, get_momentum_metrics
from app.news_data import get_news_sentiment
from config import FINNHUB_API_KEY

def run_prediction(app):
    """Run daily prediction: score each watchlist symbol, save best pick for today."""
    from app.models import get_watchlist, save_prediction
    watchlist = get_watchlist(app)
    symbols = [w["symbol"] for w in watchlist]
    if not symbols:
        return None
    today = datetime.now().strftime("%Y-%m-%d")
    prices = fetch_prices(symbols, days=90)
    scores = []
    for sym in symbols:
        series = prices.get(sym)
        if series is None or len(series) < 2:
            continue
        metrics = get_momentum_metrics(series)
        if not metrics:
            continue
        # Score: weight short-term momentum (1d, 5d) more than 20d
        score = 0.0
        parts = []
        if metrics.get("return_1d") is not None:
            score += 2.0 * metrics["return_1d"]
            parts.append(f"1d:{metrics['return_1d']:.1f}%")
        if metrics.get("return_5d") is not None:
            score += 1.5 * metrics["return_5d"]
            parts.append(f"5d:{metrics['return_5d']:.1f}%")
        if metrics.get("return_20d") is not None:
            score += 0.5 * metrics["return_20d"]
            parts.append(f"20d:{metrics['return_20d']:.1f}%")
        # Optional news sentiment
        if FINNHUB_API_KEY:
            sent = get_news_sentiment(FINNHUB_API_KEY, sym)
            if sent is not None:
                score += 10.0 * sent
                parts.append(f"news:{sent:.2f}")
        reason = " | ".join(parts)
        scores.append((sym, score, reason))
    if not scores:
        return None
    best = max(scores, key=lambda x: x[1])
    symbol, score, reason = best
    save_prediction(app, symbol, today, score, reason)
    return {"symbol": symbol, "date": today, "score": score, "reason": reason}
