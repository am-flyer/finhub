from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from finhub_app.collectors import FinnhubCollector, MarketauxCollector, YFinanceCollector
from finhub_app.config import get_settings
from finhub_app.domain import AssetScope, Position
from finhub_app.storage import PortfolioStore


def refresh_position_history(position: Position, store: PortfolioStore | None = None) -> None:
    settings = get_settings()
    if store is None:
        store = PortfolioStore(settings.database_url)

    if not position.symbol:
        return

    start_date = (position.added_at or datetime.now(UTC) - timedelta(days=365)).replace(tzinfo=UTC)
    start_date = start_date - timedelta(days=365)
    end_date = datetime.now(UTC)

    yfinance_collector = YFinanceCollector()
    for date_str, price in yfinance_collector.get_historical_prices(position.symbol, start_date, end_date):
        store.save_price_history(position.symbol, date_str, price)

    for collector in [
        FinnhubCollector(settings.finnhub_api_key),
        MarketauxCollector(settings.marketaux_api_key),
    ]:
        for item in collector.get_news(position.symbol, start_date, end_date):
            store.save_news_record(
                symbol=item.symbol,
                published_at=item.published_at or datetime.now(UTC),
                title=item.title,
                summary=item.summary,
                source=item.source,
                url=str(item.url) if item.url else None,
                sentiment_score=item.sentiment_score,
            )
