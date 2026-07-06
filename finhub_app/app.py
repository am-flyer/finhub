from datetime import UTC, datetime

from finhub_app.collectors import (
    FinnhubCollector,
    MarketauxCollector,
    SecEdgarCollector,
    YFinanceCollector,
    collect_for_positions,
)
from finhub_app.config import get_settings
from finhub_app.domain import ReportContext
from finhub_app.processing import calculate_impact_scores, deduplicate_news
from finhub_app.reporting import GeminiReportGenerator, OpenAIReportGenerator
from finhub_app.storage import PortfolioStore


def generate_daily_report() -> str:
    settings = get_settings()
    store = PortfolioStore(settings.database_url)
    store.initialize()

    positions = store.list_positions()
    profile = store.get_profile(settings.monthly_investment_budget_usd)

    snapshots, raw_news, filings = collect_for_positions(
        positions=positions,
        market_collector=YFinanceCollector(),
        news_collectors=[
            FinnhubCollector(settings.finnhub_api_key),
            MarketauxCollector(settings.marketaux_api_key),
        ],
        filing_collector=SecEdgarCollector(),
    )
    news = deduplicate_news(raw_news)
    impacts = calculate_impact_scores(snapshots, news)

    context = ReportContext(
        generated_for=datetime.now(UTC),
        profile=profile,
        positions=positions,
        market_snapshots=snapshots,
        news=news,
        filings=filings,
        impacts=impacts,
    )

    provider = settings.llm_provider.strip().lower()
    if provider == "gemini":
        gemini_key = settings.gemini_api_key or settings.google_api_key
        if not gemini_key:
            return "GEMINI_API_KEY or GOOGLE_API_KEY is missing. Add one to .env before generating reports."
        return GeminiReportGenerator(
            api_key=gemini_key,
            model=settings.gemini_model,
        ).generate(context)

    if provider == "openai":
        if not settings.openai_api_key:
            return "OPENAI_API_KEY is missing. Add it to .env before generating reports."
        return OpenAIReportGenerator(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        ).generate(context)

    return f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. Use 'gemini' or 'openai'."
