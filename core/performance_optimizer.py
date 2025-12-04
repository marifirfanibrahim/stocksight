"""
performance optimizer module
manages memory and processing for large datasets
handles chunking and caching strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Generator
import gc
import sys
from functools import lru_cache

import config


# ============================================================================
#                        PERFORMANCE OPTIMIZER
# ============================================================================

class PerformanceOptimizer:
    # optimizes processing for large sku datasets
    
    def __init__(self):
        # initialize with performance configuration
        self.config = config.PERFORMANCE
        self.cache = {}
        self.memory_log = []
    
    # ---------- MEMORY MANAGEMENT ----------
    
    def get_memory_usage(self) -> Dict[str, float]:
        # get current memory usage statistics
        import psutil
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / (1024 * 1024),
            "vms_mb": memory_info.vms / (1024 * 1024),
            "percent": process.memory_percent()
        }
    
    def check_memory_threshold(self) -> bool:
        # check if memory usage exceeds threshold
        try:
            import psutil
            usage = psutil.Process().memory_percent() / 100
            return usage > self.config["gc_threshold"]
        except Exception:
            return False
    
    def force_cleanup(self) -> None:
        # force garbage collection and cache cleanup
        self.cache.clear()
        gc.collect()
    
    def optimize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        # reduce memory usage of dataframe
        result = df.copy()
        
        for col in result.columns:
            col_type = result[col].dtype
            
            # optimize integers
            if col_type == np.int64:
                if result[col].min() >= 0:
                    if result[col].max() < 255:
                        result[col] = result[col].astype(np.uint8)
                    elif result[col].max() < 65535:
                        result[col] = result[col].astype(np.uint16)
                    elif result[col].max() < 4294967295:
                        result[col] = result[col].astype(np.uint32)
                else:
                    if result[col].min() > -128 and result[col].max() < 127:
                        result[col] = result[col].astype(np.int8)
                    elif result[col].min() > -32768 and result[col].max() < 32767:
                        result[col] = result[col].astype(np.int16)
                    elif result[col].min() > -2147483648 and result[col].max() < 2147483647:
                        result[col] = result[col].astype(np.int32)
            
            # optimize floats
            elif col_type == np.float64:
                result[col] = result[col].astype(np.float32)
            
            # optimize objects to category if low cardinality
            elif col_type == object:
                num_unique = result[col].nunique()
                num_total = len(result[col])
                if num_unique / num_total < 0.5:
                    result[col] = result[col].astype("category")
        
        return result
    
    # ---------- CHUNKED PROCESSING ----------
    
    def chunk_dataframe(self, df: pd.DataFrame, chunk_size: Optional[int] = None) -> Generator:
        # yield dataframe in chunks
        if chunk_size is None:
            chunk_size = self.config["chunk_size"]
        
        for start in range(0, len(df), chunk_size):
            yield df.iloc[start:start + chunk_size]
    
    def chunk_by_sku(self, 
                     df: pd.DataFrame, 
                     sku_col: str, 
                     chunk_size: Optional[int] = None) -> Generator:
        # yield dataframe chunks grouped by sku
        if chunk_size is None:
            chunk_size = self.config["max_skus_in_memory"]
        
        skus = df[sku_col].unique()
        
        for start in range(0, len(skus), chunk_size):
            chunk_skus = skus[start:start + chunk_size]
            yield df[df[sku_col].isin(chunk_skus)]
    
    def process_in_chunks(self,
                          df: pd.DataFrame,
                          sku_col: str,
                          process_func: callable,
                          chunk_size: Optional[int] = None,
                          progress_callback: Optional[callable] = None) -> List:
        # process dataframe in chunks with memory cleanup
        results = []
        
        skus = df[sku_col].unique()
        total_skus = len(skus)
        
        if chunk_size is None:
            chunk_size = self.config["max_skus_in_memory"]
        
        for i, start in enumerate(range(0, total_skus, chunk_size)):
            # get chunk skus
            chunk_skus = skus[start:start + chunk_size]
            chunk_df = df[df[sku_col].isin(chunk_skus)]
            
            # process chunk
            chunk_result = process_func(chunk_df)
            results.append(chunk_result)
            
            # progress callback
            if progress_callback:
                progress = min(100, (start + chunk_size) / total_skus * 100)
                progress_callback(progress)
            
            # memory cleanup between chunks
            if self.check_memory_threshold():
                self.force_cleanup()
        
        return results
    
    # ---------- CACHING ----------
    
    def cache_result(self, key: str, value: Any) -> None:
        # cache computation result
        # check cache size limit
        cache_size = sys.getsizeof(self.cache) / (1024 * 1024)
        if cache_size > self.config["cache_size_mb"]:
            # remove oldest entries
            keys_to_remove = list(self.cache.keys())[:len(self.cache) // 2]
            for k in keys_to_remove:
                del self.cache[k]
        
        self.cache[key] = value
    
    def get_cached(self, key: str) -> Optional[Any]:
        # get cached result
        return self.cache.get(key)
    
    def clear_cache(self) -> None:
        # clear all cached results
        self.cache.clear()
    
    # ---------- SAMPLING ----------
    
    def sample_skus(self, 
                    sku_list: List[str], 
                    n: int, 
                    stratify_by: Optional[Dict[str, str]] = None) -> List[str]:
        # sample skus for visualization
        if len(sku_list) <= n:
            return sku_list
        
        if stratify_by is None:
            # random sample
            return list(np.random.choice(sku_list, n, replace=False))
        
        # stratified sample
        sampled = []
        groups = {}
        
        for sku in sku_list:
            group = stratify_by.get(sku, "default")
            if group not in groups:
                groups[group] = []
            groups[group].append(sku)
        
        # sample from each group
        per_group = max(1, n // len(groups))
        
        for group, group_skus in groups.items():
            sample_size = min(per_group, len(group_skus))
            sampled.extend(np.random.choice(group_skus, sample_size, replace=False).tolist())
        
        return sampled[:n]
    
    def get_representative_sample(self,
                                   df: pd.DataFrame,
                                   sku_col: str,
                                   qty_col: str,
                                   n: int = 20) -> List[str]:
        # get representative sample across volume distribution
        # calculate sku volumes
        sku_volumes = df.groupby(sku_col)[qty_col].sum().sort_values(ascending=False)
        
        if len(sku_volumes) <= n:
            return sku_volumes.index.tolist()
        
        # sample from quantiles
        sampled = []
        quantiles = [0, 0.25, 0.5, 0.75, 1.0]
        per_quantile = n // (len(quantiles) - 1)
        
        for i in range(len(quantiles) - 1):
            lower = sku_volumes.quantile(quantiles[i])
            upper = sku_volumes.quantile(quantiles[i + 1])
            
            mask = (sku_volumes >= lower) & (sku_volumes <= upper)
            quantile_skus = sku_volumes[mask].index.tolist()
            
            if quantile_skus:
                sample_size = min(per_quantile, len(quantile_skus))
                sampled.extend(np.random.choice(quantile_skus, sample_size, replace=False).tolist())
        
        return list(set(sampled))[:n]
    
    # ---------- PARALLEL PROCESSING ----------
    
    def get_optimal_workers(self) -> int:
        # get optimal number of worker threads
        import os
        
        cpu_count = os.cpu_count() or 4
        return min(self.config["background_threads"], cpu_count - 1)
    
    # ---------- TIMING ----------
    
    def estimate_time(self, sku_count: int, operation: str) -> str:
        # estimate processing time based on sku count
        timing = config.TIMING_TARGETS
        
        if operation == "upload":
            seconds = (sku_count / 10000) * timing["upload_per_10k"]
        elif operation == "exploration":
            seconds = timing["exploration_initial"]
        elif operation == "features":
            seconds = (sku_count / 10000) * timing["feature_engineering"]
        elif operation == "simple_forecast":
            seconds = (sku_count / 10000) * timing["simple_forecast"]
        elif operation == "balanced_forecast":
            seconds = (sku_count / 10000) * timing["balanced_forecast"]
        elif operation == "advanced_forecast":
            seconds = (sku_count / 10000) * timing["advanced_forecast"]
        else:
            seconds = 60
        
        # format as human readable
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            return f"{int(seconds / 60)} minutes"
        else:
            return f"{seconds / 3600:.1f} hours"