from pathlib import Path

from finhub_app.config import normalize_database_url


def test_relative_sqlite_database_url_is_resolved_against_project_root() -> None:
    project_root = Path(__file__).resolve().parents[1]
    result = normalize_database_url("sqlite:///finhub.db")

    assert result == f"sqlite:///{project_root / 'finhub.db'}"
