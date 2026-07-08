from datetime import datetime
from pathlib import Path
import json

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func, inspect, or_, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from finhub_app.config import normalize_database_url
from finhub_app.database import create_database_engine, create_session_factory
from finhub_app.domain import (
    AssetScope,
    Position,
    UserProfile,
    RawDataPoint,
    RawNewsPayload,
    RawFilingPayload,
    RawOptionsPayload,
    RawMacroPayload,
    RawEventPayload,
)


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


class RawDataRecord(Base):
    __tablename__ = "raw_data_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    as_of_date: Mapped[str | None] = mapped_column(String(10), index=True, nullable=True)
    data_type: Mapped[str] = mapped_column(String(64), index=True)
    field_name: Mapped[str] = mapped_column(String(128))
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawNewsRecord(Base):
    __tablename__ = "raw_news_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    title: Mapped[str] = mapped_column(String(512))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(64))
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawFilingRecord(Base):
    __tablename__ = "raw_filing_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    form_type: Mapped[str] = mapped_column(String(64))
    filed_at: Mapped[datetime] = mapped_column(DateTime, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawOptionsRecord(Base):
    __tablename__ = "raw_options_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    as_of_date: Mapped[str | None] = mapped_column(String(10), index=True, nullable=True)
    field_name: Mapped[str] = mapped_column(String(128))
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawMacroRecord(Base):
    __tablename__ = "raw_macro_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    macro_name: Mapped[str] = mapped_column(String(128), index=True)
    as_of_date: Mapped[str | None] = mapped_column(String(10), index=True, nullable=True)
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RawEventRecord(Base):
    __tablename__ = "raw_event_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    symbol: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    event_date: Mapped[datetime | None] = mapped_column(DateTime, index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FeatureRecord(Base):
    __tablename__ = "feature_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(16), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    as_of_date: Mapped[str | None] = mapped_column(String(10), index=True, nullable=True)
    feature_name: Mapped[str] = mapped_column(String(128), index=True)
    numeric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_name: Mapped[str] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


def has_useful_news_content(title: str | None, summary: str | None, url: str | None) -> bool:
    return bool((title or "").strip() and ((summary or "").strip() or (url or "").strip()))



class PortfolioStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_database_engine(database_url)
        self.session_factory = create_session_factory(self.engine)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        expected_columns = {
            "portfolio_assets": [
                ("added_at", "DATETIME"),
            ],
            "reports": [
                ("json_data", "TEXT"),
            ],
            "news_records": [
                ("sentiment_score", "FLOAT"),
            ],
        }

        inspector = inspect(self.engine)
        with self.engine.begin() as connection:
            for table_name, columns in expected_columns.items():
                if not inspector.has_table(table_name):
                    continue
                existing_columns = {col_info["name"] for col_info in inspector.get_columns(table_name)}
                for column_name, column_type in columns:
                    if column_name not in existing_columns:
                        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))

    def list_positions(self) -> list[Position]:
        with self.session_factory() as session:
            try:
                rows = session.query(PortfolioAsset).order_by(PortfolioAsset.symbol).all()
            except Exception:
                rows = []
                for row in session.execute(text("SELECT symbol, name, quantity, average_cost, scope FROM portfolio_assets ORDER BY symbol")).fetchall():
                    rows.append(
                        Position(
                            symbol=row[0],
                            name=row[1],
                            quantity=row[2] or 0,
                            average_cost=row[3],
                            scope=AssetScope(row[4]),
                            added_at=None,
                        )
                    )
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
        with self.session_factory() as session:
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
        with self.session_factory() as session:
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
        with self.session_factory() as session:
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
        with self.session_factory() as session:
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
        with self.session_factory() as session:
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
        with self.session_factory() as session:
            row = session.get(PortfolioAsset, symbol.upper())
            if row is not None:
                session.delete(row)
                session.commit()
                return True
            return False

    def delete_report(self, report_id: int) -> bool:
        with self.session_factory() as session:
            row = session.get(ReportRecord, report_id)
            if row is not None:
                session.delete(row)
                session.commit()
                return True
            return False

    def save_price_history(self, symbol: str, date_str: str, price: float) -> None:
        with self.session_factory() as session:
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

        with self.session_factory() as session:
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

    def save_raw_data_record(self, record: RawDataPoint) -> None:
            with self.session_factory() as session:
                payload = json.dumps(record.raw_payload, default=str) if record.raw_payload is not None else None
                session.add(
                    RawDataRecord(
                        market=record.market,
                        symbol=record.symbol.upper(),
                        as_of_date=record.as_of_date,
                        data_type=record.data_type,
                        field_name=record.field_name,
                        numeric_value=record.numeric_value,
                        text_value=record.text_value,
                        source_name=record.source_name,
                        source_type=record.source_type,
                        raw_payload=payload,
                        retrieved_at=record.retrieved_at or datetime.now(),
                    )
                )
                session.commit()

    def save_raw_news_record(self, record: RawNewsPayload) -> bool:
            title = (record.title or "").strip()
            if not title:
                return False

            with self.session_factory() as session:
                existing = session.query(RawNewsRecord).filter(
                    RawNewsRecord.symbol == record.symbol.upper(),
                    RawNewsRecord.title == title,
                    RawNewsRecord.source_name == record.source_name,
                    RawNewsRecord.published_at == (record.published_at or datetime.now()),
                ).first()
                if existing is not None:
                    return False

                payload = json.dumps(record.raw_payload, default=str) if record.raw_payload is not None else None
                session.add(
                    RawNewsRecord(
                        market=record.market,
                        symbol=record.symbol.upper(),
                        published_at=record.published_at or datetime.now(),
                        title=title,
                        summary=record.summary,
                        source_name=record.source_name,
                        source_type=record.source_type,
                        url=str(record.url) if record.url else None,
                        sentiment_score=record.sentiment_score,
                        raw_payload=payload,
                        retrieved_at=record.retrieved_at or datetime.now(),
                    )
                )
                session.commit()
                return True

    def save_raw_filing_record(self, record: RawFilingPayload) -> bool:
            with self.session_factory() as session:
                existing = session.query(RawFilingRecord).filter(
                    RawFilingRecord.symbol == record.symbol.upper(),
                    RawFilingRecord.form_type == record.form_type,
                    RawFilingRecord.filed_at == (record.filed_at or datetime.now()),
                    RawFilingRecord.source_name == record.source_name,
                ).first()
                if existing is not None:
                    return False

                payload = json.dumps(record.raw_payload, default=str) if record.raw_payload is not None else None
                session.add(
                    RawFilingRecord(
                        market=record.market,
                        symbol=record.symbol.upper(),
                        form_type=record.form_type,
                        filed_at=record.filed_at,
                        title=record.title,
                        url=str(record.url) if record.url else None,
                        source_name=record.source_name,
                        source_type=record.source_type,
                        raw_payload=payload,
                        retrieved_at=record.retrieved_at or datetime.now(),
                    )
                )
                session.commit()
                return True

    def save_raw_options_record(self, record: RawOptionsPayload) -> None:
            with self.session_factory() as session:
                payload = json.dumps(record.raw_payload, default=str) if record.raw_payload is not None else None
                session.add(
                    RawOptionsRecord(
                        market=record.market,
                        symbol=record.symbol.upper(),
                        as_of_date=record.as_of_date,
                        field_name=record.field_name,
                        numeric_value=record.numeric_value,
                        text_value=record.text_value,
                        source_name=record.source_name,
                        source_type=record.source_type,
                        raw_payload=payload,
                        retrieved_at=record.retrieved_at or datetime.now(),
                    )
                )
                session.commit()

    def save_raw_macro_record(self, record: RawMacroPayload) -> None:
            with self.session_factory() as session:
                payload = json.dumps(record.raw_payload, default=str) if record.raw_payload is not None else None
                session.add(
                    RawMacroRecord(
                        market=record.market,
                        macro_name=record.macro_name,
                        as_of_date=record.as_of_date,
                        numeric_value=record.numeric_value,
                        text_value=record.text_value,
                        source_name=record.source_name,
                        source_type=record.source_type,
                        raw_payload=payload,
                        retrieved_at=record.retrieved_at or datetime.now(),
                    )
                )
                session.commit()

    def save_raw_event_record(self, record: RawEventPayload) -> None:
        with self.session_factory() as session:
            payload = json.dumps(record.raw_payload, default=str) if record.raw_payload is not None else None
            session.add(
                RawEventRecord(
                    market=record.market,
                    symbol=record.symbol.upper() if record.symbol else None,
                    event_type=record.event_type,
                    event_date=record.event_date,
                    description=record.description,
                    source_name=record.source_name,
                    source_type=record.source_type,
                    raw_payload=payload,
                    retrieved_at=record.retrieved_at or datetime.now(),
                )
            )
            session.commit()

    def save_feature_record(self, feature: "FeatureRecord") -> None:
        with self.session_factory() as session:
            existing = session.query(FeatureRecord).filter(
                FeatureRecord.market == feature.market,
                FeatureRecord.symbol == feature.symbol,
                FeatureRecord.as_of_date == feature.as_of_date,
                FeatureRecord.feature_name == feature.feature_name,
                FeatureRecord.source_name == feature.source_name,
            ).first()
            if existing is None:
                existing = FeatureRecord(
                    market=feature.market,
                    symbol=feature.symbol,
                    as_of_date=feature.as_of_date,
                    feature_name=feature.feature_name,
                    numeric_value=feature.numeric_value,
                    text_value=feature.text_value,
                    source_name=feature.source_name,
                    source_type=feature.source_type,
                    raw_payload=json.dumps(feature.raw_payload, default=str) if feature.raw_payload is not None else None,
                )
                session.add(existing)
            else:
                existing.numeric_value = feature.numeric_value
                existing.text_value = feature.text_value
                existing.source_type = feature.source_type
                existing.raw_payload = json.dumps(feature.raw_payload, default=str) if feature.raw_payload is not None else None
            session.commit()

    def clear_feature_records(self, market: str, symbol: str, as_of_date: str | None = None) -> None:
        with self.session_factory() as session:
            query = session.query(FeatureRecord).filter(
                FeatureRecord.market == market,
                FeatureRecord.symbol == symbol.upper(),
            )
            if as_of_date is not None:
                query = query.filter(FeatureRecord.as_of_date == as_of_date)
            query.delete(synchronize_session=False)
            session.commit()

    def get_feature_rows(self, market: str, symbol: str, as_of_date: str | None = None) -> list[dict]:
        with self.session_factory() as session:
            query = session.query(FeatureRecord).filter(
                FeatureRecord.market == market,
                FeatureRecord.symbol == symbol.upper(),
            )
            if as_of_date is not None:
                query = query.filter(FeatureRecord.as_of_date == as_of_date)

            rows = query.order_by(FeatureRecord.feature_name.asc()).all()
            return [
                {
                    "market": row.market,
                    "symbol": row.symbol,
                    "as_of_date": row.as_of_date,
                    "feature_name": row.feature_name,
                    "numeric_value": row.numeric_value,
                    "text_value": row.text_value,
                    "source_name": row.source_name,
                    "source_type": row.source_type,
                    "raw_payload": json.loads(row.raw_payload) if row.raw_payload else None,
                    "computed_at": row.computed_at.isoformat() if row.computed_at else None,
                }
                for row in rows
            ]

    def get_debug_ingestion_status(self) -> dict:
        with self.session_factory() as session:
            summary = {}
            table_specs = [
                ("raw_data_records", RawDataRecord, RawDataRecord.retrieved_at),
                ("raw_news_records", RawNewsRecord, RawNewsRecord.retrieved_at),
                ("raw_options_records", RawOptionsRecord, RawOptionsRecord.retrieved_at),
                ("raw_macro_records", RawMacroRecord, RawMacroRecord.retrieved_at),
                ("raw_event_records", RawEventRecord, RawEventRecord.retrieved_at),
                ("feature_records", FeatureRecord, FeatureRecord.computed_at),
            ]
            for table_name, model, time_column in table_specs:
                count = session.query(func.count()).select_from(model).scalar() or 0
                latest_time = session.query(func.max(time_column)).scalar()
                summary[table_name] = {
                    "count": int(count),
                    "latest_timestamp": latest_time.isoformat() if latest_time else None,
                }
            return summary

    def get_raw_counts_by_market(self) -> dict:
        with self.session_factory() as session:
            rows = (
                session.query(RawDataRecord.market, func.count())
                .group_by(RawDataRecord.market)
                .all()
            )
            return {market: int(count) for market, count in rows}

    def get_feature_sample(
        self,
        market: str,
        symbol: str,
        as_of_date: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        with self.session_factory() as session:
            query = session.query(FeatureRecord).filter(
                FeatureRecord.market == market,
                FeatureRecord.symbol == symbol.upper(),
            )
            if as_of_date is not None:
                query = query.filter(FeatureRecord.as_of_date == as_of_date)
            rows = query.order_by(FeatureRecord.as_of_date.desc(), FeatureRecord.feature_name.asc()).limit(limit).all()
            return [
                {
                    "market": row.market,
                    "symbol": row.symbol,
                    "as_of_date": row.as_of_date,
                    "feature_name": row.feature_name,
                    "numeric_value": row.numeric_value,
                    "text_value": row.text_value,
                    "source_name": row.source_name,
                    "source_type": row.source_type,
                    "raw_payload": json.loads(row.raw_payload) if row.raw_payload else None,
                    "computed_at": row.computed_at.isoformat() if row.computed_at else None,
                }
                for row in rows
            ]

    def get_portfolio_value_history(self) -> list[dict]:
        with self.session_factory() as session:
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
        with self.session_factory() as session:
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
        with self.session_factory() as session:
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

