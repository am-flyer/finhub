from __future__ import annotations

from datetime import datetime
from typing import Protocol

from sqlalchemy import inspect

from finhub_app.domain import (
    RawDataPoint,
    RawFilingPayload,
    RawMacroPayload,
    RawNewsPayload,
    RawOptionsPayload,
    RawEventPayload,
)
from finhub_app.ingestion import RawSourceIngestionManager, MarketAdapter
from finhub_app.feature_store import FeatureEngineeringPipeline
from finhub_app.storage import (
    PortfolioStore,
    RawDataRecord,
    RawNewsRecord,
    RawFilingRecord,
    RawOptionsRecord,
    RawMacroRecord,
    RawEventRecord,
)


def test_raw_ingestion_tables_and_save(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'raw_ingestion_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()

    inspector = inspect(store.engine)
    expected_tables = [
        "raw_data_records",
        "raw_news_records",
        "raw_filing_records",
        "raw_options_records",
        "raw_macro_records",
        "raw_event_records",
    ]
    existing_tables = inspector.get_table_names()
    for table_name in expected_tables:
        assert table_name in existing_tables, f"Missing table {table_name}"

    raw_data = RawDataPoint(
        market="US",
        symbol="AAPL",
        as_of_date="2026-07-08",
        data_type="price",
        field_name="close",
        numeric_value=195.25,
        source_name="yfinance",
        source_type="market",
        raw_payload={"close": 195.25},
        retrieved_at=datetime.now(),
    )
    store.save_raw_data_record(raw_data)

    raw_news = RawNewsPayload(
        market="US",
        symbol="AAPL",
        published_at=datetime.now(),
        title="Earnings call preview",
        summary="Apple prepares to announce earnings.",
        source_name="marketaux",
        source_type="news",
        url="https://example.com/article",
        sentiment_score=0.6,
        raw_payload={"headline": "Earnings call preview"},
        retrieved_at=datetime.now(),
    )
    assert store.save_raw_news_record(raw_news)
    assert not store.save_raw_news_record(raw_news)

    raw_filing = RawFilingPayload(
        market="US",
        symbol="AAPL",
        form_type="8-K",
        filed_at=datetime.now(),
        title="New product announcement",
        url="https://example.com/filing",
        source_name="sec_edgar",
        source_type="filing",
        raw_payload={"form_type": "8-K"},
        retrieved_at=datetime.now(),
    )
    assert store.save_raw_filing_record(raw_filing)

    raw_options = RawOptionsPayload(
        market="US",
        symbol="AAPL",
        as_of_date="2026-07-15",
        field_name="call_avg_iv",
        numeric_value=0.25,
        text_value=None,
        source_name="yfinance",
        source_type="options",
        raw_payload={"expiry": "2026-07-15"},
        retrieved_at=datetime.now(),
    )
    store.save_raw_options_record(raw_options)

    raw_macro = RawMacroPayload(
        market="US",
        macro_name="VIX",
        as_of_date="2026-07-08",
        numeric_value=18.5,
        text_value=None,
        source_name="fred",
        source_type="macro",
        raw_payload={"series_id": "VIX"},
        retrieved_at=datetime.now(),
    )
    store.save_raw_macro_record(raw_macro)

    raw_event = RawEventPayload(
        market="US",
        symbol="AAPL",
        event_type="earnings",
        event_date=datetime.now(),
        description="Earnings release scheduled.",
        source_name="company_site",
        source_type="event",
        raw_payload={"event": "earnings"},
        retrieved_at=datetime.now(),
    )
    store.save_raw_event_record(raw_event)


def test_raw_record_deduplication_and_update(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'raw_ingestion_dedup_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()

    raw_data = RawDataPoint(
        market="US",
        symbol="AAPL",
        as_of_date="2026-07-08",
        data_type="price",
        field_name="volume",
        numeric_value=1000000.0,
        source_name="yfinance",
        source_type="market",
        raw_payload={"volume": 1000000},
        retrieved_at=datetime.now(),
    )
    store.save_raw_data_record(raw_data)
    raw_data.numeric_value = 1200000.0
    store.save_raw_data_record(raw_data)

    # The record should be updated, not duplicated.
    with store.session_factory() as session:
        count = session.query(RawDataRecord).filter(
            RawDataRecord.market == "US",
            RawDataRecord.symbol == "AAPL",
            RawDataRecord.as_of_date == "2026-07-08",
            RawDataRecord.field_name == "volume",
        ).count()
        assert count == 1

    raw_macro = RawMacroPayload(
        market="US",
        macro_name="VIX",
        as_of_date="2026-07-08",
        numeric_value=18.5,
        text_value=None,
        source_name="fred",
        source_type="macro",
        raw_payload={"series_id": "VIX"},
        retrieved_at=datetime.now(),
    )
    store.save_raw_macro_record(raw_macro)
    raw_macro.numeric_value = 19.0
    store.save_raw_macro_record(raw_macro)

    with store.session_factory() as session:
        count = session.query(RawMacroRecord).filter(
            RawMacroRecord.market == "US",
            RawMacroRecord.macro_name == "VIX",
            RawMacroRecord.as_of_date == "2026-07-08",
        ).count()
        assert count == 1

    raw_event = RawEventPayload(
        market="US",
        symbol="AAPL",
        event_type="earnings",
        event_date=datetime.fromisoformat("2026-07-08T15:30:00"),
        description="Earnings release scheduled.",
        source_name="company_site",
        source_type="event",
        raw_payload={"event": "earnings"},
        retrieved_at=datetime.now(),
    )
    store.save_raw_event_record(raw_event)
    raw_event.description = "Earnings release scheduled, updated."
    store.save_raw_event_record(raw_event)

    with store.session_factory() as session:
        count = session.query(RawEventRecord).filter(
            RawEventRecord.market == "US",
            RawEventRecord.symbol == "AAPL",
            RawEventRecord.event_type == "earnings",
            RawEventRecord.event_date == datetime.fromisoformat("2026-07-08T15:30:00"),
        ).count()
        assert count == 1


def test_ingestion_manager_saves_all_raw_payloads(tmp_path):
    class FakeUSAdapter(MarketAdapter):
        market = "US"

        def collect_market_data(self, symbol: str, start_date=None, end_date=None):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="price",
                    field_name="close",
                    numeric_value=150.0,
                    source_name="fake",
                    source_type="market",
                    raw_payload={"close": 150.0},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_fundamentals(self, symbol: str):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="fundamental",
                    field_name="trailing_pe",
                    numeric_value=28.0,
                    source_name="fake",
                    source_type="fundamental",
                    raw_payload={"trailingPE": 28.0},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_news(self, symbol: str, start_date=None, end_date=None):
            return [
                RawNewsPayload(
                    market="US",
                    symbol=symbol,
                    published_at=datetime.now(),
                    title="Fake news article",
                    summary="Fake summary.",
                    source_name="fake",
                    source_type="news",
                    url="https://example.com/fake",
                    sentiment_score=0.0,
                    raw_payload={"headline": "Fake"},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_filings(self, symbol: str):
            return [
                RawFilingPayload(
                    market="US",
                    symbol=symbol,
                    form_type="8-K",
                    filed_at=datetime.now(),
                    title="Fake filing",
                    url="https://example.com/fake-filing",
                    source_name="fake",
                    source_type="filing",
                    raw_payload={"form_type": "8-K"},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_options(self, symbol: str, as_of_date=None):
            return [
                RawOptionsPayload(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-15",
                    field_name="call_avg_iv",
                    numeric_value=0.22,
                    text_value=None,
                    source_name="fake",
                    source_type="options",
                    raw_payload={"expiry": "2026-07-15"},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_macro(self):
            return [
                RawMacroPayload(
                    market="US",
                    macro_name="VIX",
                    as_of_date="2026-07-08",
                    numeric_value=18.7,
                    text_value=None,
                    source_name="fake",
                    source_type="macro",
                    raw_payload={"series_id": "VIX"},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_events(self, symbol: str):
            return [
                RawEventPayload(
                    market="US",
                    symbol=symbol,
                    event_type="earnings",
                    event_date=datetime.now(),
                    description="Fake earnings event.",
                    source_name="fake",
                    source_type="event",
                    raw_payload={"event": "earnings"},
                    retrieved_at=datetime.now(),
                )
            ]

    database_url = f"sqlite:///{tmp_path / 'raw_ingestion_manager_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()
    ingestion_manager = RawSourceIngestionManager(store, adapters=[FakeUSAdapter()])

    ingestion_manager.ingest_symbol("AAPL", market="US")

    with store.session_factory() as session:
        raw_data_count = session.query(RawDataRecord).count()
        raw_price_count = session.query(RawDataRecord).filter(RawDataRecord.data_type == "price").count()
        raw_fundamental_count = session.query(RawDataRecord).filter(RawDataRecord.data_type == "fundamental").count()
        raw_news_count = session.query(RawNewsRecord).count()
        raw_filing_count = session.query(RawFilingRecord).count()
        raw_options_count = session.query(RawOptionsRecord).count()
        raw_macro_count = session.query(RawMacroRecord).count()
        raw_event_count = session.query(RawEventRecord).count()

    assert raw_data_count == 2
    assert raw_price_count == 1
    assert raw_fundamental_count == 1
    assert raw_news_count == 1
    assert raw_filing_count == 1
    assert raw_options_count == 1
    assert raw_macro_count == 1
    assert raw_event_count == 1


def test_ingestion_manager_and_feature_pipeline_integration(tmp_path):
    class FakeUSAdapter(MarketAdapter):
        market = "US"

        def collect_market_data(self, symbol: str, start_date=None, end_date=None):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="price",
                    field_name="close",
                    numeric_value=150.0,
                    source_name="fake",
                    source_type="market",
                    raw_payload={"close": 150.0},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_fundamentals(self, symbol: str):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="fundamental",
                    field_name="trailing_pe",
                    numeric_value=28.0,
                    source_name="fake",
                    source_type="fundamental",
                    raw_payload={"trailingPE": 28.0},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_news(self, symbol: str, start_date=None, end_date=None):
            return [
                RawNewsPayload(
                    market="US",
                    symbol=symbol,
                    published_at=datetime.now(),
                    title="Integration news article",
                    summary="Integration test news.",
                    source_name="fake",
                    source_type="news",
                    url="https://example.com/integration-news",
                    sentiment_score=0.4,
                    raw_payload={"headline": "Integration news"},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_filings(self, symbol: str):
            return [
                RawFilingPayload(
                    market="US",
                    symbol=symbol,
                    form_type="8-K",
                    filed_at=datetime.now(),
                    title="Integration filing",
                    url="https://example.com/integration-filing",
                    source_name="fake",
                    source_type="filing",
                    raw_payload={"form_type": "8-K"},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_options(self, symbol: str, as_of_date=None):
            return [
                RawOptionsPayload(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    field_name="call_avg_iv",
                    numeric_value=0.30,
                    text_value=None,
                    source_name="fake",
                    source_type="options",
                    raw_payload={"expiry": "2026-07-08"},
                    retrieved_at=datetime.now(),
                ),
                RawOptionsPayload(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    field_name="put_avg_iv",
                    numeric_value=0.25,
                    text_value=None,
                    source_name="fake",
                    source_type="options",
                    raw_payload={"expiry": "2026-07-08"},
                    retrieved_at=datetime.now(),
                ),
            ]

        def collect_macro(self):
            return [
                RawMacroPayload(
                    market="US",
                    macro_name="VIX",
                    as_of_date="2026-07-08",
                    numeric_value=18.0,
                    text_value=None,
                    source_name="fake",
                    source_type="macro",
                    raw_payload={"series_id": "VIX"},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_events(self, symbol: str):
            return [
                RawEventPayload(
                    market="US",
                    symbol=symbol,
                    event_type="earnings",
                    event_date=datetime.fromisoformat("2026-07-09T09:00:00"),
                    description="Integration earnings surprise event.",
                    source_name="fake",
                    source_type="event",
                    raw_payload={"event": "earnings"},
                    retrieved_at=datetime.now(),
                )
            ]

    database_url = f"sqlite:///{tmp_path / 'raw_ingestion_feature_integration_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()
    ingestion_manager = RawSourceIngestionManager(store, adapters=[FakeUSAdapter()])

    summary = ingestion_manager.ingest_symbol("AAPL", market="US")
    assert summary["market_data_saved"] == 1
    assert summary["fundamentals_saved"] == 1
    assert summary["news_saved"] == 1
    assert summary["filings_saved"] == 1
    assert summary["options_saved"] == 2
    assert summary["events_saved"] == 1
    assert summary["macro_saved"] == 1
    assert summary["errors"] == []

    pipeline = FeatureEngineeringPipeline(store)
    features = pipeline.build_features_for_symbol("AAPL", market="US", as_of_date="2026-07-08")
    assert len(features) > 0
    feature_names = {feature.feature_name for feature in features}
    assert "close" in feature_names
    assert "fundamental_trailing_pe" in feature_names
    assert "news_count_7d" in feature_names
    assert "options_avg_iv" in feature_names
    assert "macro_VIX" in feature_names
    assert "event_has_earnings_surprise" in feature_names or "event_count_7d" in feature_names

    saved_features = store.get_feature_rows("US", "AAPL", as_of_date="2026-07-08")
    assert any(row["feature_name"] == "close" for row in saved_features)
    assert any(row["feature_name"] == "fundamental_trailing_pe" for row in saved_features)
    assert any(row["feature_name"] == "news_count_7d" for row in saved_features)
    assert any(row["feature_name"] == "options_avg_iv" for row in saved_features)


def test_ingestion_positions_aggregates_multiple_symbols(tmp_path):
    class FakeUSAdapter(MarketAdapter):
        market = "US"

        def collect_market_data(self, symbol: str, start_date=None, end_date=None):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="price",
                    field_name="close",
                    numeric_value=150.0,
                    source_name="fake",
                    source_type="market",
                    raw_payload={"close": 150.0},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_fundamentals(self, symbol: str):
            return []

        def collect_news(self, symbol: str, start_date=None, end_date=None):
            return []

        def collect_filings(self, symbol: str):
            return []

        def collect_options(self, symbol: str, as_of_date=None):
            return []

        def collect_macro(self):
            return []

        def collect_events(self, symbol: str):
            return []

    database_url = f"sqlite:///{tmp_path / 'raw_ingestion_positions_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()
    ingestion_manager = RawSourceIngestionManager(store, adapters=[FakeUSAdapter()])

    summary = ingestion_manager.ingest_positions(["aapl", "MSFT", "AAPL"], market="US")
    assert summary["symbols"] == ["AAPL", "MSFT"]
    assert summary["market_data_saved"] == 2
    assert summary["errors"] == []

    with store.session_factory() as session:
        assert session.query(RawDataRecord).filter(RawDataRecord.symbol == "AAPL").count() == 1
        assert session.query(RawDataRecord).filter(RawDataRecord.symbol == "MSFT").count() == 1


def test_ingestion_and_feature_pipeline_debug_status(tmp_path):
    class DebugAdapter(MarketAdapter):
        market = "US"

        def collect_market_data(self, symbol: str, start_date=None, end_date=None):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="price",
                    field_name="close",
                    numeric_value=150.0,
                    source_name="fake",
                    source_type="market",
                    raw_payload={"close": 150.0},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_fundamentals(self, symbol: str):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="fundamental",
                    field_name="trailing_pe",
                    numeric_value=28.0,
                    source_name="fake",
                    source_type="fundamental",
                    raw_payload={"trailingPE": 28.0},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_news(self, symbol: str, start_date=None, end_date=None):
            return []

        def collect_filings(self, symbol: str):
            return []

        def collect_options(self, symbol: str, as_of_date=None):
            return []

        def collect_macro(self):
            return []

        def collect_events(self, symbol: str):
            return []

    database_url = f"sqlite:///{tmp_path / 'raw_ingestion_debug_status_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()
    ingestion_manager = RawSourceIngestionManager(store, adapters=[DebugAdapter()])

    ingestion_manager.ingest_symbol("AAPL", market="US")
    pipeline = FeatureEngineeringPipeline(store)
    pipeline.build_features_for_symbol("AAPL", market="US", as_of_date="2026-07-08")

    status = store.get_debug_ingestion_status()
    assert status["raw_data_records"]["count"] == 2
    assert status["feature_records"]["count"] > 0
    assert status["raw_data_records"]["latest_timestamp"] is not None
    assert status["feature_records"]["latest_timestamp"] is not None


def test_ingestion_manager_continues_after_partial_adapter_failure(tmp_path):
    class PartialFailureAdapter(MarketAdapter):
        market = "US"

        def collect_market_data(self, symbol: str, start_date=None, end_date=None):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="price",
                    field_name="close",
                    numeric_value=150.0,
                    source_name="fake",
                    source_type="market",
                    raw_payload={"close": 150.0},
                    retrieved_at=datetime.now(),
                )
            ]

        def collect_fundamentals(self, symbol: str):
            raise RuntimeError("fundamentals source unavailable")

        def collect_news(self, symbol: str, start_date=None, end_date=None):
            return []

        def collect_filings(self, symbol: str):
            return []

        def collect_options(self, symbol: str, as_of_date=None):
            return []

        def collect_macro(self):
            return []

        def collect_events(self, symbol: str):
            return []

    database_url = f"sqlite:///{tmp_path / 'raw_ingestion_partial_failure_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()
    ingestion_manager = RawSourceIngestionManager(store, adapters=[PartialFailureAdapter()])

    summary = ingestion_manager.ingest_symbol("AAPL", market="US")

    with store.session_factory() as session:
        raw_data_count = session.query(RawDataRecord).count()

    assert raw_data_count == 1
    assert summary["market_data_saved"] == 1
    assert "fundamentals collection failed" in summary["errors"][0]


def test_ingestion_manager_idempotency(tmp_path):
    now = datetime.now()

    class IdempotentAdapter(MarketAdapter):
        market = "US"

        def collect_market_data(self, symbol: str, start_date=None, end_date=None):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="price",
                    field_name="close",
                    numeric_value=150.0,
                    source_name="fake",
                    source_type="market",
                    raw_payload={"close": 150.0},
                    retrieved_at=now,
                )
            ]

        def collect_fundamentals(self, symbol: str):
            return [
                RawDataPoint(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-08",
                    data_type="fundamental",
                    field_name="trailing_pe",
                    numeric_value=28.0,
                    source_name="fake",
                    source_type="fundamental",
                    raw_payload={"trailingPE": 28.0},
                    retrieved_at=now,
                )
            ]

        def collect_news(self, symbol: str, start_date=None, end_date=None):
            return [
                RawNewsPayload(
                    market="US",
                    symbol=symbol,
                    published_at=now,
                    title="Fake news article",
                    summary="Fake summary.",
                    source_name="fake",
                    source_type="news",
                    url="https://example.com/fake",
                    sentiment_score=0.0,
                    raw_payload={"headline": "Fake"},
                    retrieved_at=now,
                )
            ]

        def collect_filings(self, symbol: str):
            return [
                RawFilingPayload(
                    market="US",
                    symbol=symbol,
                    form_type="8-K",
                    filed_at=now,
                    title="Fake filing",
                    url="https://example.com/fake-filing",
                    source_name="fake",
                    source_type="filing",
                    raw_payload={"form_type": "8-K"},
                    retrieved_at=now,
                )
            ]

        def collect_options(self, symbol: str, as_of_date=None):
            return [
                RawOptionsPayload(
                    market="US",
                    symbol=symbol,
                    as_of_date="2026-07-15",
                    field_name="call_avg_iv",
                    numeric_value=0.22,
                    text_value=None,
                    source_name="fake",
                    source_type="options",
                    raw_payload={"expiry": "2026-07-15"},
                    retrieved_at=now,
                )
            ]

        def collect_macro(self):
            return [
                RawMacroPayload(
                    market="US",
                    macro_name="VIX",
                    as_of_date="2026-07-08",
                    numeric_value=18.7,
                    text_value=None,
                    source_name="fake",
                    source_type="macro",
                    raw_payload={"series_id": "VIX"},
                    retrieved_at=now,
                )
            ]

        def collect_events(self, symbol: str):
            return [
                RawEventPayload(
                    market="US",
                    symbol=symbol,
                    event_type="earnings",
                    event_date=now,
                    description="Fake earnings event.",
                    source_name="fake",
                    source_type="event",
                    raw_payload={"event": "earnings"},
                    retrieved_at=now,
                )
            ]

    database_url = f"sqlite:///{tmp_path / 'raw_ingestion_idempotency_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()
    ingestion_manager = RawSourceIngestionManager(store, adapters=[IdempotentAdapter()])

    ingestion_manager.ingest_symbol("AAPL", market="US")
    ingestion_manager.ingest_symbol("AAPL", market="US")

    with store.session_factory() as session:
        assert session.query(RawDataRecord).filter(RawDataRecord.data_type == "price").count() == 1
        assert session.query(RawDataRecord).filter(RawDataRecord.data_type == "fundamental").count() == 1
        assert session.query(RawNewsRecord).count() == 1
        assert session.query(RawFilingRecord).count() == 1
        assert session.query(RawOptionsRecord).count() == 1
        assert session.query(RawMacroRecord).count() == 1
        assert session.query(RawEventRecord).count() == 1
