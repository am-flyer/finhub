from apscheduler.schedulers.blocking import BlockingScheduler

from finhub_app.config import Settings


def build_scheduler(settings: Settings, job) -> BlockingScheduler:
    scheduler = BlockingScheduler(timezone=settings.market_timezone)
    scheduler.add_job(
        job,
        trigger="cron",
        hour=settings.pre_market_report_hour,
        minute=settings.pre_market_report_minute,
        id="daily_pre_market_report",
        replace_existing=True,
    )
    return scheduler
