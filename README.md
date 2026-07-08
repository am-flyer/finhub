# FinHub Daily Investment Report

FinHub scans a beginner investor's holdings and watchlist before the market opens, gathers market/news/filing/fundamental signals, scores likely short-term investment impact, scores longer-term business quality, and generates a careful AI report using LangChain with Gemini by default.

The system is designed for a user with limited investing capacity, around USD 100 per month. Reports should be educational, conservative, source-aware, and careful about risk.

## Recent Updates

Recent improvements include:

- Fixed database initialization so SQLite paths resolve correctly from the project root, avoiding report-generation failures.
- Added asset add/edit/delete flows that refresh the portfolio, analytics view, and dashboard in sync.
- Added historical backfill for newly saved assets so price and news data are collected for roughly the last year.
- Updated the dashboard and report history to reflect the current live portfolio instead of stale report snapshots.
- Improved compatibility with existing SQLite data so holdings continue to load even when older schema columns are missing.

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

## Multi-Market Prediction Architecture

FinHub is evolving from a pre-market report system into a multi-market prediction platform. The initial implementation will focus on US equities, but the architecture is explicitly designed to support future markets such as India and Japan by adding market-specific data adapters.

The design is market-agnostic at the core: the same feature engineering, prediction, and explanation layers can be reused across regions. Only the data ingestion layer changes when new markets are added.

```text
                            +------------------------------+
                            |   Market Universe Selector   |
                            |   - US equities              |
                            |   - India equities           |
                            |   - Japan equities           |
                            +--------------+---------------+
                                           |
                                           v
                     +---------------------------------------------+
                     |   Market-Specific Collector Adapters Layer   |
                     +---------------------------------------------+
                     |  US Adapter: Yahoo Finance, SEC EDGAR, FRED |
                     |  India Adapter: NSE/BSE public feeds, RBI   |
                     |  Japan Adapter: TSE public feeds, BOJ       |
                     +---------------------------------------------+
                                           |
                                           v
                     +---------------------------------------------+
                     |   Abstract Data Collector Interfaces        |
                     +---------------------------------------------+
                     |  MarketDataCollector                         |
                     |  FundamentalDataCollector                    |
                     |  NewsCollector                               |
                     |  FilingsCollector                            |
                     |  OptionsCollector                            |
                     |  EventCalendarCollector                      |
                     |  MacroCollector                              |
                     +---------------------------------------------+
                                           |
                                           v
                     +---------------------------------------------+
                     |      Feature Engineering / Feature Store    |
                     +---------------------------------------------+
                     |  Technical indicators                        |
                     |  Returns / gap / volatility                  |
                     |  Options-derived signals                     |
                     |  News sentiment / event tags                 |
                     |  Macro / market regime context               |
                     |  Fundamentals                                |
                     +---------------------------------------------+
                                           |
                                           v
                     +---------------------------------------------+
                     |          Prediction Engine                  |
                     +---------------------------------------------+
                     |  XGBoost / LightGBM / CatBoost              |
                     |  Calibration / confidence scoring           |
                     |  Backtest / baseline evaluation             |
                     +---------------------------------------------+
                                           |
                                           v
                     +---------------------------------------------+
                     |           LLM Analyst Layer                 |
                     +---------------------------------------------+
                     |  Explain model outputs                       |
                     |  Summarize top factors                       |
                     |  Call out risks and confidence               |
                     +---------------------------------------------+
                                           |
                                           v
                     +---------------------------------------------+
                     |      Report / Dashboard / Storage           |
                     +---------------------------------------------+
                     |  Pre-market report + predictions             |
                     |  Stored feature / prediction history         |
                     |  Market-specific UI sections                 |
                     +---------------------------------------------+
```

The first market to build is US equities. Once the US adapter layer is validated, the same architecture can be extended to India, Japan, or other markets by adding new collector adapters and market-specific sources.

A few design principles:
- Prefer public and government-based sources over paid vendor services when possible.
- Keep third-party vendor adapters like Finnhub and Marketaux optional and replaceable.
- Persist raw source metadata in the database for every collected record so we can compare sources, audit data quality, and migrate between providers later.
- Build generic feature engineering around normalized data rows keyed by `(market, symbol, date)`.
- Keep the new prediction/feature-engineering layer decoupled from the existing report generation logic by using separate database tables and services while sharing the same SQLite database file.

