"""Entry point: start Flask app and scheduler (can be toggled off in UI)."""
import os
from app import create_app
from app.scheduler import start_scheduler

app = create_app()

if __name__ == "__main__":
    # Start scheduler; if DISABLE_SCHEDULER=1, start with jobs paused (toggle on in UI to test)
    start_paused = os.getenv("DISABLE_SCHEDULER") == "1"
    start_scheduler(app, start_paused=start_paused)
    app.run(host="0.0.0.0", port=5000, debug=True)
