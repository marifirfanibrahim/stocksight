"""
generate realistic industry inventory dataset
simulate real world patterns and behaviors
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random


# ================ PATHS ================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")


# ================ CONFIGURATION ================

# product categories with seasonal patterns
PRODUCT_CONFIG = {
    # electronics - black friday, back to school
    'ELEC-LAPTOP-001': {'base': 50, 'category': 'Electronics', 'peak_months': [8, 9, 11, 12], 'trend': 0.02},
    'ELEC-PHONE-001': {'base': 120, 'category': 'Electronics', 'peak_months': [9, 11, 12], 'trend': 0.03},
    'ELEC-TABLET-001': {'base': 40, 'category': 'Electronics', 'peak_months': [8, 11, 12], 'trend': 0.01},
    'ELEC-HEADPHONES-001': {'base': 200, 'category': 'Electronics', 'peak_months': [11, 12], 'trend': 0.05},
    
    # clothing - seasonal fashion
    'CLTH-TSHIRT-001': {'base': 300, 'category': 'Clothing', 'peak_months': [5, 6, 7], 'trend': 0.01},
    'CLTH-JACKET-001': {'base': 80, 'category': 'Clothing', 'peak_months': [10, 11, 12, 1, 2], 'trend': 0.0},
    'CLTH-JEANS-001': {'base': 150, 'category': 'Clothing', 'peak_months': [8, 9], 'trend': 0.02},
    'CLTH-SNEAKERS-001': {'base': 100, 'category': 'Clothing', 'peak_months': [3, 4, 8, 9], 'trend': 0.03},
    
    # home & garden - spring/summer
    'HOME-FURNITURE-001': {'base': 25, 'category': 'Home', 'peak_months': [3, 4, 5, 6], 'trend': 0.01},
    'HOME-GARDEN-001': {'base': 60, 'category': 'Home', 'peak_months': [3, 4, 5], 'trend': -0.01},
    'HOME-KITCHEN-001': {'base': 80, 'category': 'Home', 'peak_months': [11, 12], 'trend': 0.02},
    
    # food & beverage - holidays
    'FOOD-SNACKS-001': {'base': 500, 'category': 'Food', 'peak_months': [7, 12], 'trend': 0.01},
    'FOOD-DRINKS-001': {'base': 400, 'category': 'Food', 'peak_months': [6, 7, 8], 'trend': 0.02},
    'FOOD-CANDY-001': {'base': 200, 'category': 'Food', 'peak_months': [2, 10, 12], 'trend': 0.0},
    
    # toys - christmas, summer
    'TOYS-GAMES-001': {'base': 100, 'category': 'Toys', 'peak_months': [11, 12], 'trend': 0.03},
    'TOYS-OUTDOOR-001': {'base': 80, 'category': 'Toys', 'peak_months': [5, 6, 7], 'trend': 0.02},
}

# warehouse locations
WAREHOUSES = ['NYC-01', 'LAX-02', 'CHI-03', 'DAL-04']

# event calendar (special demand events)
SPECIAL_EVENTS = [
    {'name': 'Black Friday', 'date': '11-25', 'impact': 3.0, 'duration': 4},
    {'name': 'Cyber Monday', 'date': '11-28', 'impact': 2.5, 'duration': 1},
    {'name': 'Christmas', 'date': '12-20', 'impact': 2.0, 'duration': 5},
    {'name': 'Back to School', 'date': '08-15', 'impact': 1.8, 'duration': 14},
    {'name': 'Valentines', 'date': '02-10', 'impact': 1.5, 'duration': 5},
    {'name': 'Easter', 'date': '04-01', 'impact': 1.3, 'duration': 7},
    {'name': 'Summer Sale', 'date': '07-04', 'impact': 1.6, 'duration': 7},
]


# ================ GENERATION FUNCTIONS ================

def generate_base_demand(num_days, base_qty, trend_rate):
    """
    generate base demand with trend
    """
    days = np.arange(num_days)
    trend = base_qty * (1 + trend_rate) ** (days / 365)
    return trend


def add_seasonality(values, dates, peak_months, peak_factor=2.0):
    """
    add monthly seasonality
    """
    result = values.copy()
    
    for i, date in enumerate(dates):
        if date.month in peak_months:
            result[i] *= peak_factor
        else:
            # slight decrease in off-peak
            result[i] *= 0.8
    
    return result


def add_weekly_pattern(values, dates):
    """
    add day-of-week patterns
    """
    result = values.copy()
    
    for i, date in enumerate(dates):
        weekday = date.weekday()
        
        if weekday == 0:  # monday - slow start
            result[i] *= 0.85
        elif weekday == 4:  # friday - pre-weekend
            result[i] *= 1.15
        elif weekday == 5:  # saturday - peak
            result[i] *= 1.25
        elif weekday == 6:  # sunday - good
            result[i] *= 1.10
    
    return result


def add_special_events(values, dates, year):
    """
    add special event impacts
    """
    result = values.copy()
    
    for event in SPECIAL_EVENTS:
        event_month, event_day = map(int, event['date'].split('-'))
        
        try:
            event_date = datetime(year, event_month, event_day)
            
            for i, date in enumerate(dates):
                days_diff = (date - event_date).days
                
                if 0 <= days_diff < event['duration']:
                    # peak at start, gradual decline
                    factor = event['impact'] * (1 - days_diff / event['duration'] * 0.5)
                    result[i] *= factor
                elif -3 <= days_diff < 0:
                    # slight buildup before event
                    result[i] *= 1.2
        except:
            pass
    
    return result


def add_noise(values, noise_level=0.15):
    """
    add realistic noise
    """
    noise = np.random.normal(1, noise_level, len(values))
    return values * noise


def add_stockouts(values, stockout_probability=0.02):
    """
    simulate random stockouts
    """
    result = values.copy()
    
    for i in range(len(result)):
        if random.random() < stockout_probability:
            # stockout - zero or very low sales
            result[i] *= random.uniform(0, 0.1)
    
    return result


def add_promotions(values, dates, promo_probability=0.05, promo_impact=1.5):
    """
    simulate random promotions
    """
    result = values.copy()
    
    i = 0
    while i < len(result):
        if random.random() < promo_probability:
            # promotion lasts 3-7 days
            promo_duration = random.randint(3, 7)
            for j in range(min(promo_duration, len(result) - i)):
                result[i + j] *= promo_impact
            i += promo_duration
        else:
            i += 1
    
    return result


# ================ MAIN GENERATOR ================

def generate_realistic_dataset(
    start_date='2022-01-01',
    num_days=730,  # 2 years
    include_warehouses=True,
    include_pricing=True
):
    """
    generate complete realistic dataset
    """
    np.random.seed(42)
    random.seed(42)
    
    start = pd.to_datetime(start_date)
    dates = [start + timedelta(days=i) for i in range(num_days)]
    year = start.year
    
    records = []
    
    for sku, config in PRODUCT_CONFIG.items():
        warehouses = WAREHOUSES if include_warehouses else ['MAIN-01']
        
        for warehouse in warehouses:
            # warehouse factor
            wh_factor = random.uniform(0.7, 1.3)
            
            # base demand
            base_demand = generate_base_demand(
                num_days, 
                config['base'] * wh_factor, 
                config['trend']
            )
            
            # add patterns
            demand = add_seasonality(base_demand, dates, config['peak_months'])
            demand = add_weekly_pattern(demand, dates)
            demand = add_special_events(demand, dates, year)
            demand = add_noise(demand)
            demand = add_stockouts(demand)
            demand = add_promotions(demand, dates)
            
            # ensure positive integers
            demand = np.maximum(demand, 0).astype(int)
            
            # pricing
            if include_pricing:
                base_price = random.uniform(10, 500)
                base_cost = base_price * random.uniform(0.4, 0.7)
            
            # create records
            for i, date in enumerate(dates):
                record = {
                    'Date': date.strftime('%Y-%m-%d'),
                    'Product_Code': sku,
                    'Warehouse': warehouse,
                    'Sales_Quantity': demand[i],
                    'Category': config['category']
                }
                
                if include_pricing:
                    # price varies slightly
                    price_var = base_price * random.uniform(0.95, 1.05)
                    record['Unit_Price'] = round(price_var, 2)
                    record['Unit_Cost'] = round(base_cost, 2)
                    record['Revenue'] = round(demand[i] * price_var, 2)
                
                records.append(record)
    
    df = pd.DataFrame(records)
    
    return df


def generate_simple_realistic_dataset(
    start_date='2023-01-01',
    num_days=365
):
    """
    generate simpler dataset with standard column names
    """
    np.random.seed(42)
    random.seed(42)
    
    start = pd.to_datetime(start_date)
    dates = [start + timedelta(days=i) for i in range(num_days)]
    year = start.year
    
    # fewer products
    products = {
        'PROD-001': {'base': 100, 'peak_months': [11, 12], 'trend': 0.02},
        'PROD-002': {'base': 200, 'peak_months': [6, 7, 8], 'trend': 0.01},
        'PROD-003': {'base': 150, 'peak_months': [3, 4, 8, 9], 'trend': 0.03},
        'PROD-004': {'base': 80, 'peak_months': [10, 11, 12, 1, 2], 'trend': 0.0},
        'PROD-005': {'base': 300, 'peak_months': [7, 12], 'trend': 0.01},
    }
    
    records = []
    
    for sku, config in products.items():
        base_demand = generate_base_demand(num_days, config['base'], config['trend'])
        demand = add_seasonality(base_demand, dates, config['peak_months'])
        demand = add_weekly_pattern(demand, dates)
        demand = add_special_events(demand, dates, year)
        demand = add_noise(demand, 0.1)
        demand = np.maximum(demand, 1).astype(int)
        
        for i, date in enumerate(dates):
            records.append({
                'Date': date.strftime('%d %b %Y'),  # different format
                'SKU': sku,
                'Quantity': demand[i]
            })
    
    return pd.DataFrame(records)


# ================ SAVE FUNCTIONS ================

def save_dataset(df, filename):
    """
    save dataframe to csv
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    df.to_csv(filepath, index=False)
    
    print(f"saved: {filepath}")
    print(f"records: {len(df)}")
    print(f"date range: {df.iloc[:, 0].min()} to {df.iloc[:, 0].max()}")
    print(f"columns: {list(df.columns)}")
    print()
    
    return filepath


