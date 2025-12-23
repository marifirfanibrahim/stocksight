import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from core.data_processor import DataProcessor
from core.feature_engineer import FeatureEngineer
from core.forecaster import Forecaster


@pytest.mark.slow
def test_large_end_to_end():
    # generate a larger dataset (integration, slow)
    np.random.seed(0)
    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="D")
    skus = [f"SKU{i:04d}" for i in range(1000)]  # larger SKU set

    rows = []
    for sku in skus[:100]:  # not all 1000 to keep runtime reasonable in CI but still larger
        base = np.random.randint(5, 500)
        noise = np.random.normal(0, base * 0.1, len(dates))
        demand = np.maximum(0, (base + noise).astype(int))
        for d, q in zip(dates, demand):
            rows.append({"date": d, "sku": sku, "quantity": q})

    df = pd.DataFrame(rows)

    dp = DataProcessor()
    dp.raw_data = df
    dp.set_column_mapping({"date": "date", "sku": "sku", "quantity": "quantity"})
    ok, msg = dp.process_data()
    assert ok

    fe = FeatureEngineer()
    # create features in parallel
    featured = fe.create_features_batch(dp.processed_data, 'sku', 'date', 'quantity', {s: 'C' for s in skus[:100]}, parallel=True, max_workers=4)
    assert not featured.empty

    fc = Forecaster()
    results = fc.forecast_batch(dp.processed_data[dp.processed_data['sku'].isin(skus[:20])], 'sku', 'date', 'quantity', strategy='simple', horizon=7, parallel=True, max_workers=4)
    assert isinstance(results, dict)