### Feature Store and Feature Set

The feature store is the core of the prediction platform. It ingests normalized raw records and computes a consistent, market-agnostic set of derived features that can be consumed by the prediction engine.

The platform is being built around six broad feature sets:

1. Technical indicators
   - RSI (Relative Strength Index): measures recent price momentum and overbought/oversold conditions.
   - MACD / signal crossovers: captures momentum shifts in price action.
   - Bollinger band percent: shows where the close sits inside recent volatility bands.
   - EMA / SMA crossovers and distance: tracks trend direction and price divergence from moving averages.
   - ATR (Average True Range): measures intraday volatility and price range.
   - ADX (Average Directional Index): measures directional strength in a trend.
   - OBV (On-Balance Volume): accumulates volume flow as a proxy for buying/selling pressure.
   - Volume momentum and relative volume: compares today's volume to recent averages.

2. Price/return structure
   - Next-day and multi-day returns: raw percentage moves over 1, 5, 10, and 20 days.
   - Gap percentages: compute open-to-close and close-to-open price gaps.
   - Rolling volatility: standard deviation over multiple lookback windows.
   - Range percentages: daily high/low amplitude relative to closing price.
   - Relative price level: distance from moving averages and historical price distribution.
   - Historical percentile ranks: compare today's close/volume to recent history.

3. Options-derived signals
   - Put/Call ratio: relative demand for downside protection versus bullish exposure.
   - Implied volatility and IV spreads: captures option market pricing skew.
   - Open interest ratios and spreads: measures sentiment from call/put positioning.
   - ATM IV and aggregate option volatility: near-term expectations from the options surface.
   - Net call/put exposure: approximate directional bias from OI differences.

4. News / event / sentiment features
   - News sentiment scores: aggregated polarity across recent news items.
   - Event tags: earnings surprise, guidance change, rating change, and other corporate actions.
   - News volume: count of news items and positive/negative story frequency.
   - Event proximity: days until the next scheduled event and whether one is imminent.

5. Macro / regime context
   - Macro indicator values: VIX, yields, currency indices, commodity prices, and other regime signals.
   - Macro changes: recent percent changes in the same macro series.
   - Market regime context: rising/falling risk environment for the chosen market.
   - Country-specific macro readings: CPI, interest rate decisions, and central bank signals for each market.

6. Fundamentals and company context
   - Raw fundamentals: valuation, leverage, profitability, and payout metrics.
   - Derived ratios: P/E spread, forward/trailing P/E ratio, P/E-to-PEG, and margin spreads.
   - Leverage and quality: debt/equity, return on equity, gross vs profit margin comparison.
   - Event-driven fundamentals: earnings surprises, guidance changes, and rating action flags.

Current implementation status:
- The current feature engineering pipeline already normalizes fundamentals, raw options, news/events, and macro values into raw tables and generates derived features in `feature_records`.
- Most technical and price structure indicators are already implemented, including RSI, MACD, Bollinger %B, ATR, EMAs/SMA crossovers, volume momentum, and OBV.
- Options-derived features include raw call/put IV and open interest values plus derived IV/oi ratios and spreads.
- News/event features include sentiment aggregation, recent counts, and event flags for earnings surprise, guidance change, and rating change.
- Macro features include latest macro values and change calculations versus prior observations.
- Fundamental features include normalized raw fundamentals and derived valuation/leverage ratios when source data is available.
- Sector-relative and market-relative benchmarks are not yet fully implemented because they require benchmark and sector metadata ingestion; the platform already supports internal historical relative measures and will extend to cross-asset/sector ranking as market adapters are enhanced.

Not yet fully covered:
- Options analytics beyond aggregate call/put IV and OI: IV rank/percentile, skew, true ATM IV, and richer chain-level expiry metrics.
- Sector-relative and market-relative benchmarking using peer, sector, and index reference data.
- Industry risk factor ingestion such as sector-specific macro drivers and business-cycle exposures.
- Advanced fundamental event extraction from filings/news for granular surprises, guidance text, and analyst rating metadata.
- Country-specific macro sources for non-US markets until those adapters are added and validated.
- Direct earnings surprise numeric values or seasonality-adjusted fundamental growth rates, since current fundamentals are derived from static snapshot fields.

