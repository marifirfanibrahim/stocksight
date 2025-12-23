"""
core logic tests
unit tests for core business logic
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# add project root to path before any other imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.data_processor import DataProcessor
from core.column_detector import ColumnDetector
from core.rule_clustering import RuleClustering
from core.feature_engineer import FeatureEngineer
from core.forecaster import Forecaster
from core.anomaly_detector import AnomalyDetector


# ============================================================================
#                           TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_data():
    # create sample dataframe for testing
    np.random.seed(42)
    
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
    skus = [f"SKU{i:03d}" for i in range(20)]
    
    rows = []
    for sku in skus:
        base_demand = np.random.randint(10, 1000)
        seasonality = np.sin(np.arange(len(dates)) * 2 * np.pi / 365) * base_demand * 0.3
        noise = np.random.normal(0, base_demand * 0.1, len(dates))
        demand = base_demand + seasonality + noise
        demand = np.maximum(0, demand).astype(int)
        
        for date, qty in zip(dates, demand):
            rows.append({
                "date": date,
                "sku": sku,
                "quantity": qty,
                "category": f"CAT{sku[3]}"
            })
    
    return pd.DataFrame(rows)


@pytest.fixture
def processor(sample_data):
    # create configured data processor
    proc = DataProcessor()
    proc.raw_data = sample_data
    proc.set_column_mapping({
        "date": "date",
        "sku": "sku",
        "quantity": "quantity",
        "category": "category"
    })
    proc.process_data()
    return proc


# ============================================================================
#                        DATA PROCESSOR TESTS
# ============================================================================

class TestDataProcessor:
    # data processor test cases
    
    def test_load_and_process(self, sample_data):
        # test data loading and processing
        proc = DataProcessor()
        proc.raw_data = sample_data
        proc.set_column_mapping({
            "date": "date",
            "sku": "sku",
            "quantity": "quantity"
        })
        
        success, message = proc.process_data()
        
        assert success
        assert proc.processed_data is not None
        assert len(proc.sku_list) == 20
    
    def test_quality_calculation(self, processor):
        # test quality score calculation
        quality = processor.calculate_quality()
        
        assert "overall_score" in quality
        assert 0 <= quality["overall_score"] <= 100
        assert "metrics" in quality
    
    def test_sku_classification(self, processor):
        # test abc classification
        classification = processor.classify_skus()
        
        assert "A" in classification
        assert "B" in classification
        assert "C" in classification
        
        total = len(classification["A"]) + len(classification["B"]) + len(classification["C"])
        assert total == len(processor.sku_list)
    
    def test_get_sku_data(self, processor):
        # test getting single sku data
        sku = processor.sku_list[0]
        sku_data = processor.get_sku_data(sku)
        
        assert not sku_data.empty
        assert "quantity" in sku_data.columns


# ============================================================================
#                       COLUMN DETECTOR TESTS
# ============================================================================

class TestColumnDetector:
    # column detector test cases
    
    def test_detect_date_column(self, sample_data):
        # test date column detection
        detector = ColumnDetector()
        detections = detector.detect_columns(sample_data)
        
        assert "date" in detections
        assert detections["date"]["detected_type"] == "date"
        assert detections["date"]["confidence"] > 0.7
    
    def test_detect_sku_column(self, sample_data):
        # test sku column detection
        detector = ColumnDetector()
        detections = detector.detect_columns(sample_data)
        
        assert "sku" in detections
        assert detections["sku"]["detected_type"] == "sku"
    
    def test_get_best_mapping(self, sample_data):
        # test automatic mapping
        detector = ColumnDetector()
        detections = detector.detect_columns(sample_data)
        mapping = detector.get_best_mapping(detections)
        
        assert "date" in mapping
        assert "sku" in mapping
        assert "quantity" in mapping


# ============================================================================
#                        RULE CLUSTERING TESTS
# ============================================================================

class TestRuleClustering:
    # rule clustering test cases
    
    def test_cluster_skus(self, processor):
        # test clustering
        clustering = RuleClustering()
        
        clusters = clustering.cluster_skus(
            processor.processed_data,
            "sku", "date", "quantity"
        )
        
        assert len(clusters) == len(processor.sku_list)
        
        for sku, cluster in clusters.items():
            assert cluster.volume_tier in ["A", "B", "C"]
            assert cluster.pattern_type in ["seasonal", "erratic", "variable", "steady"]
    
    def test_cluster_summary(self, processor):
        # test cluster summary
        clustering = RuleClustering()
        clustering.cluster_skus(
            processor.processed_data,
            "sku", "date", "quantity"
        )
        
        summary = clustering.get_cluster_summary()
        
        assert len(summary) > 0
        
        for item in summary:
            assert "cluster" in item
            assert "item_count" in item
            assert "pct_of_items" in item
    
    def test_filter_by_tier(self, processor):
        # test filtering by tier
        clustering = RuleClustering()
        clustering.cluster_skus(
            processor.processed_data,
            "sku", "date", "quantity"
        )
        
        a_items = clustering.get_skus_by_tier("A")
        b_items = clustering.get_skus_by_tier("B")
        c_items = clustering.get_skus_by_tier("C")
        
        total = len(a_items) + len(b_items) + len(c_items)
        assert total == len(processor.sku_list)


# ============================================================================
#                      FEATURE ENGINEER TESTS
# ============================================================================

class TestFeatureEngineer:
    # feature engineer test cases
    
    def test_create_features(self, processor):
        # test feature creation
        engineer = FeatureEngineer()
        
        sku = processor.sku_list[0]
        sku_data = processor.get_sku_data(sku)
        
        featured = engineer.create_features(
            sku_data, "date", "quantity", "all_20"
        )
        
        assert "lag_1" in featured.columns
        assert "rolling_mean_7" in featured.columns
        assert "month" in featured.columns
    
    def test_feature_sets(self, processor):
        # test different feature sets
        engineer = FeatureEngineer()
        
        sku = processor.sku_list[0]
        sku_data = processor.get_sku_data(sku)
        
        # basic 5
        basic = engineer.create_features(sku_data, "date", "quantity", "basic_5")
        basic_features = [c for c in basic.columns if c not in sku_data.columns]
        
        # top 10
        top10 = engineer.create_features(sku_data, "date", "quantity", "top_10")
        top10_features = [c for c in top10.columns if c not in sku_data.columns]
        
        assert len(basic_features) <= len(top10_features)
    
    def test_feature_importance(self, processor):
        # test feature importance calculation
        engineer = FeatureEngineer()
        
        sku = processor.sku_list[0]
        sku_data = processor.get_sku_data(sku)
        
        featured = engineer.create_features(sku_data, "date", "quantity", "top_10")
        featured = featured.dropna()
        
        feature_cols = ["lag_1", "lag_7", "rolling_mean_7"]
        importance = engineer.get_feature_importance(featured, "quantity", feature_cols)
        
        assert len(importance) > 0
        assert sum(importance.values()) <= 1.01  # allow small float error


# ============================================================================
#                          FORECASTER TESTS
# ============================================================================

class TestForecaster:
    # forecaster test cases
    
    def test_naive_forecast(self, processor):
        # test naive forecast
        forecaster = Forecaster()
        
        sku = processor.sku_list[0]
        sku_data = processor.get_sku_data(sku)
        
        result = forecaster.forecast(
            sku_data, "date", "quantity",
            strategy="simple", horizon=30
        )
        
        assert len(result.forecast) == 30
        assert len(result.dates) == 30
        assert result.model is not None
    
    def test_forecast_batch(self, processor):
        # test batch forecasting
        forecaster = Forecaster()
        
        # use small subset
        small_df = processor.processed_data[
            processor.processed_data["sku"].isin(processor.sku_list[:5])
        ]
        
        results = forecaster.forecast_batch(
            small_df, "sku", "date", "quantity",
            strategy="simple", horizon=14
        )
        
        assert len(results) == 5
        
        for sku, result in results.items():
            assert len(result.forecast) == 14
    
    def test_forecast_metrics(self, processor):
        # test forecast metrics
        forecaster = Forecaster()
        
        sku = processor.sku_list[0]
        sku_data = processor.get_sku_data(sku)
        
        result = forecaster.forecast(
            sku_data, "date", "quantity",
            strategy="simple", horizon=30
        )
        
        assert "mape" in result.metrics
        assert "mae" in result.metrics
        assert result.metrics["mape"] >= 0


# ============================================================================
#                       ANOMALY DETECTOR TESTS
# ============================================================================

class TestAnomalyDetector:
    # anomaly detector test cases
    
    def test_detect_iqr(self, processor):
        # test iqr detection
        detector = AnomalyDetector()
        
        sku = processor.sku_list[0]
        sku_data = processor.get_sku_data(sku)
        
        anomalies = detector.detect_anomalies(sku_data, "date", "quantity", "iqr")
        
        # may or may not find anomalies
        assert isinstance(anomalies, list)
    
    def test_detect_zscore(self, processor):
        # test zscore detection
        detector = AnomalyDetector()
        
        sku = processor.sku_list[0]
        sku_data = processor.get_sku_data(sku)
        
        anomalies = detector.detect_anomalies(sku_data, "date", "quantity", "zscore")
        
        assert isinstance(anomalies, list)
    
    def test_detect_batch(self, processor):
        # test batch detection
        detector = AnomalyDetector()
        
        # use small subset
        small_df = processor.processed_data[
            processor.processed_data["sku"].isin(processor.sku_list[:10])
        ]
        
        all_anomalies = detector.detect_batch(
            small_df, "sku", "date", "quantity"
        )
        
        assert isinstance(all_anomalies, dict)
    
    def test_anomaly_summary(self, processor):
        # test anomaly summary
        detector = AnomalyDetector()
        
        small_df = processor.processed_data[
            processor.processed_data["sku"].isin(processor.sku_list[:10])
        ]
        
        detector.detect_batch(small_df, "sku", "date", "quantity")
        summary = detector.get_summary()
        
        assert "total_anomalies" in summary
        assert "skus_with_anomalies" in summary


# ============================================================================
#                            RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])