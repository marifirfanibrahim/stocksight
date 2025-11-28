"""
data loading and validation operations
handle csv files and data cleaning
"""


# ================ IMPORTS ================

import pandas as pd
from pathlib import Path
import os
import shutil

from config import Paths, ExportConfig, DataConfig
from core.state import STATE
from utils.preprocessing import (
    validate_columns,
    validate_data_types,
    clean_dataframe,
    prepare_for_autots,
    get_sku_list,
    export_forecast_csv,
    export_summary_report,
    format_dates_output,
    group_forecast_by_period
)
from utils.features import (
    detect_additional_columns,
    detect_seasonality_pattern
)


# ================ OUTPUT DIRECTORY ================

def get_output_directory():
    """
    get current output directory
    user documents or custom
    """
    if hasattr(STATE, 'custom_output_dir') and STATE.custom_output_dir:
        return Path(STATE.custom_output_dir)
    
    if ExportConfig.USE_USER_DOCUMENTS:
        os.makedirs(Paths.USER_OUTPUT, exist_ok=True)
        return Paths.USER_OUTPUT
    
    return Paths.OUTPUT_DIR


# ================ DATA LOADING ================

def load_csv_file(file_path):
    """
    load and process csv file
    return success status and message
    """
    try:
        # ---------- LOAD CSV ----------
        df = pd.read_csv(file_path)
        
        # ---------- VALIDATE COLUMNS ----------
        valid, msg = validate_columns(df)
        if not valid:
            return False, f"Error: {msg}"
        
        # ---------- VALIDATE TYPES ----------
        valid, msg = validate_data_types(df)
        if not valid:
            return False, f"Error: {msg}"
        
        # ---------- CLEAN DATA ----------
        STATE.raw_data = df
        STATE.clean_data = clean_dataframe(df, store_format=True)
        STATE.sku_list = get_sku_list(STATE.clean_data)
        
        # ---------- DETECT ADDITIONAL COLUMNS ----------
        STATE.feature_columns = detect_additional_columns(STATE.clean_data)
        STATE.selected_features = STATE.feature_columns.copy()
        
        if STATE.feature_columns:
            print(f"detected additional columns: {STATE.feature_columns}")
        
        # ---------- ANALYZE SEASONALITY ----------
        STATE.seasonality_info = detect_seasonality_pattern(STATE.clean_data)
        print(f"seasonality analysis:")
        print(f"  monthly: {STATE.seasonality_info['has_monthly_seasonality']}")
        print(f"  weekly: {STATE.seasonality_info['has_weekly_seasonality']}")
        
        print(f"loaded {file_path}")
        print(f"records: {len(STATE.clean_data)}, skus: {len(STATE.sku_list)}")
        print(f"detected date format: {STATE.detected_date_format}")
        
        feature_count = len(STATE.feature_columns)
        return True, f"Loaded: {len(STATE.clean_data)} records, {len(STATE.sku_list)} SKUs, {feature_count} features"
        
    except Exception as e:
        print(f"load error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error loading file: {str(e)}"


def clear_all_data():
    """
    clear all loaded data
    reset to initial state
    """
    STATE.raw_data = None
    STATE.clean_data = None
    STATE.forecast_data = None
    STATE.upper_forecast = None
    STATE.lower_forecast = None
    STATE.sku_list = []
    STATE.feature_columns = []
    STATE.selected_features = []
    STATE.exog_data = None
    STATE.encoders = None
    STATE.seasonality_info = {}
    STATE.scenario_history = []
    STATE.original_date_format = None
    STATE.detected_date_format = '%Y-%m-%d'
    STATE.grouped_forecast = None
    STATE.error_margins = None
    
    print("all data cleared")


# ================ VALIDATION ================

def validate_forecast_requirements():
    """
    check if data meets forecast requirements
    return validation status and message
    """
    if STATE.clean_data is None:
        return False, "No data loaded"
    
    # ---------- CHECK DATA LENGTH ----------
    df_pivot = prepare_for_autots(STATE.clean_data, use_features=False)
    data_length = len(df_pivot)
    
    if data_length < DataConfig.MIN_DATA_POINTS:
        return False, f"Need at least {DataConfig.MIN_DATA_POINTS} days of data (have {data_length})"
    
    # ---------- CHECK FORECAST LENGTH ----------
    if STATE.forecast_days > data_length // 2:
        suggested = data_length // 3
        return True, f"Warning: forecast may be reduced to {suggested} days"
    
    return True, "Data validation passed"


# ================ DASHBOARD DATA ================

def calculate_dashboard_data(grouping='Daily'):
    """
    calculate dashboard statistics
    return formatted data
    """
    if STATE.forecast_data is None:
        return None
    
    # ---------- GROUP DATA ----------
    forecast_grouped, upper_grouped, lower_grouped, error_margins = group_forecast_by_period(
        STATE.forecast_data,
        STATE.upper_forecast,
        STATE.lower_forecast,
        grouping
    )
    
    STATE.grouped_forecast = forecast_grouped
    STATE.error_margins = error_margins
    
    # ---------- CALCULATE STATS ----------
    total_forecast = forecast_grouped.sum().sum()
    avg_daily = STATE.forecast_data.mean().mean()
    
    total_upper = upper_grouped.sum().sum()
    total_lower = lower_grouped.sum().sum()
    
    avg_error = error_margins.mean().mean()
    
    num_periods = len(forecast_grouped)
    num_skus = len(forecast_grouped.columns)
    
    # ---------- DATE RANGE ----------
    if hasattr(forecast_grouped.index, 'min'):
        start_date = forecast_grouped.index.min()
        end_date = forecast_grouped.index.max()
    else:
        start_date = forecast_grouped.index[0]
        end_date = forecast_grouped.index[-1]
    
    return {
        'total_forecast': total_forecast,
        'avg_daily': avg_daily,
        'total_upper': total_upper,
        'total_lower': total_lower,
        'avg_error': avg_error,
        'num_periods': num_periods,
        'num_skus': num_skus,
        'start_date': start_date,
        'end_date': end_date,
        'forecast_grouped': forecast_grouped,
        'upper_grouped': upper_grouped,
        'lower_grouped': lower_grouped,
        'error_margins': error_margins
    }


# ================ EXPORT ================

def export_results(timestamp):
    """
    export forecast results
    return success status
    """
    if STATE.forecast_data is None:
        return False, "No forecast to export"
    
    output_dir = get_output_directory()
    
    try:
        # ---------- EXPORT DATA ----------
        if ExportConfig.EXPORT_DATA:
            export_forecast_csv(STATE.forecast_data, output_dir / f"forecast_{timestamp}.csv")
            
            if STATE.upper_forecast is not None:
                export_forecast_csv(STATE.upper_forecast, output_dir / f"forecast_upper_{timestamp}.csv")
            
            if STATE.lower_forecast is not None:
                export_forecast_csv(STATE.lower_forecast, output_dir / f"forecast_lower_{timestamp}.csv")
        
        # ---------- EXPORT SUMMARY ----------
        if ExportConfig.EXPORT_SUMMARY:
            export_summary_report(STATE.forecast_data, STATE.clean_data, output_dir / f"summary_{timestamp}.txt")
        
        # ---------- EXPORT CHARTS ----------
        if ExportConfig.EXPORT_CHARTS:
            chart_src = output_dir / "forecast.png"
            chart_dst = output_dir / f"forecast_chart_{timestamp}.png"
            
            if chart_src.exists():
                shutil.copy(chart_src, chart_dst)
                print(f"chart exported: {chart_dst}")
        
        print(f"exported forecast_{timestamp} to {output_dir}")
        return True, f"Exported to {output_dir}"
        
    except Exception as e:
        return False, f"Export error: {str(e)}"