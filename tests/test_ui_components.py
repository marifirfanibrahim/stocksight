"""
ui component tests
unit tests for pyqt widgets and dialogs
"""

import pytest
import sys
from pathlib import Path

# add project root to path before any other imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

# create qapplication for tests
app = QApplication.instance() or QApplication(sys.argv)

import pandas as pd
import numpy as np

from ui.models.session_model import SessionModel
from ui.models.sku_table_model import SKUTableModel
from ui.models.forecast_model import ForecastTableModel
from core.forecaster import ForecastResult


# ============================================================================
#                           TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_dataframe():
    # create sample dataframe
    return pd.DataFrame({
        "sku": [f"SKU{i:03d}" for i in range(100)],
        "category": [f"CAT{i % 5}" for i in range(100)],
        "volume": np.random.randint(100, 10000, 100),
        "tier": np.random.choice(["A", "B", "C"], 100)
    })


@pytest.fixture
def sample_forecasts():
    # create sample forecast results
    forecasts = {}
    for i in range(10):
        sku = f"SKU{i:03d}"
        forecasts[sku] = ForecastResult(
            sku=sku,
            model="exponential_smoothing",
            forecast=[100 + j for j in range(30)],
            dates=[f"2024-01-{j+1:02d}" for j in range(30)],
            lower_bound=[90 + j for j in range(30)],
            upper_bound=[110 + j for j in range(30)],
            metrics={"mape": np.random.uniform(5, 30), "mae": 10.5}
        )
    return forecasts


# ============================================================================
#                       SESSION MODEL TESTS
# ============================================================================

class TestSessionModel:
    # session model test cases
    
    def test_initial_state(self):
        # test initial session state
        session = SessionModel()
        
        assert not session.state.file_loaded
        assert not session.state.data_cleaned
        assert session.get_workflow_step() == 0
    
    def test_update_state(self):
        # test state update
        session = SessionModel()
        session.update_state(file_loaded=True, total_skus=100)
        
        assert session.state.file_loaded
        assert session.state.total_skus == 100
    
    def test_bookmarks(self):
        # test bookmark functionality
        session = SessionModel()
        
        session.add_bookmark("SKU001", "important item")
        assert session.is_bookmarked("SKU001")
        
        session.remove_bookmark("SKU001")
        assert not session.is_bookmarked("SKU001")
    
    def test_workflow_progression(self):
        # test workflow step progression
        # matches get_workflow_step implementation in session_model.py
        session = SessionModel()
        
        # initial state - step 0
        assert session.get_workflow_step() == 0
        
        # after file loaded and columns mapped but not cleaned - step 1
        session.update_state(file_loaded=True, columns_mapped=True)
        assert session.get_workflow_step() == 1
        
        # after data cleaned but clusters not created - still step 1
        session.update_state(data_cleaned=True)
        assert session.get_workflow_step() == 1
        
        # after clusters created - step 2 (ready for features)
        session.update_state(clusters_created=True)
        assert session.get_workflow_step() == 2
        
        # after features created - step 3 (ready for forecasting)
        session.update_state(features_created=True)
        assert session.get_workflow_step() == 3
        
        # after forecasts generated - step 4 (complete)
        session.update_state(forecasts_generated=True)
        assert session.get_workflow_step() == 4
    
    def test_reset(self):
        # test session reset
        session = SessionModel()
        session.update_state(file_loaded=True, total_skus=100)
        session.add_bookmark("SKU001")
        
        session.reset()
        
        assert not session.state.file_loaded
        assert session.state.total_skus == 0
        assert len(session.get_bookmarks()) == 0
    
    def test_can_proceed_to_tab(self):
        # test tab access control
        session = SessionModel()
        
        # initially can only access tab 0
        assert session.can_proceed_to_tab(0) == True
        assert session.can_proceed_to_tab(1) == False
        assert session.can_proceed_to_tab(2) == False
        assert session.can_proceed_to_tab(3) == False
        
        # after data cleaned can access tab 1
        session.update_state(file_loaded=True, columns_mapped=True, data_cleaned=True)
        assert session.can_proceed_to_tab(1) == True
        
        # after clusters created can access tab 2
        session.update_state(clusters_created=True)
        assert session.can_proceed_to_tab(2) == True
        
        # after features created can access tab 3
        session.update_state(features_created=True)
        assert session.can_proceed_to_tab(3) == True
    
    def test_session_summary(self):
        # test session summary generation
        session = SessionModel()
        session.update_state(
            file_loaded=True,
            file_path="/path/to/file.csv",
            total_rows=10000,
            total_skus=500,
            total_categories=10,
            data_quality_score=85.5
        )
        
        summary = session.get_session_summary()
        
        assert summary["rows"] == 10000
        assert summary["skus"] == 500
        assert summary["categories"] == 10
        assert summary["quality_score"] == 85.5
    
    def test_data_management(self):
        # test data getter and setter
        session = SessionModel()
        
        test_data = pd.DataFrame({"a": [1, 2, 3]})
        session.set_data(test_data)
        
        assert session.state.file_loaded
        retrieved = session.get_data()
        assert retrieved is not None
        assert len(retrieved) == 3


