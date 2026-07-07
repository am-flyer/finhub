from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class AssetScope(str, Enum):
    HOLDING = "holding"
    WATCHLIST = "watchlist"


class Position(BaseModel):
    symbol: str
    name: str | None = None
    quantity: float = 0
    average_cost: float | None = None
    scope: AssetScope = AssetScope.HOLDING
    added_at: datetime | None = None


class UserProfile(BaseModel):
    monthly_budget_usd: float = 100
    beginner: bool = True
    risk_notes: list[str] = Field(default_factory=list)


class NewsItem(BaseModel):
    symbol: str
    title: str
    summary: str | None = None
    source: str
    published_at: datetime | None = None
    url: HttpUrl | None = None
    sentiment_score: float | None = None


class FilingItem(BaseModel):
    symbol: str
    form_type: str
    filed_at: datetime | None = None
    title: str
    url: HttpUrl | None = None


class MarketSnapshot(BaseModel):
    symbol: str
    latest_price: float | None = None
    previous_close: float | None = None
    technical_summary: str | None = None


class MetricEvaluation(BaseModel):
    metric: str
    rating: str
    value: str | None = None
    reason: str


class FundamentalSnapshot(BaseModel):
    symbol: str
    revenue_growth: float | None = None
    eps_growth: float | None = None
    free_cash_flow: float | None = None
    free_cash_flow_growth: float | None = None
    debt_to_equity: float | None = None
    return_on_equity: float | None = None
    dividend_yield: float | None = None
    payout_ratio: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    peg_ratio: float | None = None
    profit_margin: float | None = None
    gross_margin: float | None = None
    market_cap: float | None = None
    notes: list[str] = Field(default_factory=list)


class BusinessQualityAssessment(BaseModel):
    symbol: str
    score: int = Field(ge=0, le=8)
    max_score: int = 8
    rating: str
    metrics: list[MetricEvaluation]
    reason: str
    risks: list[str] = Field(default_factory=list)


class ImpactAssessment(BaseModel):
    symbol: str
    score: int = Field(ge=-100, le=100)
    reason: str
    risks: list[str] = Field(default_factory=list)
    source_titles: list[str] = Field(default_factory=list)


class ReportContext(BaseModel):
    generated_for: datetime
    profile: UserProfile
    positions: list[Position]
    market_snapshots: list[MarketSnapshot]
    fundamental_snapshots: list[FundamentalSnapshot]
    news: list[NewsItem]
    filings: list[FilingItem]
    impacts: list[ImpactAssessment]
    business_quality: list[BusinessQualityAssessment]


class Report(BaseModel):
    id: int | None = None
    created_at: datetime | None = None
    title: str = "Daily Pre-Market Investment Report"
    content: str
    summary: str | None = None
    holding_count: int = 0
    watchlist_count: int = 0
    generated_for: datetime
    profile: UserProfile
    positions: list[Position]
    market_snapshots: list[MarketSnapshot]
    fundamental_snapshots: list[FundamentalSnapshot]
    news: list[NewsItem]
    filings: list[FilingItem]
    impacts: list[ImpactAssessment]
    business_quality: list[BusinessQualityAssessment]
