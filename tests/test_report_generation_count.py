from pathlib import Path

from finhub_app.app import generate_daily_report
from finhub_app.domain import AssetScope, Position
from finhub_app.storage import PortfolioStore


class DummySettings:
    database_url: str
    monthly_investment_budget_usd: float = 100.0
    finnhub_api_key: str = ""
    marketaux_api_key: str = ""
    llm_provider: str = "gemini"
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"


def test_generate_daily_report_saves_snapshot_when_llm_keys_missing(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    settings = DummySettings()
    settings.database_url = f"sqlite:///{db_path}"

    monkeypatch.setattr("finhub_app.app.get_settings", lambda: settings)
    monkeypatch.setattr("finhub_app.app.collect_for_positions", lambda **kwargs: ([], [], [], []))
    monkeypatch.setattr("finhub_app.app.calculate_impact_scores", lambda snapshots, news: [])
    monkeypatch.setattr("finhub_app.app.calculate_business_quality_scores", lambda fundamentals: [])
    monkeypatch.setattr("finhub_app.app.deduplicate_news", lambda news: [])

    store = PortfolioStore(settings.database_url)
    store.initialize()
    store.upsert_position(
        Position(
            symbol="AAPL",
            name="Apple",
            quantity=10,
            average_cost=100.0,
            scope=AssetScope.HOLDING,
        )
    )
    store.upsert_position(
        Position(
            symbol="MSFT",
            name="Microsoft",
            quantity=1,
            average_cost=200.0,
            scope=AssetScope.WATCHLIST,
        )
    )

    generate_daily_report()

    reports = store.list_reports()
    assert len(reports) == 1
    assert reports[0]["holding_count"] == 1
    assert reports[0]["watchlist_count"] == 1
