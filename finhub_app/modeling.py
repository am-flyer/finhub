from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from joblib import dump, load
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from finhub_app.config import get_settings
from finhub_app.storage import FeatureRecord, PortfolioStore, RawDataRecord


@dataclass
class ModelMetadata:
    model_version: str
    trained_at: str
    market: str
    sample_count: int
    feature_count: int
    accuracy: float
    roc_auc: float | None
    positive_class_ratio: float
    model_path: str
    metadata_path: str


class ModelTrainingError(Exception):
    pass


def _resolve_model_paths(settings) -> Tuple[Path, Path]:
    model_dir = Path(settings.model_storage_dir).expanduser().resolve()
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "stock_predictor.joblib"
    metadata_path = model_dir / "stock_predictor_metadata.json"
    return model_path, metadata_path


def save_model_artifacts(
    model: Any,
    scaler: StandardScaler,
    feature_names: list[str],
    metadata: dict[str, Any],
    settings: Any,
) -> ModelMetadata:
    model_path, metadata_path = _resolve_model_paths(settings)
    dump({"model": model, "scaler": scaler, "feature_names": feature_names}, model_path)
    metadata_contents = {
        "model_version": metadata.get("model_version", "baseline-v0.1"),
        "trained_at": metadata.get("trained_at", datetime.now().isoformat()),
        "market": metadata.get("market", "US"),
        "sample_count": metadata.get("sample_count", 0),
        "feature_count": metadata.get("feature_count", 0),
        "accuracy": metadata.get("accuracy", 0.0),
        "roc_auc": metadata.get("roc_auc"),
        "positive_class_ratio": metadata.get("positive_class_ratio", 0.0),
        "model_path": str(model_path),
        "metadata_path": str(metadata_path),
    }
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata_contents, f, indent=2)

    return ModelMetadata(**metadata_contents)


def load_model_artifacts(settings: Any = None) -> Optional[dict[str, Any]]:
    if settings is None:
        settings = get_settings()
    model_path, metadata_path = _resolve_model_paths(settings)
    if not model_path.exists() or not metadata_path.exists():
        return None
    try:
        artifacts = load(model_path)
        if not isinstance(artifacts, dict) or "model" not in artifacts or "scaler" not in artifacts or "feature_names" not in artifacts:
            return None
        with metadata_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
        artifacts["metadata"] = metadata
        return artifacts
    except Exception:
        return None


def build_training_dataset(store: PortfolioStore, market: str = "US") -> Tuple[np.ndarray, np.ndarray, list[dict[str, Any]], list[str]]:
    with store.session_factory() as session:
        feature_rows = (
            session.query(FeatureRecord)
            .filter(FeatureRecord.market == market)
            .order_by(FeatureRecord.symbol.asc(), FeatureRecord.as_of_date.asc(), FeatureRecord.feature_name.asc())
            .all()
        )
        price_rows = (
            session.query(RawDataRecord)
            .filter(
                RawDataRecord.market == market,
                RawDataRecord.data_type == "price",
                RawDataRecord.field_name == "close",
                RawDataRecord.as_of_date != None,
                RawDataRecord.numeric_value != None,
            )
            .order_by(RawDataRecord.symbol.asc(), RawDataRecord.as_of_date.asc())
            .all()
        )

    feature_map: dict[tuple[str, str], dict[str, float]] = {}
    feature_keys: set[str] = set()
    for row in feature_rows:
        if row.as_of_date is None or row.symbol is None or row.feature_name is None:
            continue
        key = (row.symbol.upper(), row.as_of_date)
        if key not in feature_map:
            feature_map[key] = {}
        if row.numeric_value is not None:
            feature_map[key][row.feature_name] = row.numeric_value
            feature_keys.add(row.feature_name)

    closes_by_symbol: dict[str, dict[str, float]] = {}
    for row in price_rows:
        symbol = row.symbol.upper()
        if row.as_of_date is None or row.numeric_value is None:
            continue
        closes_by_symbol.setdefault(symbol, {})[row.as_of_date] = row.numeric_value

    X: list[list[float]] = []
    y: list[int] = []
    rows_metadata: list[dict[str, Any]] = []

    feature_names = sorted(feature_keys)
    if not feature_names:
        raise ModelTrainingError("No feature records available for training")

    for symbol, closes in closes_by_symbol.items():
        sorted_dates = sorted(closes.keys())
        for index, as_of_date in enumerate(sorted_dates[:-1]):
            next_date = sorted_dates[index + 1]
            current_close = closes.get(as_of_date)
            next_close = closes.get(next_date)
            if current_close is None or next_close is None or current_close == 0:
                continue
            sample_key = (symbol, as_of_date)
            features = feature_map.get(sample_key)
            if not features:
                continue
            vector = [float(features.get(name, 0.0)) for name in feature_names]
            price_change = (next_close - current_close) / current_close
            label = 1 if price_change > 0 else 0
            X.append(vector)
            y.append(label)
            rows_metadata.append(
                {
                    "symbol": symbol,
                    "as_of_date": as_of_date,
                    "next_date": next_date,
                    "price_change": price_change,
                }
            )

    if not X:
        raise ModelTrainingError("No labeled training samples could be built from feature records")

    return np.array(X, dtype=float), np.array(y, dtype=int), rows_metadata, feature_names


