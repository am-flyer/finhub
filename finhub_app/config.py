import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(database_url: str) -> str:
    if not database_url or not database_url.startswith("sqlite:///"):
        return database_url

    raw_path = database_url[len("sqlite:///"):]
    if raw_path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[/\\]", raw_path):
        return database_url

    project_root = Path(__file__).resolve().parents[1]
    resolved_path = (project_root / raw_path).resolve()
    return f"sqlite:///{resolved_path}".replace("\\", "/")


class Settings(BaseSettings):
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")
    finnhub_api_key: str = Field(default="", alias="FINNHUB_API_KEY")
    marketaux_api_key: str = Field(default="", alias="MARKETAUX_API_KEY")
    database_url: str = Field(default="sqlite:///finhub.db", alias="DATABASE_URL")
    monthly_investment_budget_usd: float = Field(
        default=100.0, alias="MONTHLY_INVESTMENT_BUDGET_USD"
    )
    market_timezone: str = Field(default="America/New_York", alias="MARKET_TIMEZONE")
    pre_market_report_hour: int = Field(default=8, alias="PRE_MARKET_REPORT_HOUR")
    pre_market_report_minute: int = Field(default=0, alias="PRE_MARKET_REPORT_MINUTE")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_database_url(self) -> "Settings":
        self.database_url = normalize_database_url(self.database_url)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
