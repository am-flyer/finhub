import argparse

from finhub_app.app import generate_daily_report
from finhub_app.config import get_settings
from finhub_app.domain import AssetScope, Position
from finhub_app.scheduler import build_scheduler
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


def run_scheduler() -> None:
    scheduler = build_scheduler(get_settings(), generate_daily_report)
    scheduler.start()


if __name__ == "__main__":
    main()
