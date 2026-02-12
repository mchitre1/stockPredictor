"""App configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "data" / "stock_predictor.db"
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
FLASK_ENV = os.getenv("FLASK_ENV", "development")

# Market hours: run prediction at 9:00 AM EST
SCHEDULE_HOUR = 9
SCHEDULE_MINUTE = 0
SCHEDULE_TIMEZONE = "America/New_York"
