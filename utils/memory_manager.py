"""
memory manager module
monitors and manages application memory
handles cleanup for large datasets
"""

import gc
import sys
from typing import Dict, List, Optional, Any
from functools import wraps
import weakref

import config


# ============================================================================
#                            MEMORY MANAGER
# ============================================================================

class MemoryManager:
    # manages memory for large dataset processing
    
    _instance = None
    
    def __new__(cls):
        # singleton pattern
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # initialize memory manager
        if self._initialized:
            return
        
        self.config = config.PERFORMANCE
        self.cache = {}
        self.weak_refs = {}
        self.memory_log = []
        self._initialized = True
    
    # ---------- MEMORY MONITORING ----------
    
    def get_memory_info(self) -> Dict[str, float]:
        # get current memory usage
        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            
            return {
                "rss_mb": mem_info.rss / (1024 * 1024),
                "vms_mb": mem_info.vms / (1024 * 1024),
                "percent": process.memory_percent(),
                "available_mb": psutil.virtual_memory().available / (1024 * 1024)
            }
        except ImportError:
            # fallback without psutil
            return {
                "rss_mb": 0,
                "vms_mb": 0,
                "percent": 0,
                "available_mb": 0
            }
    
    def check_memory_pressure(self) -> bool:
        # check if memory usage is high
        info = self.get_memory_info()
        threshold = self.config["gc_threshold"] * 100
        return info["percent"] > threshold
    
    def log_memory(self, label: str = "") -> None:
        # log current memory state
        info = self.get_memory_info()
        self.memory_log.append({
            "label": label,
            "rss_mb": info["rss_mb"],
            "percent": info["percent"]
        })
        
        # keep log size manageable
        if len(self.memory_log) > 100:
            self.memory_log = self.memory_log[-50:]
    
    # ---------- CLEANUP OPERATIONS ----------
    
    def force_cleanup(self) -> int:
        # force garbage collection
        self.cache.clear()
        collected = gc.collect()
        return collected
    
    def cleanup_if_needed(self) -> bool:
        # cleanup if memory pressure is high
        if self.check_memory_pressure():
            self.force_cleanup()
            return True
        return False
    
    def clear_cache(self, pattern: Optional[str] = None) -> int:
        # clear cache entries matching pattern
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            return count
        
        keys_to_remove = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_remove:
            del self.cache[key]
        return len(keys_to_remove)
    
    # ---------- CACHING ----------
    
    def cache_set(self, key: str, value: Any, weak: bool = False) -> None:
        # store value in cache
        if weak:
            try:
                self.weak_refs[key] = weakref.ref(value)
            except TypeError:
                # not all types support weak references
                self.cache[key] = value
        else:
            # check cache size
            cache_size = self._estimate_cache_size()
            if cache_size > self.config["cache_size_mb"]:
                self._evict_cache_entries()
            
            self.cache[key] = value
    
    def cache_get(self, key: str) -> Optional[Any]:
        # get value from cache
        if key in self.cache:
            return self.cache[key]
        
        if key in self.weak_refs:
            ref = self.weak_refs[key]
            value = ref()
            if value is not None:
                return value
            else:
                del self.weak_refs[key]
        
        return None
    
    def cache_has(self, key: str) -> bool:
        # check if key exists in cache
        return key in self.cache or key in self.weak_refs
    
    def _estimate_cache_size(self) -> float:
        # estimate cache size in mb
        total = 0
        for value in self.cache.values():
            total += sys.getsizeof(value)
        return total / (1024 * 1024)
    
    def _evict_cache_entries(self) -> None:
        # remove oldest cache entries
        keys = list(self.cache.keys())
        # remove first half of entries
        for key in keys[:len(keys) // 2]:
            del self.cache[key]
    
    # ---------- DATAFRAME OPTIMIZATION ----------
    
    def optimize_dataframe(self, df) -> Any:
        # reduce dataframe memory usage
        import pandas as pd
        import numpy as np
        
        result = df.copy()
        
        for col in result.columns:
            col_type = result[col].dtype
            
            if col_type == np.int64:
                # downcast integers
                c_min = result[col].min()
                c_max = result[col].max()
                
                if c_min >= 0:
                    if c_max < 255:
                        result[col] = result[col].astype(np.uint8)
                    elif c_max < 65535:
                        result[col] = result[col].astype(np.uint16)
                    elif c_max < 4294967295:
                        result[col] = result[col].astype(np.uint32)
                else:
                    if c_min > -128 and c_max < 127:
                        result[col] = result[col].astype(np.int8)
                    elif c_min > -32768 and c_max < 32767:
                        result[col] = result[col].astype(np.int16)
                    elif c_min > -2147483648 and c_max < 2147483647:
                        result[col] = result[col].astype(np.int32)
            
            elif col_type == np.float64:
                result[col] = result[col].astype(np.float32)
            
            elif col_type == object:
                num_unique = result[col].nunique()
                num_total = len(result[col])
                if num_unique / num_total < 0.5:
                    result[col] = result[col].astype("category")
        
        return result
    
    def get_dataframe_memory(self, df) -> float:
        # get dataframe memory usage in mb
        return df.memory_usage(deep=True).sum() / (1024 * 1024)


# ============================================================================
#                              DECORATORS
# ============================================================================

def memory_tracked(func):
    # decorator to track memory before and after function
    @wraps(func)
    def wrapper(*args, **kwargs):
        manager = MemoryManager()
        manager.log_memory(f"before_{func.__name__}")
        
        result = func(*args, **kwargs)
        
        manager.log_memory(f"after_{func.__name__}")
        manager.cleanup_if_needed()
        
        return result
    return wrapper


def cached_result(cache_key: str):
    # decorator to cache function results
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = MemoryManager()
            
            # check cache
            cached = manager.cache_get(cache_key)
            if cached is not None:
                return cached
            
            # compute and cache
            result = func(*args, **kwargs)
            manager.cache_set(cache_key, result)
            
            return result
        return wrapper
    return decorator