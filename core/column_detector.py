"""
column detector module
automatically detects column types from data
provides confidence scores for mappings
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import re

import config


# ============================================================================
#                            COLUMN DETECTOR
# ============================================================================

class ColumnDetector:
    # automatic column type detection for uploaded data
    
    def __init__(self):
        # initialize with detection keywords from config
        self.keywords = config.COLUMN_DETECTION
        self.confidence_threshold = self.keywords["confidence_threshold"]
    
    # ---------- MAIN DETECTION ----------
    
    def detect_columns(self, df: pd.DataFrame) -> Dict[str, Dict]:
        # detect all column types and return with confidence scores
        detections = {}
        
        for col in df.columns:
            col_lower = col.lower().strip()
            dtype = str(df[col].dtype)
            sample = df[col].dropna().head(100)
            
            # check each column type
            scores = {
                "date": self._score_date_column(col_lower, dtype, sample),
                "sku": self._score_sku_column(col_lower, dtype, sample),
                "quantity": self._score_quantity_column(col_lower, dtype, sample),
                "category": self._score_category_column(col_lower, dtype, sample),
                "price": self._score_price_column(col_lower, dtype, sample),
                "promo": self._score_promo_column(col_lower, dtype, sample)
            }
            
            # get best match
            best_type = max(scores, key=scores.get)
            best_score = scores[best_type]
            
            detections[col] = {
                "detected_type": best_type if best_score >= self.confidence_threshold else "unknown",
                "confidence": best_score,
                "all_scores": scores,
                "dtype": dtype,
                "sample_values": sample.head(5).tolist()
            }
        
        return detections
    
    def get_best_mapping(self, detections: Dict) -> Dict[str, str]:
        # get best column for each required type
        mapping = {}
        used_columns = set()
        
        # priority order for column types
        priority = ["date", "sku", "quantity", "category", "price", "promo"]
        
        for col_type in priority:
            best_col = None
            best_score = 0
            
            for col, info in detections.items():
                if col in used_columns:
                    continue
                
                score = info["all_scores"].get(col_type, 0)
                if score > best_score and score >= self.confidence_threshold:
                    best_col = col
                    best_score = score
            
            if best_col:
                mapping[col_type] = best_col
                used_columns.add(best_col)
        
        return mapping
    
    # ---------- SCORING METHODS ----------
    
    def _score_date_column(self, col_name: str, dtype: str, sample: pd.Series) -> float:
        # score likelihood of being date column
        score = 0.0
        
        # check column name
        for keyword in self.keywords["date_keywords"]:
            if keyword in col_name:
                score += 0.4
                break
        
        # check dtype
        if "datetime" in dtype:
            score += 0.5
        elif "object" in dtype:
            # try parsing as date
            try:
                parsed = pd.to_datetime(sample.head(20), errors="coerce")
                valid_pct = parsed.notna().sum() / len(parsed)
                score += valid_pct * 0.4
            except:
                pass
        
        return min(1.0, score)
    
    def _score_sku_column(self, col_name: str, dtype: str, sample: pd.Series) -> float:
        # score likelihood of being sku column
        score = 0.0
        
        # check column name
        for keyword in self.keywords["sku_keywords"]:
            if keyword in col_name:
                score += 0.4
                break
        
        # check uniqueness ratio
        if len(sample) > 0:
            unique_ratio = sample.nunique() / len(sample)
            if unique_ratio > 0.01 and unique_ratio < 0.5:
                score += 0.3
        
        # check if string type
        if "object" in dtype or "string" in dtype:
            score += 0.2
            
            # check for code-like patterns
            sample_str = sample.astype(str).head(20)
            code_pattern = sample_str.str.match(r"^[A-Za-z0-9\-_]+$").mean()
            score += code_pattern * 0.2
        
        return min(1.0, score)
    
    def _score_quantity_column(self, col_name: str, dtype: str, sample: pd.Series) -> float:
        # score likelihood of being quantity column
        score = 0.0
        
        # check column name
        for keyword in self.keywords["quantity_keywords"]:
            if keyword in col_name:
                score += 0.4
                break
        
        # check numeric type
        if "int" in dtype or "float" in dtype:
            score += 0.3
            
            # check if mostly positive integers
            if len(sample) > 0:
                numeric_sample = pd.to_numeric(sample, errors="coerce").dropna()
                if len(numeric_sample) > 0:
                    positive_ratio = (numeric_sample >= 0).mean()
                    integer_ratio = (numeric_sample == numeric_sample.astype(int)).mean()
                    score += positive_ratio * 0.15
                    score += integer_ratio * 0.15
        
        return min(1.0, score)
    
    def _score_category_column(self, col_name: str, dtype: str, sample: pd.Series) -> float:
        # score likelihood of being category column
        score = 0.0
        
        # check column name
        for keyword in self.keywords["category_keywords"]:
            if keyword in col_name:
                score += 0.4
                break
        
        # check for low cardinality
        if len(sample) > 0:
            unique_ratio = sample.nunique() / len(sample)
            if unique_ratio < 0.1:
                score += 0.3
            elif unique_ratio < 0.3:
                score += 0.2
        
        # check if string type
        if "object" in dtype or "string" in dtype or "category" in dtype:
            score += 0.2
        
        return min(1.0, score)
    
    def _score_price_column(self, col_name: str, dtype: str, sample: pd.Series) -> float:
        # score likelihood of being price column
        score = 0.0
        
        # check column name
        for keyword in self.keywords["price_keywords"]:
            if keyword in col_name:
                score += 0.4
                break
        
        # check numeric type with decimals
        if "float" in dtype:
            score += 0.3
            
            if len(sample) > 0:
                numeric_sample = pd.to_numeric(sample, errors="coerce").dropna()
                if len(numeric_sample) > 0:
                    # prices are usually positive
                    positive_ratio = (numeric_sample > 0).mean()
                    score += positive_ratio * 0.2
                    
                    # prices often have 2 decimal places
                    decimal_check = numeric_sample.apply(lambda x: len(str(x).split(".")[-1]) == 2 if "." in str(x) else False)
                    score += decimal_check.mean() * 0.1
        
        return min(1.0, score)
    
    def _score_promo_column(self, col_name: str, dtype: str, sample: pd.Series) -> float:
        # score likelihood of being promo column
        score = 0.0
        
        # check column name
        for keyword in self.keywords["promo_keywords"]:
            if keyword in col_name:
                score += 0.5
                break
        
        # check for binary values
        if len(sample) > 0:
            unique_vals = sample.nunique()
            if unique_vals <= 5:
                score += 0.3
            
            # check for 0/1 or yes/no patterns
            str_sample = sample.astype(str).str.lower()
            binary_patterns = ["0", "1", "yes", "no", "true", "false", "y", "n"]
            binary_match = str_sample.isin(binary_patterns).mean()
            score += binary_match * 0.2
        
        return min(1.0, score)
    
    # ---------- HELPER METHODS ----------
    
    def get_detection_summary(self, detections: Dict) -> List[Dict]:
        # get human readable summary of detections
        summary = []
        
        for col, info in detections.items():
            detected = info["detected_type"]
            confidence = info["confidence"]
            
            # create user friendly message
            if detected == "unknown":
                message = f"Could not determine type for '{col}'"
                status = "warning"
            elif confidence >= 0.8:
                message = f"'{col}' looks like your {detected.upper()} column"
                status = "good"
            else:
                message = f"'{col}' might be your {detected.upper()} column"
                status = "uncertain"
            
            summary.append({
                "column": col,
                "type": detected,
                "confidence": confidence,
                "message": message,
                "status": status,
                "samples": info["sample_values"]
            })
        
        return summary
    
    def validate_mapping(self, mapping: Dict[str, str], df: pd.DataFrame) -> Tuple[bool, List[str]]:
        # validate that mapping is usable
        errors = []
        
        # check required columns
        if "date" not in mapping:
            errors.append("Date column is required")
        if "sku" not in mapping:
            errors.append("Item/SKU column is required")
        if "quantity" not in mapping:
            errors.append("Quantity/Sales column is required")
        
        # check columns exist in dataframe
        for col_type, col_name in mapping.items():
            if col_name not in df.columns:
                errors.append(f"Column '{col_name}' not found in data")
        
        return len(errors) == 0, errors