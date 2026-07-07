import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import email.utils
import yfinance as yf
from datetime import datetime
from pathlib import Path

from finhub_app.collectors import YFinanceCollector
from finhub_app.domain import AssetScope
from finhub_app.processing import calculate_business_quality_scores
from finhub_app.storage import PortfolioStore, has_useful_news_content


def configure_yfinance_cache() -> None:
    cache_dir = Path(".yfinance-cache").resolve()
    cache_dir.mkdir(exist_ok=True)
    yf.set_tz_cache_location(str(cache_dir))


def fetch_google_news_rss(symbol: str) -> list[dict]:
    articles = []
    # Search for symbol specific stock news
    query = f"{symbol} stock news"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()
            
        import html
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            
            source = "Google News"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                source = parts[1]
                
            pub_date_str = item.find("pubDate").text if item.find("pubDate") is not None else ""
            published_at = datetime.now()
            if pub_date_str:
                try:
                    published_at = email.utils.parsedate_to_datetime(pub_date_str)
                except Exception:
                    pass
            
            description = item.find("description").text if item.find("description") is not None else ""
            
            # Unescape entities and format spacing cleanly
            title = html.unescape(title).replace("\xa0", " ").strip()
            description = html.unescape(description).replace("\xa0", " ").strip()
            
            # Simple clean of HTML tags in description if any
            if description and "<" in description:
                try:
                    # Strip basic HTML tags
                    import re
                    description = re.sub('<[^<]+?>', '', description)
                except Exception:
                    pass
            
            articles.append({
                "title": title,
                "summary": description,
                "source": source,
                "url": link,
                "published_at": published_at
            })
    except Exception as e:
        print(f"Warning: Failed to fetch Google News RSS for {symbol}: {e}")
        
    return articles



def seed_historical_data(database_url: str, start_date: str = "2025-01-01") -> None:
    configure_yfinance_cache()

    store = PortfolioStore(database_url)
    store.initialize()

    positions = [
        position
        for position in store.list_positions()
        if position.scope == AssetScope.HOLDING
    ]
    if not positions:
        print("No holding positions found in database. Add holdings first.")
        return

    print(f"\n==========================================")
    print(f"Seeding historical prices from {start_date}...")
    print(f"==========================================\n")

    for pos in positions:
        symbol = pos.symbol.upper()
        try:
            print(f"[{symbol}] Fetching daily prices from yfinance...")
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, interval="1d")
            
            price_count = 0
            for date, row in hist.iterrows():
                date_str = date.strftime("%Y-%m-%d")
                price = float(row["Close"])
                store.save_price_history(symbol, date_str, price)
                price_count += 1
            print(f"[{symbol}] Saved {price_count} price points.")

            # Seed some initial historical news signals
            print(f"[{symbol}] Fetching news signals...")
            news_items = ticker.news
            news_count = 0
            for item in news_items:
                title = item.get("title", "")
                summary = item.get("summary", "")
                source = item.get("publisher", "Yahoo Finance")
                url = item.get("link", "")
                pub_time = item.get("providerPublishTime", 0)

                published_at = datetime.fromtimestamp(pub_time) if pub_time else datetime.now()
                sentiment_score = calculate_simple_sentiment(title + " " + (summary or ""))

                store.save_news_record(
                    symbol=symbol,
                    published_at=published_at,
                    title=title,
                    summary=summary,
                    source=source,
                    url=url,
                    sentiment_score=sentiment_score
                )
                news_count += 1
            print(f"[{symbol}] Saved {news_count} news items.\n")

        except Exception as e:
            print(f"[{symbol}] Error during seeding: {e}\n")

    print("Seeding completed successfully!")


def calculate_simple_sentiment(text: str) -> float:
    text = text.lower()
    pos_words = ["buy", "upgrade", "growth", "positive", "gain", "surpass", "soar", "jump", "partnership", "deal", "beat", "higher", "record"]
    neg_words = ["sell", "downgrade", "decline", "negative", "loss", "layoff", "drop", "cut", "concern", "miss", "lower", "fall", "warn"]
    
    score = 0.0
    for w in pos_words:
        if w in text:
            score += 0.25
    for w in neg_words:
        if w in text:
            score -= 0.25
            
    # Return bounded sentiment score between -1.0 and 1.0 (defaults to 0.0 if neutral)
    return min(1.0, max(-1.0, score))


