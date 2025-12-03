"""
preprocessing utilities for inventory data
clean and validate csv files
prepare data for forecasting
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DataConfig
except ImportError:
    class DataConfig:
        DATE_FORMATS = [
            '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y',
            '%Y/%m/%d', '%d %b %Y', '%d %B %Y', '%b %d, %Y', '%B %d, %Y',
            '%b %Y', '%B %Y', '%Y-%m'
        ]
        REQUIRED_COLUMNS = ['Date', 'SKU', 'Quantity']
        MIN_DATA_POINTS = 14


# ================ DATE FORMAT DETECTION ================

def detect_date_format(date_series: pd.Series) -> str:
    """
    detect original date format
    return format string
    """
    if len(date_series) == 0:
        return '%Y-%m-%d'
    
    sample = str(date_series.iloc[0])
    
    for fmt in DataConfig.DATE_FORMATS:
        try:
            datetime.strptime(sample, fmt)
            print(f"detected date format: {fmt}")
            return fmt
        except ValueError:
            continue
    
    return '%Y-%m-%d'


def parse_dates_flexible(date_series: pd.Series) -> pd.Series:
    """
    parse dates with multiple format attempts
    """
    if pd.api.types.is_datetime64_any_dtype(date_series):
        return date_series
    
    # try pandas mixed format
    try:
        parsed = pd.to_datetime(date_series, format='mixed', dayfirst=False)
        print("dates parsed with pandas mixed format")
        return parsed
    except Exception:
        pass
    
    # try specific formats
    for fmt in DataConfig.DATE_FORMATS:
        try:
            parsed = pd.to_datetime(date_series, format=fmt)
            print(f"dates parsed with format: {fmt}")
            return parsed
        except Exception:
            continue
    
    # try dateutil parser
    try:
        from dateutil import parser
        parsed = date_series.astype(str).apply(
            lambda x: parser.parse(x) if x and str(x).strip() != 'nan' else pd.NaT
        )
        print("dates parsed with dateutil parser")
        return parsed
    except Exception:
        pass
    
    # try excel serial numbers
    try:
        numeric_dates = pd.to_numeric(date_series, errors='coerce')
        if numeric_dates.notna().sum() > len(date_series) * 0.5:
            if numeric_dates.min() > 30000 and numeric_dates.max() < 60000:
                parsed = pd.to_datetime(numeric_dates, unit='D', origin='1899-12-30')
                print("dates parsed as Excel serial numbers")
                return parsed
    except Exception:
        pass
    
    # last resort coerce
    try:
        parsed = pd.to_datetime(date_series, errors='coerce')
        if parsed.notna().sum() > 0:
            print("dates parsed with coerce mode")
            return parsed
    except Exception:
        pass
    
    raise ValueError(f"unable to parse dates. Sample: {date_series.head(3).tolist()}")


def format_dates_output(date_series: pd.Series, original_format: str) -> pd.Series:
    """
    format dates back to original format
    """
    if original_format is None:
        return date_series.astype(str)
    
    try:
        return date_series.dt.strftime(original_format)
    except Exception:
        return date_series.astype(str)


# ================ DATA FORMAT DETECTION ================

def detect_data_format(df: pd.DataFrame) -> str:
    """
    detect if data is wide or long format
    returns 'wide', 'long', or 'unknown'
    """
    columns = df.columns.tolist()
    
    # check for long format
    if 'Date' in columns and 'SKU' in columns and 'Quantity' in columns:
        return 'long'
    
    # check for wide format
    if len(columns) > 2:
        first_col = str(columns[0]).lower()
        sku_indicators = ['sku', 'product', 'item', 'code', 'name', 'id', 'part', 'material', 'article']
        
        if any(kw in first_col for kw in sku_indicators):
            date_like_count = 0
            total_check = min(20, len(columns) - 1)
            
            for col in columns[1:total_check + 1]:
                col_str = str(col).lower()
                months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                          'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                
                if any(m in col_str for m in months):
                    date_like_count += 1
                elif any(c.isdigit() for c in col_str):
                    date_like_count += 1
                elif isinstance(col, (datetime, pd.Timestamp)):
                    date_like_count += 1
            
            if date_like_count >= total_check * 0.5:
                return 'wide'
    
    return 'unknown'


def convert_wide_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """
    convert wide format to long format
    """
    sku_col = df.columns[0]
    date_columns = df.columns[1:].tolist()
    
    df_long = df.melt(
        id_vars=[sku_col],
        value_vars=date_columns,
        var_name='Date',
        value_name='Quantity'
    )
    
    df_long = df_long.rename(columns={sku_col: 'SKU'})
    
    try:
        df_long['Date'] = parse_dates_flexible(df_long['Date'])
    except ValueError:
        df_long['Date'] = parse_dates_flexible(df_long['Date'].astype(str))
    
    df_long['Quantity'] = pd.to_numeric(df_long['Quantity'], errors='coerce').fillna(0)
    df_long = df_long.sort_values(['Date', 'SKU']).reset_index(drop=True)
    
    print(f"converted wide format: {len(df)} rows x {len(date_columns)} periods -> {len(df_long)} records")
    
    return df_long


# ================ VALIDATION ================

def validate_columns(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    check required columns exist
    """
    required = DataConfig.REQUIRED_COLUMNS
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        return False, f"Missing columns: {missing}"
    
    return True, "Validation passed"


