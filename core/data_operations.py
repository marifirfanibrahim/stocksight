"""
data loading and validation operations
handle csv files and data cleaning
"""


# ================ IMPORTS ================

import pandas as pd
from pathlib import Path
import os
import shutil
from typing import Tuple, Dict, List, Optional

from config import Paths, ExportConfig, DataConfig
from core.state import STATE
from utils.preprocessing import (
    validate_columns,
    validate_data_types,
    clean_dataframe,
    prepare_for_autots,
    get_sku_list,
    aggregate_by_period,
    group_forecast_by_period,
    get_data_summary
)
from utils.features import (
    detect_additional_columns,
    detect_seasonality_pattern
)
from utils.export import export_dataframe, export_forecast, export_summary_report


# ================ OUTPUT DIRECTORY ================

def get_output_directory() -> Path:
    """
    get current output directory
    """
    if hasattr(STATE, 'custom_output_dir') and STATE.custom_output_dir:
        return Path(STATE.custom_output_dir)
    
    if ExportConfig.USE_USER_DOCUMENTS:
        os.makedirs(Paths.USER_OUTPUT, exist_ok=True)
        return Paths.USER_OUTPUT
    
    return Paths.OUTPUT_DIR


def set_output_directory(path: str):
    """
    set custom output directory
    """
    STATE.custom_output_dir = path
    os.makedirs(path, exist_ok=True)


# ================ DATA LOADING ================

