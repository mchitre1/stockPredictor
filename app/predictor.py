"""Score S&P 500 symbols and pick top 3 for the day. Uses ML when trained, else momentum + news."""
from datetime import datetime

from app.stock_data import fetch_prices_batched, get_momentum_metrics, get_ml_features
from app.news_data import get_news_sentiment
from app.sp500 import get_sp500_tickers
from app.ml_model import load_model, score_with_ml, train_model, FEATURE_NAMES
from config import FINNHUB_API_KEY

TOP_N_FOR_NEWS = 10


def _momentum_score(metrics, use_news=False, news_sentiment=None):
    """Compute momentum score only."""
    if not metrics:
        return None
    score = 0.0
    if metrics.get("return_1d") is not None:
        score += 2.0 * metrics["return_1d"]
    if metrics.get("return_5d") is not None:
        score += 1.5 * metrics["return_5d"]
    if metrics.get("return_20d") is not None:
        score += 0.5 * metrics["return_20d"]
    if use_news and news_sentiment is not None:
        score += 10.0 * news_sentiment
    return score


def _format_explanation(metrics, news_sentiment=None, use_ml=False, ml_proba=None):
    """Build a clear, human-readable explanation of why this stock was ranked."""
    parts = []
    if use_ml and ml_proba is not None:
        pct = round(ml_proba * 100)
        parts.append(
            f"The ML model (trained on past accuracy) gives this stock a {pct}% probability "
            "of a positive next-day return. The model uses recent price momentum and volatility."
        )
    if metrics:
        r1 = metrics.get("return_1d")
        r5 = metrics.get("return_5d")
        r20 = metrics.get("return_20d")
        if r1 is not None or r5 is not None or r20 is not None:
            momentum = []
            if r1 is not None:
                momentum.append(f"{r1:+.1f}% over 1 day")
            if r5 is not None:
                momentum.append(f"{r5:+.1f}% over 5 days")
            if r20 is not None:
                momentum.append(f"{r20:+.1f}% over 20 days")
            if momentum:
                parts.append(
                    "Short-term momentum: " + ", ".join(momentum) + ". "
                    "We weight recent returns more heavily."
                )
    if news_sentiment is not None:
        if news_sentiment > 0.15:
            parts.append("Recent news sentiment is positive.")
        elif news_sentiment < -0.15:
            parts.append("Recent news sentiment is negative.")
        else:
            parts.append("Recent news sentiment is neutral.")
    if not parts:
        return "Ranked by combined score (momentum and optional news)."
    return " ".join(parts)


def run_prediction(app):
    """Run daily prediction: score S&P 500, save top 3 picks for today. Uses ML if trained."""
    from app.models import save_daily_picks

    tickers = get_sp500_tickers()
    if not tickers:
        return None
    today = datetime.now().strftime("%Y-%m-%d")
    prices = fetch_prices_batched(tickers, days=90, chunk_size=80)

    # Build features for each symbol; compute ML score or momentum score
    model, _ = load_model()
    use_ml = model is not None
    scores = []
    features_list = []

    for sym in tickers:
        series = prices.get(sym)
        if series is None or len(series) < 2:
            continue
        metrics = get_momentum_metrics(series)
        feats = get_ml_features(series) if len(series) >= 21 else None
        features_list.append((sym, feats, metrics))

    if use_ml and features_list:
        valid = [(s, f, m) for s, f, m in features_list if f is not None]
        if valid:
            probas = score_with_ml([x[1] for x in valid])
            if probas is not None:
                for (sym, feats, metrics), proba in zip(valid, probas):
                    explanation = _format_explanation(metrics, use_ml=True, ml_proba=proba)
                    scores.append((sym, float(proba), explanation))
                use_ml = True
    if not scores:
        use_ml = False
        for sym, feats, metrics in features_list:
            sc = _momentum_score(metrics, use_news=False)
            if sc is not None:
                explanation = _format_explanation(metrics)
                scores.append((sym, sc, explanation))

    if not scores:
        return None

    scores.sort(key=lambda x: x[1], reverse=True)
    top_symbols = [s[0] for s in scores[:TOP_N_FOR_NEWS]]

    if FINNHUB_API_KEY:
        for i, (sym, sc, explanation) in enumerate(scores):
            if sym not in top_symbols:
                continue
            sent = get_news_sentiment(FINNHUB_API_KEY, sym)
            if sent is not None:
                new_explanation = _format_explanation(
                    get_momentum_metrics(prices.get(sym)) if prices.get(sym) is not None else None,
                    news_sentiment=sent,
                    use_ml=use_ml,
                    ml_proba=sc if use_ml else None,
                )
                scores[i] = (sym, sc + (0.1 * sent if use_ml else 10.0 * sent), new_explanation)

    scores.sort(key=lambda x: x[1], reverse=True)
    top3 = []
    for s, sc, re in scores[:3]:
        series = prices.get(s)
        price = float(series.iloc[-1]) if series is not None and len(series) else None
        top3.append((s, sc, re, price))

    save_daily_picks(app, today, top3)

    # Optionally train ML model if we have enough accuracy history and no model yet
    if model is None:
        train_model(app)

    return {
        "date": today,
        "picks": [{"symbol": s, "score": sc, "reason": re, "price": pr} for s, sc, re, pr in top3],
        "universe": "S&P 500",
        "used_ml": use_ml,
    }