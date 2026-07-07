from datetime import UTC, datetime

from finhub_app.collectors import (
    FinnhubCollector,
    MarketauxCollector,
    SecEdgarCollector,
    YFinanceCollector,
    collect_for_positions,
)
from finhub_app.config import get_settings
from finhub_app.domain import ReportContext, AssetScope
from finhub_app.processing import (
    calculate_business_quality_scores,
    calculate_impact_scores,
    deduplicate_news,
)
from finhub_app.reporting import GeminiReportGenerator, OpenAIReportGenerator
from finhub_app.storage import PortfolioStore


def generate_daily_report() -> str:
    settings = get_settings()
    store = PortfolioStore(settings.database_url)
    store.initialize()

    positions = store.list_positions()
    profile = store.get_profile(settings.monthly_investment_budget_usd)

    yfinance_collector = YFinanceCollector()
    snapshots, fundamentals, raw_news, filings = collect_for_positions(
        positions=positions,
        market_collector=yfinance_collector,
        fundamental_collector=yfinance_collector,
        news_collectors=[
            FinnhubCollector(settings.finnhub_api_key),
            MarketauxCollector(settings.marketaux_api_key),
        ],
        filing_collector=SecEdgarCollector(),
    )
    news = deduplicate_news(raw_news)
    impacts = calculate_impact_scores(snapshots, news)
    business_quality = calculate_business_quality_scores(fundamentals)

    context = ReportContext(
        generated_for=datetime.now(UTC),
        profile=profile,
        positions=positions,
        market_snapshots=snapshots,
        fundamental_snapshots=fundamentals,
        news=news,
        filings=filings,
        impacts=impacts,
        business_quality=business_quality,
    )

    provider = settings.llm_provider.strip().lower()
    content = ""
    if provider == "gemini":
        gemini_key = settings.gemini_api_key or settings.google_api_key
        if not gemini_key:
            content = "GEMINI_API_KEY or GOOGLE_API_KEY is missing. Add one to .env before generating reports."
        else:
            content = GeminiReportGenerator(
                api_key=gemini_key,
                model=settings.gemini_model,
            ).generate(context)

    elif provider == "openai":
        if not settings.openai_api_key:
            content = "OPENAI_API_KEY is missing. Add it to .env before generating reports."
        else:
            content = OpenAIReportGenerator(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            ).generate(context)
    else:
        content = f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. Use 'gemini' or 'openai'."

    # If generation succeeded and is not an error string, save it
    if "is missing" not in content and "Unsupported LLM_PROVIDER" not in content:
        try:
            holding_count = sum(1 for p in positions if p.scope == AssetScope.HOLDING)
            watchlist_count = sum(1 for p in positions if p.scope == AssetScope.WATCHLIST)
            json_data = context.model_dump_json()
            
            # Simple summary extraction
            summary = ""
            if "### 1. Plain-English Summary" in content:
                try:
                    parts = content.split("### 1. Plain-English Summary")
                    summary_part = parts[1].split("---")[0].strip()
                    paragraphs = [p.strip() for p in summary_part.split("\n\n") if p.strip()]
                    if paragraphs:
                        summary = paragraphs[0]
                except Exception:
                    pass
            if not summary:
                summary = "Pre-market daily report and analysis for your holdings and watchlist."

            # Save real-time price snapshots to PriceHistory
            date_today_str = datetime.now().strftime("%Y-%m-%d")
            for snap in snapshots:
                if snap.latest_price is not None:
                    store.save_price_history(snap.symbol, date_today_str, snap.latest_price)

            # Save real-time news to NewsRecord
            for item in news:
                store.save_news_record(
                    symbol=item.symbol,
                    published_at=item.published_at or datetime.now(),
                    title=item.title,
                    summary=item.summary,
                    source=item.source,
                    url=str(item.url) if item.url else None,
                    sentiment_score=item.sentiment_score
                )

            store.save_report(
                title="Daily Pre-Market Investment Report",
                content=content,
                summary=summary[:500] if summary else None,
                holding_count=holding_count,
                watchlist_count=watchlist_count,
                json_data=json_data
            )
        except Exception as e:
            # Print warning but still return content
            print(f"Warning: Failed to save report to database: {e}")

    return content
