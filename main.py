import argparse
import json
from datetime import datetime

from finhub_app.config import get_settings
from finhub_app.domain import AssetScope, Position
from finhub_app.storage import PortfolioStore


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "add-holding":
        add_position(args, AssetScope.HOLDING)
        return

    if args.command == "add-watchlist":
        add_position(args, AssetScope.WATCHLIST)
        return

    if args.command == "list-positions":
        list_positions()
        return

    if args.command == "serve":
        from finhub_app.server import run_server
        run_server(args.port)
        return

    if args.command == "ingest-symbol":
        ingest_symbol(args)
        return

    if args.command == "build-features":
        build_features()
        return

    if args.command == "train-model":
        train_prediction_model()
        return

    if args.command == "model-status":
        report_model_status()
        return

    if args.command == "seed-history":
        from finhub_app.seeding import seed_historical_data
        settings = get_settings()
        seed_historical_data(settings.database_url, args.start_date)
        return

    if args.command == "seed-reports":
        from finhub_app.seeding import seed_past_reports
        settings = get_settings()
        seed_past_reports(settings.database_url, args.days, args.articles_per_day)
        return

    if args.command == "clean-history":
        from sqlalchemy.orm import Session
        from finhub_app.storage import PortfolioStore, ReportRecord, PriceHistory, NewsRecord
        settings = get_settings()
        store = PortfolioStore(settings.database_url)
        store.initialize()
        with Session(store.engine) as session:
            reports_deleted = session.query(ReportRecord).delete()
            prices_deleted = session.query(PriceHistory).delete()
            news_deleted = session.query(NewsRecord).delete()
            session.commit()
            print("Successfully cleaned up all seeded data:")
            print(f" - Deleted {reports_deleted} Report Records")
            print(f" - Deleted {prices_deleted} Price History points")
            print(f" - Deleted {news_deleted} News Records")
            print("Portfolio holding assets remain intact.")
        return

    from finhub_app.app import generate_daily_report

    report = generate_daily_report()
    print(report)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FinHub daily investment report")
    subparsers = parser.add_subparsers(dest="command")

    holding = subparsers.add_parser("add-holding", help="Add or update a portfolio holding")
    holding.add_argument("symbol", help="Ticker symbol, for example MSFT")
    holding.add_argument("--name", default=None, help="Company or asset name")
    holding.add_argument("--quantity", type=float, required=True, help="Number of shares")
    holding.add_argument(
        "--average-cost",
        type=float,
        required=True,
        help="Average purchase price per share",
    )

    watchlist = subparsers.add_parser("add-watchlist", help="Add or update a watchlist item")
    watchlist.add_argument("symbol", help="Ticker symbol, for example VOO")
    watchlist.add_argument("--name", default=None, help="Company or asset name")

    subparsers.add_parser("list-positions", help="Show holdings and watchlist items")

    serve = subparsers.add_parser("serve", help="Start the Web Dashboard server")
    serve.add_argument("--port", type=int, default=8000, help="Port to run server on (default: 8000)")

    seed = subparsers.add_parser("seed-history", help="Seed historical price and news data from Yahoo Finance")
    seed.add_argument("--start-date", default="2025-01-01", help="Start date in YYYY-MM-DD format (default: 2025-01-01)")

    seed_rep = subparsers.add_parser("seed-reports", help="Seed daily reports for the past month")
    seed_rep.add_argument("--days", type=int, default=30, help="Number of historical days to seed reports for (default: 30)")
    seed_rep.add_argument("--articles-per-day", type=int, default=20, help="Target count of real news articles per stock per day (default: 20)")

    subparsers.add_parser("clean-history", help="Wipe all seeded historical reports, price history, and news records, keeping assets intact")

    ingest = subparsers.add_parser("ingest-symbol", help="Ingest raw market and fundamental data for a symbol")
    ingest.add_argument("symbol", help="Ticker symbol, for example AAPL")
    ingest.add_argument("--start-date", default=None, help="Optional start date for data ingestion")
    ingest.add_argument("--end-date", default=None, help="Optional end date for data ingestion")

    subparsers.add_parser("build-features", help="Build feature records for saved positions using ingested raw data")

    subparsers.add_parser("train-model", help="Train a prediction model from available feature records")
    subparsers.add_parser("model-status", help="Show the current prediction model status")

    return parser


def add_position(args: argparse.Namespace, scope: AssetScope) -> None:
    settings = get_settings()
    store = PortfolioStore(settings.database_url)
    store.initialize()
    store.upsert_position(
        Position(
            symbol=args.symbol.upper(),
            name=args.name,
            quantity=args.quantity if scope == AssetScope.HOLDING else 0,
            average_cost=args.average_cost if scope == AssetScope.HOLDING else None,
            scope=scope,
        )
    )
    label = "holding" if scope == AssetScope.HOLDING else "watchlist item"
    print(f"Saved {label}: {args.symbol.upper()}")


def list_positions() -> None:
    settings = get_settings()
    store = PortfolioStore(settings.database_url)
    store.initialize()
    positions = store.list_positions()
    if not positions:
        print("No holdings or watchlist items saved yet.")
        return

    for position in positions:
        cost = (
            f" @ ${position.average_cost:.2f}"
            if position.average_cost is not None
            else ""
        )
        name = f" ({position.name})" if position.name else ""
        print(
            f"{position.scope.value}: {position.symbol}{name} - "
            f"{position.quantity:g} share(s){cost}"
        )


def ingest_symbol(args: argparse.Namespace) -> None:
    from finhub_app.ingestion import create_default_us_ingestion_manager

    settings = get_settings()
    store = PortfolioStore(settings.database_url)
    store.initialize()
    ingestion_manager = create_default_us_ingestion_manager(store)
    summary = ingestion_manager.ingest_symbol(
        args.symbol,
        market="US",
        start_date=datetime.fromisoformat(args.start_date) if args.start_date else None,
        end_date=datetime.fromisoformat(args.end_date) if args.end_date else None,
    )
    print(f"Ingested raw data for {args.symbol.upper()}")
    print(json.dumps(summary, indent=2, default=str))


def build_features() -> None:
    from finhub_app.feature_store import create_feature_engineering_pipeline

    settings = get_settings()
    store = PortfolioStore(settings.database_url)
    store.initialize()
    pipeline = create_feature_engineering_pipeline(store)
    positions = store.list_positions()
    symbols = sorted({p.symbol.upper() for p in positions if p.symbol.strip()})
    if not symbols:
        print("No symbols found in portfolio/watchlist to build features for.")
        return

    for symbol in symbols:
        features = pipeline.build_features_for_symbol(symbol, market="US")
        print(f"Built {len(features)} feature records for {symbol}")


def train_prediction_model() -> None:
    from finhub_app.modeling import train_model

    settings = get_settings()
    store = PortfolioStore(settings.database_url)
    store.initialize()
    metadata = train_model(store, market="US")
    print(f"Trained model {metadata.model_version} on {metadata.sample_count} samples")
    print(f"Accuracy: {metadata.accuracy:.2%}")
    if metadata.roc_auc is not None:
        print(f"ROC AUC: {metadata.roc_auc:.2f}")


def report_model_status() -> None:
    from finhub_app.modeling import get_model_status

    settings = get_settings()
    status = get_model_status(settings)
    print(json.dumps(status, indent=2))


def run_scheduler() -> None:
    from finhub_app.app import generate_daily_report
    from finhub_app.scheduler import build_scheduler

    scheduler = build_scheduler(get_settings(), generate_daily_report)
    scheduler.start()


if __name__ == "__main__":
    main()
