from collections import defaultdict
from hashlib import sha256

from finhub_app.domain import (
    BusinessQualityAssessment,
    FundamentalSnapshot,
    ImpactAssessment,
    MarketSnapshot,
    MetricEvaluation,
    NewsItem,
)


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


def calculate_business_quality_scores(
    fundamentals: list[FundamentalSnapshot],
) -> list[BusinessQualityAssessment]:
    assessments: list[BusinessQualityAssessment] = []

    for item in fundamentals:
        metrics = [
            _rate_growth(
                "Revenue Growth",
                item.revenue_growth,
                "Revenue is increasing.",
                "Revenue is flat or only slightly changed.",
                "Revenue is declining.",
            ),
            _rate_growth(
                "EPS Growth",
                item.eps_growth,
                "Earnings per share are increasing.",
                "Earnings per share are flat or only slightly changed.",
                "Earnings per share are declining.",
            ),
            _rate_free_cash_flow(item.free_cash_flow, item.free_cash_flow_growth),
            _rate_debt(item.debt_to_equity),
            _rate_roe(item.return_on_equity),
            _rate_dividend(item.dividend_yield, item.payout_ratio),
            _rate_valuation(item.trailing_pe, item.forward_pe, item.peg_ratio),
            _rate_moat_proxy(item.profit_margin, item.gross_margin, item.market_cap),
        ]
        score = sum(1 for metric in metrics if metric.rating == "good")
        rating = _overall_quality_rating(score)
        assessments.append(
            BusinessQualityAssessment(
                symbol=item.symbol,
                score=score,
                rating=rating,
                metrics=metrics,
                reason=(
                    f"{item.symbol} has a business quality score of {score}/8. "
                    f"This is separate from the short-term news impact score."
                ),
                risks=_business_quality_risks(item, metrics),
            )
        )

    return assessments


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


def _rate_growth(
    metric: str,
    growth: float | None,
    good_reason: str,
    okay_reason: str,
    bad_reason: str,
) -> MetricEvaluation:
    if growth is None:
        return MetricEvaluation(
            metric=metric,
            rating="unknown",
            value=None,
            reason="Not enough recent financial statement data was available.",
        )

    if growth > 0.03:
        rating = "good"
        reason = good_reason
    elif growth >= -0.03:
        rating = "okay"
        reason = okay_reason
    else:
        rating = "bad"
        reason = bad_reason

    return MetricEvaluation(
        metric=metric,
        rating=rating,
        value=_format_percent(growth),
        reason=reason,
    )


def _rate_free_cash_flow(
    free_cash_flow: float | None, free_cash_flow_growth: float | None
) -> MetricEvaluation:
    if free_cash_flow is None:
        return MetricEvaluation(
            metric="Free Cash Flow",
            rating="unknown",
            value=None,
            reason="Free cash flow data was not available.",
        )

    if free_cash_flow > 0 and (free_cash_flow_growth is None or free_cash_flow_growth >= 0):
        rating = "good"
        reason = "Free cash flow is positive and not shrinking based on available data."
    elif free_cash_flow > 0:
        rating = "okay"
        reason = "Free cash flow is positive, but recent growth is weaker."
    else:
        rating = "bad"
        reason = "Free cash flow is negative, which can pressure the business."

    growth_text = (
        f", growth {_format_percent(free_cash_flow_growth)}"
        if free_cash_flow_growth is not None
        else ""
    )
    return MetricEvaluation(
        metric="Free Cash Flow",
        rating=rating,
        value=f"{_format_large_number(free_cash_flow)}{growth_text}",
        reason=reason,
    )


def _rate_debt(debt_to_equity: float | None) -> MetricEvaluation:
    if debt_to_equity is None:
        return MetricEvaluation(
            metric="Debt",
            rating="unknown",
            value=None,
            reason="Debt-to-equity data was not available.",
        )

    ratio = debt_to_equity / 100
    if ratio < 0.75:
        rating = "good"
        reason = "Debt looks low relative to shareholder equity."
    elif ratio <= 1.5:
        rating = "okay"
        reason = "Debt looks moderate and should be watched."
    else:
        rating = "bad"
        reason = "Debt looks high relative to shareholder equity."

    return MetricEvaluation(
        metric="Debt",
        rating=rating,
        value=f"Debt/equity {ratio:.2f}",
        reason=reason,
    )


def _rate_roe(return_on_equity: float | None) -> MetricEvaluation:
    if return_on_equity is None:
        return MetricEvaluation(
            metric="ROE",
            rating="unknown",
            value=None,
            reason="Return on equity data was not available.",
        )

    if return_on_equity > 0.15:
        rating = "good"
        reason = "ROE is above 15%, which can indicate efficient use of capital."
    elif return_on_equity >= 0.10:
        rating = "okay"
        reason = "ROE is in the 10% to 15% range."
    else:
        rating = "bad"
        reason = "ROE is below 10%, which may indicate weaker profitability."

    return MetricEvaluation(
        metric="ROE",
        rating=rating,
        value=_format_percent(return_on_equity),
        reason=reason,
    )


