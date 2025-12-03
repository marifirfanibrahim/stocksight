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
    validate_mapped_columns,
    validate_data_types,
    clean_mapped_dataframe,
    prepare_for_autots,
    get_sku_list,
    aggregate_by_period,
    group_forecast_by_period,
    get_data_summary,
    parse_dates_flexible
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


# ================ RAW DATA LOADING ================

def load_csv_raw(file_path: str) -> Tuple[bool, str]:
    """
    load csv file without column validation
    """
    try:
        df = pd.read_csv(file_path)
        return _store_raw_data(df, file_path)
        
    except Exception as e:
        print(f"load error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error loading file: {str(e)}"


def load_excel_raw(file_path: str, sheet_name: str = None) -> Tuple[bool, str]:
    """
    load excel file without column validation
    """
    try:
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
        
        return _store_raw_data(df, file_path)
        
    except Exception as e:
        print(f"load error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error loading file: {str(e)}"


def _store_raw_data(df: pd.DataFrame, source: str) -> Tuple[bool, str]:
    """
    store raw data in state
    """
    try:
        if len(df) == 0:
            return False, "File is empty"
        
        if len(df.columns) < 2:
            return False, "File must have at least 2 columns"
        
        # store raw data
        STATE.set_raw_data(df)
        
        # log summary
        print(f"loaded raw data: {source}")
        print(f"rows: {len(df)}, columns: {len(df.columns)}")
        print(f"columns: {df.columns.tolist()}")
        
        return True, f"Loaded: {len(df):,} rows, {len(df.columns)} columns"
        
    except Exception as e:
        print(f"store error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error storing data: {str(e)}"


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


# ================ COLUMN MAPPING ================

def apply_column_mapping(mapping: Dict) -> Tuple[bool, str]:
    """
    apply column mapping to raw data
    """
    try:
        if STATE.raw_data is None:
            return False, "No data loaded"
        
        date_col = mapping.get('date_column')
        sku_col = mapping.get('sku_column')
        quantity_col = mapping.get('quantity_column')
        additional_cols = mapping.get('additional_columns', [])
        
        # validate columns exist
        missing = []
        for col in [date_col, sku_col, quantity_col]:
            if col not in STATE.raw_data.columns:
                missing.append(col)
        
        if missing:
            return False, f"Columns not found: {missing}"
        
        # build rename map
        rename_map = {
            date_col: 'Date',
            sku_col: 'SKU',
            quantity_col: 'Quantity'
        }
        
        # select and rename columns
        columns_to_keep = [date_col, sku_col, quantity_col] + additional_cols
        columns_to_keep = [c for c in columns_to_keep if c in STATE.raw_data.columns]
        
        df = STATE.raw_data[columns_to_keep].copy()
        df = df.rename(columns=rename_map)
        
        # store mapping in state
        STATE.set_column_mapping(
            date_column=date_col,
            sku_column=sku_col,
            quantity_column=quantity_col,
            additional_columns=additional_cols
        )
        
        # clean and validate
        df = clean_mapped_dataframe(df)
        
        # store cleaned data
        STATE.clean_data = df
        STATE.sku_list = get_sku_list(df)
        STATE.additional_columns = additional_cols
        
        # analyze seasonality
        STATE.seasonality_info = detect_seasonality_pattern(df)
        
        print(f"mapping applied: {len(df)} records, {len(STATE.sku_list)} skus")
        
        return True, f"Mapping applied: {len(df):,} records, {len(STATE.sku_list)} SKUs"
        
    except Exception as e:
        print(f"mapping error: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error applying mapping: {str(e)}"


def clear_column_mapping():
    """
    clear current column mapping
    """
    STATE.clear_column_mapping()
    STATE.reset_after_mapping_change()
    print("column mapping cleared")


# ================ LEGACY SUPPORT ================

def load_csv_file(file_path: str) -> Tuple[bool, str]:
    """
    load csv file - legacy function
    attempts auto-detection of columns
    """
    success, msg = load_csv_raw(file_path)
    
    if not success:
        return success, msg
    
    # try to auto-detect and map columns
    mapping = auto_detect_columns(STATE.raw_data)
    
    if mapping:
        return apply_column_mapping(mapping)
    
    return True, msg


def load_excel_file(file_path: str, sheet_name: str = None) -> Tuple[bool, str]:
    """
    load excel file - legacy function
    """
    success, msg = load_excel_raw(file_path, sheet_name)
    
    if not success:
        return success, msg
    
    # try to auto-detect and map columns
    mapping = auto_detect_columns(STATE.raw_data)
    
    if mapping:
        return apply_column_mapping(mapping)
    
    return True, msg


def auto_detect_columns(df: pd.DataFrame) -> Optional[Dict]:
    """
    auto-detect date, sku, quantity columns
    returns mapping dict if successful, none otherwise
    """
    # check if already named correctly
    if all(c in df.columns for c in ['Date', 'SKU', 'Quantity']):
        return {
            'date_column': 'Date',
            'sku_column': 'SKU',
            'quantity_column': 'Quantity',
            'additional_columns': [c for c in df.columns if c not in ['Date', 'SKU', 'Quantity']]
        }
    
    # try keyword matching
    date_keywords = ['date', 'time', 'timestamp', 'day', 'period']
    sku_keywords = ['sku', 'product', 'item', 'code', 'article', 'name', 'id']
    qty_keywords = ['quantity', 'qty', 'amount', 'count', 'units', 'sales', 'demand']
    
    date_col = None
    sku_col = None
    qty_col = None
    
    for col in df.columns:
        col_lower = col.lower().strip()
        
        if date_col is None:
            for kw in date_keywords:
                if kw in col_lower:
                    date_col = col
                    break
        
        if sku_col is None:
            for kw in sku_keywords:
                if kw in col_lower:
                    sku_col = col
                    break
        
        if qty_col is None:
            for kw in qty_keywords:
                if kw in col_lower:
                    qty_col = col
                    break
    
    if date_col and sku_col and qty_col:
        additional = [c for c in df.columns if c not in [date_col, sku_col, qty_col]]
        return {
            'date_column': date_col,
            'sku_column': sku_col,
            'quantity_column': qty_col,
            'additional_columns': additional
        }
    
    return None


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
    if not STATE.is_columns_mapped():
        return False, "Columns not mapped. Configure column mapping first."
    
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
    result = {
        'has_raw_data': STATE.raw_data is not None,
        'is_mapped': STATE.is_columns_mapped(),
        'has_clean_data': STATE.clean_data is not None,
        'raw_rows': len(STATE.raw_data) if STATE.raw_data is not None else 0,
        'raw_columns': len(STATE.raw_columns),
        'column_names': STATE.raw_columns,
        'mapping': STATE.get_column_mapping()
    }
    
    if STATE.clean_data is not None:
        from utils.preprocessing import validate_data_quality
        
        validation = validate_data_quality(STATE.clean_data)
        summary = get_data_summary(STATE.clean_data)
        
        result.update({
            'valid': validation['valid'],
            'issues': validation['issues'],
            'warnings': validation['warnings'],
            'summary': summary
        })
    
    return result


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