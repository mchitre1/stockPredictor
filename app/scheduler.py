"""Run prediction every day at 9 AM EST. Can be paused/resumed via UI."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from config import SCHEDULE_HOUR, SCHEDULE_MINUTE, SCHEDULE_TIMEZONE

JOB_PREDICTION = "daily_prediction"
JOB_ACCURACY = "daily_accuracy"

def start_scheduler(app, start_paused=False):
    """Schedule daily prediction at 9 AM EST and accuracy update at 5 PM. Returns scheduler."""
    tz = pytz.timezone(SCHEDULE_TIMEZONE)

    def job_prediction():
        with app.app_context():
            from app.predictor import run_prediction
            run_prediction(app)

    def job_accuracy():
        with app.app_context():
            from app.accuracy import update_latest_accuracy
            update_latest_accuracy(app)

    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(
        job_prediction,
        CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
        id=JOB_PREDICTION,
    )
    scheduler.add_job(
        job_accuracy,
        CronTrigger(hour=17, minute=0),
        id=JOB_ACCURACY,
    )
    scheduler.start()
    app.config["scheduler"] = scheduler
    app.config["scheduler_enabled"] = not start_paused
    if start_paused:
        scheduler.pause_job(JOB_PREDICTION)
        scheduler.pause_job(JOB_ACCURACY)
    return scheduler

def set_scheduler_enabled(app, enabled):
    """Turn scheduler jobs on or off."""
    scheduler = app.config.get("scheduler")
    if not scheduler:
        return False
    if enabled:
        scheduler.resume_job(JOB_PREDICTION)
        scheduler.resume_job(JOB_ACCURACY)
    else:
        scheduler.pause_job(JOB_PREDICTION)
        scheduler.pause_job(JOB_ACCURACY)
    app.config["scheduler_enabled"] = enabled
    return True

def get_scheduler_status(app):
    """Return dict with enabled and next run times."""
    enabled = app.config.get("scheduler_enabled", False)
    return {
        "enabled": enabled,
        "next_prediction": "9:00 AM EST" if enabled else "—",
        "next_accuracy": "5:00 PM EST" if enabled else "—",
    }
