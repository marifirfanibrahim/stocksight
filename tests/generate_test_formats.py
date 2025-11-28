"""
generate test datasets with various formats
test date parsing and multi column support
validate data handling capabilities
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys


# ================ PATHS ================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
TEST_DATA_DIR = os.path.join(DATA_DIR, "test_formats")


# ================ DATE FORMAT GENERATORS ================

def generate_dates_format1(start_date, num_days):
    """
    format: 12 jan 2024
    """
    start = pd.to_datetime(start_date)
    dates = []
    for i in range(num_days):
        date = start + timedelta(days=i)
        dates.append(date.strftime('%d %b %Y'))
    return dates


def generate_dates_format2(start_date, num_days):
    """
    format: 12 january 2024
    """
    start = pd.to_datetime(start_date)
    dates = []
    for i in range(num_days):
        date = start + timedelta(days=i)
        dates.append(date.strftime('%d %B %Y'))
    return dates


def generate_dates_format3(start_date, num_days):
    """
    format: jan 12, 2024
    """
    start = pd.to_datetime(start_date)
    dates = []
    for i in range(num_days):
        date = start + timedelta(days=i)
        dates.append(date.strftime('%b %d, %Y'))
    return dates


def generate_dates_format4(start_date, num_days):
    """
    format: 01/12/2024
    """
    start = pd.to_datetime(start_date)
    dates = []
    for i in range(num_days):
        date = start + timedelta(days=i)
        dates.append(date.strftime('%m/%d/%Y'))
    return dates


def generate_dates_format5(start_date, num_days):
    """
    format: 12/01/2024
    """
    start = pd.to_datetime(start_date)
    dates = []
    for i in range(num_days):
        date = start + timedelta(days=i)
        dates.append(date.strftime('%d/%m/%Y'))
    return dates


def generate_dates_format6(start_date, num_days):
    """
    format: 2024-01-12
    """
    start = pd.to_datetime(start_date)
    dates = []
    for i in range(num_days):
        date = start + timedelta(days=i)
        dates.append(date.strftime('%Y-%m-%d'))
    return dates


# ================ FORMAT MAPPING ================

FORMAT_MAP = {
    'format1': {'func': generate_dates_format1, 'parse_format': '%d %b %Y'},
    'format2': {'func': generate_dates_format2, 'parse_format': '%d %B %Y'},
    'format3': {'func': generate_dates_format3, 'parse_format': '%b %d, %Y'},
    'format4': {'func': generate_dates_format4, 'parse_format': '%m/%d/%Y'},
    'format5': {'func': generate_dates_format5, 'parse_format': '%d/%m/%Y'},
    'format6': {'func': generate_dates_format6, 'parse_format': '%Y-%m-%d'}
}


# ================ DATASET GENERATORS ================

def generate_basic_dataset(num_days=90, date_format='format1'):
    """
    basic dataset with date sku quantity
    """
    # ---------- SELECT DATE FORMAT ----------
    dates = FORMAT_MAP[date_format]['func']('2024-01-01', num_days)
    
    # ---------- GENERATE DATA ----------
    records = []
    skus = ['PROD-001', 'PROD-002', 'PROD-003']
    
    for sku_idx, sku in enumerate(skus):
        base_qty = 100 + (sku_idx * 50)
        
        for day_idx, date in enumerate(dates):
            qty = base_qty + day_idx * 2 + np.random.randint(-10, 10)
            qty = max(1, qty)
            
            records.append({
                'Date': date,
                'SKU': sku,
                'Quantity': qty
            })
    
    return pd.DataFrame(records)


def generate_multicolumn_dataset(num_days=90, date_format='format1'):
    """
    dataset with additional columns
    category warehouse price cost
    """
    # ---------- SELECT DATE FORMAT ----------
    dates = FORMAT_MAP[date_format]['func']('2024-01-01', num_days)
    parse_format = FORMAT_MAP[date_format]['parse_format']
    
    # ---------- SKU DEFINITIONS ----------
    sku_config = {
        'PROD-001': {
            'category': 'Electronics',
            'warehouse': 'WH-01',
            'price': 150.00,
            'cost': 90.00,
            'base_qty': 200
        },
        'PROD-002': {
            'category': 'Clothing',
            'warehouse': 'WH-02',
            'price': 45.00,
            'cost': 20.00,
            'base_qty': 150
        },
        'PROD-003': {
            'category': 'Electronics',
            'warehouse': 'WH-01',
            'price': 299.00,
            'cost': 180.00,
            'base_qty': 100
        },
        'PROD-004': {
            'category': 'Home',
            'warehouse': 'WH-03',
            'price': 75.00,
            'cost': 40.00,
            'base_qty': 180
        },
        'PROD-005': {
            'category': 'Clothing',
            'warehouse': 'WH-02',
            'price': 65.00,
            'cost': 30.00,
            'base_qty': 220
        }
    }
    
    # ---------- GENERATE DATA ----------
    records = []
    
    for sku, config in sku_config.items():
        for day_idx, date in enumerate(dates):
            # ---------- QUANTITY WITH TREND ----------
            qty = config['base_qty'] + day_idx * 1.5
            
            # ---------- PARSE DATE FOR SEASONALITY ----------
            try:
                date_obj = pd.to_datetime(date, format=parse_format)
            except:
                date_obj = pd.to_datetime(date)
            
            # ---------- WEEKLY SEASONALITY ----------
            weekday = date_obj.weekday()
            if weekday in [5, 6]:  # weekend
                qty *= 1.3
            
            # ---------- MONTHLY SEASONALITY ----------
            month = date_obj.month
            monthly_factor = 1 + 0.2 * np.sin(2 * np.pi * month / 12)
            qty *= monthly_factor
            
            # ---------- NOISE ----------
            qty += np.random.normal(0, config['base_qty'] * 0.05)
            qty = max(1, int(round(qty)))
            
            # ---------- PRICE VARIATION ----------
            price_var = config['price'] * (1 + np.random.uniform(-0.05, 0.05))
            
            records.append({
                'Date': date,
                'SKU': sku,
                'Quantity': qty,
                'Category': config['category'],
                'Warehouse': config['warehouse'],
                'Price': round(price_var, 2),
                'Cost': config['cost']
            })
    
    return pd.DataFrame(records)


def generate_seasonal_dataset(num_days=365, date_format='format1'):
    """
    dataset with strong seasonal patterns
    monthly and weekly variations
    """
    # ---------- SELECT DATE FORMAT ----------
    dates = FORMAT_MAP[date_format]['func']('2024-01-01', num_days)
    parse_format = FORMAT_MAP[date_format]['parse_format']
    
    # ---------- SEASONAL PRODUCTS ----------
    seasonal_config = {
        'WINTER-001': {
            'category': 'Seasonal',
            'warehouse': 'WH-01',
            'peak_months': [11, 12, 1, 2],
            'base_qty': 50
        },
        'SUMMER-001': {
            'category': 'Seasonal',
            'warehouse': 'WH-02',
            'peak_months': [6, 7, 8],
            'base_qty': 50
        },
        'YEAR-ROUND-001': {
            'category': 'Regular',
            'warehouse': 'WH-01',
            'peak_months': [],
            'base_qty': 100
        }
    }
    
    records = []
    
    for sku, config in seasonal_config.items():
        for day_idx, date in enumerate(dates):
            # ---------- PARSE DATE ----------
            try:
                date_obj = pd.to_datetime(date, format=parse_format)
            except:
                date_obj = pd.to_datetime(date)
            
            month = date_obj.month
            
            # ---------- BASE QUANTITY ----------
            qty = config['base_qty']
            
            # ---------- SEASONAL BOOST ----------
            if config['peak_months']:
                if month in config['peak_months']:
                    qty *= 3.5
                else:
                    qty *= 0.5
            
            # ---------- WEEKLY PATTERN ----------
            weekday = date_obj.weekday()
            if weekday in [4, 5]:  # friday saturday
                qty *= 1.4
            elif weekday == 0:  # monday
                qty *= 0.8
            
            # ---------- NOISE ----------
            qty += np.random.normal(0, qty * 0.1)
            qty = max(1, int(round(qty)))
            
            records.append({
                'Date': date,
                'SKU': sku,
                'Quantity': qty,
                'Category': config['category'],
                'Warehouse': config['warehouse']
            })
    
    return pd.DataFrame(records)


# ================ SAVE FUNCTIONS ================

def save_dataset(df, filename, subdir=''):
    """
    save dataframe to csv
    """
    if subdir:
        output_dir = os.path.join(TEST_DATA_DIR, subdir)
    else:
        output_dir = TEST_DATA_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False)
    
    print(f"saved: {filepath}")
    print(f"records: {len(df)}")
    print(f"columns: {list(df.columns)}")
    print()
    
    return filepath


# ================ MAIN GENERATION ================

def generate_all_test_datasets():
    """
    generate all test format datasets
    """
    print("generating test datasets")
    print("=" * 50)
    
    # ---------- BASIC FORMATS ----------
    print("basic date formats")
    print("-" * 50)
    
    formats = {
        'format1_12jan2024.csv': 'format1',
        'format2_12january2024.csv': 'format2',
        'format3_jan12_2024.csv': 'format3',
        'format4_mmddyyyy.csv': 'format4',
        'format5_ddmmyyyy.csv': 'format5',
        'format6_yyyymmdd.csv': 'format6'
    }
    
    for filename, fmt in formats.items():
        df = generate_basic_dataset(num_days=90, date_format=fmt)
        save_dataset(df, filename, 'date_formats')
    
    # ---------- MULTI COLUMN ----------
    print("multi column datasets")
    print("-" * 50)
    
    for filename, fmt in formats.items():
        multi_filename = filename.replace('.csv', '_multicolumn.csv')
        df = generate_multicolumn_dataset(num_days=90, date_format=fmt)
        save_dataset(df, multi_filename, 'multicolumn')
    
    # ---------- SEASONAL ----------
    print("seasonal datasets")
    print("-" * 50)
    
    df_seasonal = generate_seasonal_dataset(num_days=365, date_format='format1')
    save_dataset(df_seasonal, 'seasonal_yearly.csv', 'seasonal')
    
    print("=" * 50)
    print("all test datasets generated")
    print(f"location: {TEST_DATA_DIR}")


# ================ CLI ================

if __name__ == "__main__":
    generate_all_test_datasets()