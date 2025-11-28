"""
feature engineering for forecasting
extract features from additional columns
handle categorical and numeric variables
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler


# ================ FEATURE EXTRACTION ================

def detect_additional_columns(df, required_cols=['Date', 'SKU', 'Quantity']):
    """
    find columns beyond required set
    return list of feature columns
    """
    all_cols = df.columns.tolist()
    feature_cols = [col for col in all_cols if col not in required_cols]
    
    return feature_cols


def categorize_column_type(df, column):
    """
    determine if column is categorical or numeric
    return type and info
    """
    dtype = df[column].dtype
    unique_count = df[column].nunique()
    
    if dtype == 'object' or unique_count < 20:
        return 'categorical'
    else:
        return 'numeric'


def encode_categorical_features(df, column):
    """
    encode categorical column
    return encoded dataframe and encoder
    """
    encoder = LabelEncoder()
    encoded = encoder.fit_transform(df[column].astype(str))
    
    return encoded, encoder


def normalize_numeric_features(df, column):
    """
    normalize numeric column
    return normalized values and scaler
    """
    scaler = StandardScaler()
    values = df[column].values.reshape(-1, 1)
    normalized = scaler.fit_transform(values)
    
    return normalized.flatten(), scaler


# ================ EXOGENOUS VARIABLES ================

def prepare_exogenous_features(df, feature_columns):
    """
    prepare features for autots
    create exogenous variable dataframe
    """
    if not feature_columns:
        return None, {}
    
    exog_data = pd.DataFrame()
    exog_data['Date'] = df['Date']
    
    encoders = {}
    
    for col in feature_columns:
        col_type = categorize_column_type(df, col)
        
        if col_type == 'categorical':
            # ---------- ENCODE CATEGORICAL ----------
            encoded, encoder = encode_categorical_features(df, col)
            exog_data[col] = encoded
            encoders[col] = {'type': 'categorical', 'encoder': encoder}
            
        else:
            # ---------- NORMALIZE NUMERIC ----------
            normalized, scaler = normalize_numeric_features(df, col)
            exog_data[col] = normalized
            encoders[col] = {'type': 'numeric', 'scaler': scaler}
    
    # ---------- AGGREGATE BY DATE ----------
    exog_agg = exog_data.groupby('Date').mean().reset_index()
    
    return exog_agg, encoders


def create_future_exogenous(last_known_values, forecast_length, encoders):
    """
    create exogenous variables for forecast period
    repeat last known values
    """
    future_exog = pd.DataFrame()
    
    for col, info in encoders.items():
        if col in last_known_values:
            future_exog[col] = [last_known_values[col]] * forecast_length
    
    return future_exog


# ================ SEASONALITY DETECTION ================

def extract_date_features(df):
    """
    extract temporal features from date
    day of week month quarter
    """
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    
    # ---------- TEMPORAL FEATURES ----------
    df['DayOfWeek'] = df['Date'].dt.dayofweek
    df['DayOfMonth'] = df['Date'].dt.day
    df['DayOfYear'] = df['Date'].dt.dayofyear
    df['Month'] = df['Date'].dt.month
    df['Quarter'] = df['Date'].dt.quarter
    df['Year'] = df['Date'].dt.year
    df['WeekOfYear'] = df['Date'].dt.isocalendar().week
    
    # ---------- CYCLICAL ENCODING ----------
    df['Month_Sin'] = np.sin(2 * np.pi * df['Month'] / 12)
    df['Month_Cos'] = np.cos(2 * np.pi * df['Month'] / 12)
    df['DayOfWeek_Sin'] = np.sin(2 * np.pi * df['DayOfWeek'] / 7)
    df['DayOfWeek_Cos'] = np.cos(2 * np.pi * df['DayOfWeek'] / 7)
    
    # ---------- WEEKEND FLAG ----------
    df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)
    
    return df


def detect_seasonality_pattern(df, sku=None):
    """
    analyze data for seasonal patterns
    return seasonality info
    """
    if sku:
        data = df[df['SKU'] == sku].copy()
    else:
        data = df.copy()
    
    data = extract_date_features(data)
    
    # ---------- MONTHLY SEASONALITY ----------
    monthly_avg = data.groupby('Month')['Quantity'].mean()
    monthly_std = monthly_avg.std()
    monthly_mean = monthly_avg.mean()
    monthly_cv = monthly_std / monthly_mean if monthly_mean > 0 else 0
    
    # ---------- WEEKLY SEASONALITY ----------
    weekly_avg = data.groupby('DayOfWeek')['Quantity'].mean()
    weekly_std = weekly_avg.std()
    weekly_mean = weekly_avg.mean()
    weekly_cv = weekly_std / weekly_mean if weekly_mean > 0 else 0
    
    # ---------- SEASONALITY DETECTION ----------
    has_monthly = monthly_cv > 0.15
    has_weekly = weekly_cv > 0.10
    
    seasonality_info = {
        'has_monthly_seasonality': has_monthly,
        'has_weekly_seasonality': has_weekly,
        'monthly_cv': monthly_cv,
        'weekly_cv': weekly_cv,
        'monthly_pattern': monthly_avg.to_dict(),
        'weekly_pattern': weekly_avg.to_dict()
    }
    
    return seasonality_info


# ================ FEATURE PIPELINE ================

def build_feature_pipeline(df, include_date_features=True, include_additional=True):
    """
    complete feature engineering pipeline
    return enhanced dataframe
    """
    df_features = df.copy()
    
    # ---------- DATE FEATURES ----------
    if include_date_features:
        df_features = extract_date_features(df_features)
    
    # ---------- ADDITIONAL COLUMNS ----------
    if include_additional:
        feature_cols = detect_additional_columns(df)
        
        for col in feature_cols:
            col_type = categorize_column_type(df, col)
            
            if col_type == 'categorical':
                encoded, _ = encode_categorical_features(df, col)
                df_features[f'{col}_Encoded'] = encoded
    
    return df_features


def prepare_multicolumn_forecast(df, feature_columns=None, include_seasonality=True):
    """
    prepare data for forecasting with multiple features
    return processed dataframe and metadata
    """
    df_processed = df.copy()
    metadata = {}
    
    # ---------- EXTRACT DATE FEATURES ----------
    if include_seasonality:
        df_processed = extract_date_features(df_processed)
        metadata['seasonality'] = detect_seasonality_pattern(df_processed)
    
    # ---------- PROCESS ADDITIONAL FEATURES ----------
    if feature_columns:
        exog_data, encoders = prepare_exogenous_features(df_processed, feature_columns)
        metadata['exogenous'] = exog_data
        metadata['encoders'] = encoders
    
    # ---------- CLEAN FOR AUTOTS ----------
    base_cols = ['Date', 'SKU', 'Quantity']
    df_base = df_processed[base_cols].copy()
    
    metadata['feature_columns'] = feature_columns
    metadata['original_shape'] = df.shape
    metadata['processed_shape'] = df_processed.shape
    
    return df_base, metadata