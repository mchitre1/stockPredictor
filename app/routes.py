"""Flask routes for the stock predictor UI."""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, current_app
from app.models import (
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    get_latest_prediction,
    get_predictions_history,
    get_accuracy_history,
    get_accuracy_stats,
)
from app.predictor import run_prediction
from app.scheduler import get_scheduler_status, set_scheduler_enabled

bp = Blueprint("main", __name__)

@bp.route("/")
def index():
    stats = get_accuracy_stats(current_app)
    latest = get_latest_prediction(current_app)
    return render_template(
        "index.html",
        watchlist=get_watchlist(current_app),
        latest_prediction=latest,
        accuracy_stats=stats,
        accuracy_history=get_accuracy_history(current_app, limit=30),
        predictions_history=get_predictions_history(current_app, limit=14),
        scheduler_status=get_scheduler_status(current_app),
    )

@bp.route("/api/watchlist", methods=["POST"])
def api_add_stock():
    data = request.get_json() or request.form
    symbol = (data.get("symbol") or "").strip().upper()
    if not symbol:
        return jsonify({"ok": False, "error": "Symbol required"}), 400
    name = (data.get("name") or symbol).strip()
    if add_to_watchlist(current_app, symbol, name):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Already in watchlist or invalid"}), 400

@bp.route("/api/watchlist/<symbol>", methods=["DELETE"])
def api_remove_stock(symbol):
    remove_from_watchlist(current_app, symbol.upper())
    return jsonify({"ok": True})

@bp.route("/api/run-prediction", methods=["POST"])
def api_run_prediction():
    result = run_prediction(current_app)
    if result:
        return jsonify({"ok": True, "result": result})
    return jsonify({"ok": False, "error": "No watchlist or data"}), 400

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