def validate_data_types(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    check data types are correct
    """
    try:
        parse_dates_flexible(df['Date'])
    except Exception as e:
        return False, f"Date column invalid: {str(e)}"
    
    if not pd.api.types.is_numeric_dtype(df['Quantity']):
        try:
            pd.to_numeric(df['Quantity'])
        except Exception:
            return False, "Quantity column not numeric"
    
    return True, "Data types valid"


def validate_data_quality(df: pd.DataFrame) -> Dict:
    """
    comprehensive data quality validation
    """
    issues = []
    warnings = []
    
    # check missing values
    for col in df.columns:
        missing_pct = df[col].isna().sum() / len(df) * 100
        if missing_pct > 0:
            if missing_pct > 20:
                issues.append(f"{col}: {missing_pct:.1f}% missing")
            elif missing_pct > 5:
                warnings.append(f"{col}: {missing_pct:.1f}% missing")
    
    # check duplicates
    dup_count = df.duplicated(subset=['Date', 'SKU']).sum()
    if dup_count > 0:
        warnings.append(f"{dup_count} duplicate Date-SKU combinations")
    
    # check data length
    if len(df) < DataConfig.MIN_DATA_POINTS:
        issues.append(f"Insufficient data: {len(df)} rows (need {DataConfig.MIN_DATA_POINTS})")
    
    # check negative quantities
    if 'Quantity' in df.columns:
        neg_count = (df['Quantity'] < 0).sum()
        if neg_count > 0:
            warnings.append(f"{neg_count} negative quantity values")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'row_count': len(df),
        'column_count': len(df.columns)
    }


# ================ DATA CLEANING ================

def clean_dataframe(
    df: pd.DataFrame,
    store_format: bool = True
) -> pd.DataFrame:
    """
    clean and standardize dataframe
    """
    from core.state import STATE
    
    df_clean = df.copy()
    
    # detect and store date format
    if store_format:
        STATE.detected_date_format = detect_date_format(df_clean['Date'])
    
    # parse dates
    df_clean['Date'] = parse_dates_flexible(df_clean['Date'])
    
    # convert quantity
    df_clean['Quantity'] = pd.to_numeric(df_clean['Quantity'], errors='coerce')
    
    # remove invalid rows
    df_clean = df_clean.dropna(subset=['Date', 'SKU'])
    df_clean['Quantity'] = df_clean['Quantity'].fillna(0)
    
    # sort and deduplicate
    df_clean = df_clean.sort_values('Date').reset_index(drop=True)
    df_clean = df_clean.drop_duplicates(subset=['Date', 'SKU'], keep='last')
    
    return df_clean


def prepare_for_autots(
    df: pd.DataFrame,
    use_features: bool = False
) -> pd.DataFrame:
    """
    prepare dataframe for autots format
    """
    df_pivot = df.pivot_table(
        index='Date',
        columns='SKU',
        values='Quantity',
        aggfunc='sum'
    ).fillna(0)
    
    df_pivot = df_pivot.reset_index()
    df_pivot.columns.name = None
    
    return df_pivot


# ================ AGGREGATION ================

def aggregate_by_period(
    df: pd.DataFrame,
    period: str = 'Weekly'
) -> pd.DataFrame:
    """
    aggregate data by time period
    """
    df_agg = df.copy()
    df_agg['Date'] = pd.to_datetime(df_agg['Date'])
    
    if period == 'Daily':
        return df_agg
    
    freq_map = {
        'Weekly': 'W',
        'Monthly': 'MS',
        'Quarterly': 'QS'
    }
    
    freq = freq_map.get(period, 'D')
    
    df_agg['Period'] = df_agg['Date'].dt.to_period(freq[0]).dt.start_time
    
    # build aggregation spec
    agg_spec = {'Quantity': 'sum'}
    
    extra_cols = [c for c in df_agg.columns if c not in ['Date', 'SKU', 'Quantity', 'Period']]
    for col in extra_cols:
        if pd.api.types.is_numeric_dtype(df_agg[col]):
            agg_spec[col] = 'sum'
        else:
            agg_spec[col] = 'first'
    
    grouped = df_agg.groupby(['Period', 'SKU']).agg(agg_spec).reset_index()
    grouped = grouped.rename(columns={'Period': 'Date'})
    
    print(f"aggregated: {len(df)} -> {len(grouped)} rows ({period})")
    
    return grouped


def group_forecast_by_period(
    forecast_df: pd.DataFrame,
    upper_df: pd.DataFrame,
    lower_df: pd.DataFrame,
    period: str = 'Weekly'
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    group forecast data by period
    """
    if period == 'Daily':
        error_margins = upper_df - lower_df
        return forecast_df, upper_df, lower_df, error_margins
    
    freq_map = {
        'Weekly': 'W',
        'Monthly': 'MS',
        'Quarterly': 'QS'
    }
    
    freq = freq_map.get(period, 'D')
    
    forecast_copy = forecast_df.copy()
    upper_copy = upper_df.copy()
    lower_copy = lower_df.copy()
    
    forecast_copy['Period'] = pd.to_datetime(forecast_copy.index).to_period(freq[0]).start_time
    upper_copy['Period'] = pd.to_datetime(upper_copy.index).to_period(freq[0]).start_time
    lower_copy['Period'] = pd.to_datetime(lower_copy.index).to_period(freq[0]).start_time
    
    forecast_grouped = forecast_copy.groupby('Period').sum()
    upper_grouped = upper_copy.groupby('Period').sum()
    lower_grouped = lower_copy.groupby('Period').sum()
    
    error_margins = upper_grouped - lower_grouped
    
    return forecast_grouped, upper_grouped, lower_grouped, error_margins


# ================ UTILITIES ================

def get_sku_list(df: pd.DataFrame) -> List[str]:
    """
    extract unique sku values
    """
    return sorted(df['SKU'].unique().tolist())


def filter_by_sku(df: pd.DataFrame, sku: str) -> pd.DataFrame:
    """
    filter dataframe by single sku
    """
    return df[df['SKU'] == sku].copy()


def get_date_range(df: pd.DataFrame) -> Tuple[datetime, datetime]:
    """
    get min and max dates
    """
    return df['Date'].min(), df['Date'].max()


def get_data_summary(df: pd.DataFrame) -> Dict:
    """
    get summary statistics for dataframe
    """
    summary = {
        'rows': len(df),
        'columns': len(df.columns),
        'skus': df['SKU'].nunique() if 'SKU' in df.columns else 0,
        'date_range': None,
        'quantity_stats': None
    }
    
    if 'Date' in df.columns:
        summary['date_range'] = {
            'start': df['Date'].min().isoformat() if pd.notna(df['Date'].min()) else None,
            'end': df['Date'].max().isoformat() if pd.notna(df['Date'].max()) else None
        }
    
    if 'Quantity' in df.columns:
        summary['quantity_stats'] = {
            'total': float(df['Quantity'].sum()),
            'mean': float(df['Quantity'].mean()),
            'std': float(df['Quantity'].std()),
            'min': float(df['Quantity'].min()),
            'max': float(df['Quantity'].max())
        }
    
    return summary