"""SQLite database setup and access."""
import sqlite3
from contextlib import contextmanager
from flask import g

def get_db_path(app):
    return app.config["DATABASE"]

def init_db(app):
    """Create tables if they don't exist."""
    path = get_db_path(app)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            score REAL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        );
        CREATE TABLE IF NOT EXISTS accuracy_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL UNIQUE,
            predicted_symbol TEXT NOT NULL,
            predicted_return REAL,
            actual_return REAL,
            actual_close REAL,
            was_correct INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS daily_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            rank INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            score REAL,
            reason TEXT,
            price REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, rank)
        );
    """)
    conn.commit()
    try:
        conn.execute("ALTER TABLE daily_picks ADD COLUMN price REAL")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()

def get_db(app=None):
    """Get database connection for current app context."""
    if app is None:
        from flask import current_app
        app = current_app
    if "db" not in g:
        g.db = sqlite3.connect(get_db_path(app))
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)

@contextmanager
def db_connection(app):
    """Standalone connection for use outside request context (e.g. scheduler)."""
    path = app.config["DATABASE"]
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
