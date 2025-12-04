"""
integration tests
end to end workflow tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os
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
from utils.export_formatter import ExportFormatter


# ============================================================================
#                           TEST FIXTURES
# ============================================================================

@pytest.fixture
def large_sample_data():
    # create larger sample dataset
    np.random.seed(42)
    
    dates = pd.date_range(start="2022-01-01", end="2023-12-31", freq="D")
    skus = [f"SKU{i:04d}" for i in range(500)]  # 500 skus
    
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
                "category": f"CAT{int(sku[3:5])}"
            })
    
    return pd.DataFrame(rows)


@pytest.fixture
def temp_csv_file(large_sample_data):
    # create temporary csv file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        large_sample_data.to_csv(f.name, index=False)
        yield f.name
    
    # cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


# ============================================================================
#                      FULL WORKFLOW TESTS
# ============================================================================

class TestFullWorkflow:
    # full workflow integration tests
    
    def test_complete_workflow(self, large_sample_data):
        # test complete workflow from data to forecast
        
        # step 1 - data processing
        processor = DataProcessor()
        processor.raw_data = large_sample_data
        
        # column detection
        detector = ColumnDetector()
        detections = detector.detect_columns(large_sample_data)
        mapping = detector.get_best_mapping(detections)
        
        assert "date" in mapping
        assert "sku" in mapping
        assert "quantity" in mapping
        
        processor.set_column_mapping(mapping)
        success, message = processor.process_data()
        
        assert success
        assert len(processor.sku_list) == 500
        
        # step 2 - quality check
        quality = processor.calculate_quality()
        assert quality["overall_score"] > 50
        
        # step 3 - clustering
        clustering = RuleClustering()
        clusters = clustering.cluster_skus(
            processor.processed_data,
            "sku", "date", "quantity"
        )
        
        assert len(clusters) == 500
        
        # check abc distribution
        a_count = len(clustering.get_skus_by_tier("A"))
        b_count = len(clustering.get_skus_by_tier("B"))
        c_count = len(clustering.get_skus_by_tier("C"))
        
        assert a_count + b_count + c_count == 500
        
        # step 4 - feature engineering for sample
        engineer = FeatureEngineer()
        sample_skus = processor.sku_list[:10]
        
        for sku in sample_skus:
            sku_data = processor.get_sku_data(sku)
            featured = engineer.create_features(sku_data, "date", "quantity", "top_10")
            
            assert "lag_1" in featured.columns
            assert "rolling_mean_7" in featured.columns
        
        # step 5 - forecasting for sample
        forecaster = Forecaster()
        
        sample_df = processor.processed_data[
            processor.processed_data["sku"].isin(sample_skus)
        ]
        
        results = forecaster.forecast_batch(
            sample_df, "sku", "date", "quantity",
            strategy="simple", horizon=30
        )
        
        assert len(results) == 10
        
        for sku, result in results.items():
            assert len(result.forecast) == 30
            assert result.metrics["mape"] >= 0
    
    def test_file_load_workflow(self, temp_csv_file):
        # test loading from file
        processor = DataProcessor()
        
        success, message = processor.load_file(temp_csv_file)
        
        assert success
        assert processor.raw_data is not None
        assert len(processor.raw_data) > 0
    
    def test_anomaly_workflow(self, large_sample_data):
        # test anomaly detection workflow
        processor = DataProcessor()
        processor.raw_data = large_sample_data
        processor.set_column_mapping({
            "date": "date",
            "sku": "sku",
            "quantity": "quantity"
        })
        processor.process_data()
        
        detector = AnomalyDetector()
        
        # detect for small sample
        sample_skus = processor.sku_list[:20]
        sample_df = processor.processed_data[
            processor.processed_data["sku"].isin(sample_skus)
        ]
        
        all_anomalies = detector.detect_batch(
            sample_df, "sku", "date", "quantity"
        )
        
        summary = detector.get_summary()
        
        assert "total_anomalies" in summary
        assert "skus_with_anomalies" in summary
    
    def test_export_workflow(self, large_sample_data):
        # test export workflow
        processor = DataProcessor()
        processor.raw_data = large_sample_data
        processor.set_column_mapping({
            "date": "date",
            "sku": "sku",
            "quantity": "quantity"
        })
        processor.process_data()
        
        # generate forecasts
        forecaster = Forecaster()
        
        sample_skus = processor.sku_list[:5]
        sample_df = processor.processed_data[
            processor.processed_data["sku"].isin(sample_skus)
        ]
        
        results = forecaster.forecast_batch(
            sample_df, "sku", "date", "quantity",
            strategy="simple", horizon=14
        )
        
        # export
        exporter = ExportFormatter()
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            csv_path = f.name
        
        try:
            df = exporter.format_forecast_csv(results)
            success, message = exporter.export_csv(df, csv_path)
            
            assert success
            assert os.path.exists(csv_path)
            
            # verify content
            loaded = pd.read_csv(csv_path)
            assert len(loaded) == 5 * 14  # 5 skus * 14 days
            assert "forecast" in loaded.columns
        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)


# ============================================================================
#                      PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    # performance test cases
    
    def test_clustering_performance(self, large_sample_data):
        # test clustering performance
        import time
        
        processor = DataProcessor()
        processor.raw_data = large_sample_data
        processor.set_column_mapping({
            "date": "date",
            "sku": "sku",
            "quantity": "quantity"
        })
        processor.process_data()
        
        clustering = RuleClustering()
        
        start = time.time()
        clusters = clustering.cluster_skus(
            processor.processed_data,
            "sku", "date", "quantity"
        )
        elapsed = time.time() - start
        
        # should complete in reasonable time
        assert elapsed < 30  # 30 seconds max for 500 skus
        assert len(clusters) == 500
    
    def test_memory_usage(self, large_sample_data):
        # test memory usage
        from utils.memory_manager import MemoryManager
        
        manager = MemoryManager()
        
        initial = manager.get_memory_info()["rss_mb"]
        
        processor = DataProcessor()
        processor.raw_data = large_sample_data
        processor.set_column_mapping({
            "date": "date",
            "sku": "sku",
            "quantity": "quantity"
        })
        processor.process_data()
        
        after_load = manager.get_memory_info()["rss_mb"]
        
        # memory increase should be reasonable
        increase = after_load - initial
        assert increase < 500  # less than 500mb increase


# ============================================================================
#                            RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])