# FinHub Daily Investment Report

FinHub scans a beginner investor's holdings and watchlist before the market opens, gathers market/news/filing/fundamental signals, scores likely short-term investment impact, scores longer-term business quality, and generates a careful AI report using LangChain with Gemini by default.

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
Financials
News
 +------+------------+------------+
        |
        v
News + Filing + Fundamentals Processing Engine
        |
        v
Duplicate Removal
        |
        v
Sentiment + Technical + Fundamental Context
        |
        v
Impact Score (-100 to +100)
Business Quality Score (0 to 8)
        |
        v
LangChain + Gemini/OpenAI Explanation Engine
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
| - yfinance prices/financials|
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
| - Score business quality    |
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
| LangChain + Gemini/OpenAI   |
| Generates explanation/report|
+--------------+--------------+
               |
               v
+-----------------------------+
| Daily Investment Report     |
| - Summary                   |
| - Holdings impact           |
| - Business quality          |
| - Risks                     |
| - Watchlist opportunities   |
| - Diversification notes     |
+-----------------------------+
```

## Configuration

Create a `.env` file:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash

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

## Stock Evaluation Metrics

FinHub now computes a separate business quality score from 0 to 8. This is different from the short-term impact score from -100 to +100.

| Metric | Question | Good | Okay | Bad |
| --- | --- | --- | --- | --- |
| Revenue Growth | Is the business getting bigger? | Increasing | Flat | Declining |
| EPS Growth | Is it becoming more profitable? | Increasing | Flat | Declining |
| Free Cash Flow | Is it generating real cash? | Positive and stable/growing | Positive but weakening | Negative |
| Debt | Can it survive hard times? | Low | Medium | High |
| ROE | Is management good at using money? | Above 15% | 10% to 15% | Below 10% |
| Dividend Safety | Can it keep rewarding shareholders? | Well covered | Borderline | At risk |
| P/E / Forward P/E / PEG | Am I paying a fair price? | PEG below 1 or moderate P/E | PEG 1 to 2 | PEG above 2 or high P/E |
| Competitive Advantage (Moat) | Can competitors easily copy it? | Strong proxy signals | Average proxy signals | Weak proxy signals |

The moat rating is estimated from available margin and company-size signals. It should be treated as a starting point for review, not a definitive moat judgment.

## Portfolio Commands

Use the project virtual environment for all local commands:

```powershell
.\.venv\Scripts\Activate.ps1
```

Add or update a holding:

```powershell
python main.py add-holding MSFT --name "Microsoft" --quantity 1.18321439 --average-cost 464.84
```

Add or update a watchlist item:

```powershell
python main.py add-watchlist VOO --name "Vanguard S&P 500 ETF"
```

Show saved holdings and watchlist items:

```powershell
python main.py list-positions
```

## Seeding Local Data

The seeding commands use holding stocks only. Seeded reports include the same impact and business quality fields that the dashboard expects.

Clean old seeded reports, price history, and news records while keeping saved holdings:

```powershell
.\.venv\Scripts\python.exe main.py clean-history
```

Seed historical daily prices and initial news for holding stocks:

```powershell
.\.venv\Scripts\python.exe main.py seed-history --start-date 2025-01-01
```

Seed past daily report records for the dashboard:

```powershell
.\.venv\Scripts\python.exe main.py seed-reports --days 30 --articles-per-day 20
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
- Business quality score from 0 to 8
- LangChain report generation with Gemini or OpenAI
- Conservative recommendation guardrails