# ============================================================================
#                       SKU TABLE MODEL TESTS
# ============================================================================

class TestSKUTableModel:
    # sku table model test cases
    
    def test_set_data(self, sample_dataframe):
        # test setting data
        model = SKUTableModel()
        model.set_data(sample_dataframe)
        
        assert model.rowCount() == 100
        assert model.columnCount() > 0
    
    def test_get_row_data(self, sample_dataframe):
        # test getting row data
        model = SKUTableModel()
        model.set_data(sample_dataframe)
        
        row_data = model.get_row_data(0)
        
        assert "sku" in row_data
        assert row_data["sku"] == "SKU000"
    
    def test_filtering(self, sample_dataframe):
        # test data filtering
        model = SKUTableModel()
        model.set_data(sample_dataframe)
        
        model.set_filter("SKU00")
        
        assert model.rowCount() < 100
    
    def test_display_columns(self, sample_dataframe):
        # test column display
        model = SKUTableModel()
        model.set_data(sample_dataframe, display_columns=["sku", "volume"])
        
        assert model.columnCount() == 2
        
        model.set_display_columns(["sku", "category", "tier"])
        assert model.columnCount() == 3
    
    def test_empty_data(self):
        # test with empty dataframe
        model = SKUTableModel()
        model.set_data(pd.DataFrame())
        
        assert model.rowCount() == 0
        assert model.columnCount() == 0
    
    def test_clear_filter(self, sample_dataframe):
        # test clearing filter
        model = SKUTableModel()
        model.set_data(sample_dataframe)
        
        model.set_filter("SKU00")
        filtered_count = model.rowCount()
        
        model.clear_filter()
        
        assert model.rowCount() == 100
        assert model.rowCount() > filtered_count


# ============================================================================
#                     FORECAST TABLE MODEL TESTS
# ============================================================================

class TestForecastTableModel:
    # forecast table model test cases
    
    def test_set_forecasts(self, sample_forecasts):
        # test setting forecasts
        model = ForecastTableModel()
        model.set_forecasts(sample_forecasts)
        
        assert model.rowCount() == 10
    
    def test_get_forecast(self, sample_forecasts):
        # test getting forecast
        model = ForecastTableModel()
        model.set_forecasts(sample_forecasts)
        
        forecast = model.get_forecast("SKU000")
        
        assert forecast is not None
        assert forecast.sku == "SKU000"
    
    def test_get_row_forecast(self, sample_forecasts):
        # test getting forecast by row
        model = ForecastTableModel()
        model.set_forecasts(sample_forecasts)
        
        forecast = model.get_row_forecast(0)
        
        assert forecast is not None
        assert len(forecast.forecast) == 30
    
    def test_get_summary(self, sample_forecasts):
        # test getting summary
        model = ForecastTableModel()
        model.set_forecasts(sample_forecasts)
        
        summary = model.get_summary()
        
        assert "total_items" in summary
        assert summary["total_items"] == 10
        assert "avg_mape" in summary
        assert "total_forecast" in summary
    
    def test_problem_rows(self, sample_forecasts):
        # test getting problem rows
        model = ForecastTableModel()
        model.set_forecasts(sample_forecasts)
        
        problems = model.get_problem_rows()
        
        assert isinstance(problems, list)
    
    def test_empty_forecasts(self):
        # test with no forecasts
        model = ForecastTableModel()
        model.set_forecasts({})
        
        assert model.rowCount() == 0
        
        summary = model.get_summary()
        assert summary == {}
    
    def test_column_count(self, sample_forecasts):
        # test column count
        model = ForecastTableModel()
        model.set_forecasts(sample_forecasts)
        
        assert model.columnCount() == len(model.COLUMNS)


# ============================================================================
#                            RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])