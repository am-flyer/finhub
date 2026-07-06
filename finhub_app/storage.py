from sqlalchemy import Boolean, Float, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

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


class BudgetProfile(Base):
    __tablename__ = "budget_profile"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    monthly_budget_usd: Mapped[float] = mapped_column(Float, default=100)
    beginner: Mapped[bool] = mapped_column(Boolean, default=True)


class PortfolioStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url)
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
