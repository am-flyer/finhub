import os
from datetime import datetime

from finhub_app.feature_store import FeatureEngineeringPipeline
from finhub_app.storage import PortfolioStore, RawDataRecord
from finhub_app.modeling import build_training_dataset, predict_market_symbol, train_model


def test_build_training_dataset_and_predict(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'modeling_test.db'}"
    os.environ["MODEL_STORAGE_DIR"] = str(tmp_path / "model_artifacts")
    store = PortfolioStore(database_url)
    store.initialize()

    # Create raw price close history for multiple consecutive days
    close_prices = [100.0, 102.0, 101.0, 103.0]
    dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"]
    for date_str, close_price in zip(dates, close_prices):
        store.save_raw_data_record(
            RawDataRecord(
                market="US",
                symbol="AAPL",
                as_of_date=date_str,
                data_type="price",
                field_name="close",
                numeric_value=close_price,
                text_value=None,
                source_name="test",
                source_type="market",
                raw_payload=None,
                retrieved_at=datetime.now(),
            )
        )

    # Insert synthetic open/high/low/volume to support feature generation
    pipeline = FeatureEngineeringPipeline(store)
    for date_str, close_price in zip(dates, close_prices):
        for field_name, numeric_value in [
            ("open", close_price - 1.0),
            ("high", close_price + 1.0),
            ("low", close_price - 2.0),
            ("volume", 1_000_000.0),
        ]:
            store.save_raw_data_record(
                RawDataRecord(
                    market="US",
                    symbol="AAPL",
                    as_of_date=date_str,
                    data_type="price",
                    field_name=field_name,
                    numeric_value=numeric_value,
                    text_value=None,
                    source_name="test",
                    source_type="market",
                    raw_payload=None,
                    retrieved_at=datetime.now(),
                )
            )

    for date_str in dates:
        features = pipeline.build_features_for_symbol("AAPL", market="US", as_of_date=date_str)
        assert features, f"Expected features for {date_str}"

    features = pipeline.build_features_for_symbol("AAPL", market="US", as_of_date="2026-07-04")
    assert any(feature.feature_name == "return_1d" for feature in features)

    X, y, metadata, feature_names = build_training_dataset(store, market="US")
    assert X.shape[0] >= 3
    assert X.shape[1] > 0
    assert set(y).issubset({0, 1})
    assert feature_names, "Expected feature names for training dataset"

    model_metadata = train_model(store, market="US", min_samples=2)
    assert model_metadata.sample_count >= 2
    assert model_metadata.feature_count > 0

    prediction = predict_market_symbol(store, "AAPL", market="US")
    assert "predicted_up_probability" in prediction
    assert 0.0 <= prediction["predicted_up_probability"] <= 1.0
