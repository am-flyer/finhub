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
    news: list[NewsItem]
    filings: list[FilingItem]
    impacts: list[ImpactAssessment]