def load_csv_file(file_path: str) -> Tuple[bool, str]:
    """
    load and process csv file
    """
    try:
        df = pd.read_csv(file_path)
        return process_dataframe(df, file_path)
        
    except Exception as e:
        print(f"load error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error loading file: {str(e)}"


def load_excel_file(file_path: str, sheet_name: str = None) -> Tuple[bool, str]:
    """
    load and process excel file
    """
    try:
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
        
        return process_dataframe(df, file_path)
        
    except Exception as e:
        print(f"load error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error loading file: {str(e)}"


def get_excel_sheets(file_path: str) -> List[str]:
    """
    get list of sheets in excel file
    """
    try:
        excel_file = pd.ExcelFile(file_path)
        return excel_file.sheet_names
    except Exception as e:
        print(f"error reading excel sheets: {e}")
        return []


def process_dataframe(df: pd.DataFrame, source: str = "") -> Tuple[bool, str]:
    """
    process loaded dataframe
    """
    try:
        # validate columns
        valid, msg = validate_columns(df)
        if not valid:
            return False, f"Error: {msg}"
        
        # validate types
        valid, msg = validate_data_types(df)
        if not valid:
            return False, f"Error: {msg}"
        
        # store raw data
        STATE.raw_data = df.copy()
        
        # clean and store
        STATE.clean_data = clean_dataframe(df, store_format=True)
        STATE.sku_list = get_sku_list(STATE.clean_data)
        
        # detect additional columns
        STATE.additional_columns = detect_additional_columns(STATE.clean_data)
        
        if STATE.additional_columns:
            print(f"detected additional columns: {STATE.additional_columns}")
        
        # analyze seasonality
        STATE.seasonality_info = detect_seasonality_pattern(STATE.clean_data)
        print(f"seasonality: monthly={STATE.seasonality_info['has_monthly_seasonality']}, weekly={STATE.seasonality_info['has_weekly_seasonality']}")
        
        # log summary
        print(f"loaded {source}")
        print(f"records: {len(STATE.clean_data)}, skus: {len(STATE.sku_list)}")
        
        feature_count = len(STATE.additional_columns)
        return True, f"Loaded: {len(STATE.clean_data)} records, {len(STATE.sku_list)} SKUs, {feature_count} features"
        
    except Exception as e:
        print(f"process error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error processing data: {str(e)}"


# ================ DATA CLEARING ================

def clear_all_data():
    """
    clear all loaded data
    """
    STATE.reset_all()
    print("all data cleared")


def clear_forecast_data():
    """
    clear only forecast data
    """
    STATE.reset_forecast()
    print("forecast data cleared")


# ================ VALIDATION ================

def validate_forecast_requirements() -> Tuple[bool, str]:
    """
    check if data meets forecast requirements
    """
    if STATE.clean_data is None:
        return False, "No data loaded"
    
    # check data length
    df_pivot = prepare_for_autots(STATE.clean_data, use_features=False)
    data_length = len(df_pivot)
    
    if data_length < DataConfig.MIN_DATA_POINTS:
        return False, f"Need at least {DataConfig.MIN_DATA_POINTS} days of data (have {data_length})"
    
    # check forecast length
    if STATE.forecast_days > data_length // 2:
        suggested = data_length // 3
        return True, f"Warning: forecast may be reduced to {suggested} days"
    
    return True, "Data validation passed"


def get_data_validation_report() -> Dict:
    """
    get comprehensive data validation report
    """
    if STATE.clean_data is None:
        return {'valid': False, 'message': 'No data loaded'}
    
    from utils.preprocessing import validate_data_quality
    
    validation = validate_data_quality(STATE.clean_data)
    summary = get_data_summary(STATE.clean_data)
    
    return {
        'valid': validation['valid'],
        'issues': validation['issues'],
        'warnings': validation['warnings'],
        'summary': summary
    }


# ================ DASHBOARD DATA ================

def calculate_dashboard_data(grouping: str = 'Daily') -> Optional[Dict]:
    """
    calculate dashboard statistics
    """
    if STATE.forecast_data is None:
        return None
    
    # group data
    forecast_grouped, upper_grouped, lower_grouped, error_margins = group_forecast_by_period(
        STATE.forecast_data,
        STATE.upper_forecast if STATE.upper_forecast is not None else STATE.forecast_data,
        STATE.lower_forecast if STATE.lower_forecast is not None else STATE.forecast_data,
        grouping
    )
    
    STATE.grouped_forecast = forecast_grouped
    STATE.error_margins = error_margins
    
    # calculate stats
    total_forecast = forecast_grouped.sum().sum()
    avg_daily = STATE.forecast_data.mean().mean()
    total_upper = upper_grouped.sum().sum()
    total_lower = lower_grouped.sum().sum()
    avg_error = error_margins.mean().mean()
    num_periods = len(forecast_grouped)
    num_skus = len(forecast_grouped.columns)
    
    # date range
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

def export_results(timestamp: str = None) -> Tuple[bool, str]:
    """
    export forecast results
    """
    if STATE.forecast_data is None:
        return False, "No forecast to export"
    
    if timestamp is None:
        from datetime import datetime
        timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
    
    output_dir = get_output_directory()
    
    try:
        # export forecast
        paths = export_forecast(
            STATE.forecast_data,
            STATE.upper_forecast,
            STATE.lower_forecast,
            output_dir=output_dir
        )
        
        # export summary
        export_summary_report(output_dir)
        
        # copy chart if exists
        if ExportConfig.EXPORT_CHARTS:
            chart_src = output_dir / "forecast.png"
            chart_dst = output_dir / f"forecast_chart_{timestamp}.png"
            
            if chart_src.exists():
                shutil.copy(chart_src, chart_dst)
        
        print(f"exported to {output_dir}")
        return True, f"Exported to {output_dir}"
        
    except Exception as e:
        return False, f"Export error: {str(e)}"


# ================ DATA FILTERING ================

def filter_data_by_skus(skus: List[str]) -> pd.DataFrame:
    """
    filter data by sku list
    """
    if STATE.clean_data is None:
        return pd.DataFrame()
    
    return STATE.clean_data[STATE.clean_data['SKU'].isin(skus)].copy()


def filter_data_by_date_range(start_date, end_date) -> pd.DataFrame:
    """
    filter data by date range
    """
    if STATE.clean_data is None:
        return pd.DataFrame()
    
    df = STATE.clean_data.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    
    mask = (df['Date'] >= pd.to_datetime(start_date)) & (df['Date'] <= pd.to_datetime(end_date))
    
    return df[mask]


def get_sku_data(sku: str) -> pd.DataFrame:
    """
    get data for single sku
    """
    if STATE.clean_data is None:
        return pd.DataFrame()
    
    return STATE.clean_data[STATE.clean_data['SKU'] == sku].copy()


# ================ DATA STATISTICS ================

def get_sku_statistics(sku: str = None) -> Dict:
    """
    get statistics for sku or all data
    """
    if STATE.clean_data is None:
        return {}
    
    if sku:
        df = STATE.clean_data[STATE.clean_data['SKU'] == sku]
    else:
        df = STATE.clean_data
    
    if len(df) == 0:
        return {}
    
    return {
        'count': len(df),
        'total_quantity': df['Quantity'].sum(),
        'mean_quantity': df['Quantity'].mean(),
        'std_quantity': df['Quantity'].std(),
        'min_quantity': df['Quantity'].min(),
        'max_quantity': df['Quantity'].max(),
        'date_range': {
            'start': df['Date'].min(),
            'end': df['Date'].max()
        }
    }


def get_all_sku_statistics() -> Dict[str, Dict]:
    """
    get statistics for all skus
    """
    if STATE.clean_data is None:
        return {}
    
    stats = {}
    for sku in STATE.sku_list:
        stats[sku] = get_sku_statistics(sku)
    
    return stats