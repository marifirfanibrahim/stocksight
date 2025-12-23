"""
feature engineer module
creates curated features for forecasting
manages feature sets for different sku tiers
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

import config


# ============================================================================
#                           FEATURE ENGINEER
# ============================================================================

class FeatureEngineer:
    # creates and manages forecasting features
    
    def __init__(self):
        # initialize with feature configuration
        self.feature_config = config.FEATURES
        self.feature_descriptions = config.FEATURE_DESCRIPTIONS
        self.computed_features = {}
        self.feature_importance = {}
    
    # ---------- FEATURE CREATION ----------
    
    def create_features(self, 
                        df: pd.DataFrame, 
                        date_col: str, 
                        qty_col: str,
                        feature_set: str = "all_20",
                        price_col: Optional[str] = None,
                        promo_col: Optional[str] = None) -> pd.DataFrame:
        # create features for time series data
        
        result = df.copy()
        
        # ensure date is datetime
        result[date_col] = pd.to_datetime(result[date_col])
        result = result.sort_values(date_col)
        
        # determine which features to create
        if feature_set == "all_20":
            features_to_create = self.feature_config["curated"]
        elif feature_set == "top_10":
            features_to_create = self.feature_config["top_10"]
        elif feature_set == "basic_5":
            features_to_create = self.feature_config["basic_5"]
        else:
            features_to_create = self.feature_config["curated"]
        
        # create each feature
        for feature in features_to_create:
            try:
                if feature.startswith("lag_"):
                    result = self._create_lag_feature(result, qty_col, feature)
                elif feature.startswith("rolling_mean_"):
                    result = self._create_rolling_mean(result, qty_col, feature)
                elif feature.startswith("rolling_std_"):
                    result = self._create_rolling_std(result, qty_col, feature)
                elif feature in ["year", "month", "week_of_year", "day_of_week"]:
                    result = self._create_date_feature(result, date_col, feature)
                elif feature == "is_weekend":
                    result = self._create_weekend_feature(result, date_col)
                elif feature == "is_holiday":
                    result = self._create_holiday_feature(result, date_col)
                elif feature == "days_to_holiday":
                    result = self._create_days_to_holiday(result, date_col)
                elif feature == "price_change_pct" and price_col:
                    result = self._create_price_change(result, price_col)
                elif feature == "price_relative_to_avg" and price_col:
                    result = self._create_price_relative(result, price_col)
                elif feature == "promo_flag" and promo_col:
                    result = self._create_promo_flag(result, promo_col)
                elif feature == "promo_intensity" and promo_col:
                    result = self._create_promo_intensity(result, promo_col)
                elif feature == "seasonal_index":
                    result = self._create_seasonal_index(result, date_col, qty_col)
                elif feature == "trend_component":
                    result = self._create_trend_component(result, qty_col)
            except Exception as e:
                # skip feature if creation fails
                continue
        
        return result
    
    # ---------- LAG FEATURES ----------
    
    def _create_lag_feature(self, df: pd.DataFrame, qty_col: str, feature: str) -> pd.DataFrame:
        # create lag feature
        lag_period = int(feature.split("_")[1])
        df[feature] = df[qty_col].shift(lag_period)
        return df
    
    # ---------- ROLLING FEATURES ----------
    
    def _create_rolling_mean(self, df: pd.DataFrame, qty_col: str, feature: str) -> pd.DataFrame:
        # create rolling mean feature
        window = int(feature.split("_")[2])
        df[feature] = df[qty_col].rolling(window=window, min_periods=1).mean()
        return df
    
    def _create_rolling_std(self, df: pd.DataFrame, qty_col: str, feature: str) -> pd.DataFrame:
        # create rolling std feature
        window = int(feature.split("_")[2])
        df[feature] = df[qty_col].rolling(window=window, min_periods=1).std()
        return df
    
    # ---------- DATE FEATURES ----------
    
    def _create_date_feature(self, df: pd.DataFrame, date_col: str, feature: str) -> pd.DataFrame:
        # create date based feature
        if feature == "year":
            df[feature] = df[date_col].dt.year
        elif feature == "month":
            df[feature] = df[date_col].dt.month
        elif feature == "week_of_year":
            df[feature] = df[date_col].dt.isocalendar().week.astype(int)
        elif feature == "day_of_week":
            df[feature] = df[date_col].dt.dayofweek
        return df
    
    def _create_weekend_feature(self, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        # create weekend indicator
        df["is_weekend"] = df[date_col].dt.dayofweek.isin([5, 6]).astype(int)
        return df
    
    # ---------- HOLIDAY FEATURES ----------
    
    def _create_holiday_feature(self, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        # create holiday indicator using common holidays
        holidays = self._get_common_holidays(df[date_col].dt.year.unique())
        df["is_holiday"] = df[date_col].dt.date.isin(holidays).astype(int)
        return df
    
    def _create_days_to_holiday(self, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        # create days until next holiday feature
        holidays = self._get_common_holidays(df[date_col].dt.year.unique())
        holidays = sorted(holidays)
        
        def days_to_next_holiday(date):
            date = date.date() if hasattr(date, "date") else date
            for h in holidays:
                if h >= date:
                    return (h - date).days
            return 365
        
        df["days_to_holiday"] = df[date_col].apply(days_to_next_holiday)
        return df
    
    def _get_common_holidays(self, years: List[int]) -> List:
        # get common us holidays for years
        from datetime import date
        holidays = []
        
        for year in years:
            # fixed holidays
            holidays.extend([
                date(year, 1, 1),   # new years
                date(year, 7, 4),   # july 4th
                date(year, 12, 25), # christmas
                date(year, 12, 31), # new years eve
            ])
            
            # approximate thanksgiving (4th thursday november)
            nov_first = date(year, 11, 1)
            days_until_thursday = (3 - nov_first.weekday()) % 7
            thanksgiving = nov_first + timedelta(days=days_until_thursday + 21)
            holidays.append(thanksgiving)
            
            # black friday
            holidays.append(thanksgiving + timedelta(days=1))
        
        return holidays
    
    # ---------- PRICE FEATURES ----------
    
    def _create_price_change(self, df: pd.DataFrame, price_col: str) -> pd.DataFrame:
        # create price change percentage
        df["price_change_pct"] = df[price_col].pct_change().fillna(0)
        return df
    
    def _create_price_relative(self, df: pd.DataFrame, price_col: str) -> pd.DataFrame:
        # create price relative to average
        avg_price = df[price_col].mean()
        df["price_relative_to_avg"] = df[price_col] / avg_price if avg_price > 0 else 1
        return df
    
    # ---------- PROMO FEATURES ----------
    
    def _create_promo_flag(self, df: pd.DataFrame, promo_col: str) -> pd.DataFrame:
        # create binary promo flag
        df["promo_flag"] = (df[promo_col] > 0).astype(int)
        return df
    
    def _create_promo_intensity(self, df: pd.DataFrame, promo_col: str) -> pd.DataFrame:
        # create promo intensity normalized
        max_promo = df[promo_col].max()
        df["promo_intensity"] = df[promo_col] / max_promo if max_promo > 0 else 0
        return df
    
    # ---------- SEASONAL FEATURES ----------
    
    def _create_seasonal_index(self, df: pd.DataFrame, date_col: str, qty_col: str) -> pd.DataFrame:
        # create seasonal index based on monthly averages
        df["_month"] = df[date_col].dt.month
        monthly_avg = df.groupby("_month")[qty_col].transform("mean")
        overall_avg = df[qty_col].mean()
        df["seasonal_index"] = monthly_avg / overall_avg if overall_avg > 0 else 1
        df = df.drop("_month", axis=1)
        return df
    
    def _create_trend_component(self, df: pd.DataFrame, qty_col: str) -> pd.DataFrame:
        # create trend component using simple regression
        n = len(df)
        if n < 2:
            df["trend_component"] = 0
            return df
        
        x = np.arange(n)
        y = df[qty_col].fillna(0).values
        
        # simple linear regression
        slope = np.cov(x, y)[0, 1] / np.var(x) if np.var(x) > 0 else 0
        df["trend_component"] = slope * x
        return df
    
    # ---------- FEATURE SELECTION ----------
    
    def get_feature_set_for_tier(self, tier: str) -> str:
        # get appropriate feature set for sku tier
        return self.feature_config["group_config"].get(tier, "all_20")
    
    def get_feature_importance(self, 
                               df: pd.DataFrame, 
                               target_col: str, 
                               feature_cols: List[str]) -> Dict[str, float]:
        # calculate feature importance using correlation
        importance = {}
        
        for col in feature_cols:
            if col in df.columns and col != target_col:
                # use absolute correlation as importance
                corr = df[col].corr(df[target_col])
                importance[col] = abs(corr) if not np.isnan(corr) else 0
        
        # normalize to sum to 1
        total = sum(importance.values())
        if total > 0:
            importance = {k: v/total for k, v in importance.items()}
        
        # sort by importance
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        
        self.feature_importance = importance
        return importance
    
    def get_feature_summary(self, feature_cols: List[str]) -> List[Dict]:
        # get human readable feature summary
        summary = []
        
        for feature in feature_cols:
            importance = self.feature_importance.get(feature, 0)
            description = self.feature_descriptions.get(feature, "custom feature")
            
            summary.append({
                "feature": feature,
                "importance": importance,
                "importance_pct": f"{importance * 100:.1f}%",
                "description": description
            })
        
        return summary
    
    # ---------- BATCH PROCESSING ----------
    
    def create_features_batch(self,
                              df: pd.DataFrame,
                              sku_col: str,
                              date_col: str,
                              qty_col: str,
                              tier_mapping: Dict[str, str],
                              price_col: Optional[str] = None,
                              promo_col: Optional[str] = None,
                              progress_callback: Optional[callable] = None,
                              parallel: bool = False,
                              max_workers: int = 4,
                              use_processes: bool = False) -> pd.DataFrame:
        # create features for all skus with tier-appropriate feature sets
        
        results = []
        grouped = df.groupby(sku_col)
        total = len(grouped)

        if parallel and max_workers and max_workers > 1:
            # support threaded or process-based parallelism
            if use_processes:
                from concurrent.futures import ProcessPoolExecutor, as_completed

                futures = {}
                with ProcessPoolExecutor(max_workers=max_workers) as exe:
                    for sku, sku_df in grouped:
                        sku_df = sku_df.copy()
                        tier = tier_mapping.get(sku, "C")
                        feature_set = self.get_feature_set_for_tier(tier)
                        # send minimal args to worker (function is picklable)
                        futures[exe.submit(self.create_features, sku_df, date_col, qty_col, feature_set, price_col, promo_col)] = sku

                    for fut in as_completed(futures):
                        sku = futures[fut]
                        try:
                            featured_df = fut.result()
                            results.append(featured_df)
                        except Exception:
                            continue

                        if progress_callback:
                            percent = len(results) / total * 100
                            progress_callback(percent, sku)

                if results:
                    return pd.concat(results, ignore_index=True)
                return pd.DataFrame()
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed

                futures = {}
                with ThreadPoolExecutor(max_workers=max_workers) as exe:
                    for sku, sku_df in grouped:
                        sku_df = sku_df.copy()
                        tier = tier_mapping.get(sku, "C")
                        feature_set = self.get_feature_set_for_tier(tier)
                        futures[exe.submit(self.create_features, sku_df, date_col, qty_col, feature_set, price_col, promo_col)] = sku

                    for fut in as_completed(futures):
                        sku = futures[fut]
                        try:
                            featured_df = fut.result()
                            results.append(featured_df)
                        except Exception:
                            continue

                        if progress_callback:
                            percent = len(results) / total * 100
                            progress_callback(percent, sku)

                if results:
                    return pd.concat(results, ignore_index=True)
                return pd.DataFrame()

        for i, (sku, sku_df) in enumerate(grouped):
            sku_df = sku_df.copy()

            # determine feature set based on tier
            tier = tier_mapping.get(sku, "C")
            feature_set = self.get_feature_set_for_tier(tier)

            # create features
            featured_df = self.create_features(
                sku_df, date_col, qty_col, feature_set, price_col, promo_col
            )

            results.append(featured_df)

            # progress callback with standardized signature (percent, sku)
            if progress_callback:
                percent = (i + 1) / total * 100
                progress_callback(percent, sku)

        if results:
            return pd.concat(results, ignore_index=True)
        return pd.DataFrame()