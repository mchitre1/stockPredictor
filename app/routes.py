"""Flask routes for the stock predictor UI."""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from app.models import (
    get_latest_daily_picks,
    get_predictions_history,
    get_accuracy_history,
    get_accuracy_stats,
    clear_predictions,
)
from app.predictor import run_prediction
from app.scheduler import get_scheduler_status, set_scheduler_enabled
from app.ml_model import train_model, load_model
from app.stock_data import get_chart_data, get_stock_name
from app.news_data import get_company_news
from config import FINNHUB_API_KEY

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    stats = get_accuracy_stats(current_app)
    latest_picks = get_latest_daily_picks(current_app)
    ml_available = load_model()[0] is not None
    return render_template(
        "index.html",
        latest_picks=latest_picks,
        accuracy_stats=stats,
        accuracy_history=get_accuracy_history(current_app, limit=30),
        predictions_history=get_predictions_history(current_app, limit=14),
        scheduler_status=get_scheduler_status(current_app),
        ml_available=ml_available,
    )

@bp.route("/api/run-prediction", methods=["POST"])
def api_run_prediction():
    result = run_prediction(current_app)
    if result:
        return jsonify({"ok": True, "result": result})
    return jsonify({
        "ok": False,
        "error": "Could not load S&P 500 data or fetch prices. Try again in a moment.",
    }), 400

@bp.route("/api/accuracy")
def api_accuracy():
    return jsonify({
        "stats": get_accuracy_stats(current_app),
        "history": get_accuracy_history(current_app, limit=90),
    })

@bp.route("/api/scheduler", methods=["GET"])
def api_scheduler_get():
    return jsonify(get_scheduler_status(current_app))

@bp.route("/api/scheduler", methods=["POST"])
def api_scheduler_set():
    data = request.get_json() or {}
    enabled = data.get("enabled")
    if enabled is None:
        return jsonify({"ok": False, "error": "enabled required"}), 400
    if set_scheduler_enabled(current_app, bool(enabled)):
        return jsonify({"ok": True, "scheduler": get_scheduler_status(current_app)})
    return jsonify({"ok": False, "error": "Scheduler not available"}), 500


@bp.route("/api/predictions/clear", methods=["POST"])
def api_clear_predictions():
    clear_predictions(current_app)
    return jsonify({"ok": True})


@bp.route("/api/ml/train", methods=["POST"])
def api_ml_train():
    if train_model(current_app):
        return jsonify({"ok": True, "message": "Model trained."})
    return jsonify({"ok": False, "error": "Not enough accuracy data (need 8+ days)."}), 400


@bp.route("/api/stock/<symbol>/chart")
def api_stock_chart(symbol):
    days = request.args.get("days", 90, type=int)
    days = min(max(days, 5), 365)
    sym = symbol.upper()
    data = get_chart_data(sym, days=days)
    if not data:
        return jsonify({"ok": False, "error": "No data for symbol"}), 404
    name = get_stock_name(sym)
    return jsonify({"ok": True, "symbol": sym, "name": name, "data": data})


@bp.route("/api/stock/<symbol>/news")
def api_stock_news(symbol):
    sym = symbol.upper()
    news = get_company_news(FINNHUB_API_KEY, sym, days=5)
    return jsonify({"ok": True, "symbol": sym, "news": news})