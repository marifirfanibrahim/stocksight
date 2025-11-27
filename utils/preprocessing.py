import pandas as pd
import numpy as np
from datetime import datetime
import os

def normalize_column_names(df):
    """
    Normalize column names to handle case sensitivity
    """
    df.columns = [col.strip().lower() for col in df.columns]
    return df

def validate_data(df):
    """
    Validate inventory dataset structure and data quality
    """
    errors = []
    
    # Normalize column names first
    df = normalize_column_names(df)
    
    # Check required columns (case insensitive)
    required_columns = ['date', 'sku', 'quantity']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        return False, errors
    
    # Check data types
    try:
        df['date'] = pd.to_datetime(df['date'])
    except:
        errors.append("Date column must contain valid dates")
    
    try:
        df['quantity'] = pd.to_numeric(df['quantity'])
    except:
        errors.append("Quantity column must contain numeric values")
    
    # Check for missing values
    if df[['date', 'sku', 'quantity']].isnull().any().any():
        errors.append("Dataset contains missing values")
    
    # Check for negative quantities
    if (df['quantity'] < 0).any():
        errors.append("Dataset contains negative quantities")
    
    return len(errors) == 0, errors

def clean_data(df):
    """
    Clean and preprocess the inventory data
    """
    # Normalize column names first
    df = normalize_column_names(df)
    
    # Convert to proper data types
    df['date'] = pd.to_datetime(df['date'])
    df['quantity'] = pd.to_numeric(df['quantity'])
    
    # Remove duplicates
    df = df.drop_duplicates()
    
    # Sort by date and SKU
    df = df.sort_values(['date', 'sku'])
    
    return df

def prepare_forecast_data(df, sku_column='sku', value_column='quantity'):
    """
    Prepare data for AutoTS forecasting
    """
    # Normalize column names first
    df = normalize_column_names(df)
    
    # Pivot data for time series format
    pivot_df = df.pivot_table(
        index='date', 
        columns=sku_column, 
        values=value_column, 
        aggfunc='sum'
    ).fillna(0)
    
    return pivot_df

def export_forecast(forecast_df, filename=None):
    """
    Export forecast results to CSV
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"forecast_{timestamp}.csv"
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, filename)
    forecast_df.to_csv(filepath)
    
    return filepath