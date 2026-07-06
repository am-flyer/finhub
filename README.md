# FinHub Daily Investment Report

FinHub scans a beginner investor's holdings and watchlist before the market opens, gathers market/news/filing signals, scores likely investment impact, and generates a careful AI report using OpenAI through LangChain.

The system is designed for a user with limited investing capacity, around USD 100 per month. Reports should be educational, conservative, source-aware, and careful about risk.

## Architecture

```text
Portfolio + Watchlist
        |
        v
Scan Holdings + Watchlist
        |
 +------+------------+------------+
 |      |            |            |
 v      v            v            v
yfinance Finnhub   Marketaux   SEC EDGAR
Prices   Quotes    Sentiment   Filings
News
 +------+------------+------------+
        |
        v
News + Filing Processing Engine
        |
        v
Duplicate Removal
        |
        v
Sentiment + Technical Context
        |
        v
Impact Score (-100 to +100)
        |
        v
LangChain + OpenAI Explanation Engine
        |
        v
AI Daily Investment Report
```

```text
+-----------------------------+
| SQLite Portfolio Database   |
| - Holdings                  |
| - Watchlist                 |
| - User budget profile       |
+--------------+--------------+
               |
               v
+-----------------------------+
| APScheduler                 |
| Runs before market open     |
+--------------+--------------+
               |
               v
+-----------------------------+
| Data Collection Layer       |
| - yfinance                  |
| - Finnhub                   |
| - Marketaux                 |
| - SEC EDGAR                 |
+--------------+--------------+
               |
               v
+-----------------------------+
| Processing Layer            |
| - Normalize data            |
| - Remove duplicates         |
| - Calculate indicators      |
| - Score sentiment/impact    |
+--------------+--------------+
               |
               v
+-----------------------------+
| Recommendation Guardrails   |
| - No hard buy/sell commands |
| - Budget-aware guidance     |
| - Beginner explanations     |
| - Risk-first wording        |
+--------------+--------------+
               |
               v
+-----------------------------+
| LangChain + OpenAI          |
| Generates explanation/report|
+--------------+--------------+
               |
               v
+-----------------------------+
| Daily Investment Report     |
| - Summary                   |
| - Holdings impact           |
| - Risks                     |
| - Watchlist opportunities   |
| - Diversification notes     |
+-----------------------------+
```

## Configuration

Create a `.env` file:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

FINNHUB_API_KEY=your_finnhub_api_key
MARKETAUX_API_KEY=your_marketaux_api_key

DATABASE_URL=sqlite:///finhub.db
MONTHLY_INVESTMENT_BUDGET_USD=100
MARKET_TIMEZONE=America/New_York
PRE_MARKET_REPORT_HOUR=8
PRE_MARKET_REPORT_MINUTE=0
```

## Guardrails

The report must avoid hard instructions such as "buy this now" or "sell everything." It should use careful language such as "consider," "monitor," "risk increased," and "no urgent action suggested." Important conclusions should include reasons and be written for a complete beginner.

## Current Scope

- SQLite portfolio/watchlist storage
- User budget profile
- Before-market-open scheduler
- Data collector interfaces for yfinance, Finnhub, Marketaux, and SEC EDGAR
- Duplicate removal
- Impact score from -100 to +100
- LangChain + OpenAI report generation
- Conservative recommendation guardrails
