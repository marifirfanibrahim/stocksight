"""
StockSight Test Data Generator
Generates comprehensive synthetic datasets to test all application features.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# ============================================================================
#                               CONFIGURATION
# ============================================================================

CONFIG = {
    "num_skus": 500,           # Total items (keep < 2000 for Excel speed, higher for CSV)
    "start_date": "2022-01-01",
    "duration_days": 730,      # 2 years of data
    "seed": 42,
    "output_csv": "stocksight_test_data_large.csv",
    "output_excel": "stocksight_test_data_multi_sheet.xlsx"
}

# Distribution of Tiers (Pareto-ish)
TIER_DIST = {
    "A": 0.10,  # 10% High volume
    "B": 0.30,  # 30% Medium volume
    "C": 0.60   # 60% Low volume
}

# Categories mapped to likely patterns
CATEGORIES = {
    "Seasonal_Decor": "seasonal",
    "Electronics": "variable",
    "Groceries": "steady",
    "Fashion": "trend_seasonal",
    "Spare_Parts": "erratic"
}

# ============================================================================
#                               GENERATOR LOGIC
# ============================================================================

class DataGenerator:
    def __init__(self, config):
        self.config = config
        np.random.seed(config["seed"])
        random.seed(config["seed"])
        self.dates = pd.date_range(
            start=config["start_date"], 
            periods=config["duration_days"], 
            freq='D'
        )
        self.n_days = len(self.dates)

    def generate_wave(self, pattern_type, base_vol, noise_level):
        """Generates a time series wave based on pattern type."""
        x = np.arange(self.n_days)
        
        # Base components
        seasonality = np.sin(x * 2 * np.pi / 365) # Annual cycle
        weekly = np.sin(x * 2 * np.pi / 7)        # Weekly cycle
        trend = np.linspace(0, 0.5, self.n_days)  # Slight upward trend
        
        if pattern_type == "seasonal":
            # Strong Q4 peak (Oct-Dec)
            q4_spike = np.exp(-((x % 365 - 320)**2) / (2 * 20**2)) * 3
            y = base_vol + (base_vol * 0.5 * seasonality) + (base_vol * q4_spike)
            
        elif pattern_type == "trend_seasonal":
            # Growing trend + seasonality
            y = base_vol * (1 + trend) + (base_vol * 0.3 * seasonality)
            
        elif pattern_type == "steady":
            # Very consistent, slight weekly pattern
            y = base_vol + (base_vol * 0.05 * weekly)
            
        elif pattern_type == "erratic":
            # High random noise, occasional spikes
            random_spikes = np.random.exponential(scale=base_vol, size=self.n_days) * 0.5
            y = base_vol + random_spikes
            noise_level *= 2.0 # Double noise
            
        else: # Variable
            y = base_vol + (base_vol * 0.2 * seasonality) + (base_vol * 0.1 * weekly)

        # Add noise
        noise = np.random.normal(0, base_vol * noise_level, self.n_days)
        y = y + noise
        
        # Ensure non-negative (initially)
        y = np.maximum(0, y)
        return y

    def generate_pricing_promo(self, base_price, demand_series):
        """Generates price and promo columns correlated with demand."""
        # Base price with small random fluctuation
        price = np.random.normal(base_price, base_price * 0.02, self.n_days)
        
        # Create promotions (binary)
        # 5% chance of promo on any day
        promo = np.random.choice([0, 1], size=self.n_days, p=[0.95, 0.05])
        
        # Promo logic: Price drops 20%, Demand increases 30-50%
        price = np.where(promo == 1, price * 0.8, price)
        
        # Adjust demand based on promo (injecting signal for Feature Engineering)
        promo_lift = np.random.uniform(1.3, 1.5, self.n_days)
        demand_series = np.where(promo == 1, demand_series * promo_lift, demand_series)
        
        return price, promo, demand_series

    def create_dataset(self):
        print(f"🚀 Generating data for {self.config['num_skus']} SKUs over {self.config['duration_days']} days...")
        
        all_data = []
        
        # Calculate counts per tier
        n_a = int(self.config["num_skus"] * TIER_DIST["A"])
        n_b = int(self.config["num_skus"] * TIER_DIST["B"])
        n_c = self.config["num_skus"] - n_a - n_b
        
        sku_configs = []
        
        # Define SKU profiles
        for i in range(self.config["num_skus"]):
            if i < n_a:
                tier, vol = "A", np.random.randint(500, 2000)
            elif i < n_a + n_b:
                tier, vol = "B", np.random.randint(50, 499)
            else:
                tier, vol = "C", np.random.randint(5, 49)
            
            cat_name = random.choice(list(CATEGORIES.keys()))
            pattern = CATEGORIES[cat_name]
            
            # Override pattern for C-items to be intermittent/erratic often
            if tier == "C" and random.random() > 0.5:
                pattern = "erratic"
                
            sku_configs.append({
                "sku": f"SKU_{i+1:04d}",
                "tier": tier,
                "vol": vol,
                "cat": cat_name,
                "pattern": pattern
            })

        # Generate Data
        for conf in sku_configs:
            # Generate base quantity
            qty = self.generate_wave(conf['pattern'], conf['vol'], noise_level=0.15)
            
            # Generate Price/Promo
            base_price = np.random.uniform(10, 200)
            price, promo, qty = self.generate_pricing_promo(base_price, qty)
            
            # C-Item Specific: Intermittency (Zero inflation)
            if conf['tier'] == "C":
                mask = np.random.choice([0, 1], size=self.n_days, p=[0.4, 0.6]) # 40% zeros
                qty = qty * mask
            
            # Create DataFrame for this SKU
            df = pd.DataFrame({
                'trx_date': self.dates, # Intentionally not just "date" to test detector
                'product_id': conf['sku'], # Intentionally not just "sku"
                'category_group': conf['cat'],
                'sales_qty': np.round(qty).astype(int),
                'unit_price': np.round(price, 2),
                'is_promo': promo
            })
            
            all_data.append(df)
            
        full_df = pd.concat(all_data, ignore_index=True)
        
        # ====================================================================
        # INJECT DATA HEALTH ISSUES (Testing Data Tab)
        # ====================================================================
        print("💉 Injecting data health issues and anomalies...")
        
        n_rows = len(full_df)
        
        # 1. Missing Values (random 1%)
        indices = np.random.choice(full_df.index, int(n_rows * 0.01), replace=False)
        full_df.loc[indices, 'sales_qty'] = np.nan
        
        # 2. Negative Values (Returns - random 0.5%)
        indices = np.random.choice(full_df.index, int(n_rows * 0.005), replace=False)
        full_df.loc[indices, 'sales_qty'] = full_df.loc[indices, 'sales_qty'] * -1
        
        # 3. Duplicates (Duplicate 0.5% of rows)
        duplicates = full_df.sample(frac=0.005)
        full_df = pd.concat([full_df, duplicates], ignore_index=True)
        
        # 4. Outliers (Anomalies) - Massive spikes
        # Pick 5 A-tier items to give massive spikes
        a_skus = [c['sku'] for c in sku_configs if c['tier'] == "A"][:5]
        for sku in a_skus:
            sku_indices = full_df[full_df['product_id'] == sku].index
            spike_idx = np.random.choice(sku_indices, 3, replace=False)
            full_df.loc[spike_idx, 'sales_qty'] = full_df.loc[spike_idx, 'sales_qty'] * 10 # 10x spike
            
        # 5. Gaps (Missing dates)
        # Drop a chunk of dates for a specific SKU
        gap_sku = sku_configs[0]['sku']
        gap_start = self.dates[100]
        gap_end = self.dates[110]
        full_df = full_df[~((full_df['product_id'] == gap_sku) & 
                            (full_df['trx_date'] >= gap_start) & 
                            (full_df['trx_date'] <= gap_end))]

        return full_df

    def save_files(self, df):
        # 1. Save Main CSV
        print(f"💾 Saving CSV to {self.config['output_csv']}...")
        df.to_csv(self.config['output_csv'], index=False)
        
        # 2. Save Multi-sheet Excel (to test sheet selection dialog)
        # We will split data: Sheet 1 (Data), Sheet 2 (Reference/Junk)
        print(f"💾 Saving Excel to {self.config['output_excel']} (this might take a moment)...")
        
        # Limit Excel rows to 100k to keep file size manageable for testing
        excel_df = df.head(100000) 
        
        with pd.ExcelWriter(self.config['output_excel']) as writer:
            excel_df.to_excel(writer, sheet_name='Historical_Sales', index=False)
            
            # Create a reference sheet (metadata)
            ref_data = pd.DataFrame([
                {"Code": "A", "Desc": "High Vol"},
                {"Code": "B", "Desc": "Med Vol"}
            ])
            ref_data.to_excel(writer, sheet_name='Reference_Codes', index=False)
            
        print("✅ Done! Test datasets created.")

# ============================================================================
#                               MAIN
# ============================================================================

if __name__ == "__main__":
    generator = DataGenerator(CONFIG)
    dataset = generator.create_dataset()
    generator.save_files(dataset)
    
    print("\n" + "="*60)
    print("TESTING INSTRUCTIONS FOR STOCKSIGHT")
    print("="*60)
    print("1. Open App -> Data Health Tab")
    print(f"   - Upload '{CONFIG['output_csv']}'")
    print(f"   - Upload '{CONFIG['output_excel']}' to test Sheet Selection Dialog.")
    print("   - Notice 'trx_date' and 'product_id' mapped automatically.")
    print("   - Check Data Quality: You should see ~1% missing, negatives, and duplicates.")
    print("   - Click 'Apply Recommended Fixes'.")
    print("\n2. Pattern Discovery Tab")
    print("   - Run Clustering.")
    print("   - Check Navigator: 'Seasonal_Decor' items should show Seasonal patterns.")
    print("   - Click 'Detect Anomalies': Should find the 10x spikes injected into A-items.")
    print("\n3. Feature Engineering Tab")
    print("   - Select 'All 20 Features'.")
    print("   - Notice 'promo_flag' and 'price_change' should have high importance.")
    print("\n4. Forecast Factory")
    print("   - Run 'Balanced' strategy.")
    print("   - Check A-items (SKU_0001 to SKU_0005) for outlier handling.")
    print("="*60)