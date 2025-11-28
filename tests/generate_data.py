"""
dataset generation script
create sample inventory data
configurable parameters for testing
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
import argparse


# ================ PATHS ================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")


# ================ CONFIGURATION ================

class DataConfig:
    """
    default generation parameters
    """
    # ---------- DATE SETTINGS ----------
    START_DATE = "2024-01-01"
    NUM_DAYS = 90
    
    # ---------- SKU SETTINGS ----------
    NUM_SKUS = 3
    SKU_PREFIX = "PROD"
    
    # ---------- QUANTITY SETTINGS ----------
    BASE_QUANTITY = 100
    TREND_FACTOR = 2.0
    SEASONALITY_AMPLITUDE = 20
    NOISE_LEVEL = 10
    
    # ---------- OUTPUT ----------
    OUTPUT_FILE = "inventory.csv"


# ================ GENERATION FUNCTIONS ================

def generate_dates(start_date, num_days):
    """
    create date range
    return list of dates
    """
    start = pd.to_datetime(start_date)
    dates = [start + timedelta(days=i) for i in range(num_days)]
    return dates


def generate_sku_codes(num_skus, prefix="PROD"):
    """
    create sku identifiers
    return list of sku codes
    """
    skus = [f"{prefix}-{str(i+1).zfill(3)}" for i in range(num_skus)]
    return skus


def generate_base_pattern(num_days, base_qty, trend_factor):
    """
    create base quantity pattern
    linear trend over time
    """
    trend = np.linspace(0, trend_factor * base_qty, num_days)
    base = np.full(num_days, base_qty)
    return base + trend


def add_seasonality(values, amplitude, period=7):
    """
    add weekly seasonality
    sine wave pattern
    """
    days = np.arange(len(values))
    seasonal = amplitude * np.sin(2 * np.pi * days / period)
    return values + seasonal


def add_noise(values, noise_level):
    """
    add random noise
    normal distribution
    """
    noise = np.random.normal(0, noise_level, len(values))
    return values + noise


def add_spikes(values, num_spikes=3, spike_magnitude=2.0):
    """
    add random demand spikes
    simulate irregular events
    """
    values = values.copy()
    spike_indices = np.random.choice(len(values), num_spikes, replace=False)
    
    for idx in spike_indices:
        values[idx] *= spike_magnitude
    
    return values


def add_dips(values, num_dips=2, dip_magnitude=0.5):
    """
    add random demand dips
    simulate low demand periods
    """
    values = values.copy()
    dip_indices = np.random.choice(len(values), num_dips, replace=False)
    
    for idx in dip_indices:
        values[idx] *= dip_magnitude
    
    return values


def generate_sku_quantities(num_days, base_qty, config):
    """
    generate quantity series for one sku
    combine all patterns
    """
    # ---------- BASE PATTERN ----------
    values = generate_base_pattern(num_days, base_qty, config.get('trend', 2.0))
    
    # ---------- ADD SEASONALITY ----------
    if config.get('seasonality', True):
        values = add_seasonality(values, config.get('seasonality_amp', 20))
    
    # ---------- ADD NOISE ----------
    if config.get('noise', True):
        values = add_noise(values, config.get('noise_level', 10))
    
    # ---------- ADD SPIKES ----------
    if config.get('spikes', False):
        values = add_spikes(values, config.get('num_spikes', 3))
    
    # ---------- ADD DIPS ----------
    if config.get('dips', False):
        values = add_dips(values, config.get('num_dips', 2))
    
    # ---------- ENSURE POSITIVE ----------
    values = np.maximum(values, 1)
    
    # ---------- ROUND VALUES ----------
    values = np.round(values).astype(int)
    
    return values


# ================ DATASET BUILDERS ================

def generate_simple_dataset(num_days=90, num_skus=3, start_date="2024-01-01"):
    """
    create basic dataset
    linear trend with noise
    """
    dates = generate_dates(start_date, num_days)
    skus = generate_sku_codes(num_skus)
    
    records = []
    
    for sku_idx, sku in enumerate(skus):
        # ---------- VARY BASE BY SKU ----------
        base_qty = 100 + (sku_idx * 50)
        
        config = {
            'trend': 2.0,
            'seasonality': True,
            'seasonality_amp': 15,
            'noise': True,
            'noise_level': 8,
            'spikes': False,
            'dips': False
        }
        
        quantities = generate_sku_quantities(num_days, base_qty, config)
        
        for date, qty in zip(dates, quantities):
            records.append({
                'Date': date.strftime('%Y-%m-%d'),
                'SKU': sku,
                'Quantity': qty
            })
    
    return pd.DataFrame(records)


def generate_complex_dataset(num_days=180, num_skus=5, start_date="2024-01-01"):
    """
    create complex dataset
    multiple patterns per sku
    """
    dates = generate_dates(start_date, num_days)
    skus = generate_sku_codes(num_skus)
    
    # ---------- SKU CONFIGURATIONS ----------
    sku_configs = [
        {
            'base': 150,
            'trend': 3.0,
            'seasonality': True,
            'seasonality_amp': 25,
            'noise': True,
            'noise_level': 12,
            'spikes': True,
            'num_spikes': 5,
            'dips': False
        },
        {
            'base': 80,
            'trend': 1.5,
            'seasonality': True,
            'seasonality_amp': 10,
            'noise': True,
            'noise_level': 5,
            'spikes': False,
            'dips': True,
            'num_dips': 3
        },
        {
            'base': 200,
            'trend': 0.5,
            'seasonality': False,
            'noise': True,
            'noise_level': 20,
            'spikes': True,
            'num_spikes': 8,
            'dips': True,
            'num_dips': 4
        },
        {
            'base': 120,
            'trend': 2.5,
            'seasonality': True,
            'seasonality_amp': 30,
            'noise': True,
            'noise_level': 15,
            'spikes': False,
            'dips': False
        },
        {
            'base': 50,
            'trend': 4.0,
            'seasonality': True,
            'seasonality_amp': 8,
            'noise': True,
            'noise_level': 3,
            'spikes': True,
            'num_spikes': 2,
            'dips': False
        }
    ]
    
    records = []
    
    for sku_idx, sku in enumerate(skus):
        config = sku_configs[sku_idx % len(sku_configs)]
        quantities = generate_sku_quantities(num_days, config['base'], config)
        
        for date, qty in zip(dates, quantities):
            records.append({
                'Date': date.strftime('%Y-%m-%d'),
                'SKU': sku,
                'Quantity': qty
            })
    
    return pd.DataFrame(records)


def generate_seasonal_dataset(num_days=365, num_skus=3, start_date="2024-01-01"):
    """
    create yearly seasonal dataset
    monthly and weekly patterns
    """
    dates = generate_dates(start_date, num_days)
    skus = generate_sku_codes(num_skus)
    
    records = []
    
    for sku_idx, sku in enumerate(skus):
        base_qty = 100 + (sku_idx * 30)
        
        quantities = []
        for day_idx, date in enumerate(dates):
            # ---------- BASE VALUE ----------
            value = base_qty
            
            # ---------- YEARLY TREND ----------
            value += (day_idx / num_days) * base_qty * 0.5
            
            # ---------- MONTHLY SEASONALITY ----------
            month = date.month
            monthly_factor = 1 + 0.3 * np.sin(2 * np.pi * month / 12)
            value *= monthly_factor
            
            # ---------- WEEKLY SEASONALITY ----------
            weekday = date.weekday()
            if weekday in [5, 6]:  # weekend
                value *= 1.2
            
            # ---------- NOISE ----------
            value += np.random.normal(0, base_qty * 0.1)
            
            # ---------- ENSURE POSITIVE ----------
            value = max(1, int(round(value)))
            quantities.append(value)
        
        for date, qty in zip(dates, quantities):
            records.append({
                'Date': date.strftime('%Y-%m-%d'),
                'SKU': sku,
                'Quantity': qty
            })
    
    return pd.DataFrame(records)


def generate_sparse_dataset(num_days=90, num_skus=3, start_date="2024-01-01", 
                           missing_pct=0.1):
    """
    create dataset with missing days
    simulate irregular data
    """
    # ---------- GENERATE BASE ----------
    df = generate_simple_dataset(num_days, num_skus, start_date)
    
    # ---------- REMOVE RANDOM ROWS ----------
    num_remove = int(len(df) * missing_pct)
    remove_indices = np.random.choice(df.index, num_remove, replace=False)
    df = df.drop(remove_indices).reset_index(drop=True)
    
    return df


def generate_multi_warehouse_dataset(num_days=90, num_skus=3, num_warehouses=2,
                                     start_date="2024-01-01"):
    """
    create dataset with warehouse dimension
    multiple locations per sku
    """
    dates = generate_dates(start_date, num_days)
    skus = generate_sku_codes(num_skus)
    warehouses = [f"WH-{str(i+1).zfill(2)}" for i in range(num_warehouses)]
    
    records = []
    
    for warehouse in warehouses:
        for sku_idx, sku in enumerate(skus):
            # ---------- VARY BY WAREHOUSE ----------
            wh_factor = 0.8 + (0.4 * np.random.random())
            base_qty = int((100 + (sku_idx * 50)) * wh_factor)
            
            config = {
                'trend': 2.0 * wh_factor,
                'seasonality': True,
                'seasonality_amp': 15,
                'noise': True,
                'noise_level': 10,
                'spikes': False,
                'dips': False
            }
            
            quantities = generate_sku_quantities(num_days, base_qty, config)
            
            for date, qty in zip(dates, quantities):
                records.append({
                    'Date': date.strftime('%Y-%m-%d'),
                    'Warehouse': warehouse,
                    'SKU': sku,
                    'Quantity': qty
                })
    
    return pd.DataFrame(records)


# ================ EXPORT FUNCTIONS ================

def save_dataset(df, filename, output_dir=None):
    """
    save dataframe to csv
    create directory if needed
    """
    if output_dir is None:
        output_dir = DATA_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, filename)
    df.to_csv(filepath, index=False)
    
    print(f"saved: {filepath}")
    print(f"records: {len(df)}")
    print(f"columns: {list(df.columns)}")
    
    return filepath


def preview_dataset(df, rows=10):
    """
    display dataset preview
    show statistics
    """
    print("\n--- dataset preview ---")
    print(df.head(rows).to_string(index=False))
    
    print("\n--- statistics ---")
    print(f"total records: {len(df)}")
    print(f"date range: {df['Date'].min()} to {df['Date'].max()}")
    print(f"unique skus: {df['SKU'].nunique()}")
    
    if 'Quantity' in df.columns:
        print(f"quantity range: {df['Quantity'].min()} to {df['Quantity'].max()}")
        print(f"quantity mean: {df['Quantity'].mean():.2f}")


# ================ CLI INTERFACE ================

def parse_arguments():
    """
    parse command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Generate inventory dataset for testing'
    )
    
    parser.add_argument(
        '--type', '-t',
        choices=['simple', 'complex', 'seasonal', 'sparse', 'warehouse'],
        default='simple',
        help='dataset type to generate'
    )
    
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=90,
        help='number of days'
    )
    
    parser.add_argument(
        '--skus', '-s',
        type=int,
        default=3,
        help='number of skus'
    )
    
    parser.add_argument(
        '--start', '-st',
        type=str,
        default='2024-01-01',
        help='start date (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='inventory.csv',
        help='output filename'
    )
    
    parser.add_argument(
        '--preview', '-p',
        action='store_true',
        help='show dataset preview'
    )
    
    parser.add_argument(
        '--seed', '-r',
        type=int,
        default=None,
        help='random seed for reproducibility'
    )
    
    return parser.parse_args()


