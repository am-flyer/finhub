from datetime import datetime

from finhub_app.feature_store import FeatureEngineeringPipeline
from finhub_app.storage import PortfolioStore, RawDataRecord
from finhub_app.domain import RawOptionsPayload, RawEventPayload


def test_feature_engineering_builds_features_for_price_history(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'feature_store_test.db'}"
    store = PortfolioStore(database_url)
    store.initialize()

    prices = [
        ("2026-07-01", 150.0, 152.0, 149.0, 151.0, 1_000_000),
        ("2026-07-02", 151.0, 153.0, 150.0, 152.0, 1_100_000),
        ("2026-07-03", 152.0, 154.0, 151.0, 153.0, 1_050_000),
        ("2026-07-04", 153.0, 155.0, 152.0, 154.0, 1_200_000),
        ("2026-07-05", 154.0, 156.0, 153.0, 155.0, 1_250_000),
    ]

    for date_str, open_price, high, low, close, volume in prices:
        for field_name, value in [
            ("open", open_price),
            ("high", high),
            ("low", low),
            ("close", close),
            ("volume", volume),
        ]:
            store.save_raw_data_record(
                RawDataRecord(
                    market="US",
                    symbol="AAPL",
                    as_of_date=date_str,
                    data_type="price",
                    field_name=field_name,
                    numeric_value=float(value),
                    text_value=None,
                    source_name="test",
                    source_type="market",
                    raw_payload=None,
                )
            )

    store.save_raw_data_record(
        RawDataRecord(
            market="US",
            symbol="AAPL",
            as_of_date="2026-07-05",
            data_type="fundamental",
            field_name="trailing_pe",
            numeric_value=28.5,
            text_value=None,
            source_name="test",
            source_type="fundamental",
            raw_payload=None,
        )
    )
    store.save_raw_data_record(
        RawDataRecord(
            market="US",
            symbol="AAPL",
            as_of_date="2026-07-05",
            data_type="fundamental",
            field_name="forward_pe",
            numeric_value=26.0,
            text_value=None,
            source_name="test",
            source_type="fundamental",
            raw_payload=None,
        )
    )
    store.save_raw_data_record(
        RawDataRecord(
            market="US",
            symbol="AAPL",
            as_of_date="2026-07-05",
            data_type="fundamental",
            field_name="peg_ratio",
            numeric_value=1.8,
            text_value=None,
            source_name="test",
            source_type="fundamental",
            raw_payload=None,
        )
    )
    store.save_raw_options_record(
        RawOptionsPayload(
            market="US",
            symbol="AAPL",
            as_of_date="2026-07-05",
            field_name="call_avg_iv",
            numeric_value=0.35,
            text_value=None,
            source_name="test",
            source_type="options",
            raw_payload=None,
            retrieved_at=datetime.now(),
        )
    )
    store.save_raw_options_record(
        RawOptionsPayload(
            market="US",
            symbol="AAPL",
            as_of_date="2026-07-05",
            field_name="put_avg_iv",
            numeric_value=0.25,
            text_value=None,
            source_name="test",
            source_type="options",
            raw_payload=None,
            retrieved_at=datetime.now(),
        )
    )
    store.save_raw_event_record(
        RawEventPayload(
            market="US",
            symbol="AAPL",
            event_type="Earnings Surprise",
            event_date=datetime.now(),
            description="AAPL reported stronger than expected earnings.",
            source_name="test",
            source_type="event",
            raw_payload=None,
            retrieved_at=datetime.now(),
        )
    )
 
    pipeline = FeatureEngineeringPipeline(store)
    features = pipeline.build_features_for_symbol("AAPL", market="US")
    feature_names = {feature.feature_name for feature in features}

    assert "return_1d" in feature_names
    assert "gap_pct" in feature_names
    assert "return_5d" in feature_names
    assert "close" in feature_names
    assert "volatility_5d" in feature_names
    assert "fundamental_trailing_pe" in feature_names
    assert "fundamental_pe_spread" in feature_names
    assert "options_iv_ratio" in feature_names
    assert "event_has_earnings_surprise" in feature_names
 
    saved = store.get_feature_rows("US", "AAPL")
    saved_names = {row["feature_name"] for row in saved}
    assert "return_1d" in saved_names
    assert "gap_pct" in saved_names
    assert "fundamental_trailing_pe" in saved_names
    assert "fundamental_pe_spread" in saved_names
    assert "options_iv_ratio" in saved_names
    assert "event_has_earnings_surprise" in saved_names
