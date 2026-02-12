"""Stock Predictor application."""
from flask import Flask
from config import DATABASE_PATH, SECRET_KEY
from app.database import init_db, get_db, init_app

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["DATABASE"] = str(DATABASE_PATH)
    init_db(app)
    init_app(app)
    from app import routes
    app.register_blueprint(routes.bp, url_prefix="/")
    return app
