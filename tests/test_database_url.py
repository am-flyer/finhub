from pathlib import Path

from finhub_app.config import normalize_database_url


def test_relative_sqlite_database_url_is_resolved_against_project_root() -> None:
    project_root = Path(__file__).resolve().parents[1]
    result = normalize_database_url("sqlite:///finhub.db")

    expected = f"sqlite:///{(project_root / 'finhub.db').as_posix()}"
    assert result == expected


def test_non_sqlite_database_url_is_left_unchanged() -> None:
    url = "postgresql+psycopg2://user:pass@localhost:5432/finhub"
    result = normalize_database_url(url)

    assert result == url
