from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev
import math
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
        fundamental_features = self._build_fundamental_features(symbol, market, as_of_date)
        news_features = self._build_news_features(symbol, market, as_of_date)
        options_features = self._build_options_features(symbol, market, as_of_date)
        event_features = self._build_event_features(symbol, market, as_of_date)
        macro_features = self._build_macro_features(market, as_of_date)
        relative_features = self._build_relative_features(symbol, market, as_of_date)

        features.extend(price_features)
        features.extend(fundamental_features)
        features.extend(news_features)
        features.extend(options_features)
        features.extend(event_features)
        features.extend(macro_features)
        features.extend(relative_features)

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
        volumes = [row["volume"] for row in price_history if row.get("volume") is not None]
 
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
            if len(price_history) >= 2:
                features.append(self._feature("true_range", self._true_range(price_history[-2:]), symbol, market, as_of_date))
 
        if len(volumes) >= 2:
            previous_volume = volumes[-2]
            if previous_volume != 0:
                features.append(self._feature(
                    "volume_change_1d",
                    (volumes[-1] - previous_volume) / previous_volume,
                    symbol,
                    market,
                    as_of_date,
                ))
 
        if len(volumes) >= 5:
            if volumes[-5] != 0:
                features.append(self._feature(
                    "volume_change_5d",
                    (volumes[-1] - volumes[-5]) / volumes[-5],
                    symbol,
                    market,
                    as_of_date,
                ))
 
        if len(close_values) >= 14:
            rsi = self._rsi(close_values[-15:])
            features.append(self._feature("rsi_14", rsi, symbol, market, as_of_date))
 
        if len(close_values) >= 20:
            features.append(self._feature("ma_20", mean(close_values[-20:]), symbol, market, as_of_date))
            ema_20 = self._ema(close_values, 20)
            features.append(self._feature("ema_20", ema_20, symbol, market, as_of_date))
            features.append(self._feature(
                "bollinger_pct_20",
                self._bollinger_percent(close_values, 20),
                symbol,
                market,
                as_of_date,
            ))
            if ema_20 is not None:
                features.append(self._feature("close_vs_ema20_pct", (close_values[-1] - ema_20) / ema_20 if ema_20 != 0 else None, symbol, market, as_of_date))
 
        if len(close_values) >= 26:
            ema_12 = self._ema(close_values, 12)
            ema_26 = self._ema(close_values, 26)
            if ema_12 is not None and ema_26 is not None:
                features.append(self._feature("ema_12", ema_12, symbol, market, as_of_date))
                features.append(self._feature("ema_26", ema_26, symbol, market, as_of_date))
                macd_series = self._macd_series(close_values)
                if macd_series and len(macd_series) >= 9:
                    macd = macd_series[-1]
                    macd_signal = self._ema(macd_series, 9)
                    features.append(self._feature("macd", macd, symbol, market, as_of_date))
                    features.append(self._feature("macd_signal", macd_signal, symbol, market, as_of_date))
                    if macd_signal is not None:
                        features.append(self._feature("macd_histogram", macd - macd_signal, symbol, market, as_of_date))
 
        if len(close_values) >= 50:
            features.append(self._feature("ma_50", mean(close_values[-50:]), symbol, market, as_of_date))
            features.append(self._feature("ema_50", self._ema(close_values, 50), symbol, market, as_of_date))
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
            if self._ema(close_values, 20) is not None and self._ema(close_values, 50) is not None:
                features.append(
                    self._feature(
                        "ema_20_minus_ema_50",
                        self._ema(close_values, 20) - self._ema(close_values, 50),
                        symbol,
                        market,
                        as_of_date,
                    )
                )
 
        if len(price_history) >= 14:
            atr_14 = self._average_true_range(price_history[-14:])
            features.append(self._feature("atr_14", atr_14, symbol, market, as_of_date))
            adx_14 = self._adx(price_history[-14:])
            features.append(self._feature("adx_14", adx_14, symbol, market, as_of_date))
 
        if len(price_history) >= 2:
            obv = self._on_balance_volume(price_history)
            features.append(self._feature("obv", obv, symbol, market, as_of_date))
            if len(price_history) >= 2:
                prev_obv = self._on_balance_volume(price_history[:-1])
                if prev_obv is not None and obv is not None and prev_obv != 0:
                    features.append(self._feature("obv_change_1d", (obv - prev_obv) / prev_obv, symbol, market, as_of_date))
 
        return features

    def _build_fundamental_features(
        self,
        symbol: str,
        market: str,
        as_of_date: str,
    ) -> list[FeatureRecord]:
        with self.store.session_factory() as session:
            rows = (
                session.query(RawDataRecord)
                .filter(
                    RawDataRecord.market == market,
                    RawDataRecord.symbol == symbol,
                    RawDataRecord.data_type == "fundamental",
                    RawDataRecord.as_of_date != None,
                    RawDataRecord.as_of_date <= as_of_date,
                )
                .order_by(RawDataRecord.as_of_date.desc())
                .all()
            )

        if not rows:
            return []

        latest_values: dict[str, float | None] = {}
        for row in rows:
            if row.numeric_value is not None and row.field_name not in latest_values:
                latest_values[row.field_name] = row.numeric_value

        features: list[FeatureRecord] = []
        for name, value in latest_values.items():
            features.append(
                self._feature(
                    f"fundamental_{name}",
                    value,
                    symbol,
                    market,
                    as_of_date,
                    source_name="raw_fundamental",
                    source_type="fundamental",
                    raw_payload={"field_name": name},
                )
            )

        if latest_values.get("market_cap") is not None and latest_values.get("profit_margin") is not None:
            features.append(
                self._feature(
                    "fundamental_value_to_profit",
                    latest_values.get("market_cap") * latest_values.get("profit_margin"),
                    symbol,
                    market,
                    as_of_date,
                    source_name="raw_fundamental",
                    source_type="fundamental",
                )
            )
 
        trailing_pe = latest_values.get("trailing_pe")
        forward_pe = latest_values.get("forward_pe")
        peg_ratio = latest_values.get("peg_ratio")
        profit_margin = latest_values.get("profit_margin")
        gross_margin = latest_values.get("gross_margin")
        market_cap = latest_values.get("market_cap")
 
        if trailing_pe is not None and forward_pe is not None:
            features.append(
                self._feature(
                    "fundamental_pe_spread",
                    forward_pe - trailing_pe,
                    symbol,
                    market,
                    as_of_date,
                    source_name="raw_fundamental",
                    source_type="fundamental",
                )
            )
            if trailing_pe != 0:
                features.append(
                    self._feature(
                        "fundamental_forward_to_trailing_pe",
                        forward_pe / trailing_pe,
                        symbol,
                        market,
                        as_of_date,
                        source_name="raw_fundamental",
                        source_type="fundamental",
                    )
                )
 
        if trailing_pe is not None and peg_ratio is not None and peg_ratio != 0:
            features.append(
                self._feature(
                    "fundamental_pe_to_peg",
                    trailing_pe / peg_ratio,
                    symbol,
                    market,
                    as_of_date,
                    source_name="raw_fundamental",
                    source_type="fundamental",
                )
            )
 
        if market_cap is not None and gross_margin is not None:
            features.append(
                self._feature(
                    "fundamental_market_cap_to_gross_profit",
                    market_cap * gross_margin,
                    symbol,
                    market,
                    as_of_date,
                    source_name="raw_fundamental",
                    source_type="fundamental",
                )
            )
 
        if profit_margin is not None and gross_margin is not None:
            features.append(
                self._feature(
                    "fundamental_margin_spread",
                    gross_margin - profit_margin,
                    symbol,
                    market,
                    as_of_date,
                    source_name="raw_fundamental",
                    source_type="fundamental",
                )
            )
 
        return features

    def _build_relative_features(
        self,
        symbol: str,
        market: str,
        as_of_date: str,
    ) -> list[FeatureRecord]:
        price_history = self._load_price_history(symbol, market, as_of_date, lookback=60)
        if not price_history:
            return []

        latest = next((row for row in reversed(price_history) if row["date"] == as_of_date), None)
        if latest is None or latest.get("close") is None:
            return []

        closes = [row["close"] for row in price_history if row.get("close") is not None]
        volumes = [row["volume"] for row in price_history if row.get("volume") is not None]

        features: list[FeatureRecord] = []
        if len(closes) >= 20:
            mean_20 = mean(closes[-20:])
            features.append(self._feature("close_vs_ma20_pct", (latest["close"] - mean_20) / mean_20 if mean_20 else None, symbol, market, as_of_date))
            features.append(self._feature("close_vs_ema20_pct", (latest["close"] - self._ema(closes, 20)) / self._ema(closes, 20) if self._ema(closes, 20) else None, symbol, market, as_of_date))
            features.append(self._feature("close_zscore_20d", self._zscore(closes[-20:], latest["close"]), symbol, market, as_of_date))

        if len(volumes) >= 20 and latest.get("volume") is not None:
            avg_volume = mean(volumes[-20:])
            features.append(self._feature("volume_vs_20d_avg", latest["volume"] / avg_volume if avg_volume else None, symbol, market, as_of_date))
 
        if len(closes) >= 20:
            features.append(self._feature("close_percentile_20d", self._percentile_rank(closes[-20:], latest["close"]), symbol, market, as_of_date))
        if len(volumes) >= 20 and latest.get("volume") is not None:
            features.append(self._feature("volume_percentile_20d", self._percentile_rank(volumes[-20:], latest["volume"]), symbol, market, as_of_date))
 
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

        positive_count = 0
        negative_count = 0
        for row in rows:
            if row.sentiment_score is None or row.published_at is None:
                continue
            row_date = row.published_at.date()
            age = (date_target - row_date).days
            if age < 0:
                continue
            if row.sentiment_score >= 0.1:
                positive_count += 1
            elif row.sentiment_score <= -0.1:
                negative_count += 1

        features: list[FeatureRecord] = []
        for window, count_value in counts.items():
            features.append(self._feature(f"news_count_{window}d", float(count_value), symbol, market, as_of_date))
        features.append(self._feature("news_positive_count_7d", float(positive_count), symbol, market, as_of_date))
        features.append(self._feature("news_negative_count_7d", float(negative_count), symbol, market, as_of_date))
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
        metrics: dict[str, float | None] = {}
        for row in relevant_rows:
            metrics[row.field_name] = row.numeric_value
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
 
        call_iv = metrics.get("call_avg_iv")
        put_iv = metrics.get("put_avg_iv")
        call_oi = metrics.get("call_open_interest")
        put_oi = metrics.get("put_open_interest")
 
        if call_iv is not None and put_iv is not None and put_iv != 0:
            features.append(self._feature("options_iv_ratio", call_iv / put_iv, symbol, market, as_of_date))
            features.append(self._feature("options_iv_spread", call_iv - put_iv, symbol, market, as_of_date))
 
        if call_oi is not None and put_oi is not None and put_oi != 0:
            features.append(self._feature("options_oi_ratio", call_oi / put_oi, symbol, market, as_of_date))
            features.append(self._feature("options_oi_spread", call_oi - put_oi, symbol, market, as_of_date))
            features.append(self._feature("options_call_put_exposure", call_oi - put_oi, symbol, market, as_of_date))
 
        if call_iv is not None and put_iv is not None:
            features.append(self._feature("options_avg_iv", (call_iv + put_iv) / 2, symbol, market, as_of_date))
 
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
        future_event_days = None
        future_event_candidates: list[int] = []
        has_earnings_surprise = False
        has_guidance_change = False
        has_rating_change = False
        for row in rows:
            if row.event_date is None:
                continue
            event_date = row.event_date.date()
            delta_days = (event_date - target_dt).days
            age = abs(delta_days)
            if age <= 7:
                count_7d += 1
            if age <= 30:
                count_30d += 1
            if delta_days >= 0:
                future_event_candidates.append(delta_days)
            event_types[row.event_type] = event_types.get(row.event_type, 0) + 1
 
            text_context = f"{row.event_type or ''} {row.description or ''}".lower()
            if "earnings" in text_context and "surprise" in text_context:
                has_earnings_surprise = True
            if "guidance" in text_context:
                has_guidance_change = True
            if any(keyword in text_context for keyword in ["rating", "upgrade", "downgrade"]):
                has_rating_change = True
 
        if future_event_candidates:
            future_event_days = min(future_event_candidates)

        features = [
            self._feature("event_count_7d", float(count_7d), symbol, market, as_of_date),
            self._feature("event_count_30d", float(count_30d), symbol, market, as_of_date),
        ]
        if future_event_days is not None:
            features.append(self._feature("days_to_next_event", float(future_event_days), symbol, market, as_of_date))
            features.append(self._feature("has_event_next_30d", float(1 if future_event_days <= 30 else 0), symbol, market, as_of_date))
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
 
        features.append(self._feature("event_has_earnings_surprise", float(1 if has_earnings_surprise else 0), symbol, market, as_of_date))
        features.append(self._feature("event_has_guidance_change", float(1 if has_guidance_change else 0), symbol, market, as_of_date))
        features.append(self._feature("event_has_rating_change", float(1 if has_rating_change else 0), symbol, market, as_of_date))
 
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
        latest_rows = [r for r in rows if r.as_of_date == latest_date]
        previous_values: dict[str, float | None] = {}
        for row in rows:
            if row.as_of_date != latest_date and row.macro_name not in previous_values:
                previous_values[row.macro_name] = row.numeric_value

        features: list[FeatureRecord] = []
        for row in latest_rows:
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
            if row.macro_name in previous_values and row.numeric_value is not None and previous_values[row.macro_name] is not None:
                previous_value = previous_values[row.macro_name]
                if previous_value != 0:
                    features.append(
                        self._feature(
                            f"macro_{row.macro_name}_change",
                            (row.numeric_value - previous_value) / previous_value,
                            "",
                            market,
                            as_of_date,
                            source_name=row.source_name,
                            source_type=row.source_type,
                            raw_payload={"current_date": row.as_of_date, "previous_value": previous_value, "macro_name": row.macro_name},
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

    def _ema(self, values: list[float], period: int) -> float | None:
        if len(values) < period or period <= 0:
            return None
        k = 2 / (period + 1)
        ema = float(values[0])
        for value in values[1:]:
            ema = value * k + ema * (1 - k)
        return ema

    def _rsi(self, prices: list[float], period: int = 14) -> float | None:
        if len(prices) < period + 1:
            return None
        gains = []
        losses = []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            if diff >= 0:
                gains.append(diff)
            else:
                losses.append(-diff)
        avg_gain = mean(gains) if gains else 0.0
        avg_loss = mean(losses) if losses else 0.0
        if avg_loss == 0.0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _bollinger_percent(self, closes: list[float], period: int = 20) -> float | None:
        if len(closes) < period:
            return None
        window = closes[-period:]
        mean_close = mean(window)
        std_close = self._rolling_std(window)
        if mean_close is None or std_close is None or std_close == 0:
            return None
        return (closes[-1] - mean_close) / (2 * std_close)

    def _average_true_range(self, history: list[dict[str, Any]]) -> float | None:
        trs: list[float] = []
        previous_close = None
        for row in history:
            high = row.get("high")
            low = row.get("low")
            close = row.get("close")
            if high is None or low is None or close is None:
                continue
            if previous_close is None:
                trs.append(high - low)
            else:
                trs.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
            previous_close = close
        return mean(trs) if trs else None
 
    def _true_range(self, recent_period: list[dict[str, Any]]) -> float | None:
        if len(recent_period) < 2:
            return None
        previous = recent_period[-2]
        current = recent_period[-1]
        if previous.get("close") is None or current.get("high") is None or current.get("low") is None:
            return None
        return max(
            current["high"] - current["low"],
            abs(current["high"] - previous["close"]),
            abs(current["low"] - previous["close"]),
        )
 
    def _adx(self, history: list[dict[str, Any]], period: int = 14) -> float | None:
        if len(history) < period + 1:
            return None
 
        trs: list[float] = []
        plus_dm: list[float] = []
        minus_dm: list[float] = []
        for i in range(1, len(history)):
            current = history[i]
            previous = history[i - 1]
            if current.get("high") is None or current.get("low") is None or current.get("close") is None or previous.get("high") is None or previous.get("low") is None or previous.get("close") is None:
                continue
            high_diff = current["high"] - previous["high"]
            low_diff = previous["low"] - current["low"]
            plus_dm.append(high_diff if high_diff > low_diff and high_diff > 0 else 0.0)
            minus_dm.append(low_diff if low_diff > high_diff and low_diff > 0 else 0.0)
            trs.append(max(
                current["high"] - current["low"],
                abs(current["high"] - previous["close"]),
                abs(current["low"] - previous["close"]),
            ))
 
        if len(trs) < period or len(plus_dm) < period or len(minus_dm) < period:
            return None
 
        atr = self._wilder_smoothing(trs, period)
        smoothed_plus = self._wilder_smoothing(plus_dm, period)
        smoothed_minus = self._wilder_smoothing(minus_dm, period)
        if atr is None or smoothed_plus is None or smoothed_minus is None or atr == 0:
            return None
 
        plus_di = 100.0 * smoothed_plus / atr
        minus_di = 100.0 * smoothed_minus / atr
        if plus_di + minus_di == 0:
           return None
        return abs(plus_di - minus_di) / (plus_di + minus_di) * 100.0
 
    def _wilder_smoothing(self, values: list[float], period: int) -> float | None:
        if len(values) < period:
            return None
        smoothed = float(values[0])
        for value in values[1:]:
            smoothed = (smoothed * (period - 1) + value) / period
        return smoothed
 
    def _macd_series(self, closes: list[float]) -> list[float]:
        macd_values: list[float] = []
        for i in range(len(closes)):
            if i + 1 < 26:
                macd_values.append(None)
                continue
            ema_12 = self._ema(closes[: i + 1], 12)
            ema_26 = self._ema(closes[: i + 1], 26)
            macd_values.append(ema_12 - ema_26 if ema_12 is not None and ema_26 is not None else None)
        return [value for value in macd_values if value is not None]
 
    def _percentile_rank(self, window: list[float], value: float | None) -> float | None:
        if value is None or not window:
            return None
        sorted_window = sorted(window)
        rank = sum(1 for item in sorted_window if item <= value)
        return rank / len(sorted_window)
 
    def _on_balance_volume(self, history: list[dict[str, Any]]) -> float | None:
        obv = 0.0
        previous_close = None
        for row in history:
            close = row.get("close")
            volume = row.get("volume")
            if close is None or volume is None:
                continue
            if previous_close is None:
                previous_close = close
                continue
            if close > previous_close:
                obv += volume
            elif close < previous_close:
                obv -= volume
            previous_close = close
        return obv
 
    def _zscore(self, window: list[float], value: float) -> float | None:
        if not window:
            return None
        mean_value = mean(window)
        std_value = self._rolling_std(window)
        if std_value is None or std_value == 0:
            return None
        return (value - mean_value) / std_value


def create_feature_engineering_pipeline(store: PortfolioStore) -> FeatureEngineeringPipeline:
    return FeatureEngineeringPipeline(store=store)
