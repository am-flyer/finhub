from datetime import datetime

from sqlalchemy import inspect

from finhub_app.domain import RawDataPoint, RawFilingPayload, RawMacroPayload, RawNewsPayload, RawOptionsPayload, RawEventPayload
from finhub_app.storage import PortfolioStore


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
