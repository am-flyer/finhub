from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import List

import yfinance as yf

from finhub_app.modeling import ModelTrainingError, predict_market_symbol


@dataclass
class PredictionResult:
    symbol: str
    market: str
    predicted_up_probability: float
    expected_move_percent: float
    expected_price: float | None
    confidence: str
    top_drivers: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    model_version: str = "baseline-v0.1"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "yfinance"


def _format_confidence(score: float) -> str:
    if score >= 0.80:
        return "High"
    if score >= 0.60:
        return "Medium"
    return "Low"


def _percent(value: float) -> float:
    return round(value * 100.0, 2)


def predict_symbol(symbol: str, market: str = "US") -> PredictionResult:
    symbol = symbol.strip().upper()
    model_version = "baseline-v0.1"

    try:
        store = None
        from finhub_app.storage import PortfolioStore
        from finhub_app.config import get_settings

        settings = get_settings()
        store = PortfolioStore(settings.database_url)
        artifact = None
        try:
            prediction_context = predict_market_symbol(store, symbol, market=market)
            model_version = prediction_context.get("model_version", "trained")
            return PredictionResult(
                symbol=symbol,
                market=market.upper(),
                predicted_up_probability=prediction_context["predicted_up_probability"],
                expected_move_percent=prediction_context["expected_move_percent"],
                expected_price=prediction_context["expected_price"],
                confidence=prediction_context["confidence"],
                top_drivers=[f"Model-based forecast for {symbol}."],
                risks=["Model predictions are based on historical features and may not reflect future events."],
                model_version=model_version,
                source="trained_model",
            )
        except ModelTrainingError:
            pass

        ticker = yf.Ticker(symbol)
        history = ticker.history(period="60d", interval="1d")
        close_series = history["Close"].dropna()
        if len(close_series) < 10:
            raise ValueError("Not enough historical data")

        latest_price = float(close_series.iloc[-1])
        returns = close_series.pct_change().dropna()
        mean_return = float(returns.mean())
        volatility = float(returns.std())
        last_5_mean = float(returns.tail(5).mean())

        predicted_up_probability = 0.5 + min(max(mean_return * 5.0, -0.25), 0.25)
        predicted_up_probability = round(min(max(predicted_up_probability, 0.05), 0.95), 2)

        expected_move_percent = round(min(max(last_5_mean * 100.0, -2.0), 2.0), 2)
        expected_price = round(latest_price * (1 + expected_move_percent / 100.0), 2)

        confidence_score = 1.0 - min(volatility * 5.0, 0.7)
        confidence = _format_confidence(confidence_score)

        top_drivers = [
            f"Recent average return { _percent(mean_return) }%",
            f"5-day momentum { _percent(last_5_mean) }%",
            f"Historical volatility { _percent(volatility) }%",
        ]

        risks = [
            "Prediction is based on recent price history only.",
            "Event, news, and options data are not yet included in this estimate.",
        ]

        return PredictionResult(
            symbol=symbol,
            market=market.upper(),
            predicted_up_probability=predicted_up_probability,
            expected_move_percent=expected_move_percent,
            expected_price=expected_price,
            confidence=confidence,
            top_drivers=top_drivers,
            risks=risks,
            model_version=model_version,
            source="yfinance",
        )
    except Exception as exc:
        return PredictionResult(
            symbol=symbol,
            market=market.upper(),
            predicted_up_probability=0.5,
            expected_move_percent=0.0,
            expected_price=None,
            confidence="Low",
            top_drivers=["Model fallback: insufficient data or unexpected symbol."],
            risks=["Real model not available yet.", str(exc)],
            model_version=model_version,
            source="yfinance",
        )


def predict_holdings(symbols: List[str], market: str = "US") -> List[PredictionResult]:
    results: List[PredictionResult] = []
    for symbol in sorted(set(symbol.strip().upper() for symbol in symbols if symbol.strip())):
        results.append(predict_symbol(symbol, market=market))
    return results


def serialize_prediction(result: PredictionResult) -> dict:
    return asdict(result)
