import os
from datetime import datetime
from pathlib import Path

from finhub_app.config import Settings
from finhub_app.feature_store import FeatureEngineeringPipeline
from finhub_app.orchestration import DataPipelineOrchestrator, build_pipeline_scheduler
from finhub_app.storage import PortfolioStore, RawDataRecord


class FakeIngestionManager:
    def __init__(self, store: PortfolioStore) -> None:
        self.store = store

    def ingest_symbol(self, symbol: str, market: str = "US", start_date: str | None = None, end_date: str | None = None) -> None:
        symbol = symbol.strip().upper()
        close_prices = [100.0, 102.0, 101.0, 103.0]
        dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"]
        for date_str, close_price in zip(dates, close_prices):
            for field_name, numeric_value in [
                ("open", close_price - 1.0),
                ("high", close_price + 1.0),
                ("low", close_price - 2.0),
                ("close", close_price),
                ("volume", 1_000_000.0),
            ]:
                self.store.save_raw_data_record(
                    RawDataRecord(
                        market=market,
                        symbol=symbol,
                        as_of_date=date_str,
                        data_type="price",
                        field_name=field_name,
                        numeric_value=numeric_value,
                        text_value=None,
                        source_name="fake",
                        source_type="market",
                        raw_payload=None,
                        retrieved_at=datetime.now(),
                    )
                )


def test_orchestrator_sync_symbol_builds_features_and_records(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'orchestrator_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()
    ingestion_manager = FakeIngestionManager(store)
    feature_pipeline = FeatureEngineeringPipeline(store)
    orchestrator = DataPipelineOrchestrator(
        store,
        ingestion_manager=ingestion_manager,
        feature_pipeline=feature_pipeline,
    )

    result = orchestrator.sync_symbol(
        "AAPL",
        market="US",
        start_date="2026-07-01",
        end_date="2026-07-04",
        as_of_date="2026-07-04",
    )

    assert result["status"] == "success"
    assert result["feature_count"] > 0
    assert result["symbol"] == "AAPL"

    job_statuses = store.list_pipeline_job_statuses()
    assert any(job["job_type"] == "sync_symbol" and job["status"] == "success" for job in job_statuses)
    assert any(job["job_type"] == "ingest_symbol" for job in job_statuses)
    assert any(job["job_type"] == "build_features" for job in job_statuses)


def test_build_pipeline_scheduler_creates_daily_job(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'scheduler_test.db'}",
        pre_market_report_hour=6,
        pre_market_report_minute=30,
    )
    store = PortfolioStore(settings.database_url)
    store.initialize()
    orchestrator = DataPipelineOrchestrator(
        store,
        ingestion_manager=FakeIngestionManager(store),
        feature_pipeline=FeatureEngineeringPipeline(store),
    )

    scheduler = build_pipeline_scheduler(settings, orchestrator)
    jobs = scheduler.get_jobs()

    assert len(jobs) == 1
    assert jobs[0].id == "daily_pipeline_sync"
    assert "cron" in str(jobs[0].trigger).lower()
