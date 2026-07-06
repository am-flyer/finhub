from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
