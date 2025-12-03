"""
feature utilities for forecasting
helper functions for feature engineering
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from sklearn.preprocessing import LabelEncoder, StandardScaler


# ================ CONSTANTS ================

MIN_FEATURE_COVERAGE = 0.5
MIN_FEATURE_VARIANCE = 0.01


# ================ COLUMN DETECTION ================

def detect_additional_columns(
    df: pd.DataFrame,
    required_cols: List[str] = None
) -> List[str]:
    """
    find columns beyond required set
    """
    if required_cols is None:
        required_cols = ['Date', 'SKU', 'Quantity']
    
    all_cols = df.columns.tolist()
    feature_cols = [col for col in all_cols if col not in required_cols]
    
    return feature_cols


def categorize_column_type(series: pd.Series) -> str:
    """
    determine if series is categorical or numeric
    """
    clean = series.dropna()
    
    if len(clean) == 0:
        return 'empty'
    
    dtype = clean.dtype
    unique_count = clean.nunique()
    
    if dtype == 'object' or dtype.name == 'category':
        return 'categorical'
    elif unique_count < 20 and unique_count < len(clean) * 0.5:
        return 'categorical'
    else:
        return 'numeric'


def get_feature_coverage(series: pd.Series) -> float:
    """
    calculate percentage of non-null values
    """
    if len(series) == 0:
        return 0.0
    return series.notna().sum() / len(series)


def get_feature_variance(series: pd.Series) -> float:
    """
    calculate variance for numeric or unique ratio for categorical
    """
    clean = series.dropna()
    
    if len(clean) == 0:
        return 0.0
    
    col_type = categorize_column_type(clean)
    
    if col_type == 'numeric':
        if clean.std() == 0:
            return 0.0
        mean = clean.mean()
        return clean.var() / (mean ** 2) if mean != 0 else clean.var()
    else:
        return clean.nunique() / len(clean)


# ================ DATE FEATURES ================

def extract_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    extract temporal features from date
    """
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    
    # basic features
    df['DayOfWeek'] = df['Date'].dt.dayofweek
    df['DayOfMonth'] = df['Date'].dt.day
    df['DayOfYear'] = df['Date'].dt.dayofyear
    df['Month'] = df['Date'].dt.month
    df['Quarter'] = df['Date'].dt.quarter
    df['Year'] = df['Date'].dt.year
    df['WeekOfYear'] = df['Date'].dt.isocalendar().week
    
    # cyclical encoding
    df['Month_Sin'] = np.sin(2 * np.pi * df['Month'] / 12)
    df['Month_Cos'] = np.cos(2 * np.pi * df['Month'] / 12)
    df['DayOfWeek_Sin'] = np.sin(2 * np.pi * df['DayOfWeek'] / 7)
    df['DayOfWeek_Cos'] = np.cos(2 * np.pi * df['DayOfWeek'] / 7)
    
    # flags
    df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)
    df['IsMonthStart'] = df['Date'].dt.is_month_start.astype(int)
    df['IsMonthEnd'] = df['Date'].dt.is_month_end.astype(int)
    
    return df


def add_lag_features(
    df: pd.DataFrame,
    column: str = 'Quantity',
    lags: List[int] = None
) -> pd.DataFrame:
    """
    add lagged features
    """
    if lags is None:
        lags = [1, 7, 14, 30]
    
    df = df.copy()
    
    for lag in lags:
        df[f'{column}_lag_{lag}'] = df.groupby('SKU')[column].shift(lag)
    
    return df


def add_rolling_features(
    df: pd.DataFrame,
    column: str = 'Quantity',
    windows: List[int] = None
) -> pd.DataFrame:
    """
    add rolling window features
    """
    if windows is None:
        windows = [7, 14, 30]
    
    df = df.copy()
    
    for window in windows:
        df[f'{column}_rolling_mean_{window}'] = (
            df.groupby('SKU')[column]
            .transform(lambda x: x.rolling(window, min_periods=1).mean())
        )
        df[f'{column}_rolling_std_{window}'] = (
            df.groupby('SKU')[column]
            .transform(lambda x: x.rolling(window, min_periods=1).std())
        )
    
    return df


# ================ SEASONALITY ================

def detect_seasonality_pattern(df: pd.DataFrame, sku: str = None) -> Dict:
    """
    analyze data for seasonal patterns
    """
    if sku:
        data = df[df['SKU'] == sku].copy()
    else:
        data = df.copy()
    
    if len(data) == 0:
        return {
            'has_monthly_seasonality': False,
            'has_weekly_seasonality': False,
            'monthly_cv': 0,
            'weekly_cv': 0,
            'monthly_pattern': {},
            'weekly_pattern': {}
        }
    
    data = extract_date_features(data)
    
    # monthly analysis
    monthly_avg = data.groupby('Month')['Quantity'].mean()
    monthly_std = monthly_avg.std()
    monthly_mean = monthly_avg.mean()
    monthly_cv = monthly_std / monthly_mean if monthly_mean > 0 else 0
    
    # weekly analysis
    weekly_avg = data.groupby('DayOfWeek')['Quantity'].mean()
    weekly_std = weekly_avg.std()
    weekly_mean = weekly_avg.mean()
    weekly_cv = weekly_std / weekly_mean if weekly_mean > 0 else 0
    
    return {
        'has_monthly_seasonality': monthly_cv > 0.15,
        'has_weekly_seasonality': weekly_cv > 0.10,
        'monthly_cv': monthly_cv,
        'weekly_cv': weekly_cv,
        'monthly_pattern': monthly_avg.to_dict(),
        'weekly_pattern': weekly_avg.to_dict()
    }


