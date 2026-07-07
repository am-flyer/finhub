from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, create_engine, func, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from finhub_app.config import normalize_database_url
from finhub_app.domain import AssetScope, Position, UserProfile


class Base(DeclarativeBase):
    pass


class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"

    symbol: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    average_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    scope: Mapped[str] = mapped_column(String(16), default=AssetScope.HOLDING.value)
    added_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BudgetProfile(Base):
    __tablename__ = "budget_profile"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    monthly_budget_usd: Mapped[float] = mapped_column(Float, default=100)
    beginner: Mapped[bool] = mapped_column(Boolean, default=True)


class ReportRecord(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    title: Mapped[str] = mapped_column(String(255), default="Daily Pre-Market Investment Report")
    content: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    holding_count: Mapped[int] = mapped_column(Integer, default=0)
    watchlist_count: Mapped[int] = mapped_column(Integer, default=0)
    json_data: Mapped[str | None] = mapped_column(Text, nullable=True)


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    date: Mapped[str] = mapped_column(String(10), index=True)  # YYYY-MM-DD
    close_price: Mapped[float] = mapped_column(Float)


class NewsRecord(Base):
    __tablename__ = "news_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(128))
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)


def has_useful_news_content(title: str | None, summary: str | None, url: str | None) -> bool:
    return bool((title or "").strip() and ((summary or "").strip() or (url or "").strip()))



