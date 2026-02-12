"""ML model trained on accuracy history to score symbols (probability of positive next-day return)."""
import json
from pathlib import Path

import numpy as np

from config import DATA_DIR

MODEL_FILE = DATA_DIR / "model.joblib"
FEATURE_NAMES = ["return_1d", "return_5d", "return_20d", "volatility_10d"]
MIN_TRAINING_SAMPLES = 8


def _get_training_data(app):
    """Build X (list of feature lists) and y (0/1) from accuracy_log."""
    from app.database import get_db
    from app.stock_data import fetch_prices_until, get_ml_features

    with app.app_context():
        db = get_db()
        rows = db.execute(
            "SELECT date, predicted_symbol, actual_return FROM accuracy_log ORDER BY date"
        ).fetchall()
    X, y = [], []
    for r in rows:
        date_str = r["date"]
        symbol = r["predicted_symbol"]
        actual_return = r["actual_return"]
        if actual_return is None:
            continue
        series = fetch_prices_until(symbol, date_str, days=60)
        if series is None:
            continue
        feats = get_ml_features(series)
        if feats is None:
            continue
        X.append([feats[k] for k in FEATURE_NAMES])
        y.append(1 if actual_return > 0 else 0)
    return np.array(X, dtype=np.float64), np.array(y, dtype=np.int32)


def train_model(app):
    """
    Train RandomForest on accuracy_log history. Saves model to data/model.joblib.
    Returns True if trained and saved, False if not enough data.
    """
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        import joblib
    except ImportError:
        return False

    X, y = _get_training_data(app)
    if len(y) < MIN_TRAINING_SAMPLES:
        return False
    # Handle any inf/nan
    imp = SimpleImputer(strategy="median")
    X = imp.fit_transform(X)
    np.nan_to_num(X, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
    clf.fit(X, y)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "imputer": imp, "features": FEATURE_NAMES}, MODEL_FILE)
    return True


def load_model():
    """Load saved model and imputer. Returns (model, imputer) or (None, None)."""
    if not MODEL_FILE.exists():
        return None, None
    try:
        import joblib
        data = joblib.load(MODEL_FILE)
        return data.get("model"), data.get("imputer")
    except Exception:
        return None, None


def score_with_ml(features_list):
    """
    features_list: list of dicts with keys return_1d, return_5d, return_20d, volatility_10d.
    Returns list of probabilities (probability of positive next-day return), same length as input.
    If model not available, returns None.
    """
    model, imputer = load_model()
    if model is None:
        return None
    X = np.array([[f.get(k, 0) for k in FEATURE_NAMES] for f in features_list], dtype=np.float64)
    X = imputer.transform(X)
    np.nan_to_num(X, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    proba = model.predict_proba(X)[:, 1]
    return proba.tolist()