# ================ ENCODING ================

def encode_categorical(
    df: pd.DataFrame,
    columns: List[str] = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    encode categorical columns
    """
    if columns is None:
        columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    df_encoded = df.copy()
    encoders = {}
    
    for col in columns:
        if col not in df_encoded.columns:
            continue
        
        if col in ['Date', 'SKU']:
            continue
        
        encoder = LabelEncoder()
        df_encoded[col] = encoder.fit_transform(df_encoded[col].astype(str))
        encoders[col] = encoder
    
    return df_encoded, encoders


def scale_numeric(
    df: pd.DataFrame,
    columns: List[str] = None,
    exclude: List[str] = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    scale numeric columns
    """
    if exclude is None:
        exclude = ['Date', 'SKU']
    
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()
        columns = [c for c in columns if c not in exclude]
    
    df_scaled = df.copy()
    scalers = {}
    
    for col in columns:
        if col not in df_scaled.columns:
            continue
        
        scaler = StandardScaler()
        values = df_scaled[col].values.reshape(-1, 1)
        df_scaled[col] = scaler.fit_transform(values).flatten()
        scalers[col] = scaler
    
    return df_scaled, scalers


# ================ FEATURE IMPORTANCE ================

def analyze_feature_importance(
    df: pd.DataFrame,
    feature_columns: List[str],
    target_column: str = 'Quantity'
) -> Dict[str, Dict]:
    """
    analyze which features correlate with target
    """
    if not feature_columns:
        return {}
    
    importance = {}
    
    for col in feature_columns:
        if col not in df.columns:
            continue
        
        coverage = get_feature_coverage(df[col])
        if coverage < MIN_FEATURE_COVERAGE:
            importance[col] = {
                'type': 'low_coverage',
                'coverage': coverage
            }
            continue
        
        col_type = categorize_column_type(df[col])
        
        if col_type == 'numeric':
            clean_df = df[[col, target_column]].dropna()
            if len(clean_df) > 0:
                corr = clean_df[col].corr(clean_df[target_column])
                importance[col] = {
                    'type': 'numeric',
                    'correlation': corr if not pd.isna(corr) else 0,
                    'abs_correlation': abs(corr) if not pd.isna(corr) else 0,
                    'coverage': coverage
                }
        elif col_type == 'categorical':
            clean_df = df[[col, target_column]].dropna()
            if len(clean_df) > 0:
                group_means = clean_df.groupby(col)[target_column].mean()
                overall_var = clean_df[target_column].var()
                between_var = group_means.var() * len(group_means)
                var_ratio = between_var / overall_var if overall_var > 0 else 0
                
                importance[col] = {
                    'type': 'categorical',
                    'variance_ratio': var_ratio,
                    'num_categories': df[col].nunique(),
                    'coverage': coverage
                }
    
    return importance


# ================ FEATURE PREPARATION ================

def prepare_features_for_forecast(
    df: pd.DataFrame,
    feature_columns: List[str] = None,
    include_date_features: bool = True,
    include_lags: bool = True,
    include_rolling: bool = True
) -> pd.DataFrame:
    """
    prepare comprehensive feature set for forecasting
    """
    df_features = df.copy()
    
    # add date features
    if include_date_features:
        df_features = extract_date_features(df_features)
    
    # add lag features
    if include_lags:
        df_features = add_lag_features(df_features)
    
    # add rolling features
    if include_rolling:
        df_features = add_rolling_features(df_features)
    
    # encode categorical
    if feature_columns:
        cat_cols = [c for c in feature_columns if categorize_column_type(df[c]) == 'categorical']
        if cat_cols:
            df_features, _ = encode_categorical(df_features, cat_cols)
    
    # fill missing
    df_features = df_features.fillna(0)
    
    return df_features


def get_feature_summary(df: pd.DataFrame) -> Dict:
    """
    get summary of features in dataframe
    """
    summary = {
        'total_columns': len(df.columns),
        'numeric_columns': len(df.select_dtypes(include=[np.number]).columns),
        'categorical_columns': len(df.select_dtypes(include=['object', 'category']).columns),
        'datetime_columns': len(df.select_dtypes(include=['datetime64']).columns),
        'missing_by_column': {},
        'coverage_by_column': {}
    }
    
    for col in df.columns:
        missing = df[col].isna().sum()
        coverage = get_feature_coverage(df[col])
        
        if missing > 0:
            summary['missing_by_column'][col] = missing
        
        summary['coverage_by_column'][col] = coverage
    
    return summary