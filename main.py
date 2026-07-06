from finhub_app.app import generate_daily_report
from finhub_app.config import get_settings
from finhub_app.scheduler import build_scheduler


def main() -> None:
    report = generate_daily_report()
    print(report)


def run_scheduler() -> None:
    scheduler = build_scheduler(get_settings(), generate_daily_report)
    scheduler.start()


if __name__ == "__main__":
    main()
