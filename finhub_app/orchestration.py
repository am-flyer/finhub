from __future__ import annotations

from datetime import datetime
from typing import Iterable

from apscheduler.schedulers.background import BackgroundScheduler

from finhub_app.config import Settings, get_settings
from finhub_app.domain import AssetScope
from finhub_app.feature_store import create_feature_engineering_pipeline
from finhub_app.ingestion import create_default_us_ingestion_manager
from finhub_app.storage import PortfolioStore


class DataPipelineOrchestrator:
    def __init__(self, store: PortfolioStore) -> None:
        self.store = store
        self.ingestion_manager = create_default_us_ingestion_manager(store)
        self.feature_pipeline = create_feature_engineering_pipeline(store)

    def ingest_symbol(
        self,
        symbol: str,
        market: str = "US",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        job_id = self.store.create_pipeline_job_status(
            job_type="ingest_symbol",
            market=market,
            target_symbol=symbol,
            status="running",
            details=f"Ingesting raw data for {symbol} in {market}",
        )
        try:
            start_dt = datetime.fromisoformat(start_date) if start_date else None
            end_dt = datetime.fromisoformat(end_date) if end_date else None
            self.ingestion_manager.ingest_symbol(symbol, market=market, start_date=start_dt, end_date=end_dt)
            self.store.update_pipeline_job_status(job_id, "success", details=f"Raw ingestion completed for {symbol}")
            return {"job_id": job_id, "symbol": symbol, "status": "success"}
        except Exception as exc:
            self.store.update_pipeline_job_status(job_id, "failed", details=str(exc))
            raise

    def build_features_for_symbol(
        self,
        symbol: str,
        market: str = "US",
        as_of_date: str | None = None,
    ) -> dict:
        job_id = self.store.create_pipeline_job_status(
            job_type="build_features",
            market=market,
            target_symbol=symbol,
            status="running",
            details=f"Building feature records for {symbol} in {market}",
        )
        try:
            features = self.feature_pipeline.build_features_for_symbol(symbol, market=market, as_of_date=as_of_date)
            self.store.update_pipeline_job_status(
                job_id,
                "success",
                details=f"Built {len(features)} feature rows for {symbol}",
                record_count=len(features),
            )
            return {"job_id": job_id, "symbol": symbol, "market": market, "feature_count": len(features), "status": "success"}
        except Exception as exc:
            self.store.update_pipeline_job_status(job_id, "failed", details=str(exc))
            raise

    def sync_symbol(
        self,
        symbol: str,
        market: str = "US",
        start_date: str | None = None,
        end_date: str | None = None,
        as_of_date: str | None = None,
    ) -> dict:
        job_id = self.store.create_pipeline_job_status(
            job_type="sync_symbol",
            market=market,
            target_symbol=symbol,
            status="running",
            details=f"Syncing raw ingestion and feature build for {symbol} in {market}",
        )
        try:
            self.ingest_symbol(symbol, market=market, start_date=start_date, end_date=end_date)
            result = self.build_features_for_symbol(symbol, market=market, as_of_date=as_of_date)
            summary = f"Synced {symbol}: {result.get('feature_count', 0)} features"
            self.store.update_pipeline_job_status(job_id, "success", details=summary, record_count=result.get("feature_count"))
            return {"job_id": job_id, "symbol": symbol, "market": market, "feature_count": result.get("feature_count", 0), "status": "success"}
        except Exception as exc:
            self.store.update_pipeline_job_status(job_id, "failed", details=str(exc))
            raise

    def sync_portfolio(
        self,
        market: str = "US",
        include_watchlist: bool = False,
        start_date: str | None = None,
        end_date: str | None = None,
        as_of_date: str | None = None,
    ) -> dict:
        job_id = self.store.create_pipeline_job_status(
            job_type="sync_portfolio",
            market=market,
            status="running",
            details=f"Syncing portfolio data for {market} (include_watchlist={include_watchlist})",
        )

        positions = self.store.list_positions()
        symbols = [
            p.symbol.strip().upper()
            for p in positions
            if p.symbol.strip() and (
                p.scope == AssetScope.HOLDING or (include_watchlist and p.scope == AssetScope.WATCHLIST)
            )
        ]
        symbols = sorted(set(symbols))

        completed_symbols: list[str] = []
        failed_symbols: list[str] = []
        feature_counts: dict[str, int] = {}

        for symbol in symbols:
            try:
                self.ingest_symbol(symbol, market=market, start_date=start_date, end_date=end_date)
                result = self.build_features_for_symbol(symbol, market=market, as_of_date=as_of_date)
                completed_symbols.append(symbol)
                feature_counts[symbol] = result.get("feature_count", 0)
            except Exception:
                failed_symbols.append(symbol)
                continue

        details = (
            f"Completed: {len(completed_symbols)} symbols, failed: {len(failed_symbols)}"
            + (f", failed_symbols={failed_symbols}" if failed_symbols else "")
        )
        self.store.update_pipeline_job_status(
            job_id,
            "success" if not failed_symbols else "partial_failure",
            details=details,
            record_count=sum(feature_counts.values()) if feature_counts else 0,
        )

        return {
            "job_id": job_id,
            "market": market,
            "completed_symbols": completed_symbols,
            "failed_symbols": failed_symbols,
            "feature_counts": feature_counts,
            "status": "partial_failure" if failed_symbols else "success",
        }


def build_pipeline_scheduler(settings: Settings, orchestrator: DataPipelineOrchestrator) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=settings.market_timezone)
    scheduler.add_job(
        lambda: orchestrator.sync_portfolio(market="US", include_watchlist=False),
        trigger="cron",
        hour=settings.pre_market_report_hour,
        minute=settings.pre_market_report_minute,
        id="daily_pipeline_sync",
        replace_existing=True,
    )
    return scheduler
