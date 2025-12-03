"""
data cleaning utilities
configurable cleaning strategies with rollback
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum

from core.state import STATE
from config import CleaningConfig


# ================ CLEANING METHODS ================

class ImputationMethod(Enum):
    """
    imputation method enumeration
    """
    MEAN = 'mean'
    MEDIAN = 'median'
    MODE = 'mode'
    FORWARD_FILL = 'forward_fill'
    BACKWARD_FILL = 'backward_fill'
    INTERPOLATE = 'interpolate'
    ZERO = 'zero'
    DROP = 'drop'


class DuplicateMethod(Enum):
    """
    duplicate handling enumeration
    """
    KEEP_FIRST = 'keep_first'
    KEEP_LAST = 'keep_last'
    DROP_ALL = 'drop_all'


class OutlierMethod(Enum):
    """
    outlier handling enumeration
    """
    CLIP = 'clip'
    REMOVE = 'remove'
    WINSORIZE = 'winsorize'
    NONE = 'none'


# ================ CLEANING OPERATIONS ================

def impute_missing(
    df: pd.DataFrame,
    column: str,
    method: ImputationMethod = ImputationMethod.FORWARD_FILL,
    save_state: bool = True
) -> pd.DataFrame:
    """
    impute missing values in column
    """
    if save_state:
        STATE.save_cleaning_state('impute', f"Impute {column} using {method.value}")
    
    df_clean = df.copy()
    
    if method == ImputationMethod.MEAN:
        df_clean[column] = df_clean[column].fillna(df_clean[column].mean())
    
    elif method == ImputationMethod.MEDIAN:
        df_clean[column] = df_clean[column].fillna(df_clean[column].median())
    
    elif method == ImputationMethod.MODE:
        mode_val = df_clean[column].mode()
        if len(mode_val) > 0:
            df_clean[column] = df_clean[column].fillna(mode_val.iloc[0])
    
    elif method == ImputationMethod.FORWARD_FILL:
        df_clean[column] = df_clean[column].ffill()
    
    elif method == ImputationMethod.BACKWARD_FILL:
        df_clean[column] = df_clean[column].bfill()
    
    elif method == ImputationMethod.INTERPOLATE:
        df_clean[column] = df_clean[column].interpolate(method='linear')
    
    elif method == ImputationMethod.ZERO:
        df_clean[column] = df_clean[column].fillna(0)
    
    elif method == ImputationMethod.DROP:
        df_clean = df_clean.dropna(subset=[column])
    
    return df_clean


def impute_all_missing(
    df: pd.DataFrame,
    numeric_method: ImputationMethod = ImputationMethod.FORWARD_FILL,
    categorical_method: ImputationMethod = ImputationMethod.MODE,
    save_state: bool = True
) -> pd.DataFrame:
    """
    impute all missing values
    """
    if save_state:
        STATE.save_cleaning_state('impute_all', f"Impute all: numeric={numeric_method.value}, categorical={categorical_method.value}")
    
    df_clean = df.copy()
    
    for column in df_clean.columns:
        if df_clean[column].isna().sum() == 0:
            continue
        
        if pd.api.types.is_numeric_dtype(df_clean[column]):
            df_clean = impute_missing(df_clean, column, numeric_method, save_state=False)
        else:
            df_clean = impute_missing(df_clean, column, categorical_method, save_state=False)
    
    return df_clean


def handle_duplicates(
    df: pd.DataFrame,
    subset: List[str] = None,
    method: DuplicateMethod = DuplicateMethod.KEEP_LAST,
    save_state: bool = True
) -> pd.DataFrame:
    """
    handle duplicate rows
    """
    if save_state:
        STATE.save_cleaning_state('duplicates', f"Handle duplicates using {method.value}")
    
    df_clean = df.copy()
    
    if method == DuplicateMethod.KEEP_FIRST:
        df_clean = df_clean.drop_duplicates(subset=subset, keep='first')
    
    elif method == DuplicateMethod.KEEP_LAST:
        df_clean = df_clean.drop_duplicates(subset=subset, keep='last')
    
    elif method == DuplicateMethod.DROP_ALL:
        df_clean = df_clean.drop_duplicates(subset=subset, keep=False)
    
    return df_clean.reset_index(drop=True)


def handle_outliers(
    df: pd.DataFrame,
    column: str,
    method: OutlierMethod = OutlierMethod.CLIP,
    threshold: float = None,
    save_state: bool = True
) -> pd.DataFrame:
    """
    handle outliers in numeric column
    """
    if threshold is None:
        threshold = CleaningConfig.OUTLIER_STD_THRESHOLD
    
    if save_state:
        STATE.save_cleaning_state('outliers', f"Handle outliers in {column} using {method.value}")
    
    df_clean = df.copy()
    
    if not pd.api.types.is_numeric_dtype(df_clean[column]):
        return df_clean
    
    mean = df_clean[column].mean()
    std = df_clean[column].std()
    
    lower_bound = mean - threshold * std
    upper_bound = mean + threshold * std
    
    if method == OutlierMethod.CLIP:
        df_clean[column] = df_clean[column].clip(lower=lower_bound, upper=upper_bound)
    
    elif method == OutlierMethod.REMOVE:
        mask = (df_clean[column] >= lower_bound) & (df_clean[column] <= upper_bound)
        df_clean = df_clean[mask]
    
    elif method == OutlierMethod.WINSORIZE:
        # winsorize at 5th and 95th percentile
        lower_pct = df_clean[column].quantile(0.05)
        upper_pct = df_clean[column].quantile(0.95)
        df_clean[column] = df_clean[column].clip(lower=lower_pct, upper=upper_pct)
    
    return df_clean.reset_index(drop=True)


def handle_all_outliers(
    df: pd.DataFrame,
    method: OutlierMethod = OutlierMethod.CLIP,
    threshold: float = None,
    save_state: bool = True
) -> pd.DataFrame:
    """
    handle outliers in all numeric columns
    """
    if save_state:
        STATE.save_cleaning_state('outliers_all', f"Handle all outliers using {method.value}")
    
    df_clean = df.copy()
    
    for column in df_clean.select_dtypes(include=[np.number]).columns:
        if column.lower() in ['date', 'id', 'index']:
            continue
        df_clean = handle_outliers(df_clean, column, method, threshold, save_state=False)
    
    return df_clean


# ================ VALIDATION ================

def get_missing_summary(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    get summary of missing values
    """
    summary = {}
    
    for column in df.columns:
        missing_count = df[column].isna().sum()
        total_count = len(df)
        missing_pct = (missing_count / total_count) * 100 if total_count > 0 else 0
        
        summary[column] = {
            'missing_count': missing_count,
            'total_count': total_count,
            'missing_pct': missing_pct,
            'has_missing': missing_count > 0
        }
    
    return summary