Each feature set is kept generic so it can be adapted to new markets. For example, US fundamentals may come from SEC filings and Yahoo Finance, while India fundamentals can be sourced from NSE/BSE feeds and local disclosures.

The feature engineering pipeline is intentionally implemented inside the feature store layer. It has three responsibilities:
- normalize raw ingestion records into common feature input rows,
- compute derived features in a market-agnostic way,
- persist feature rows separately from raw source records for prediction and auditing.

### Prediction UI binding and workflow

The new multi-market prediction feature is exposed on its own UI page and bound to backend services through dedicated API endpoints. It supports:
- predictions for saved holdings, based on the user's portfolio and market universe.
- ad-hoc symbol estimates without saving them to the database.
- market-specific adapters that can later be expanded to India, Japan, and other regions.

The view binds to the data/model through:
- `GET /api/predictions/holdings` for portfolio-based predictions
- `GET /api/predictions/estimate?symbol=...` for on-demand symbol estimates

This separation keeps the prediction workflow independent of the existing report system, while still allowing both features to share a common database for persistence and auditing.

### Decoupled data model

The new feature engineering and prediction functionality will be implemented using independent tables in the common database, for example:
- `raw_market_data`
- `raw_news_records`
- `raw_fundamental_data`
- `feature_rows`
- `prediction_results`
- `prediction_explanations`

This allows the new system to:
- reuse the existing database file without changing the current table schema
- keep existing report generation and storage behavior intact
- store source metadata alongside raw values for audit and source comparison
- add new markets and collectors without modifying the original portfolio/report workflow

### Raw source ingestion layer

The first extensible ingestion implementation now includes:
- `raw_data_records` for generic market, fundamental, options, macro, and derived signals.
- `raw_news_records` for source-specific news items, sentiment, and article metadata.
- `raw_filing_records`, `raw_options_records`, `raw_macro_records`, and `raw_event_records` for structured raw source events.
- A US adapter layer using yfinance as the primary open-source market source, with Finnhub and Marketaux as optional news fallbacks.
- A `RawSourceIngestionManager` that keeps raw ingestion decoupled from existing report generation and makes it easy to add new markets later.

### Feature store and engineering pipeline

The feature store is the next layer on top of raw ingestion. It transforms normalized raw source rows into a consistent set of derived `feature_records` that the prediction engine can consume.

Key design points:
- `feature_records` are keyed by `(market, symbol, as_of_date, feature_name)` so the same pipeline works for US, India, Japan, or any future market.
- The feature engineering pipeline is part of the feature store and computes:
  - technical/price features such as returns, gap percent, volatility, moving averages, and range ratios
  - news features such as sentiment averages and recent news counts
  - options-derived signals such as implied volatility averages and open interest summaries
  - event signals such as earnings/event counts and event-type flags
  - macro regime indicators from market-level macro data
- The feature store is intentionally separated from ingestion and prediction so the source adapters can be swapped without changing the derived feature schema.

### Database strategy

For hobby and local development, SQLite is fine. For a production deployment that may serve many users, use a server-grade SQL database.

Recommended production databases:
- PostgreSQL: best general-purpose choice for reliability, concurrency, and SQLAlchemy compatibility.
- MySQL / MariaDB: a solid alternative if your infrastructure is already MySQL-based.

The project is designed to be DB-agnostic through SQLAlchemy. To switch databases, update `DATABASE_URL` in `.env` and install the appropriate Python DB driver.

Example database URLs:
- `sqlite:///finhub.db`
- `postgresql+psycopg2://user:password@host:5432/finhub`
- `mysql+pymysql://user:password@host:3306/finhub`

Current code supports DB selection via `DATABASE_URL`, and the new prediction tables will be added in a way that does not change the existing report workflow.

### Scale and extensibility
 