def seed_past_reports(database_url: str, days: int = 30, articles_per_day: int = 20) -> None:
    configure_yfinance_cache()

    import json
    from datetime import timedelta
    from sqlalchemy.orm import Session
    from finhub_app.storage import ReportRecord, PortfolioAsset, PriceHistory, NewsRecord

    store = PortfolioStore(database_url)
    store.initialize()

    # Step 1: Pre-fetch and cache real news articles from Google News RSS for holdings.
    with Session(store.engine) as session:
        positions = session.query(PortfolioAsset).filter(
            PortfolioAsset.scope == AssetScope.HOLDING.value
        ).all()
        if not positions:
            print("No holding positions found in database. Add holdings first.")
            return

        for pos in positions:
            symbol = pos.symbol.upper()
            print(f"[{symbol}] Pre-fetching real historical news from Google News RSS...")
            real_articles = fetch_google_news_rss(symbol)
            saved_count = 0
            for art in real_articles:
                if not has_useful_news_content(art["title"], art["summary"], art["url"]):
                    continue
                # Check duplicate news by title and symbol
                existing_art = session.query(NewsRecord).filter(
                    NewsRecord.symbol == symbol,
                    NewsRecord.title == art["title"]
                ).first()
                if not existing_art:
                    record = NewsRecord(
                        symbol=symbol,
                        published_at=art["published_at"],
                        title=art["title"],
                        summary=art["summary"],
                        source=art["source"],
                        url=art["url"],
                        sentiment_score=calculate_simple_sentiment(art["title"] + " " + (art["summary"] or ""))
                    )
                    session.add(record)
                    saved_count += 1
            session.commit()
            print(f"[{symbol}] Cached {saved_count} new real articles in database.")

    # Step 2: Seed daily reports using cached real news records
    with Session(store.engine) as session:
        # Wipe existing patterned seed reports to prevent duplicates
        session.query(ReportRecord).filter(
            ReportRecord.title.like("Daily Pre-Market Investment Report - %")
        ).delete(synchronize_session=False)
        session.commit()

        # Load holding positions for context modeling.
        positions = session.query(PortfolioAsset).filter(
            PortfolioAsset.scope == AssetScope.HOLDING.value
        ).all()
        holding_count = sum(1 for p in positions if p.scope == AssetScope.HOLDING.value)
        watchlist_count = 0

        print("Computing business quality scores for holding stocks...")
        fundamental_snapshots = []
        try:
            collector = YFinanceCollector()
            fundamentals = [
                collector.get_fundamentals(pos.symbol.upper())
                for pos in positions
            ]
            fundamental_snapshots = [
                item.model_dump(mode="json")
                for item in fundamentals
            ]
            business_quality = [
                item.model_dump(mode="json")
                for item in calculate_business_quality_scores(fundamentals)
            ]
        except Exception as exc:
            print(f"Warning: Failed to compute business quality scores: {exc}")
            business_quality = []

        existing = session.query(ReportRecord).order_by(ReportRecord.created_at.desc()).first()
        base_content = existing.content if existing else "# Mock Daily Investment Report\n\nThis is a seeded mock report."
        base_summary = existing.summary if existing else "Seeded pre-market daily report and analysis."

        print(f"Seeding {days} daily reports with real news constraints...")
        for i in range(1, days + 1):
            date_val = datetime.now() - timedelta(days=i)
            date_str = date_val.strftime("%Y-%m-%d")
            title_str = f"Daily Pre-Market Investment Report - {date_str}"

            # 1. Fetch closing prices for active holdings on date_str
            snapshots = []
            for pos in positions:
                sym = pos.symbol.upper()
                price_record = session.query(PriceHistory).filter(
                    PriceHistory.symbol == sym,
                    PriceHistory.date == date_str
                ).first()
                price = price_record.close_price if price_record else (pos.average_cost or 0.0)
                prev_price = price * 0.99  # Mock fallback

                snapshots.append({
                    "symbol": sym,
                    "latest_price": price,
                    "previous_close": prev_price,
                    "technical_summary": None
                })

            # 2. Fetch news items published on date_str
            start_of_day = datetime.combine(date_val.date(), datetime.min.time())
            end_of_day = datetime.combine(date_val.date(), datetime.max.time())

            day_news = []
            for pos in positions:
                sym = pos.symbol.upper()
                # Query real news records matching symbol and date
                news_records = session.query(NewsRecord).filter(
                    NewsRecord.symbol == sym,
                    NewsRecord.published_at >= start_of_day,
                    NewsRecord.published_at <= end_of_day
                ).order_by(NewsRecord.published_at.desc()).limit(articles_per_day).all()

                for n in news_records:
                    day_news.append({
                        "symbol": n.symbol,
                        "title": n.title,
                        "summary": n.summary,
                        "source": n.source,
                        "published_at": n.published_at.isoformat(),
                        "url": n.url,
                        "sentiment_score": n.sentiment_score
                    })

            # 3. Compute simulated impact scores
            day_impacts = []
            for pos in positions:
                sym = pos.symbol.upper()
                sym_news = [n for n in day_news if n["symbol"] == sym]
                avg_sent = sum(n["sentiment_score"] or 0.0 for n in sym_news) / len(sym_news) if sym_news else 0.0
                score_val = int(avg_sent * 100)

                reason_str = f"{sym} currently has a positive impact score based on news sentiment." if score_val > 10 else (
                    f"{sym} currently has a negative impact score based on news sentiment." if score_val < -10 else
                    f"{sym} currently has a neutral impact score."
                )

                day_impacts.append({
                    "symbol": sym,
                    "score": score_val,
                    "reason": reason_str,
                    "risks": ["Short-term news can reverse quickly.", "Sentiment changes dynamically."],
                    "source_titles": [n["title"] for n in sym_news[:3]]
                })

            # 4. Construct ReportContext json payload
            context_dict = {
                "generated_for": date_val.isoformat(),
                "profile": {
                    "monthly_investment_budget_usd": 100.0,
                    "beginner": True
                },
                "positions": [
                    {
                        "symbol": p.symbol,
                        "name": p.name,
                        "quantity": p.quantity,
                        "average_cost": p.average_cost,
                        "scope": p.scope
                    }
                    for p in positions
                ],
                "market_snapshots": snapshots,
                "fundamental_snapshots": fundamental_snapshots,
                "news": day_news,
                "filings": [],
                "impacts": day_impacts,
                "business_quality": business_quality
            }

            record = ReportRecord(
                created_at=date_val,
                title=title_str,
                content=f"# Daily Pre-Market Investment Report - {date_str}\n\n" + base_content,
                summary=f"Seeded historical report for {date_str}. " + base_summary,
                holding_count=holding_count,
                watchlist_count=watchlist_count,
                json_data=json.dumps(context_dict)
            )
            session.add(record)
        session.commit()
    print(f"Successfully seeded {days} daily reports with real news constraints.")