def get_duplicate_summary(df: pd.DataFrame, subset: List[str] = None) -> Dict:
    """
    get summary of duplicates
    """
    total = len(df)
    duplicates = df.duplicated(subset=subset, keep=False).sum()
    unique = total - duplicates
    
    return {
        'total_rows': total,
        'duplicate_rows': duplicates,
        'unique_rows': unique,
        'duplicate_pct': (duplicates / total) * 100 if total > 0 else 0
    }


def get_outlier_summary(df: pd.DataFrame, threshold: float = None) -> Dict[str, Dict]:
    """
    get summary of outliers
    """
    if threshold is None:
        threshold = CleaningConfig.OUTLIER_STD_THRESHOLD
    
    summary = {}
    
    for column in df.select_dtypes(include=[np.number]).columns:
        mean = df[column].mean()
        std = df[column].std()
        
        if std == 0:
            summary[column] = {
                'outlier_count': 0,
                'total_count': len(df),
                'outlier_pct': 0,
                'lower_bound': mean,
                'upper_bound': mean
            }
            continue
        
        lower_bound = mean - threshold * std
        upper_bound = mean + threshold * std
        
        outlier_mask = (df[column] < lower_bound) | (df[column] > upper_bound)
        outlier_count = outlier_mask.sum()
        
        summary[column] = {
            'outlier_count': outlier_count,
            'total_count': len(df),
            'outlier_pct': (outlier_count / len(df)) * 100 if len(df) > 0 else 0,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'mean': mean,
            'std': std
        }
    
    return summary