def _rate_dividend(
    dividend_yield: float | None, payout_ratio: float | None
) -> MetricEvaluation:
    if not dividend_yield:
        return MetricEvaluation(
            metric="Dividend Safety",
            rating="okay",
            value="No meaningful dividend",
            reason="Dividend safety is less relevant because this stock does not appear to pay a meaningful dividend.",
        )

    if payout_ratio is None:
        return MetricEvaluation(
            metric="Dividend Safety",
            rating="unknown",
            value=f"Yield {_format_percent(dividend_yield)}",
            reason="Dividend yield is available, but payout coverage was not available.",
        )

    if payout_ratio < 0.65:
        rating = "good"
        reason = "The dividend appears well covered by earnings."
    elif payout_ratio <= 0.85:
        rating = "okay"
        reason = "The dividend coverage is borderline and should be monitored."
    else:
        rating = "bad"
        reason = "The payout ratio looks high, so the dividend could be at risk."

    return MetricEvaluation(
        metric="Dividend Safety",
        rating=rating,
        value=f"Yield {_format_percent(dividend_yield)}, payout {_format_percent(payout_ratio)}",
        reason=reason,
    )


def _rate_valuation(
    trailing_pe: float | None, forward_pe: float | None, peg_ratio: float | None
) -> MetricEvaluation:
    if peg_ratio is not None:
        if peg_ratio < 1:
            rating = "good"
            reason = "PEG is below 1, which may suggest a fair price relative to growth."
        elif peg_ratio <= 2:
            rating = "okay"
            reason = "PEG is between 1 and 2, which is a moderate valuation signal."
        else:
            rating = "bad"
            reason = "PEG is above 2, which can indicate a richer valuation."
    elif forward_pe is not None or trailing_pe is not None:
        pe = forward_pe if forward_pe is not None else trailing_pe
        if pe is not None and pe < 20:
            rating = "good"
            reason = "P/E looks moderate based on available data."
        elif pe is not None and pe <= 35:
            rating = "okay"
            reason = "P/E is not cheap, but not extreme for many growth companies."
        else:
            rating = "bad"
            reason = "P/E looks high based on available data."
    else:
        return MetricEvaluation(
            metric="P/E / Forward P/E / PEG",
            rating="unknown",
            value=None,
            reason="Valuation ratios were not available.",
        )

    values = []
    if trailing_pe is not None:
        values.append(f"P/E {trailing_pe:.2f}")
    if forward_pe is not None:
        values.append(f"forward P/E {forward_pe:.2f}")
    if peg_ratio is not None:
        values.append(f"PEG {peg_ratio:.2f}")

    return MetricEvaluation(
        metric="P/E / Forward P/E / PEG",
        rating=rating,
        value=", ".join(values),
        reason=reason,
    )


def _rate_moat_proxy(
    profit_margin: float | None, gross_margin: float | None, market_cap: float | None
) -> MetricEvaluation:
    margin_score = 0
    if profit_margin is not None and profit_margin >= 0.15:
        margin_score += 1
    if gross_margin is not None and gross_margin >= 0.35:
        margin_score += 1
    if market_cap is not None and market_cap >= 10_000_000_000:
        margin_score += 1

    if margin_score >= 2:
        rating = "good"
        reason = "Available margin and size signals suggest a stronger competitive position."
    elif margin_score == 1:
        rating = "okay"
        reason = "Available data suggests some competitive strength, but the moat is not obvious."
    else:
        rating = "bad"
        reason = "Available data does not show a strong moat signal."

    values = []
    if profit_margin is not None:
        values.append(f"net margin {_format_percent(profit_margin)}")
    if gross_margin is not None:
        values.append(f"gross margin {_format_percent(gross_margin)}")
    if market_cap is not None:
        values.append(f"market cap {_format_large_number(market_cap)}")

    return MetricEvaluation(
        metric="Competitive Advantage (Moat)",
        rating=rating,
        value=", ".join(values) if values else None,
        reason=f"{reason} This is a proxy estimate, not a definitive moat rating.",
    )


def _overall_quality_rating(score: int) -> str:
    if score >= 6:
        return "strong"
    if score >= 4:
        return "average"
    return "weak"


def _business_quality_risks(
    snapshot: FundamentalSnapshot, metrics: list[MetricEvaluation]
) -> list[str]:
    risks = ["Fundamental data can lag and may not reflect the latest quarter."]
    if any(metric.rating == "unknown" for metric in metrics):
        risks.append("Some metrics were unavailable, so the quality score is incomplete.")
    if snapshot.notes:
        risks.extend(snapshot.notes[:2])
    risks.append("Business quality is separate from price timing and is not financial advice.")
    return risks


def _format_percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _format_large_number(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.0f}"
