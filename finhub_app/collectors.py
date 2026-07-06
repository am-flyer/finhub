from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

import requests
import yfinance as yf

from finhub_app.domain import FilingItem, MarketSnapshot, NewsItem, Position


class MarketDataCollector(Protocol):
    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        ...


class NewsCollector(Protocol):
    def get_news(self, symbol: str) -> list[NewsItem]:
        ...


class FilingCollector(Protocol):
    def get_filings(self, symbol: str) -> list[FilingItem]:
        ...


class YFinanceCollector:
    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="2d")
        if history.empty:
            return MarketSnapshot(symbol=symbol)

        latest_price = float(history["Close"].iloc[-1])
        previous_close = (
            float(history["Close"].iloc[-2]) if len(history.index) > 1 else None
        )
        return MarketSnapshot(
            symbol=symbol,
            latest_price=latest_price,
            previous_close=previous_close,
        )


class FinnhubCollector:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_news(self, symbol: str) -> list[NewsItem]:
        if not self.api_key:
            return []

        today = datetime.now(UTC).date()
        week_ago = today - timedelta(days=7)
        response = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": symbol,
                "from": week_ago.isoformat(),
                "to": today.isoformat(),
                "token": self.api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        return [
            NewsItem(
                symbol=symbol,
                title=item.get("headline", ""),
                summary=item.get("summary"),
                source=item.get("source", "Finnhub"),
                published_at=datetime.fromtimestamp(item["datetime"], tz=UTC)
                if item.get("datetime")
                else None,
                url=item.get("url"),
            )
            for item in response.json()
            if item.get("headline")
        ]


class MarketauxCollector:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_news(self, symbol: str) -> list[NewsItem]:
        if not self.api_key:
            return []

        response = requests.get(
            "https://api.marketaux.com/v1/news/all",
            params={
                "symbols": symbol,
                "filter_entities": "true",
                "language": "en",
                "api_token": self.api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        news: list[NewsItem] = []
        for item in response.json().get("data", []):
            sentiment = None
            for entity in item.get("entities", []):
                if entity.get("symbol") == symbol:
                    sentiment = entity.get("sentiment_score")
                    break
            news.append(
                NewsItem(
                    symbol=symbol,
                    title=item.get("title", ""),
                    summary=item.get("description"),
                    source=item.get("source", "Marketaux"),
                    published_at=datetime.fromisoformat(
                        item["published_at"].replace("Z", "+00:00")
                    )
                    if item.get("published_at")
                    else None,
                    url=item.get("url"),
                    sentiment_score=sentiment,
                )
            )
        return [item for item in news if item.title]


class SecEdgarCollector:
    def get_filings(self, symbol: str) -> list[FilingItem]:
        # SEC symbol-to-CIK lookup requires a company ticker map. This placeholder
        # keeps the architecture wired while the live integration is added.
        return []


def collect_for_positions(
    positions: list[Position],
    market_collector: MarketDataCollector,
    news_collectors: list[NewsCollector],
    filing_collector: FilingCollector,
) -> tuple[list[MarketSnapshot], list[NewsItem], list[FilingItem]]:
    snapshots: list[MarketSnapshot] = []
    news: list[NewsItem] = []
    filings: list[FilingItem] = []

    for position in positions:
        snapshots.append(market_collector.get_snapshot(position.symbol))
        for collector in news_collectors:
            news.extend(collector.get_news(position.symbol))
        filings.extend(filing_collector.get_filings(position.symbol))

    return snapshots, news, filings