# ================ MAIN ================

def main():
    """
    generate all realistic datasets
    """
    print("=" * 60)
    print("REALISTIC INDUSTRY DATASET GENERATOR")
    print("=" * 60)
    print()
    
    # full industry dataset (different column names - tests mapping)
    print("Generating full industry dataset...")
    df_full = generate_realistic_dataset(
        start_date='2022-01-01',
        num_days=730,
        include_warehouses=True,
        include_pricing=True
    )
    save_dataset(df_full, 'industry_full.csv')
    
    # medium dataset
    print("Generating medium dataset...")
    df_medium = generate_realistic_dataset(
        start_date='2023-01-01',
        num_days=365,
        include_warehouses=False,
        include_pricing=False
    )
    # rename to test mapping
    df_medium = df_medium.rename(columns={'Sales_Quantity': 'Quantity', 'Product_Code': 'SKU'})
    df_medium = df_medium[['Date', 'SKU', 'Quantity', 'Category']]
    save_dataset(df_medium, 'industry_medium.csv')
    
    # simple dataset with different format
    print("Generating simple dataset (different date format)...")
    df_simple = generate_simple_realistic_dataset(
        start_date='2023-01-01',
        num_days=365
    )
    save_dataset(df_simple, 'industry_simple.csv')
    
    # dataset with different column names (to test mapping)
    print("Generating dataset with custom column names...")
    df_custom = df_simple.copy()
    df_custom = df_custom.rename(columns={
        'Date': 'Transaction_Date',
        'SKU': 'Item_Code', 
        'Quantity': 'Units_Sold'
    })
    save_dataset(df_custom, 'industry_custom_columns.csv')
    
    print("=" * 60)
    print("ALL DATASETS GENERATED")
    print("=" * 60)
    print()
    print("Files created in:", DATA_DIR)
    print()
    print("Dataset descriptions:")
    print("- industry_full.csv        : 2 years, 4 warehouses, 16 products, pricing")
    print("- industry_medium.csv      : 1 year, single location, 16 products")  
    print("- industry_simple.csv      : 1 year, 5 products, standard columns")
    print("- industry_custom_columns.csv : Same as simple but different column names")


if __name__ == "__main__":
    main()