"""Data access helpers for watchlist, predictions, and accuracy."""
from app.database import get_db

def get_watchlist(app):
    with app.app_context():
        db = get_db()
        rows = db.execute("SELECT id, symbol, name, added_at FROM watchlist ORDER BY symbol").fetchall()
        return [dict(r) for r in rows]

def add_to_watchlist(app, symbol, name=None):
    with app.app_context():
        db = get_db()
        try:
            db.execute(
                "INSERT INTO watchlist (symbol, name) VALUES (?, ?)",
                (symbol.upper().strip(), name or symbol.upper())
            )
            db.commit()
            return True
        except Exception:
            return False

def remove_from_watchlist(app, symbol):
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        db.commit()

def save_prediction(app, symbol, date_str, score, reason=None):
    from app.database import db_connection
    with db_connection(app) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO predictions (symbol, date, score, reason)
               VALUES (?, ?, ?, ?)""",
            (symbol.upper(), date_str, score, reason or "")
        )

def save_daily_picks(app, date_str, picks):
    """Save top 3 picks for a date. picks = [(symbol, score, reason, price), ...] (up to 3). price can be None."""
    from app.database import db_connection
    with db_connection(app) as conn:
        conn.execute("DELETE FROM daily_picks WHERE date = ?", (date_str,))
        for rank, pick in enumerate(picks[:3], start=1):
            symbol = pick[0].upper()
            score = pick[1]
            reason = pick[2] or ""
            price = pick[3] if len(pick) > 3 else None
            conn.execute(
                """INSERT INTO daily_picks (date, rank, symbol, score, reason, price)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (date_str, rank, symbol, score, reason, price)
            )
        if picks:
            sym, sc, re = picks[0][0], picks[0][1], picks[0][2]
            conn.execute(
                """INSERT OR REPLACE INTO predictions (symbol, date, score, reason)
                   VALUES (?, ?, ?, ?)""",
                (sym.upper(), date_str, sc, re or "")
            )

def get_latest_daily_picks(app):
    """Return the 3 picks for the most recent date, or []."""
    with app.app_context():
        db = get_db()
        date_row = db.execute(
            "SELECT date FROM daily_picks ORDER BY date DESC LIMIT 1"
        ).fetchone()
        if not date_row:
            return []
        rows = db.execute(
            """SELECT date, rank, symbol, score, reason, price
               FROM daily_picks WHERE date = ? ORDER BY rank""",
            (date_row["date"],)
        ).fetchall()
        return [dict(r) for r in rows]

def get_latest_prediction(app):
    """Backward compat: single 'latest' pick (rank 1 of latest date)."""
    picks = get_latest_daily_picks(app)
    for p in picks:
        if p.get("rank") == 1:
            return p
    with app.app_context():
        db = get_db()
        row = db.execute(
            """SELECT symbol, date, score, reason, created_at
               FROM predictions ORDER BY date DESC, created_at DESC LIMIT 1"""
        ).fetchone()
        return dict(row) if row else None

def get_daily_picks_history(app, limit=30):
    """List of dates with their 3 picks each. Each item: {date, picks: [{rank, symbol, score, reason}, ...]}."""
    with app.app_context():
        db = get_db()
        dates = db.execute(
            "SELECT DISTINCT date FROM daily_picks ORDER BY date DESC LIMIT ?",
            (limit,)
        ).fetchall()
        out = []
        for d in dates:
            date_str = d["date"]
            rows = db.execute(
                """SELECT rank, symbol, score, reason, price FROM daily_picks
                   WHERE date = ? ORDER BY rank""",
                (date_str,)
            ).fetchall()
            out.append({"date": date_str, "picks": [dict(r) for r in rows]})
        return out

def get_predictions_history(app, limit=30):
    """Flat list of picks for history table (one row per pick)."""
    with app.app_context():
        db = get_db()
        rows = db.execute(
            """SELECT date, rank, symbol, score, reason, price FROM daily_picks
               ORDER BY date DESC, rank LIMIT ?""",
            (limit * 3,)
        ).fetchall()
        return [dict(r) for r in rows]

def clear_predictions(app):
    """Remove all daily picks and predictions (keeps accuracy_log)."""
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM daily_picks")
        db.execute("DELETE FROM predictions")
        db.commit()

def get_predicted_symbol_for_date(app, date_str):
    """Symbol of rank-1 pick for that date (for accuracy)."""
    with app.app_context():
        db = get_db()
        row = db.execute(
            "SELECT symbol FROM daily_picks WHERE date = ? AND rank = 1",
            (date_str,)
        ).fetchone()
        if row:
            return row["symbol"]
        row = db.execute(
            "SELECT symbol FROM predictions WHERE date = ?",
            (date_str,)
        ).fetchone()
        return row["symbol"] if row else None

def save_accuracy(app, date_str, predicted_symbol, predicted_return, actual_return, actual_close, was_correct):
    from app.database import db_connection
    with db_connection(app) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO accuracy_log
               (date, predicted_symbol, predicted_return, actual_return, actual_close, was_correct)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (date_str, predicted_symbol, predicted_return, actual_return, actual_close, 1 if was_correct else 0)
        )

def get_accuracy_history(app, limit=90):
    with app.app_context():
        db = get_db()
        rows = db.execute(
            """SELECT date, predicted_symbol, predicted_return, actual_return, actual_close, was_correct
               FROM accuracy_log ORDER BY date DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_accuracy_stats(app):
    with app.app_context():
        db = get_db()
        row = db.execute(
            """SELECT
                 COUNT(*) as total,
                 SUM(was_correct) as correct
               FROM accuracy_log"""
        ).fetchone()
        total = row["total"] or 0
        correct = row["correct"] or 0
        pct = (100.0 * correct / total) if total else 0
        return {"total": total, "correct": correct, "accuracy_pct": round(pct, 1)}
