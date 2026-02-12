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

def get_latest_prediction(app):
    with app.app_context():
        db = get_db()
        row = db.execute(
            """SELECT symbol, date, score, reason, created_at
               FROM predictions ORDER BY date DESC, created_at DESC LIMIT 1"""
        ).fetchone()
        return dict(row) if row else None

def get_predictions_history(app, limit=30):
    with app.app_context():
        db = get_db()
        rows = db.execute(
            """SELECT symbol, date, score, reason, created_at
               FROM predictions ORDER BY date DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

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
