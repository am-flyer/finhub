from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

import requests
import yfinance as yf

from finhub_app.domain import FilingItem, FundamentalSnapshot, MarketSnapshot, NewsItem, Position


class MarketDataCollector(Protocol):
    def get_snapshot(self, symbol: str) -> MarketSnapshot:
        ...


class FundamentalDataCollector(Protocol):
    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        ...


class NewsCollector(Protocol):
    def get_news(self, symbol: str) -> list[NewsItem]:
        ...


class FilingCollector(Protocol):
    def get_filings(self, symbol: str) -> list[FilingItem]:
        ...


class YFinanceCollector:
    def get_historical_prices(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[tuple[str, float]]:
        ticker = yf.Ticker(symbol)
        start_value = start_date.date().strftime("%Y-%m-%d") if start_date else None
        if end_date is None:
            end_value = datetime.now(UTC).date().strftime("%Y-%m-%d")
        else:
            end_value = (end_date + timedelta(days=1)).date().strftime("%Y-%m-%d")

        history = ticker.history(start=start_value, end=end_value, auto_adjust=False)
        if history.empty:
            return []

        prices: list[tuple[str, float]] = []
        for _, row in history.iterrows():
            close_price = _as_float(row.get("Close"))
            if close_price is None:
                continue
            prices.append((row.name.strftime("%Y-%m-%d"), close_price))
        return prices

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

    def get_fundamentals(self, symbol: str) -> FundamentalSnapshot:
        ticker = yf.Ticker(symbol)
        notes: list[str] = []

        try:
            info = ticker.info or {}
        except Exception as exc:
            return FundamentalSnapshot(
                symbol=symbol,
                notes=[f"Could not load yfinance fundamentals: {exc}"],
            )

        try:
            income_statement = ticker.income_stmt
        except Exception as exc:
            income_statement = None
            notes.append(f"Income statement unavailable: {exc}")

        try:
            cash_flow = ticker.cashflow
        except Exception as exc:
            cash_flow = None
            notes.append(f"Cash flow statement unavailable: {exc}")

        revenue_growth = _statement_growth(income_statement, ["Total Revenue"])
        eps_growth = _statement_growth(
            income_statement,
            ["Diluted EPS", "Basic EPS", "Diluted EPS Normalized"],
        )
        free_cash_flow, free_cash_flow_growth = _free_cash_flow_values(cash_flow)

        return FundamentalSnapshot(
            symbol=symbol,
            revenue_growth=revenue_growth,
            eps_growth=eps_growth,
            free_cash_flow=free_cash_flow,
            free_cash_flow_growth=free_cash_flow_growth,
            debt_to_equity=_as_float(info.get("debtToEquity")),
            return_on_equity=_as_float(info.get("returnOnEquity")),
            dividend_yield=_as_float(info.get("dividendYield")),
            payout_ratio=_as_float(info.get("payoutRatio")),
            trailing_pe=_as_float(info.get("trailingPE")),
            forward_pe=_as_float(info.get("forwardPE")),
            peg_ratio=_as_float(info.get("pegRatio")),
            profit_margin=_as_float(info.get("profitMargins")),
            gross_margin=_as_float(info.get("grossMargins")),
            market_cap=_as_float(info.get("marketCap")),
            notes=notes,
        )


class FinnhubCollector:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def get_news(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[NewsItem]:
        if not self.api_key:
            return []

        end_value = end_date or datetime.now(UTC)
        start_value = start_date or (end_value - timedelta(days=7))
        response = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": symbol,
                "from": start_value.date().isoformat(),
                "to": end_value.date().isoformat(),
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

    def get_news(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[NewsItem]:
        if not self.api_key:
            return []

        params = {
            "symbols": symbol,
            "filter_entities": "true",
            "language": "en",
            "api_token": self.api_key,
        }
        if start_date is not None:
            params["published_on_start"] = start_date.date().isoformat()
        if end_date is not None:
            params["published_on_end"] = end_date.date().isoformat()

        response = requests.get(
            "https://api.marketaux.com/v1/news/all",
            params=params,
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
    fundamental_collector: FundamentalDataCollector,
    news_collectors: list[NewsCollector],
    filing_collector: FilingCollector,
) -> tuple[
    list[MarketSnapshot],
    list[FundamentalSnapshot],
    list[NewsItem],
    list[FilingItem],
]:
    snapshots: list[MarketSnapshot] = []
    fundamentals: list[FundamentalSnapshot] = []
    news: list[NewsItem] = []
    filings: list[FilingItem] = []

    for position in positions:
        snapshots.append(market_collector.get_snapshot(position.symbol))
        fundamentals.append(fundamental_collector.get_fundamentals(position.symbol))
        for collector in news_collectors:
            news.extend(collector.get_news(position.symbol))
        filings.extend(filing_collector.get_filings(position.symbol))

    return snapshots, fundamentals, news, filings


def _as_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _statement_growth(statement, row_names: list[str]) -> float | None:
    if statement is None or getattr(statement, "empty", True):
        return None

    for row_name in row_names:
        if row_name not in statement.index or len(statement.columns) < 2:
            continue
        latest = _as_float(statement.loc[row_name].iloc[0])
        previous = _as_float(statement.loc[row_name].iloc[1])
        if latest is None or previous in (None, 0):
            continue
        return (latest - previous) / abs(previous)

    return None


def _free_cash_flow_values(cash_flow) -> tuple[float | None, float | None]:
    if cash_flow is None or getattr(cash_flow, "empty", True):
        return None, None

    values: list[float] = []
    if "Free Cash Flow" in cash_flow.index:
        values = [
            value
            for value in (_as_float(item) for item in cash_flow.loc["Free Cash Flow"])
            if value is not None
        ]
    elif "Operating Cash Flow" in cash_flow.index and "Capital Expenditure" in cash_flow.index:
        values = []
        for operating, capital_expenditure in zip(
            cash_flow.loc["Operating Cash Flow"],
            cash_flow.loc["Capital Expenditure"],
        ):
            operating_value = _as_float(operating)
            capex_value = _as_float(capital_expenditure)
            if operating_value is not None and capex_value is not None:
                values.append(operating_value + capex_value)

    if not values:
        return None, None

    growth = None
    if len(values) > 1 and values[1] != 0:
        growth = (values[0] - values[1]) / abs(values[1])

    return values[0], growth
