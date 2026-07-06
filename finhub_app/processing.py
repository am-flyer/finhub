from collections import defaultdict
from hashlib import sha256

from finhub_app.domain import ImpactAssessment, MarketSnapshot, NewsItem


def deduplicate_news(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    deduped: list[NewsItem] = []

    for item in items:
        key_text = f"{item.symbol}|{item.title.strip().lower()}"
        key = sha256(key_text.encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def calculate_impact_scores(
    snapshots: list[MarketSnapshot], news: list[NewsItem]
) -> list[ImpactAssessment]:
    news_by_symbol: dict[str, list[NewsItem]] = defaultdict(list)
    for item in news:
        news_by_symbol[item.symbol].append(item)

    snapshot_by_symbol = {snapshot.symbol: snapshot for snapshot in snapshots}
    symbols = sorted(set(snapshot_by_symbol) | set(news_by_symbol))
    impacts: list[ImpactAssessment] = []

    for symbol in symbols:
        sentiment_values = [
            item.sentiment_score
            for item in news_by_symbol[symbol]
            if item.sentiment_score is not None
        ]
        sentiment_component = (
            sum(sentiment_values) / len(sentiment_values) if sentiment_values else 0
        )

        snapshot = snapshot_by_symbol.get(symbol)
        price_component = 0.0
        if snapshot and snapshot.latest_price and snapshot.previous_close:
            price_change = (
                snapshot.latest_price - snapshot.previous_close
            ) / snapshot.previous_close
            price_component = max(min(price_change * 5, 1), -1)

        raw_score = (sentiment_component * 70) + (price_component * 30)
        score = int(max(min(round(raw_score), 100), -100))
        reason = _build_reason(symbol, score, len(news_by_symbol[symbol]))
        impacts.append(
            ImpactAssessment(
                symbol=symbol,
                score=score,
                reason=reason,
                risks=_default_risks(score),
                source_titles=[item.title for item in news_by_symbol[symbol][:5]],
            )
        )

    return impacts


def _build_reason(symbol: str, score: int, news_count: int) -> str:
    if score > 25:
        direction = "positive"
    elif score < -25:
        direction = "negative"
    else:
        direction = "mixed or neutral"

    return (
        f"{symbol} currently has a {direction} impact score based on "
        f"{news_count} recent news item(s), available sentiment, and price movement."
    )


def _default_risks(score: int) -> list[str]:
    risks = ["Short-term news can reverse quickly."]
    if score > 25:
        risks.append("Positive momentum does not guarantee future gains.")
    elif score < -25:
        risks.append("A negative score may reflect temporary uncertainty, not permanent damage.")
    else:
        risks.append("Neutral scores can hide company-specific risks that need review.")
    return risks