def train_model(store: PortfolioStore, market: str = "US", test_size: float = 0.2, min_samples: int = 20) -> ModelMetadata:
    X, y, _, feature_names = build_training_dataset(store, market=market)
    if len(X) < min_samples:
        raise ModelTrainingError("Not enough training samples to train a production model")

    stratify = None
    if len(set(y)) > 1:
        label_counts = Counter(y)
        if all(count >= 2 for count in label_counts.values()):
            stratify = y
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(class_weight="balanced", solver="liblinear", random_state=42, max_iter=1000)
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]
    accuracy = float(accuracy_score(y_test, y_pred))
    roc_auc = float(roc_auc_score(y_test, y_prob)) if len(set(y_test)) > 1 else None
    positive_ratio = float(np.mean(y))

    artifacts = load_model_artifacts(get_settings())
    previous_version = artifacts["metadata"]["model_version"] if artifacts and "metadata" in artifacts else "baseline-v0.1"
    model_version = f"trained-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    metadata = {
        "model_version": model_version,
        "trained_at": datetime.now().isoformat(),
        "market": market,
        "sample_count": len(X),
        "feature_count": X.shape[1],
        "accuracy": accuracy,
        "roc_auc": roc_auc,
        "positive_class_ratio": positive_ratio,
    }

    if not feature_names:
        raise ModelTrainingError("Could not determine feature names for model artifacts")

    save_model_artifacts(model, scaler, feature_names, metadata, get_settings())
    return ModelMetadata(**{**metadata, "model_path": str(_resolve_model_paths(get_settings())[0]), "metadata_path": str(_resolve_model_paths(get_settings())[1])})


def _feature_keys(store: PortfolioStore, market: str) -> Iterable[str]:
    with store.session_factory() as session:
        feature_names = (
            session.query(FeatureRecord.feature_name)
            .filter(FeatureRecord.market == market)
            .distinct()
            .all()
        )
        return [name for (name,) in feature_names]


def get_model_status(settings: Any = None) -> dict[str, Any]:
    if settings is None:
        settings = get_settings()
    artifacts = load_model_artifacts(settings)
    if artifacts is None:
        return {"status": "untrained", "model": None}
    return {
        "status": "ready",
        "metadata": artifacts.get("metadata", {}),
    }


def predict_market_symbol(store: PortfolioStore, symbol: str, market: str = "US") -> dict[str, Any]:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol must be provided")

    artifacts = load_model_artifacts(get_settings())
    if artifacts is None:
        raise ModelTrainingError("No trained model artifacts available")

    feature_names = artifacts["feature_names"]
    scaler: StandardScaler = artifacts["scaler"]
    model = artifacts["model"]

    with store.session_factory() as session:
        latest_date = (
            session.query(FeatureRecord.as_of_date)
            .filter(
                FeatureRecord.market == market,
                FeatureRecord.symbol == symbol,
            )
            .order_by(FeatureRecord.as_of_date.desc())
            .limit(1)
            .scalar()
        )
        if latest_date is None:
            raise ModelTrainingError(f"No feature records available for {symbol} in {market}")

        rows = (
            session.query(FeatureRecord)
            .filter(
                FeatureRecord.market == market,
                FeatureRecord.symbol == symbol,
                FeatureRecord.as_of_date == latest_date,
            )
            .all()
        )

    row_features = {row.feature_name: row.numeric_value for row in rows if row.numeric_value is not None}
    if not row_features:
        raise ModelTrainingError(f"No numeric feature values available for {symbol} on {latest_date}")

    vector = np.array([float(row_features.get(name, 0.0)) for name in feature_names], dtype=float).reshape(1, -1)
    X_scaled = scaler.transform(vector)
    probability_up = float(model.predict_proba(X_scaled)[0][1])
    expected_move = round((probability_up - 0.5) * 4.0, 2)
    expected_price = None

    return {
        "symbol": symbol,
        "market": market,
        "as_of_date": latest_date,
        "predicted_up_probability": round(min(max(probability_up, 0.01), 0.99), 2),
        "expected_move_percent": expected_move,
        "expected_price": expected_price,
        "confidence": "High" if probability_up >= 0.65 else "Medium" if probability_up >= 0.55 else "Low",
        "model_version": artifacts["metadata"].get("model_version", "trained"),
    }
