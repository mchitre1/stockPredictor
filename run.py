"""Entry point: start Flask app and scheduler (local only for security)."""
import os

from app import create_app
from app.scheduler import start_scheduler

app = create_app()

if __name__ == "__main__":
    start_paused = os.getenv("DISABLE_SCHEDULER") == "1"
    start_scheduler(app, start_paused=start_paused)
    port = 5000
    print("\n  Stock Predictor — http://127.0.0.1:{}\n".format(port))
    app.run(host="127.0.0.1", port=port, debug=True)
