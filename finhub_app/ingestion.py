from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import yfinance as yf

from finhub_app.config import get_settings
from finhub_app.domain import (
    RawDataPoint,
    RawEventPayload,
    RawFilingPayload,
    RawMacroPayload,
    RawNewsPayload,
    RawOptionsPayload,
)
from finhub_app.storage import PortfolioStore
from finhub_app.collectors import FinnhubCollector, MarketauxCollector, SecEdgarCollector


class MarketAdapter(Protocol):
    market: str

    def collect_market_data(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[RawDataPoint]:
        ...

    def collect_fundamentals(self, symbol: str) -> list[RawDataPoint]:
        ...

    def collect_news(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[RawNewsPayload]:
        ...

    def collect_filings(self, symbol: str) -> list[RawFilingPayload]:
        ...

    def collect_options(
        self,
        symbol: str,
        as_of_date: datetime | None = None,
    ) -> list[RawOptionsPayload]:
        ...

    def collect_macro(self) -> list[RawMacroPayload]:
        ...

    def collect_events(self, symbol: str) -> list[RawEventPayload]:
        ...


class USMarketAdapter:
    market = "US"
    source_name = "yfinance"
    source_type = "market"

    def __init__(self, finnhub_api_key: str = "", marketaux_api_key: str = "") -> None:
        self.finnhub = FinnhubCollector(finnhub_api_key)
        self.marketaux = MarketauxCollector(marketaux_api_key)
        self.sec_edgar = SecEdgarCollector()

    def _normalize_date(self, value: datetime | None) -> str | None:
        return value.date().isoformat() if value else None

    def collect_market_data(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[RawDataPoint]:
        symbol = symbol.strip().upper()
        ticker = yf.Ticker(symbol)
        if start_date is None:
            start_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date is None:
            end_date = datetime.now(UTC)

        start_str = self._normalize_date(start_date)
        end_str = self._normalize_date(end_date)

        history = ticker.history(start=start_str, end=end_str, auto_adjust=False)
        records: list[RawDataPoint] = []
        if not history.empty:
            for row_index, row in history.iterrows():
                date_key = row_index.date().isoformat()
                records.extend(
                    [
                        RawDataPoint(
                            market=self.market,
                            symbol=symbol,
                            as_of_date=date_key,
                            data_type="price",
                            field_name="open",
                            numeric_value=_as_float(row.get("Open")),
                            source_name=self.source_name,
                            source_type="market",
                            raw_payload={"provider": "yfinance", "date": date_key},
                            retrieved_at=datetime.now(UTC),
                        ),
                        RawDataPoint(
                            market=self.market,
                            symbol=symbol,
                            as_of_date=date_key,
                            data_type="price",
                            field_name="high",
                            numeric_value=_as_float(row.get("High")),
                            source_name=self.source_name,
                            source_type="market",
                            raw_payload={"provider": "yfinance", "date": date_key},
                            retrieved_at=datetime.now(UTC),
                        ),
                        RawDataPoint(
                            market=self.market,
                            symbol=symbol,
                            as_of_date=date_key,
                            data_type="price",
                            field_name="low",
                            numeric_value=_as_float(row.get("Low")),
                            source_name=self.source_name,
                            source_type="market",
                            raw_payload={"provider": "yfinance", "date": date_key},
                            retrieved_at=datetime.now(UTC),
                        ),
                        RawDataPoint(
                            market=self.market,
                            symbol=symbol,
                            as_of_date=date_key,
                            data_type="price",
                            field_name="close",
                            numeric_value=_as_float(row.get("Close")),
                            source_name=self.source_name,
                            source_type="market",
                            raw_payload={"provider": "yfinance", "date": date_key},
                            retrieved_at=datetime.now(UTC),
                        ),
                        RawDataPoint(
                            market=self.market,
                            symbol=symbol,
                            as_of_date=date_key,
                            data_type="price",
                            field_name="volume",
                            numeric_value=_as_float(row.get("Volume")),
                            source_name=self.source_name,
                            source_type="market",
                            raw_payload={"provider": "yfinance", "date": date_key},
                            retrieved_at=datetime.now(UTC),
                        ),
                    ]
                )
        return records

    def collect_fundamentals(self, symbol: str) -> list[RawDataPoint]:
        symbol = symbol.strip().upper()
        ticker = yf.Ticker(symbol)
        records: list[RawDataPoint] = []
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        fundamental_fields = {
            "trailingPE": "trailing_pe",
            "forwardPE": "forward_pe",
            "pegRatio": "peg_ratio",
            "marketCap": "market_cap",
            "debtToEquity": "debt_to_equity",
            "returnOnEquity": "return_on_equity",
            "dividendYield": "dividend_yield",
            "profitMargins": "profit_margin",
            "grossMargins": "gross_margin",
            "payoutRatio": "payout_ratio",
        }

        for raw_name, field_name in fundamental_fields.items():
            records.append(
                RawDataPoint(
                    market=self.market,
                    symbol=symbol,
                    as_of_date=self._normalize_date(datetime.now(UTC)),
                    data_type="fundamental",
                    field_name=field_name,
                    numeric_value=_as_float(info.get(raw_name)),
                    source_name=self.source_name,
                    source_type="fundamental",
                    raw_payload={"provider": "yfinance", "raw_field": raw_name},
                    retrieved_at=datetime.now(UTC),
                )
            )

        return records

    def collect_news(
        self,
        symbol: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[RawNewsPayload]:
        symbol = symbol.strip().upper()
        results: list[RawNewsPayload] = []
        for collector, source_name in [
            (self.finnhub, "finnhub"),
            (self.marketaux, "marketaux"),
        ]:
            try:
                items = collector.get_news(symbol, start_date=start_date, end_date=end_date)
                for item in items:
                    results.append(
                        RawNewsPayload(
                            market=self.market,
                            symbol=symbol,
                            published_at=item.published_at,
                            title=item.title,
                            summary=item.summary,
                            source_name=source_name,
                            source_type="news",
                            url=item.url,
                            sentiment_score=item.sentiment_score,
                            raw_payload={"provider": source_name, **item.model_dump()},
                            retrieved_at=datetime.now(UTC),
                        )
                    )
            except Exception:
                continue

        try:
            ticker = yf.Ticker(symbol)
            for raw_item in getattr(ticker, "news", []) or []:
                results.append(
                    RawNewsPayload(
                        market=self.market,
                        symbol=symbol,
                        published_at=raw_item.get("providerPublishTime") and datetime.fromtimestamp(raw_item.get("providerPublishTime"), tz=UTC),
                        title=raw_item.get("title", ""),
                        summary=raw_item.get("summary"),
                        source_name="yfinance",
                        source_type="news",
                        url=raw_item.get("link"),
                        sentiment_score=None,
                        raw_payload={"provider": "yfinance", **raw_item},
                        retrieved_at=datetime.now(UTC),
                    )
                )
        except Exception:
            pass

        return [item for item in results if item.title]

    def collect_filings(self, symbol: str) -> list[RawFilingPayload]:
        # Placeholder adapter for SEC EDGAR filings. This may be expanded later with a live lookup.
        filings = self.sec_edgar.get_filings(symbol)
        return [
            RawFilingPayload(
                market=self.market,
                symbol=symbol,
                form_type=filing.form_type,
                filed_at=filing.filed_at,
                title=filing.title,
                url=filing.url,
                source_name="sec_edgar",
                source_type="filing",
                raw_payload=filing.model_dump(),
                retrieved_at=datetime.now(UTC),
            )
            for filing in filings
        ]

    def collect_options(
        self,
        symbol: str,
        as_of_date: datetime | None = None,
    ) -> list[RawOptionsPayload]:
        symbol = symbol.strip().upper()
        ticker = yf.Ticker(symbol)
        results: list[RawOptionsPayload] = []
        try:
            expiries = ticker.options
            if expiries:
                expiry = expiries[0]
                chain = ticker.option_chain(expiry)
                for kind, frame in [("call", chain.calls), ("put", chain.puts)]:
                    if frame is None or frame.empty:
                        continue
                    iv_values = [float(v) for v in frame["impliedVolatility"].tolist() if _is_number(v)]
                    oi_values = [float(v) for v in frame["openInterest"].tolist() if _is_number(v)]
                    results.append(
                        RawOptionsPayload(
                            market=self.market,
                            symbol=symbol,
                            as_of_date=expiry,
                            field_name=f"{kind}_avg_iv",
                            numeric_value=float(sum(iv_values) / len(iv_values)) if iv_values else None,
                            text_value=None,
                            source_name="yfinance",
                            source_type="options",
                            raw_payload={"expiry": expiry, "kind": kind, "count": len(iv_values)},
                            retrieved_at=datetime.now(UTC),
                        )
                    )
                    results.append(
                        RawOptionsPayload(
                            market=self.market,
                            symbol=symbol,
                            as_of_date=expiry,
                            field_name=f"{kind}_open_interest",
                            numeric_value=float(sum(oi_values) / len(oi_values)) if oi_values else None,
                            text_value=None,
                            source_name="yfinance",
                            source_type="options",
                            raw_payload={"expiry": expiry, "kind": kind, "count": len(oi_values)},
                            retrieved_at=datetime.now(UTC),
                        )
                    )
        except Exception:
            pass

        return results

    def collect_macro(self) -> list[RawMacroPayload]:
        return []

    def collect_events(self, symbol: str) -> list[RawEventPayload]:
        return []


class RawSourceIngestionManager:
    def __init__(self, store: PortfolioStore, adapters: list[MarketAdapter]) -> None:
        self.store = store
        self.adapters = adapters

    def ingest_symbol(
        self,
        symbol: str,
        market: str = "US",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None:
        adapter = self._find_adapter(market)
        if adapter is None:
            raise ValueError(f"No adapter registered for market {market}")

        for record in adapter.collect_market_data(symbol, start_date=start_date, end_date=end_date):
            self.store.save_raw_data_record(record)

        for record in adapter.collect_fundamentals(symbol):
            self.store.save_raw_data_record(record)

        for news_record in adapter.collect_news(symbol, start_date=start_date, end_date=end_date):
            self.store.save_raw_news_record(news_record)

        for filing_record in adapter.collect_filings(symbol):
            self.store.save_raw_filing_record(filing_record)

        for options_record in adapter.collect_options(symbol):
            self.store.save_raw_options_record(options_record)

        for event_record in adapter.collect_events(symbol):
            self.store.save_raw_event_record(event_record)

        for macro_record in adapter.collect_macro():
            self.store.save_raw_macro_record(macro_record)

    def ingest_positions(
        self,
        symbols: list[str],
        market: str = "US",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> None:
        for symbol in sorted(set(symbol.strip().upper() for symbol in symbols if symbol.strip())):
            self.ingest_symbol(symbol, market=market, start_date=start_date, end_date=end_date)

    def _find_adapter(self, market: str) -> MarketAdapter | None:
        market_key = market.strip().upper()
        for adapter in self.adapters:
            if adapter.market.upper() == market_key:
                return adapter
        return None


def create_default_us_ingestion_manager(store: PortfolioStore) -> RawSourceIngestionManager:
    settings = get_settings()
    adapter = USMarketAdapter(
        finnhub_api_key=settings.finnhub_api_key,
        marketaux_api_key=settings.marketaux_api_key,
    )
    return RawSourceIngestionManager(store=store, adapters=[adapter])


def _as_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_number(value) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False