class PortfolioStore:
    def __init__(self, database_url: str) -> None:
        normalized_url = normalize_database_url(database_url)
        if normalized_url.startswith("sqlite:///"):
            sqlite_path = normalized_url[len("sqlite:///"):]
            if sqlite_path and not sqlite_path.startswith(("/", "\\")):
                sqlite_path = str(Path(sqlite_path).resolve())
            if sqlite_path and sqlite_path != ":memory:":
                Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(normalized_url)
        self.session_factory = sessionmaker(bind=self.engine)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def list_positions(self) -> list[Position]:
        with Session(self.engine) as session:
            rows = session.query(PortfolioAsset).order_by(PortfolioAsset.symbol).all()
            return [
                Position(
                    symbol=row.symbol,
                    name=row.name,
                    quantity=row.quantity,
                    average_cost=row.average_cost,
                    scope=AssetScope(row.scope),
                    added_at=row.added_at,
                )
                for row in rows
            ]

    def upsert_position(self, position: Position) -> None:
        with Session(self.engine) as session:
            row = session.get(PortfolioAsset, position.symbol.upper())
            if row is None:
                row = PortfolioAsset(symbol=position.symbol.upper())
                session.add(row)

            row.name = position.name
            row.quantity = position.quantity
            row.average_cost = position.average_cost
            row.scope = position.scope.value
            if row.added_at is None:
                row.added_at = position.added_at or datetime.now()
            elif position.added_at is not None:
                row.added_at = position.added_at
            session.commit()

    def get_profile(self, default_budget_usd: float) -> UserProfile:
        with Session(self.engine) as session:
            profile = session.get(BudgetProfile, 1)
            if profile is None:
                return UserProfile(monthly_budget_usd=default_budget_usd)
            return UserProfile(
                monthly_budget_usd=profile.monthly_budget_usd,
                beginner=profile.beginner,
            )

    def save_report(
        self,
        title: str,
        content: str,
        summary: str | None,
        holding_count: int,
        watchlist_count: int,
        json_data: str | None = None,
    ) -> int:
        with Session(self.engine) as session:
            record = ReportRecord(
                title=title,
                content=content,
                summary=summary,
                holding_count=holding_count,
                watchlist_count=watchlist_count,
                json_data=json_data,
            )
            session.add(record)
            session.commit()
            return record.id

    def list_reports(self) -> list[dict]:
        with Session(self.engine) as session:
            rows = session.query(ReportRecord).order_by(ReportRecord.id.desc()).all()
            return [
                {
                    "id": row.id,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "title": row.title,
                    "summary": row.summary,
                    "holding_count": row.holding_count,
                    "watchlist_count": row.watchlist_count,
                }
                for row in rows
            ]

    def get_report(self, report_id: int) -> dict | None:
        with Session(self.engine) as session:
            row = session.get(ReportRecord, report_id)
            if row is None:
                return None
            return {
                "id": row.id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "title": row.title,
                "content": row.content,
                "summary": row.summary,
                "holding_count": row.holding_count,
                "watchlist_count": row.watchlist_count,
                "json_data": row.json_data,
            }

    def delete_position(self, symbol: str) -> bool:
        with Session(self.engine) as session:
            row = session.get(PortfolioAsset, symbol.upper())
            if row is not None:
                session.delete(row)
                session.commit()
                return True
            return False

    def delete_report(self, report_id: int) -> bool:
        with Session(self.engine) as session:
            row = session.get(ReportRecord, report_id)
            if row is not None:
                session.delete(row)
                session.commit()
                return True
            return False

    def save_price_history(self, symbol: str, date_str: str, price: float) -> None:
        with Session(self.engine) as session:
            record = session.query(PriceHistory).filter(
                PriceHistory.symbol == symbol.upper(),
                PriceHistory.date == date_str
            ).first()
            if record is None:
                record = PriceHistory(symbol=symbol.upper(), date=date_str, close_price=price)
                session.add(record)
            else:
                record.close_price = price
            session.commit()

    def save_news_record(
        self,
        symbol: str,
        published_at: datetime,
        title: str,
        summary: str | None,
        source: str,
        url: str | None,
        sentiment_score: float | None
    ) -> bool:
        title = (title or "").strip()
        summary = (summary or "").strip() or None
        url = (url or "").strip() or None
        if not has_useful_news_content(title, summary, url):
            return False

        with Session(self.engine) as session:
            record = session.query(NewsRecord).filter(
                NewsRecord.symbol == symbol.upper(),
                NewsRecord.title == title
            ).first()
            if record is None:
                record = NewsRecord(
                    symbol=symbol.upper(),
                    published_at=published_at,
                    title=title,
                    summary=summary,
                    source=source,
                    url=url,
                    sentiment_score=sentiment_score
                )
                session.add(record)
                session.commit()
                return True
            return False

    def get_portfolio_value_history(self) -> list[dict]:
        with Session(self.engine) as session:
            holdings = session.query(PortfolioAsset).filter(
                PortfolioAsset.scope == "holding"
            ).all()
            if not holdings:
                return []
                
            prices = session.query(PriceHistory).order_by(PriceHistory.date.asc()).all()
            by_date = {}
            for p in prices:
                if p.date not in by_date:
                    by_date[p.date] = {}
                by_date[p.date][p.symbol] = p.close_price
                
            history = []
            for d_str, symbol_prices in sorted(by_date.items()):
                val = 0.0
                cost = 0.0
                for h in holdings:
                    if h.symbol in symbol_prices:
                        val += h.quantity * symbol_prices[h.symbol]
                        cost += h.quantity * (h.average_cost or 0.0)
                if val > 0:
                    history.append({
                        "date": d_str,
                        "value": round(val, 2),
                        "cost": round(cost, 2)
                    })
            return history

    def get_stock_value_history(self, symbol: str) -> dict:
        symbol = symbol.upper().strip()
        with Session(self.engine) as session:
            asset = session.get(PortfolioAsset, symbol)
            avg_cost = asset.average_cost if (asset and asset.scope == "holding") else None
            
            prices = session.query(PriceHistory).filter(
                PriceHistory.symbol == symbol
            ).order_by(PriceHistory.date.asc()).all()
            
            news = session.query(NewsRecord).filter(
                NewsRecord.symbol == symbol
            ).filter(
                func.trim(func.coalesce(NewsRecord.title, "")) != "",
                or_(
                    func.trim(func.coalesce(NewsRecord.summary, "")) != "",
                    func.trim(func.coalesce(NewsRecord.url, "")) != "",
                )
            ).order_by(NewsRecord.published_at.desc()).all()
            
            return {
                "symbol": symbol,
                "avg_cost": avg_cost,
                "prices": [
                    {"date": p.date, "price": p.close_price}
                    for p in prices
                ],
                "news_markers": [
                    {
                        "date": n.published_at.strftime("%Y-%m-%d") if n.published_at else None,
                        "title": n.title,
                        "sentiment": n.sentiment_score,
                        "url": n.url,
                        "source": n.source
                    }
                    for n in news
                ]
            }

    def get_paginated_news(self, symbol: str, limit: int, offset: int, date_str: str = None) -> list[dict]:
        with Session(self.engine) as session:
            query = session.query(NewsRecord)
            query = query.filter(
                func.trim(func.coalesce(NewsRecord.title, "")) != "",
                or_(
                    func.trim(func.coalesce(NewsRecord.summary, "")) != "",
                    func.trim(func.coalesce(NewsRecord.url, "")) != "",
                )
            )
            if symbol and symbol.upper().strip() != "PORTFOLIO":
                query = query.filter(NewsRecord.symbol == symbol.upper().strip())
                
            if date_str:
                from datetime import datetime, time
                try:
                    day_val = datetime.strptime(date_str, "%Y-%m-%d")
                    start_of_day = datetime.combine(day_val.date(), time.min)
                    end_of_day = datetime.combine(day_val.date(), time.max)
                    query = query.filter(
                        NewsRecord.published_at >= start_of_day,
                        NewsRecord.published_at <= end_of_day
                    )
                except Exception as ex:
                    print(f"Warning: Failed to parse date_str {date_str}: {ex}")

            rows = query.order_by(NewsRecord.published_at.desc()).offset(offset).limit(limit).all()
            
            return [
                {
                    "id": r.id,
                    "symbol": r.symbol,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "title": r.title,
                    "summary": r.summary,
                    "source": r.source,
                    "url": r.url,
                    "sentiment_score": r.sentiment_score
                }
                for r in rows
            ]

