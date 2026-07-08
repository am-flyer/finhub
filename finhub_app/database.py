from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from finhub_app.config import normalize_database_url


def create_database_engine(database_url: str):
    normalized_url = normalize_database_url(database_url)
    if normalized_url.startswith("sqlite:///"):
        sqlite_path = normalized_url[len("sqlite:///"):]
        if sqlite_path and sqlite_path != ":memory:":
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        normalized_url = f"sqlite:///{sqlite_path}".replace("\\", "/")

    engine = create_engine(normalized_url, future=True)
    return engine


def create_session_factory(engine):
    return sessionmaker(bind=engine, future=True)