The design is intended to scale from a small watchlist to thousands of stocks across multiple exchanges by:
- using batch-friendly market adapters that can collect symbols in groups and cache results when possible
- storing every raw input source with metadata so data quality can be compared across providers and markets
- keeping the core feature store and prediction pipeline independent of the source adapter implementation
- supporting incremental backfill and daily refresh for large universes of symbols
- treating optional vendor APIs as fallback or augmentation, not as the primary data source for scale
 
### Baseline modeling and data readiness
 
Before a full production prediction engine is built, the project should establish a set of simple, transparent baseline models and a data readiness process.
 
Baseline model candidates:
- Naive baselines: always predict "up", yesterday's direction, or a simple momentum rule based on recent returns.
- Linear models: logistic regression for direction labels, ridge/lasso regression for next-day return.
- Decision trees: a first non-linear tabular benchmark.
- Gradient-boosted trees: XGBoost, LightGBM, CatBoost for the first real model candidates.
- Sequence-aware models later: MLP, LSTM/GRU, or transformer-based temporal models once the tabular baselines are stable.
 
Data readiness and validation:
- The database schema already supports raw ingestion and a generic feature store.
- The remaining step is to populate the raw tables and then run the feature engineering pipeline to create `feature_records`.
- Training data is constructed from feature rows keyed by `(market, symbol, as_of_date)` plus target labels derived from future price action.
- Validation should be time-aware, using chronological splits or rolling walk-forward backtests rather than random sampling.
- A proper evaluation should compare every model against naive baselines and simple benchmark strategies.
 
Developer debug UI:
- The portal should include a dedicated developer/debug page separate from the user-facing prediction page.
- This page can expose ingestion health, feature coverage, sample feature vectors, model metrics, and backtest summaries.
- Recommended backend endpoints include:
  - `/api/debug/ingestion-status`
  - `/api/debug/feature-sample`
  - `/api/debug/backtest-summary`
  - `/api/debug/raw-counts`
- Keeping debug/diagnostic views separate lets the main prediction UX remain clean while developers inspect model readiness and data quality.
 
### Core feature pipeline

- Data collection from public and trusted sources with market-specific adapters:
  - US: Yahoo Finance, SEC EDGAR, FRED, CBOE/VIX, public news feeds
  - India: NSE/BSE public data, RBI/MOF macro feeds, company filings, local news sources
  - Japan: TSE/JPX public data, BOJ/METI macro feeds, EDINET filings, local news sources
- Feature engineering:
  - technical indicators and momentum
  - returns, gap, volatility, volume metrics
  - options-derived signals where available
  - news sentiment and event tags
  - market/regime context and macro signals
- Prediction engine:
  - next-day direction probability
  - next-day return / expected move
  - confidence scoring and calibration
  - backtesting against simple baselines
- LLM analyst:
  - explain why the model produced the forecast
  - summarize top positive/negative drivers
  - highlight risks and confidence
  - avoid asking the LLM to predict raw prices
  - summarize top positive/negative drivers
  - highlight risks and confidence
  - avoid asking the LLM to predict raw prices

### What is being built into FinHub

- A modular adapter layer so new markets can be added without changing the core prediction engine
- A US-first feature collection and storage pipeline for structured market data
- Traditional ML forecasting on next-day stock behavior
- Backtesting and performance evaluation for every signal
- Explainable model output with feature importance and confidence
- A report/dashboard layer that surfaces probability, risk, and explanation rather than deterministic buy/sell advice

### Future flexibility

The core pipeline is market-agnostic: once the market-specific collectors are implemented, the same feature engineering, prediction, and explanation engine can support additional regions. This keeps the system reusable while allowing each market to plug in its own reliable data sources.
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
# For PostgreSQL: postgresql+psycopg2://user:password@host:5432/finhub
# For MySQL: mysql+pymysql://user:password@host:3306/finhub
MONTHLY_INVESTMENT_BUDGET_USD=100
MARKET_TIMEZONE=America/New_York
PRE_MARKET_REPORT_HOUR=8
PRE_MARKET_REPORT_MINUTE=0
```

This project is built on SQLAlchemy, so the database engine is configurable via `DATABASE_URL`. SQLite is recommended for local development. For production-scale usage, PostgreSQL is the preferred DB because of its reliability, concurrency, and compatibility with millions of users. MySQL / MariaDB are also viable alternatives.

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
