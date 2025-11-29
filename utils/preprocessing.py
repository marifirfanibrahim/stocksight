"""
preprocessing utilities for inventory data
clean and validate csv files
prepare data for autots forecasting
export forecast results
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# ---------- ADD CONFIG PATH ----------
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


# ================ DATE FORMAT DETECTION ================

def detect_date_format(date_series):
    """
    detect original date format
    return format string
    """
    sample = str(date_series.iloc[0])
    
    for fmt in DataConfig.DATE_FORMATS:
        try:
            datetime.strptime(sample, fmt)
            print(f"detected date format: {fmt}")
            return fmt
        except ValueError:
            continue
    
    # fallback
    return '%Y-%m-%d'


def parse_dates_flexible(date_series):
    """
    parse dates with multiple format attempts
    handle various date formats
    """
    # ---------- TRY PANDAS AUTO ----------
    try:
        parsed = pd.to_datetime(date_series, infer_datetime_format=True)
        print("dates parsed with pandas auto detection")
        return parsed
    except:
        pass
    
    # ---------- TRY EACH FORMAT ----------
    for fmt in DataConfig.DATE_FORMATS:
        try:
            parsed = pd.to_datetime(date_series, format=fmt)
            print(f"dates parsed with format: {fmt}")
            return parsed
        except:
            continue
    
    # ---------- TRY DATEUTIL PARSER ----------
    try:
        from dateutil import parser
        parsed = date_series.apply(lambda x: parser.parse(str(x)))
        print("dates parsed with dateutil parser")
        return parsed
    except:
        pass
    
    # ---------- FINAL ATTEMPT ----------
    try:
        parsed = pd.to_datetime(date_series, errors='coerce')
        if parsed.isna().sum() == 0:
            print("dates parsed with coerce mode")
            return parsed
    except:
        pass
    
    raise ValueError("unable to parse dates with known formats")


def format_dates_output(date_series, original_format):
    """
    format dates back to original format
    for display and export
    """
    if original_format is None:
        return date_series.astype(str)
    
    try:
        return date_series.dt.strftime(original_format)
    except:
        return date_series.astype(str)


# ================ WIDE FORMAT DETECTION ================

def detect_data_format(df):
    """
    detect if data is wide or long format
    returns 'wide', 'long', or 'unknown'
    """
    columns = df.columns.tolist()
    
    # check for standard long format
    if 'Date' in columns and 'SKU' in columns and 'Quantity' in columns:
        return 'long'
    
    # check for wide format (first column is SKU, rest are dates)
    if len(columns) > 2:
        first_col = str(columns[0]).lower()
        if any(kw in first_col for kw in ['sku', 'product', 'item', 'code', 'name', 'id']):
            # check if other columns look like dates
            date_like_count = 0
            for col in columns[1:]:
                col_str = str(col).lower()
                # check for month names or date patterns
                months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                         'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                if any(m in col_str for m in months):
                    date_like_count += 1
                elif any(c.isdigit() for c in col_str):
                    date_like_count += 1
            
            if date_like_count >= len(columns) * 0.5:
                return 'wide'
    
    return 'unknown'


def convert_wide_to_long(df):
    """
    convert wide format to long format
    columns = dates, rows = skus -> Date, SKU, Quantity
    """
    # first column is SKU identifier
    sku_col = df.columns[0]
    date_columns = df.columns[1:].tolist()
    
    # melt the dataframe
    df_long = df.melt(
        id_vars=[sku_col],
        value_vars=date_columns,
        var_name='Date',
        value_name='Quantity'
    )
    
    # rename SKU column
    df_long = df_long.rename(columns={sku_col: 'SKU'})
    
    # parse dates
    df_long['Date'] = parse_dates_flexible(df_long['Date'])
    
    # ensure quantity is numeric
    df_long['Quantity'] = pd.to_numeric(df_long['Quantity'], errors='coerce').fillna(0)
    
    # sort by date and sku
    df_long = df_long.sort_values(['Date', 'SKU']).reset_index(drop=True)
    
    print(f"converted wide format: {len(df)} rows x {len(date_columns)} periods -> {len(df_long)} records")
    
    return df_long


# ================ DATA VALIDATION ================

def validate_columns(df):
    """
    check required columns exist
    return validation status and message
    """
    # ---------- COLUMN CHECK ----------
    required = ['Date', 'SKU', 'Quantity']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        return False, f"Missing columns: {missing}"
    
    return True, "Validation passed"


def validate_data_types(df):
    """
    check data types are correct
    return validation status and message
    """
    # ---------- DATE CHECK ----------
    try:
        parse_dates_flexible(df['Date'])
    except Exception as e:
        return False, f"Date column invalid: {str(e)}"
    
    # ---------- QUANTITY CHECK ----------
    if not pd.api.types.is_numeric_dtype(df['Quantity']):
        try:
            pd.to_numeric(df['Quantity'])
        except Exception:
            return False, "Quantity column not numeric"
    
    return True, "Data types valid"


# ================ DATA CLEANING ================

def clean_dataframe(df, store_format=True):
    """
    clean and standardize dataframe
    handle missing values
    convert data types
    """
    from core.state import STATE
    
    # ---------- COPY DATA ----------
    df_clean = df.copy()
    
    # ---------- DETECT AND STORE FORMAT ----------
    if store_format:
        STATE.detected_date_format = detect_date_format(df_clean['Date'])
        STATE.original_date_format = STATE.detected_date_format
    
    # ---------- DATE CONVERSION ----------
    df_clean['Date'] = parse_dates_flexible(df_clean['Date'])
    
    # ---------- QUANTITY CONVERSION ----------
    df_clean['Quantity'] = pd.to_numeric(df_clean['Quantity'], errors='coerce')
    
    # ---------- HANDLE MISSING ----------
    df_clean = df_clean.dropna(subset=['Date', 'SKU'])
    df_clean['Quantity'] = df_clean['Quantity'].fillna(0)
    
    # ---------- SORT BY DATE ----------
    df_clean = df_clean.sort_values('Date').reset_index(drop=True)
    
    # ---------- REMOVE DUPLICATES ----------
    df_clean = df_clean.drop_duplicates(subset=['Date', 'SKU'], keep='last')
    
    return df_clean


def prepare_for_autots(df, use_features=False):
    """
    prepare dataframe for autots format
    pivot data for multiple sku handling
    """
    # ---------- PIVOT DATA ----------
    df_pivot = df.pivot_table(
        index='Date',
        columns='SKU',
        values='Quantity',
        aggfunc='sum'
    ).fillna(0)
    
    # ---------- RESET INDEX ----------
    df_pivot = df_pivot.reset_index()
    df_pivot.columns.name = None
    
    # ---------- FEATURE HANDLING ----------
    if use_features:
        from utils.features import detect_additional_columns, prepare_exogenous_features
        
        feature_cols = detect_additional_columns(df)
        if feature_cols:
            print(f"detected feature columns: {feature_cols}")
            exog_data, encoders = prepare_exogenous_features(df, feature_cols)
            return df_pivot, exog_data, encoders
    
    return df_pivot


# ================ DATE GROUPING ================

def group_by_period(df, period='Weekly'):
    """
    group data by time period
    aggregate quantities
    """
    df_grouped = df.copy()
    
    if period == 'Daily':
        return df_grouped
    
    elif period == 'Weekly':
        df_grouped['Period'] = df_grouped['Date'].dt.to_period('W').dt.start_time
    
    elif period == 'Monthly':
        df_grouped['Period'] = df_grouped['Date'].dt.to_period('M').dt.start_time
    
    elif period == 'Quarterly':
        df_grouped['Period'] = df_grouped['Date'].dt.to_period('Q').dt.start_time
    
    # ---------- AGGREGATE ----------
    if 'SKU' in df_grouped.columns:
        grouped = df_grouped.groupby(['Period', 'SKU'])['Quantity'].sum().reset_index()
        grouped = grouped.rename(columns={'Period': 'Date'})
    else:
        grouped = df_grouped.groupby('Period').sum().reset_index()
        grouped = grouped.rename(columns={'Period': 'Date'})
    
    return grouped


def group_forecast_by_period(forecast_df, upper_df, lower_df, period='Weekly'):
    """
    group forecast data by period
    return aggregated forecast with margins
    """
    if period == 'Daily':
        error_margins = upper_df - lower_df
        return forecast_df, upper_df, lower_df, error_margins
    
    # ---------- ADD PERIOD COLUMN ----------
    forecast_copy = forecast_df.copy()
    upper_copy = upper_df.copy()
    lower_copy = lower_df.copy()
    
    if period == 'Weekly':
        forecast_copy['Period'] = pd.to_datetime(forecast_copy.index).to_period('W').start_time
        upper_copy['Period'] = pd.to_datetime(upper_copy.index).to_period('W').start_time
        lower_copy['Period'] = pd.to_datetime(lower_copy.index).to_period('W').start_time
    
    elif period == 'Monthly':
        forecast_copy['Period'] = pd.to_datetime(forecast_copy.index).to_period('M').start_time
        upper_copy['Period'] = pd.to_datetime(upper_copy.index).to_period('M').start_time
        lower_copy['Period'] = pd.to_datetime(lower_copy.index).to_period('M').start_time
    
    elif period == 'Quarterly':
        forecast_copy['Period'] = pd.to_datetime(forecast_copy.index).to_period('Q').start_time
        upper_copy['Period'] = pd.to_datetime(upper_copy.index).to_period('Q').start_time
        lower_copy['Period'] = pd.to_datetime(lower_copy.index).to_period('Q').start_time
    
    # ---------- AGGREGATE ----------
    forecast_grouped = forecast_copy.groupby('Period').sum()
    upper_grouped = upper_copy.groupby('Period').sum()
    lower_grouped = lower_copy.groupby('Period').sum()
    
    error_margins = upper_grouped - lower_grouped
    
    return forecast_grouped, upper_grouped, lower_grouped, error_margins


# ================ SCENARIO SIMULATION ================

def apply_demand_spike(df, sku, multiplier, start_date, end_date):
    """
    simulate demand spike for sku
    multiply quantity by factor in date range
    """
    # ---------- COPY DATA ----------
    df_sim = df.copy()
    
    # ---------- DATE FILTER ----------
    mask = (
        (df_sim['SKU'] == sku) &
        (df_sim['Date'] >= pd.to_datetime(start_date)) &
        (df_sim['Date'] <= pd.to_datetime(end_date))
    )
    
    # ---------- APPLY MULTIPLIER ----------
    df_sim.loc[mask, 'Quantity'] = df_sim.loc[mask, 'Quantity'] * multiplier
    
    return df_sim


def apply_supply_delay(df, sku, delay_days, start_date):
    """
    simulate supply chain delay
    shift quantities forward by days
    """
    # ---------- COPY DATA ----------
    df_sim = df.copy()
    
    # ---------- SKU FILTER ----------
    sku_mask = df_sim['SKU'] == sku
    sku_data = df_sim[sku_mask].copy()
    
    # ---------- SHIFT DATES ----------
    sku_data['Date'] = sku_data['Date'] + pd.Timedelta(days=delay_days)
    
    # ---------- UPDATE DATAFRAME ----------
    df_sim = df_sim[~sku_mask]
    df_sim = pd.concat([df_sim, sku_data], ignore_index=True)
    df_sim = df_sim.sort_values('Date').reset_index(drop=True)
    
    return df_sim


# ================ EXPORT FUNCTIONS ================

def export_forecast_csv(forecast_df, output_path, original_format=None):
    """
    export forecast dataframe to csv
    save in output directory
    """
    from core.state import STATE
    
    # ---------- ENSURE DIRECTORY ----------
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # ---------- FORMAT DATES ----------
    export_df = forecast_df.copy()
    
    if original_format or STATE.detected_date_format:
        fmt = original_format or STATE.detected_date_format
        if hasattr(export_df.index, 'strftime'):
            export_df.index = export_df.index.strftime(fmt)
    
    # ---------- SAVE CSV ----------
    export_df.to_csv(output_path, index=True)
    
    return output_path


def export_summary_report(forecast_df, original_df, output_path):
    """
    generate summary report
    include statistics and forecast metrics
    """
    from core.state import STATE
    
    # ---------- ENSURE DIRECTORY ----------
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # ---------- BUILD REPORT ----------
    report_lines = []
    report_lines.append("INVENTORY FORECAST SUMMARY")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Date Format: {STATE.detected_date_format}")
    report_lines.append("")
    report_lines.append("ORIGINAL DATA STATISTICS")
    report_lines.append(f"Total Records: {len(original_df)}")
    report_lines.append(f"Date Range: {original_df['Date'].min()} to {original_df['Date'].max()}")
    report_lines.append(f"Unique SKUs: {original_df['SKU'].nunique()}")
    report_lines.append("")
    report_lines.append("FORECAST SUMMARY")
    report_lines.append(f"Forecast Periods: {len(forecast_df)}")
    
    # ---------- SEASONALITY INFO ----------
    if STATE.seasonality_info:
        report_lines.append("")
        report_lines.append("SEASONALITY ANALYSIS")
        if STATE.seasonality_info.get('has_monthly_seasonality'):
            report_lines.append(f"Monthly Pattern: Yes (CV: {STATE.seasonality_info.get('monthly_cv', 0):.2f})")
        else:
            report_lines.append("Monthly Pattern: No")
        if STATE.seasonality_info.get('has_weekly_seasonality'):
            report_lines.append(f"Weekly Pattern: Yes (CV: {STATE.seasonality_info.get('weekly_cv', 0):.2f})")
        else:
            report_lines.append("Weekly Pattern: No")
    
    # ---------- WRITE FILE ----------
    with open(output_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    return output_path


# ================ PRE-AGGREGATION ================

def aggregate_before_forecast(df, granularity='Daily'):
    """
    aggregate data before forecasting
    for noisy daily data
    """
    if granularity == 'Daily':
        return df
    
    df_agg = df.copy()
    df_agg['Date'] = pd.to_datetime(df_agg['Date'])
    
    if granularity == 'Weekly':
        df_agg['Period'] = df_agg['Date'].dt.to_period('W').dt.start_time
    elif granularity == 'Monthly':
        df_agg['Period'] = df_agg['Date'].dt.to_period('M').dt.start_time
    elif granularity == 'Quarterly':
        df_agg['Period'] = df_agg['Date'].dt.to_period('Q').dt.start_time
    else:
        return df
    
    # ---------- AGGREGATE BY PERIOD AND SKU ----------
    agg_cols = {'Quantity': 'sum'}
    
    # Keep additional numeric columns
    for col in df_agg.columns:
        if col not in ['Date', 'SKU', 'Quantity', 'Period']:
            if pd.api.types.is_numeric_dtype(df_agg[col]):
                agg_cols[col] = 'mean'
    
    grouped = df_agg.groupby(['Period', 'SKU']).agg(agg_cols).reset_index()
    grouped = grouped.rename(columns={'Period': 'Date'})
    
    print(f"aggregated data from {len(df)} to {len(grouped)} rows ({granularity})")
    
    return grouped


# ================ FILE UTILITIES ================

def get_sku_list(df):
    """
    extract unique sku values
    return sorted list
    """
    return sorted(df['SKU'].unique().tolist())


def filter_by_sku(df, sku):
    """
    filter dataframe by single sku
    return filtered dataframe
    """
    return df[df['SKU'] == sku].copy()


def get_date_range(df):
    """
    get min and max dates
    return tuple of dates
    """
    return df['Date'].min(), df['Date'].max()