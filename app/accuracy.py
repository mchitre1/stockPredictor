"""Update accuracy log using actual next-day returns."""
from datetime import datetime, timedelta
from app.stock_data import fetch_prices, compute_returns
from app.models import get_latest_prediction, get_predictions_history, save_accuracy, get_accuracy_history

def update_accuracy_for_date(app, for_date_str):
    """
    For a given prediction date, get that day's #1 pick, then compute actual return
    from that day's close to the next trading day's close. Log if prediction
    was 'correct' (actual return > 0 when we picked it).
    """
    from app.models import get_predicted_symbol_for_date
    symbol = get_predicted_symbol_for_date(app, for_date_str)
    if not symbol:
        return None
    with app.app_context():
        # Get actual close on prediction date and next trading day
        end = datetime.strptime(for_date_str, "%Y-%m-%d") + timedelta(days=5)
        start = datetime.strptime(for_date_str, "%Y-%m-%d") - timedelta(days=5)
        prices = fetch_prices(symbol, days=14)
        series = prices.get(symbol.upper())
        if series is None or len(series) < 2:
            return None
        # Align to dates: close on for_date_str and close on next trading day
        series = series.sort_index()
        try:
            on_or_after = series.index[series.index >= for_date_str]
            if len(on_or_after) < 2:
                return None
            pred_close = float(series.loc[on_or_after[0]])
            next_day_close = float(series.loc[on_or_after[1]])
        except Exception:
            return None
        actual_return = (next_day_close / pred_close - 1.0) * 100
        actual_close = next_day_close
        # We "predicted" this stock would be the best; treat as correct if it went up
        was_correct = 1 if actual_return > 0 else 0
        save_accuracy(
            app,
            for_date_str,
            symbol,
            None,
            actual_return,
            actual_close,
            was_correct,
        )
        return {
            "date": for_date_str,
            "symbol": symbol,
            "actual_return": actual_return,
            "actual_close": actual_close,
            "was_correct": bool(was_correct),
        }

def update_latest_accuracy(app):
    """Update accuracy for the most recent prediction that doesn't have an accuracy log yet."""
    with app.app_context():
        from app.database import get_db
        db = get_db()
        rows = db.execute("""
            SELECT d.date FROM daily_picks d
            WHERE d.rank = 1
            AND d.date NOT IN (SELECT date FROM accuracy_log)
            ORDER BY d.date DESC
        """).fetchall()
        if not rows:
            rows = db.execute("""
                SELECT p.date FROM predictions p
                LEFT JOIN accuracy_log a ON p.date = a.date
                WHERE a.date IS NULL
                ORDER BY p.date DESC
            """).fetchall()
        for row in rows:
            update_accuracy_for_date(app, row[0])