# ================ COMPREHENSIVE CLEANING ================

def clean_dataframe(
    df: pd.DataFrame,
    imputation_method: ImputationMethod = ImputationMethod.FORWARD_FILL,
    duplicate_method: DuplicateMethod = DuplicateMethod.KEEP_LAST,
    outlier_method: OutlierMethod = OutlierMethod.CLIP,
    save_state: bool = True
) -> pd.DataFrame:
    """
    apply comprehensive cleaning
    """
    if save_state:
        STATE.save_cleaning_state('clean_all', "Comprehensive cleaning applied")
    
    df_clean = df.copy()
    
    # handle duplicates first
    df_clean = handle_duplicates(df_clean, method=duplicate_method, save_state=False)
    
    # impute missing
    df_clean = impute_all_missing(df_clean, numeric_method=imputation_method, save_state=False)
    
    # handle outliers
    if outlier_method != OutlierMethod.NONE:
        df_clean = handle_all_outliers(df_clean, method=outlier_method, save_state=False)
    
    return df_clean


def get_cleaning_recommendations(df: pd.DataFrame) -> List[Dict]:
    """
    get cleaning recommendations based on data analysis
    """
    recommendations = []
    
    # check missing values
    missing_summary = get_missing_summary(df)
    for column, info in missing_summary.items():
        if info['missing_pct'] > 0:
            severity = 'low'
            if info['missing_pct'] > 5:
                severity = 'medium'
            if info['missing_pct'] > 20:
                severity = 'high'
            
            recommendations.append({
                'type': 'missing',
                'column': column,
                'severity': severity,
                'message': f"{column}: {info['missing_pct']:.1f}% missing ({info['missing_count']} values)",
                'suggestion': 'forward_fill' if pd.api.types.is_numeric_dtype(df[column]) else 'mode'
            })
    
    # check duplicates
    dup_summary = get_duplicate_summary(df)
    if dup_summary['duplicate_rows'] > 0:
        recommendations.append({
            'type': 'duplicate',
            'column': None,
            'severity': 'medium' if dup_summary['duplicate_pct'] < 5 else 'high',
            'message': f"{dup_summary['duplicate_rows']} duplicate rows ({dup_summary['duplicate_pct']:.1f}%)",
            'suggestion': 'keep_last'
        })
    
    # check outliers
    outlier_summary = get_outlier_summary(df)
    for column, info in outlier_summary.items():
        if info['outlier_pct'] > 1:
            recommendations.append({
                'type': 'outlier',
                'column': column,
                'severity': 'low' if info['outlier_pct'] < 5 else 'medium',
                'message': f"{column}: {info['outlier_count']} outliers ({info['outlier_pct']:.1f}%)",
                'suggestion': 'clip'
            })
    
    return recommendations


# ================ ROLLBACK OPERATIONS ================

def rollback(steps: int = 1) -> bool:
    """
    rollback cleaning operations
    """
    return STATE.rollback_cleaning(steps)


def redo(steps: int = 1) -> bool:
    """
    redo cleaning operations
    """
    return STATE.redo_cleaning(steps)


def get_cleaning_history() -> List[Dict]:
    """
    get cleaning operation history
    """
    history = []
    
    for i, state in enumerate(STATE.cleaning_history):
        history.append({
            'index': i,
            'timestamp': state.timestamp.isoformat(),
            'operation': state.operation,
            'description': state.description,
            'rows_affected': state.rows_affected,
            'is_current': i == STATE.current_cleaning_index
        })
    
    return history


def can_rollback() -> bool:
    """
    check if rollback is possible
    """
    return STATE.current_cleaning_index > 0


def can_redo() -> bool:
    """
    check if redo is possible
    """
    return STATE.current_cleaning_index < len(STATE.cleaning_history) - 1