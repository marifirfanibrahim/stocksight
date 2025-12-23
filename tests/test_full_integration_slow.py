import runpy
import tempfile
import os
import pandas as pd
import pytest

# Heavy integration test that generates a realistic dataset and runs the full pipeline.
# Marked slow so it only runs on demand.

pytestmark = pytest.mark.slow


def test_full_pipeline_on_generated_data(tmp_path):
    # load generator from assets script
    script_path = os.path.join(os.path.dirname(__file__), "..", "assets", "sample_data", "generate_test_data.py")
    script_path = os.path.normpath(script_path)

    assert os.path.exists(script_path), f"generator script not found at {script_path}"

    module_globals = runpy.run_path(script_path)
    DataGenerator = module_globals.get("DataGenerator")
    assert DataGenerator is not None, "DataGenerator not found in generator script"

    # use a sizable but bounded dataset for CI/manual runs
    cfg = {
        "num_skus": 200,
        "start_date": "2023-01-01",
        "duration_days": 365,
        "seed": 123,
        "output_csv": "integration_test_dataset.csv",
        "output_excel": "integration_test_dataset.xlsx"
    }

    gen = DataGenerator(cfg)
    df = gen.create_dataset()

    # save to temporary csv to exercise file-loading functionality
    csv_path = tmp_path / cfg["output_csv"]
    df.to_csv(str(csv_path), index=False)

    # import core components
    from core.data_processor import DataProcessor
    from core.feature_engineer import FeatureEngineer
    from core.forecaster import Forecaster

    dp = DataProcessor()

    ok, msg = dp.load_file(str(csv_path))
    assert ok, f"Failed to load generated csv: {msg}"

    # set explicit mapping based on generator column names
    mapping = {
        "date": "trx_date",
        "sku": "product_id",
        "quantity": "sales_qty",
        "price": "unit_price",
        "promo": "is_promo",
        "category": "category_group"
    }

    dp.set_column_mapping(mapping)
    ok, msg = dp.process_data()
    assert ok, f"process_data failed: {msg}"

    # compute quality and apply a fix if critical issues exist
    quality = dp.calculate_quality()
    assert "overall_score" in quality

    # attempt to fill missing values and remove duplicates
    dp.apply_fix("fill_missing", method="ffill")
    dp.apply_fix("remove_duplicates", method="sum")
    dp.apply_fix("fix_negatives", method="abs")

    # create tier mapping based on average sales per SKU
    sku_col = mapping["sku"]
    qty_col = mapping["quantity"]
    avg_sales = dp.processed_data.groupby(sku_col)[qty_col].mean().sort_values(ascending=False)
    skus = avg_sales.index.tolist()

    tier_mapping = {}
    n = len(skus)
    for i, sku in enumerate(skus):
        if i < max(1, int(n * 0.1)):
            tier_mapping[sku] = "A"
        elif i < int(n * 0.4):
            tier_mapping[sku] = "B"
        else:
            tier_mapping[sku] = "C"

    fe = FeatureEngineer()
    featured = fe.create_features_batch(
        dp.processed_data,
        sku_col,
        mapping["date"],
        qty_col,
        tier_mapping,
        price_col=mapping["price"],
        promo_col=mapping["promo"],
        parallel=False,
    )

    assert not featured.empty, "Feature engineering returned empty dataframe"

    # run a forecast for one SKU using Forecaster
    fc = Forecaster()
    sample_sku = skus[0]
    sku_df = featured[featured[sku_col] == sample_sku]

    res = fc.forecast(sku_df, mapping["date"], qty_col, strategy="balanced", horizon=30, frequency="D")
    assert hasattr(res, "forecast") and len(res.forecast) > 0, "Forecast did not return expected output"

    # simple checks on metrics
    assert isinstance(res.metrics, dict)

    # cleanup
    try:
        os.remove(str(csv_path))
    except Exception:
        pass
