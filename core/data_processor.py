"""
data processor module
handles data loading cleaning validation
manages dataframe operations for large datasets
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import gc

import config


# ============================================================================
#                             DATA PROCESSOR
# ============================================================================

class DataProcessor:
    # main data processing class for stocksight
    
    def __init__(self):
        # initialize processor with empty state
        self.raw_data = None
        self.processed_data = None
        self.column_mapping = {}
        self.data_quality = {}
        self.sku_list = []
        self.category_list = []
        
    # ---------- FILE LOADING ----------
    
    def load_file(self, 
                  file_path: str, 
                  sheet_name: Optional[str] = None,
                  progress_callback: Optional[callable] = None) -> Tuple[bool, str]:
        # load data file with appropriate reader
        path = Path(file_path)
        
        if not path.exists():
            return False, "file not found"
        
        # check file size
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > config.MAX_FILE_SIZE_MB:
            return False, f"file too large: {size_mb:.0f}mb exceeds {config.MAX_FILE_SIZE_MB}mb limit"
        
        try:
            # report progress
            if progress_callback:
                progress_callback(10, "reading file")
            
            # load based on extension
            suffix = path.suffix.lower()
            
            if suffix == ".csv":
                self.raw_data = self._load_csv(path, progress_callback)
            elif suffix in [".xlsx", ".xls"]:
                self.raw_data = self._load_excel(path, sheet_name, progress_callback)
            elif suffix == ".parquet":
                self.raw_data = self._load_parquet(path, progress_callback)
            else:
                return False, f"unsupported file type: {suffix}"
            
            # report progress
            if progress_callback:
                progress_callback(80, "validating data")
            
            # basic validation
            if self.raw_data.empty:
                return False, "file is empty"
            
            if progress_callback:
                progress_callback(100, "complete")
            
            return True, f"loaded {len(self.raw_data):,} rows"
            
        except Exception as e:
            return False, f"error loading file: {str(e)}"
    
    def _load_csv(self, path: Path, progress_callback: Optional[callable] = None) -> pd.DataFrame:
        # load csv with chunking for large files
        size_mb = path.stat().st_size / (1024 * 1024)
        
        if size_mb > 100:
            # use chunked reading for large files
            chunks = []
            chunk_size = config.PERFORMANCE["chunk_size"] * 100
            total_chunks = int(size_mb / 10) + 1  # estimate
            
            for i, chunk in enumerate(pd.read_csv(path, chunksize=chunk_size)):
                chunks.append(chunk)
                if progress_callback:
                    pct = min(70, 10 + int((i / total_chunks) * 60))
                    progress_callback(pct, f"reading chunk {i+1}")
            
            return pd.concat(chunks, ignore_index=True)
        else:
            if progress_callback:
                progress_callback(50, "parsing csv")
            return pd.read_csv(path)
    
    def _load_excel(self, 
                    path: Path, 
                    sheet_name: Optional[str] = None,
                    progress_callback: Optional[callable] = None) -> pd.DataFrame:
        # load excel file with optional sheet selection
        if progress_callback:
            progress_callback(50, "parsing excel")
        
        # if sheet name provided, load that sheet
        if sheet_name:
            return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
        
        # otherwise load first sheet (default behavior)
        return pd.read_excel(path, engine="openpyxl")
    
    def _load_parquet(self, path: Path, progress_callback: Optional[callable] = None) -> pd.DataFrame:
        # load parquet file
        if progress_callback:
            progress_callback(50, "parsing parquet")
        return pd.read_parquet(path)
    
    def get_excel_sheet_info(self, file_path: str) -> Dict[str, int]:
        # get sheet names and row counts for excel file
        path = Path(file_path)
        
        if not path.exists():
            return {}
        
        if path.suffix.lower() not in [".xlsx", ".xls"]:
            return {}
        
        try:
            # read excel file to get sheet names
            xlsx = pd.ExcelFile(path, engine="openpyxl")
            sheet_info = {}
            
            for sheet_name in xlsx.sheet_names:
                # get row count without loading entire sheet
                try:
                    # read just header to get structure
                    df_sample = pd.read_excel(
                        xlsx, 
                        sheet_name=sheet_name, 
                        nrows=0
                    )
                    
                    # count rows efficiently
                    df_count = pd.read_excel(
                        xlsx,
                        sheet_name=sheet_name,
                        usecols=[0]  # only first column
                    )
                    sheet_info[sheet_name] = len(df_count)
                except Exception:
                    sheet_info[sheet_name] = 0
            
            return sheet_info
            
        except Exception:
            return {}
    
    def has_multiple_sheets(self, file_path: str) -> bool:
        # check if excel file has multiple sheets
        sheet_info = self.get_excel_sheet_info(file_path)
        return len(sheet_info) > 1
    
    # ---------- COLUMN MAPPING ----------
    
    def set_column_mapping(self, mapping: Dict[str, str]) -> None:
        # set column mapping from detection or user input
        self.column_mapping = mapping.copy()
    
    def get_mapped_column(self, column_type: str) -> Optional[str]:
        # get actual column name for column type
        return self.column_mapping.get(column_type)
    
    # ---------- DATA PROCESSING ----------
    
    def process_data(self, progress_callback: Optional[callable] = None) -> Tuple[bool, str]:
        # process raw data using column mapping
        if self.raw_data is None:
            return False, "no data loaded"
        
        if not self.column_mapping:
            return False, "column mapping not set"
        
        try:
            if progress_callback:
                progress_callback(10, "starting processing")
            
            # create copy for processing
            df = self.raw_data.copy()
            
            # process date column
            date_col = self.column_mapping.get("date")
            if date_col:
                if progress_callback:
                    progress_callback(20, "processing dates")
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                df = df.dropna(subset=[date_col])
                df = df.sort_values(date_col)
            
            # process quantity column
            qty_col = self.column_mapping.get("quantity")
            if qty_col:
                if progress_callback:
                    progress_callback(40, "processing quantities")
                df[qty_col] = pd.to_numeric(df[qty_col], errors="coerce")
            
            # process sku column
            sku_col = self.column_mapping.get("sku")
            if sku_col:
                if progress_callback:
                    progress_callback(60, "processing items")
                df[sku_col] = df[sku_col].astype(str).str.strip()
                self.sku_list = df[sku_col].unique().tolist()
            
            # process category column
            cat_col = self.column_mapping.get("category")
            if cat_col:
                if progress_callback:
                    progress_callback(70, "processing categories")
                df[cat_col] = df[cat_col].astype(str).str.strip()
                self.category_list = df[cat_col].unique().tolist()
            elif sku_col:
                # create category from sku prefix
                df["auto_category"] = df[sku_col].str[:3]
                self.column_mapping["category"] = "auto_category"
                self.category_list = df["auto_category"].unique().tolist()
            
            # process price column if exists
            price_col = self.column_mapping.get("price")
            if price_col:
                if progress_callback:
                    progress_callback(80, "processing prices")
                df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
            
            # process promo column if exists
            promo_col = self.column_mapping.get("promo")
            if promo_col:
                if progress_callback:
                    progress_callback(90, "processing promotions")
                df[promo_col] = df[promo_col].fillna(0).astype(int)
            
            self.processed_data = df
            
            if progress_callback:
                progress_callback(100, "complete")
            
            return True, f"processed {len(df):,} rows with {len(self.sku_list):,} items"
            
        except Exception as e:
            return False, f"error processing data: {str(e)}"
    
    # ---------- DATA QUALITY ----------
    
    def calculate_quality(self, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        # calculate data quality metrics
        if self.processed_data is None:
            return {"overall_score": 0, "issues": ["no data processed"]}
        
        df = self.processed_data
        quality = {
            "overall_score": 100,
            "metrics": {},
            "issues": [],
            "recommendations": []
        }
        
        if progress_callback:
            progress_callback(20, "checking missing values")
        
        # check missing values
        missing_pct = (df.isnull().sum().sum() / df.size) * 100
        quality["metrics"]["missing_data"] = {
            "value": missing_pct,
            "status": "good" if missing_pct < 5 else "warning" if missing_pct < 15 else "critical"
        }
        if missing_pct > 5:
            quality["issues"].append(f"{missing_pct:.1f}% missing values detected")
            quality["recommendations"].append("fill missing values with forward fill or interpolation")
            quality["overall_score"] -= min(20, missing_pct)
        
        if progress_callback:
            progress_callback(40, "checking duplicates")
        
        # check duplicates
        sku_col = self.column_mapping.get("sku")
        date_col = self.column_mapping.get("date")
        if sku_col and date_col:
            dup_count = df.duplicated(subset=[sku_col, date_col]).sum()
            dup_pct = (dup_count / len(df)) * 100
            quality["metrics"]["duplicates"] = {
                "value": dup_pct,
                "status": "good" if dup_pct == 0 else "warning" if dup_pct < 5 else "critical"
            }
            if dup_count > 0:
                quality["issues"].append(f"{dup_count:,} duplicate entries found")
                quality["recommendations"].append("aggregate duplicates by sum or average")
                quality["overall_score"] -= min(15, dup_pct * 2)
        
        if progress_callback:
            progress_callback(60, "checking negative values")
        
        # check negative values
        qty_col = self.column_mapping.get("quantity")
        if qty_col:
            neg_count = (df[qty_col] < 0).sum()
            neg_pct = (neg_count / len(df)) * 100
            quality["metrics"]["negative_values"] = {
                "value": neg_pct,
                "status": "good" if neg_pct == 0 else "warning" if neg_pct < 2 else "critical"
            }
            if neg_count > 0:
                quality["issues"].append(f"{neg_count:,} negative quantity values")
                quality["recommendations"].append("review negative values - may indicate returns")
                quality["overall_score"] -= min(10, neg_pct * 3)
        
        if progress_callback:
            progress_callback(80, "checking data coverage")
        
        # check data coverage
        if date_col and sku_col:
            date_range = (df[date_col].max() - df[date_col].min()).days
            points_per_sku = len(df) / len(self.sku_list) if self.sku_list else 0
            quality["metrics"]["data_coverage"] = {
                "date_range_days": date_range,
                "avg_points_per_item": points_per_sku,
                "status": "good" if points_per_sku >= 12 else "warning" if points_per_sku >= 7 else "critical"
            }
            if points_per_sku < config.DATA_QUALITY["min_data_points"]:
                quality["issues"].append(f"low data points per item: {points_per_sku:.1f} (minimum recommended: {config.DATA_QUALITY['min_data_points']})")
                quality["recommendations"].append("consider weekly or monthly aggregation")
                quality["overall_score"] -= 10
        
        # ensure score is in valid range
        quality["overall_score"] = max(0, min(100, quality["overall_score"]))
        
        self.data_quality = quality
        
        if progress_callback:
            progress_callback(100, "complete")
        
        return quality
    
    # ---------- DATA CLEANING ----------
    
    def apply_fix(self, fix_type: str, progress_callback: Optional[callable] = None, **kwargs) -> Tuple[bool, str]:
        # apply data fix based on type
        if self.processed_data is None:
            return False, "no data to fix"
        
        try:
            df = self.processed_data
            
            if fix_type == "fill_missing":
                if progress_callback:
                    progress_callback(50, "filling missing values")
                method = kwargs.get("method", "ffill")
                df = df.fillna(method=method)
                self.processed_data = df
                return True, "filled missing values"
            
            elif fix_type == "remove_duplicates":
                if progress_callback:
                    progress_callback(50, "removing duplicates")
                sku_col = self.column_mapping.get("sku")
                date_col = self.column_mapping.get("date")
                qty_col = self.column_mapping.get("quantity")
                
                if sku_col and date_col and qty_col:
                    # aggregate duplicates
                    agg_dict = {qty_col: "sum"}
                    # include other columns
                    for col in df.columns:
                        if col not in [sku_col, date_col, qty_col]:
                            agg_dict[col] = "first"
                    
                    df = df.groupby([sku_col, date_col]).agg(agg_dict).reset_index()
                    self.processed_data = df
                    return True, "aggregated duplicate entries"
                return False, "required columns not mapped"
            
            elif fix_type == "fix_negatives":
                if progress_callback:
                    progress_callback(50, "fixing negative values")
                qty_col = self.column_mapping.get("quantity")
                method = kwargs.get("method", "zero")
                
                if qty_col:
                    if method == "zero":
                        df.loc[df[qty_col] < 0, qty_col] = 0
                    elif method == "absolute":
                        df[qty_col] = df[qty_col].abs()
                    self.processed_data = df
                    return True, f"fixed negative values using {method} method"
                return False, "quantity column not mapped"
            
            elif fix_type == "remove_outliers":
                if progress_callback:
                    progress_callback(50, "removing outliers")
                qty_col = self.column_mapping.get("quantity")
                threshold = kwargs.get("threshold", 3.0)
                
                if qty_col:
                    mean = df[qty_col].mean()
                    std = df[qty_col].std()
                    lower = mean - threshold * std
                    upper = mean + threshold * std
                    
                    outlier_count = ((df[qty_col] < lower) | (df[qty_col] > upper)).sum()
                    df = df[(df[qty_col] >= lower) & (df[qty_col] <= upper)]
                    self.processed_data = df
                    return True, f"removed {outlier_count:,} outliers"
                return False, "quantity column not mapped"
            
            else:
                return False, f"unknown fix type: {fix_type}"
                
        except Exception as e:
            return False, f"error applying fix: {str(e)}"
    
    # ---------- SKU CLASSIFICATION ----------
    
    def classify_skus(self, progress_callback: Optional[callable] = None) -> Dict[str, List[str]]:
        # classify skus into a b c categories using pareto principle
        if self.processed_data is None:
            return {"A": [], "B": [], "C": []}
        
        sku_col = self.column_mapping.get("sku")
        qty_col = self.column_mapping.get("quantity")
        
        if not sku_col or not qty_col:
            return {"A": [], "B": [], "C": []}
        
        if progress_callback:
            progress_callback(30, "calculating volumes")
        
        # calculate total volume per sku
        sku_volume = self.processed_data.groupby(sku_col)[qty_col].sum().sort_values(ascending=False)
        
        if progress_callback:
            progress_callback(60, "classifying items")
        
        # calculate cumulative percentage
        total_volume = sku_volume.sum()
        cumulative_pct = (sku_volume.cumsum() / total_volume * 100).values
        
        # classify based on cumulative contribution
        a_threshold = config.CLUSTERING["volume_percentiles"]["A"]
        b_threshold = config.CLUSTERING["volume_percentiles"]["B"]
        
        classification = {"A": [], "B": [], "C": []}
        
        for i, (sku, volume) in enumerate(sku_volume.items()):
            if cumulative_pct[i] <= a_threshold:
                classification["A"].append(sku)
            elif cumulative_pct[i] <= a_threshold + b_threshold:
                classification["B"].append(sku)
            else:
                classification["C"].append(sku)
        
        if progress_callback:
            progress_callback(100, "complete")
        
        return classification
    
    # ---------- DATA ACCESS ----------
    
    def get_sku_data(self, sku: str) -> pd.DataFrame:
        # get time series data for single sku
        if self.processed_data is None:
            return pd.DataFrame()
        
        sku_col = self.column_mapping.get("sku")
        if not sku_col:
            return pd.DataFrame()
        
        return self.processed_data[self.processed_data[sku_col] == sku].copy()
    
    def get_sku_sample(self, n: int = 20, stratified: bool = True) -> List[str]:
        # get sample of skus for visualization
        if not self.sku_list:
            return []
        
        if len(self.sku_list) <= n:
            return self.sku_list.copy()
        
        if stratified:
            # sample from each abc category
            classification = self.classify_skus()
            sample = []
            per_class = n // 3
            
            for tier in ["A", "B", "C"]:
                tier_skus = classification[tier]
                if tier_skus:
                    sample_size = min(per_class, len(tier_skus))
                    sample.extend(np.random.choice(tier_skus, sample_size, replace=False).tolist())
            
            return sample[:n]
        else:
            return np.random.choice(self.sku_list, n, replace=False).tolist()
    
    def get_summary_stats(self) -> Dict[str, Any]:
        # get summary statistics for loaded data
        if self.processed_data is None:
            return {}
        
        df = self.processed_data
        date_col = self.column_mapping.get("date")
        qty_col = self.column_mapping.get("quantity")
        
        stats = {
            "total_rows": len(df),
            "total_skus": len(self.sku_list),
            "total_categories": len(self.category_list),
            "columns": list(df.columns)
        }
        
        if date_col and date_col in df.columns:
            stats["date_range"] = {
                "start": df[date_col].min().strftime("%Y-%m-%d"),
                "end": df[date_col].max().strftime("%Y-%m-%d"),
                "days": (df[date_col].max() - df[date_col].min()).days
            }
        
        if qty_col and qty_col in df.columns:
            stats["quantity"] = {
                "total": float(df[qty_col].sum()),
                "mean": float(df[qty_col].mean()),
                "median": float(df[qty_col].median()),
                "std": float(df[qty_col].std())
            }
        
        return stats
    
    # ---------- MEMORY MANAGEMENT ----------
    
    def clear_raw_data(self) -> None:
        # clear raw data to free memory
        self.raw_data = None
        gc.collect()
    
    def get_memory_usage(self) -> float:
        # get memory usage in mb
        total = 0
        if self.raw_data is not None:
            total += self.raw_data.memory_usage(deep=True).sum()
        if self.processed_data is not None:
            total += self.processed_data.memory_usage(deep=True).sum()
        return total / (1024 * 1024)