from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev
from typing import Any, Iterable, List

from finhub_app.storage import (
    FeatureRecord,
    PortfolioStore,
    RawDataRecord,
    RawEventRecord,
    RawMacroRecord,
    RawNewsRecord,
    RawOptionsRecord,
)


class FeatureEngineeringPipeline:
    def __init__(self, store: PortfolioStore) -> None:
        self.store = store

    def build_features_for_symbol(
        self,
        symbol: str,
        market: str = "US",
        as_of_date: str | None = None,
    ) -> list[FeatureRecord]:
        symbol = symbol.strip().upper()
        if as_of_date is None:
            as_of_date = self._detect_target_date(symbol, market)

        if as_of_date is None:
            return []

        self.store.clear_feature_records(market, symbol, as_of_date=as_of_date)

        features: list[FeatureRecord] = []
        price_features = self._build_price_features(symbol, market, as_of_date)
        news_features = self._build_news_features(symbol, market, as_of_date)
        options_features = self._build_options_features(symbol, market, as_of_date)
        event_features = self._build_event_features(symbol, market, as_of_date)
        macro_features = self._build_macro_features(market, as_of_date)

        features.extend(price_features)
        features.extend(news_features)
        features.extend(options_features)
        features.extend(event_features)
        features.extend(macro_features)

        for feature in features:
            self.store.save_feature_record(feature)

        return features

    def _detect_target_date(self, symbol: str, market: str) -> str | None:
        with self.store.session_factory() as session:
            latest = (
                session.query(RawDataRecord)
                .filter(
                    RawDataRecord.market == market,
                    RawDataRecord.symbol == symbol,
                    RawDataRecord.as_of_date != None,
                )
                .order_by(RawDataRecord.as_of_date.desc())
                .first()
            )
            return latest.as_of_date if latest else None

    def _load_price_history(
        self,
        symbol: str,
        market: str,
        end_date: str,
        lookback: int = 30,
    ) -> list[dict[str, Any]]:
        with self.store.session_factory() as session:
            records = (
                session.query(RawDataRecord)
                .filter(
                    RawDataRecord.market == market,
                    RawDataRecord.symbol == symbol,
                    RawDataRecord.data_type == "price",
                    RawDataRecord.as_of_date != None,
                    RawDataRecord.as_of_date <= end_date,
                )
                .order_by(RawDataRecord.as_of_date.asc())
                .all()
            )

        rows_by_date: dict[str, dict[str, float | None]] = defaultdict(lambda: {})
        for row in records:
            if row.field_name and row.numeric_value is not None:
                rows_by_date[row.as_of_date or ""][row.field_name] = row.numeric_value

        history = []
        for date_key in sorted(rows_by_date.keys()):
            row = rows_by_date[date_key]
            history.append(
                {
                    "date": date_key,
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                    "volume": row.get("volume"),
                }
            )
        return history[-lookback:]

    def _build_price_features(
        self,
        symbol: str,
        market: str,
        as_of_date: str,
    ) -> list[FeatureRecord]:
        price_history = self._load_price_history(symbol, market, as_of_date, lookback=60)
        if not price_history:
            return []

        selected = next((row for row in reversed(price_history) if row["date"] == as_of_date), None)
        if selected is None or selected.get("close") is None:
            return []

        closes = [row["close"] for row in price_history if row.get("close") is not None]
        dates = [row["date"] for row in price_history]

        close_values = closes
        open_values = [row["open"] for row in price_history if row.get("open") is not None]

        features: list[FeatureRecord] = []
        if len(close_values) >= 2:
            prev_close = close_values[-2]
            current_close = close_values[-1]
            change = (current_close - prev_close) / prev_close if prev_close != 0 else None
            features.append(self._feature("return_1d", change, symbol, market, as_of_date))
            if selected.get("open") is not None:
                gap = (selected["open"] - prev_close) / prev_close if prev_close != 0 else None
                features.append(self._feature("gap_pct", gap, symbol, market, as_of_date))

        multiday_metrics = {
            "return_5d": 5,
            "return_10d": 10,
            "return_20d": 20,
        }
        for feature_name, period in multiday_metrics.items():
            if len(close_values) >= period:
                prior_price = close_values[-period]
                current_price = close_values[-1]
                value = (current_price - prior_price) / prior_price if prior_price != 0 else None
                features.append(self._feature(feature_name, value, symbol, market, as_of_date))

        if len(close_values) >= 5:
            returns = [
                (close_values[i] - close_values[i - 1]) / close_values[i - 1]
                for i in range(1, len(close_values))
                if close_values[i - 1] != 0
            ]
            volatility_5d = self._rolling_std(returns[-5:])
            volatility_10d = self._rolling_std(returns[-10:])
            features.append(self._feature("volatility_5d", volatility_5d, symbol, market, as_of_date))
            features.append(self._feature("volatility_10d", volatility_10d, symbol, market, as_of_date))

        if len(close_values) >= 1:
            features.append(self._feature("close", close_values[-1], symbol, market, as_of_date))
            if selected.get("volume") is not None:
                features.append(self._feature("volume", selected["volume"], symbol, market, as_of_date))
            if selected.get("high") is not None and selected.get("low") is not None:
                range_pct = (selected["high"] - selected["low"]) / selected["close"] if selected["close"] else None
                features.append(self._feature("range_pct", range_pct, symbol, market, as_of_date))

        if len(close_values) >= 20:
            features.append(self._feature("ma_20", mean(close_values[-20:]), symbol, market, as_of_date))
        if len(close_values) >= 50:
            features.append(self._feature("ma_50", mean(close_values[-50:]), symbol, market, as_of_date))
        if len(close_values) >= 50:
            features.append(
                self._feature(
                    "ma_20_minus_ma_50",
                    mean(close_values[-20:]) - mean(close_values[-50:]),
                    symbol,
                    market,
                    as_of_date,
                )
            )

        return features

    def _build_news_features(
        self,
        symbol: str,
        market: str,
        as_of_date: str,
    ) -> list[FeatureRecord]:
        with self.store.session_factory() as session:
            rows = (
                session.query(RawNewsRecord)
                .filter(
                    RawNewsRecord.market == market,
                    RawNewsRecord.symbol == symbol,
                    RawNewsRecord.published_at != None,
                )
                .order_by(RawNewsRecord.published_at.asc())
                .all()
            )

        date_target = datetime.fromisoformat(as_of_date).date()
        counts = {1: 0, 3: 0, 7: 0}
        sentiment_values: list[float] = []
        for row in rows:
            if row.published_at is None:
                continue
            row_date = row.published_at.date()
            age = (date_target - row_date).days
            if age < 0:
                continue
            for window in counts:
                if age <= window:
                    counts[window] += 1
            if row.sentiment_score is not None and age <= 3:
                sentiment_values.append(row.sentiment_score)

        features: list[FeatureRecord] = []
        for window, count_value in counts.items():
            features.append(self._feature(f"news_count_{window}d", float(count_value), symbol, market, as_of_date))
        avg_sentiment = mean(sentiment_values) if sentiment_values else None
        features.append(self._feature("news_sentiment_3d", avg_sentiment, symbol, market, as_of_date))
        return features

    def _build_options_features(
        self,
        symbol: str,
        market: str,
        as_of_date: str,
    ) -> list[FeatureRecord]:
        with self.store.session_factory() as session:
            rows = (
                session.query(RawOptionsRecord)
                .filter(
                    RawOptionsRecord.market == market,
                    RawOptionsRecord.symbol == symbol,
                    RawOptionsRecord.as_of_date != None,
                )
                .order_by(RawOptionsRecord.as_of_date.desc())
                .all()
            )

        if not rows:
            return []

        latest_date = rows[0].as_of_date
        relevant_rows = [r for r in rows if r.as_of_date == latest_date]
        features: list[FeatureRecord] = []
        for row in relevant_rows:
            features.append(
                self._feature(
                    row.field_name,
                    row.numeric_value,
                    symbol,
                    market,
                    as_of_date,
                    source_name=row.source_name,
                    source_type=row.source_type,
                    raw_payload={"as_of_date": row.as_of_date, "field_name": row.field_name},
                )
            )

        return features

    def _build_event_features(
        self,
        symbol: str,
        market: str,
        as_of_date: str,
    ) -> list[FeatureRecord]:
        with self.store.session_factory() as session:
            rows = (
                session.query(RawEventRecord)
                .filter(
                    RawEventRecord.market == market,
                    RawEventRecord.symbol == symbol,
                    RawEventRecord.event_date != None,
                )
                .order_by(RawEventRecord.event_date.asc())
                .all()
            )

        if not rows:
            return []

        target_dt = datetime.fromisoformat(as_of_date).date()
        count_7d = 0
        count_30d = 0
        event_types: dict[str, int] = {}
        for row in rows:
            if row.event_date is None:
                continue
            event_date = row.event_date.date()
            age = abs((event_date - target_dt).days)
            if age <= 7:
                count_7d += 1
            if age <= 30:
                count_30d += 1
            event_types[row.event_type] = event_types.get(row.event_type, 0) + 1

        features = [
            self._feature("event_count_7d", float(count_7d), symbol, market, as_of_date),
            self._feature("event_count_30d", float(count_30d), symbol, market, as_of_date),
        ]
        for event_type, count_value in event_types.items():
            features.append(
                self._feature(
                    f"event_{event_type}_count",
                    float(count_value),
                    symbol,
                    market,
                    as_of_date,
                )
            )
        return features

    def _build_macro_features(self, market: str, as_of_date: str) -> list[FeatureRecord]:
        with self.store.session_factory() as session:
            rows = (
                session.query(RawMacroRecord)
                .filter(
                    RawMacroRecord.market == market,
                    RawMacroRecord.as_of_date != None,
                    RawMacroRecord.as_of_date <= as_of_date,
                )
                .order_by(RawMacroRecord.as_of_date.desc())
                .all()
            )

        if not rows:
            return []

        latest_date = rows[0].as_of_date
        relevant_rows = [r for r in rows if r.as_of_date == latest_date]
        features: list[FeatureRecord] = []
        for row in relevant_rows:
            features.append(
                self._feature(
                    f"macro_{row.macro_name}",
                    row.numeric_value,
                    "",
                    market,
                    as_of_date,
                    source_name=row.source_name,
                    source_type=row.source_type,
                    raw_payload={"as_of_date": row.as_of_date, "macro_name": row.macro_name},
                )
            )
        return features

    def _feature(
        self,
        name: str,
        numeric_value: float | None,
        symbol: str,
        market: str,
        as_of_date: str,
        source_name: str = "engine",
        source_type: str = "feature",
        raw_payload: dict[str, Any] | None = None,
    ) -> FeatureRecord:
        return FeatureRecord(
            market=market,
            symbol=symbol,
            as_of_date=as_of_date,
            feature_name=name,
            numeric_value=numeric_value,
            text_value=None,
            source_name=source_name,
            source_type=source_type,
            raw_payload=raw_payload,
        )

    def _rolling_std(self, values: Iterable[float]) -> float | None:
        cleaned = [float(v) for v in values if v is not None]
        if len(cleaned) < 2:
            return 0.0 if cleaned else None
        try:
            return stdev(cleaned)
        except Exception:
            return None


def create_feature_engineering_pipeline(store: PortfolioStore) -> FeatureEngineeringPipeline:
    return FeatureEngineeringPipeline(store=store)