# ================ MAIN ================

def main():
    """
    generate dataset based on arguments
    """
    args = parse_arguments()
    
    # ---------- SET SEED ----------
    if args.seed is not None:
        np.random.seed(args.seed)
        print(f"random seed: {args.seed}")
    
    # ---------- GENERATE DATA ----------
    print(f"generating {args.type} dataset")
    print(f"days: {args.days}, skus: {args.skus}")
    
    if args.type == 'simple':
        df = generate_simple_dataset(args.days, args.skus, args.start)
    
    elif args.type == 'complex':
        df = generate_complex_dataset(args.days, args.skus, args.start)
    
    elif args.type == 'seasonal':
        df = generate_seasonal_dataset(args.days, args.skus, args.start)
    
    elif args.type == 'sparse':
        df = generate_sparse_dataset(args.days, args.skus, args.start)
    
    elif args.type == 'warehouse':
        df = generate_multi_warehouse_dataset(args.days, args.skus, 2, args.start)
    
    else:
        df = generate_simple_dataset(args.days, args.skus, args.start)
    
    # ---------- PREVIEW ----------
    if args.preview:
        preview_dataset(df)
    
    # ---------- SAVE ----------
    save_dataset(df, args.output)
    
    print("generation complete")


def generate_all_samples():
    """
    generate all sample datasets
    for testing purposes
    """
    np.random.seed(42)
    
    datasets = [
        ('inventory.csv', generate_simple_dataset(90, 3)),
        ('inventory_complex.csv', generate_complex_dataset(180, 5)),
        ('inventory_seasonal.csv', generate_seasonal_dataset(365, 3)),
        ('inventory_sparse.csv', generate_sparse_dataset(90, 3)),
        ('inventory_warehouse.csv', generate_multi_warehouse_dataset(90, 3, 2))
    ]
    
    for filename, df in datasets:
        save_dataset(df, filename)
        print()
    
    print("all samples generated")


# ================ ENTRY POINT ================

if __name__ == "__main__":
    # ---------- CHECK FOR ALL FLAG ----------
    if len(sys.argv) > 1 and sys.argv[1] == '--all':
        generate_all_samples()
    else:
        main()