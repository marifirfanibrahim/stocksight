"""
anomaly detection utilities
multiple detection methods
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from enum import Enum
import warnings


# ================ ANOMALY METHODS ================

class AnomalyMethod(Enum):
    """
    anomaly detection method enumeration
    """
    ISOLATION_FOREST = 'isolation_forest'
    LOCAL_OUTLIER_FACTOR = 'local_outlier_factor'
    ZSCORE = 'zscore'
    IQR = 'iqr'
    ROLLING_ZSCORE = 'rolling_zscore'


# ================ DETECTION FUNCTIONS ================

def detect_anomalies(
    df: pd.DataFrame,
    method: AnomalyMethod = AnomalyMethod.ISOLATION_FOREST,
    value_column: str = 'Quantity',
    date_column: str = 'Date',
    contamination: float = 0.05,
    **kwargs
) -> Dict:
    """
    detect anomalies using specified method
    """
    if value_column not in df.columns:
        return {'error': f'column {value_column} not found'}
    
    # prepare data
    df_clean = df.copy()
    df_clean[date_column] = pd.to_datetime(df_clean[date_column])
    
    # aggregate by date if needed
    if df_clean.duplicated(subset=[date_column]).any():
        df_agg = df_clean.groupby(date_column)[value_column].sum().reset_index()
    else:
        df_agg = df_clean[[date_column, value_column]].copy()
    
    values = df_agg[value_column].values.reshape(-1, 1)
    
    # detect based on method
    if method == AnomalyMethod.ISOLATION_FOREST:
        result = _detect_isolation_forest(values, contamination)
    elif method == AnomalyMethod.LOCAL_OUTLIER_FACTOR:
        result = _detect_lof(values, contamination)
    elif method == AnomalyMethod.ZSCORE:
        threshold = kwargs.get('threshold', 3.0)
        result = _detect_zscore(values, threshold)
    elif method == AnomalyMethod.IQR:
        multiplier = kwargs.get('multiplier', 1.5)
        result = _detect_iqr(values, multiplier)
    elif method == AnomalyMethod.ROLLING_ZSCORE:
        window = kwargs.get('window', 7)
        threshold = kwargs.get('threshold', 3.0)
        result = _detect_rolling_zscore(values.flatten(), window, threshold)
    else:
        return {'error': f'unknown method: {method}'}
    
    # build result
    anomaly_mask = result['mask']
    anomaly_indices = np.where(anomaly_mask)[0].tolist()
    
    return {
        'method': method.value,
        'count': int(anomaly_mask.sum()),
        'indices': anomaly_indices,
        'dates': df_agg.iloc[anomaly_indices][date_column].tolist() if anomaly_indices else [],
        'values': df_agg.iloc[anomaly_indices][value_column].tolist() if anomaly_indices else [],
        'scores': result.get('scores', []),
        'threshold': result.get('threshold'),
        'total_points': len(values)
    }


def _detect_isolation_forest(values: np.ndarray, contamination: float) -> Dict:
    """
    isolation forest anomaly detection
    """
    try:
        from sklearn.ensemble import IsolationForest
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_jobs=-1
            )
            
            predictions = model.fit_predict(values)
            scores = model.score_samples(values)
        
        # -1 indicates anomaly in sklearn
        mask = predictions == -1
        
        return {
            'mask': mask,
            'scores': scores.tolist(),
            'threshold': model.offset_
        }
        
    except ImportError:
        print("sklearn not available, falling back to zscore")
        return _detect_zscore(values, 3.0)


def _detect_lof(values: np.ndarray, contamination: float) -> Dict:
    """
    local outlier factor anomaly detection
    """
    try:
        from sklearn.neighbors import LocalOutlierFactor
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            n_neighbors = min(20, len(values) - 1)
            
            model = LocalOutlierFactor(
                n_neighbors=max(n_neighbors, 2),
                contamination=contamination
            )
            
            predictions = model.fit_predict(values)
            scores = model.negative_outlier_factor_
        
        mask = predictions == -1
        
        return {
            'mask': mask,
            'scores': scores.tolist(),
            'threshold': model.offset_
        }
        
    except ImportError:
        print("sklearn not available, falling back to zscore")
        return _detect_zscore(values, 3.0)


def _detect_zscore(values: np.ndarray, threshold: float) -> Dict:
    """
    zscore based anomaly detection
    """
    values_flat = values.flatten()
    
    mean = np.mean(values_flat)
    std = np.std(values_flat)
    
    if std == 0:
        return {
            'mask': np.zeros(len(values_flat), dtype=bool),
            'scores': np.zeros(len(values_flat)).tolist(),
            'threshold': threshold
        }
    
    zscores = np.abs((values_flat - mean) / std)
    mask = zscores > threshold
    
    return {
        'mask': mask,
        'scores': zscores.tolist(),
        'threshold': threshold
    }


def _detect_iqr(values: np.ndarray, multiplier: float) -> Dict:
    """
    iqr based anomaly detection
    """
    values_flat = values.flatten()
    
    q1 = np.percentile(values_flat, 25)
    q3 = np.percentile(values_flat, 75)
    iqr = q3 - q1
    
    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr
    
    mask = (values_flat < lower_bound) | (values_flat > upper_bound)
    
    # calculate distance from bounds as score
    scores = np.zeros(len(values_flat))
    below = values_flat < lower_bound
    above = values_flat > upper_bound
    scores[below] = (lower_bound - values_flat[below]) / iqr if iqr > 0 else 0
    scores[above] = (values_flat[above] - upper_bound) / iqr if iqr > 0 else 0
    
    return {
        'mask': mask,
        'scores': scores.tolist(),
        'threshold': {'lower': lower_bound, 'upper': upper_bound}
    }


def _detect_rolling_zscore(values: np.ndarray, window: int, threshold: float) -> Dict:
    """
    rolling window zscore anomaly detection
    """
    series = pd.Series(values)
    
    rolling_mean = series.rolling(window=window, min_periods=1).mean()
    rolling_std = series.rolling(window=window, min_periods=1).std()
    
    # avoid division by zero
    rolling_std = rolling_std.replace(0, np.nan).fillna(1)
    
    zscores = np.abs((series - rolling_mean) / rolling_std)
    zscores = zscores.fillna(0)
    
    mask = zscores > threshold
    
    return {
        'mask': mask.values,
        'scores': zscores.tolist(),
        'threshold': threshold
    }


# ================ ANALYSIS FUNCTIONS ================

def analyze_anomaly_patterns(
    df: pd.DataFrame,
    anomaly_indices: List[int],
    date_column: str = 'Date'
) -> Dict:
    """
    analyze patterns in detected anomalies
    """
    if not anomaly_indices:
        return {'has_pattern': False}
    
    df_anom = df.iloc[anomaly_indices].copy()
    df_anom[date_column] = pd.to_datetime(df_anom[date_column])
    
    analysis = {
        'count': len(anomaly_indices),
        'date_range': {
            'start': df_anom[date_column].min().isoformat(),
            'end': df_anom[date_column].max().isoformat()
        }
    }
    
    # day of week pattern
    dow_counts = df_anom[date_column].dt.dayofweek.value_counts()
    if len(dow_counts) > 0:
        most_common_dow = dow_counts.idxmax()
        dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        analysis['day_of_week_pattern'] = {
            'most_common': dow_names[most_common_dow],
            'distribution': dow_counts.to_dict()
        }
    
    # month pattern
    month_counts = df_anom[date_column].dt.month.value_counts()
    if len(month_counts) > 0:
        analysis['month_pattern'] = {
            'most_common': int(month_counts.idxmax()),
            'distribution': month_counts.to_dict()
        }
    
    # clustering check
    dates_sorted = df_anom[date_column].sort_values()
    if len(dates_sorted) > 1:
        gaps = dates_sorted.diff().dropna()
        avg_gap = gaps.mean().days
        analysis['clustering'] = {
            'avg_gap_days': avg_gap,
            'is_clustered': avg_gap < 7
        }
    
    analysis['has_pattern'] = (
        analysis.get('clustering', {}).get('is_clustered', False) or
        len(month_counts) < 4
    )
    
    return analysis


def compare_detection_methods(
    df: pd.DataFrame,
    value_column: str = 'Quantity',
    contamination: float = 0.05
) -> Dict[str, Dict]:
    """
    compare results from different detection methods
    """
    methods = [
        AnomalyMethod.ISOLATION_FOREST,
        AnomalyMethod.LOCAL_OUTLIER_FACTOR,
        AnomalyMethod.ZSCORE,
        AnomalyMethod.IQR
    ]
    
    results = {}
    
    for method in methods:
        try:
            result = detect_anomalies(
                df,
                method=method,
                value_column=value_column,
                contamination=contamination
            )
            results[method.value] = result
        except Exception as e:
            results[method.value] = {'error': str(e)}
    
    # calculate agreement
    if len(results) > 1:
        valid_results = [r for r in results.values() if 'indices' in r]
        
        if valid_results:
            all_indices = set()
            for r in valid_results:
                all_indices.update(r['indices'])
            
            # count how many methods agree on each anomaly
            agreement = {}
            for idx in all_indices:
                count = sum(1 for r in valid_results if idx in r.get('indices', []))
                agreement[idx] = count
            
            # consensus anomalies (majority agreement)
            consensus = [idx for idx, count in agreement.items() if count >= len(valid_results) / 2]
            results['consensus'] = {
                'indices': consensus,
                'count': len(consensus),
                'agreement_scores': agreement
            }
    
    return results


def get_anomaly_statistics(
    df: pd.DataFrame,
    anomaly_result: Dict,
    value_column: str = 'Quantity'
) -> Dict:
    """
    get statistics about anomalous values
    """
    if 'indices' not in anomaly_result or not anomaly_result['indices']:
        return {}
    
    all_values = df[value_column].values
    anomaly_values = df.iloc[anomaly_result['indices']][value_column].values
    normal_values = np.delete(all_values, anomaly_result['indices'])
    
    stats = {
        'anomaly': {
            'count': len(anomaly_values),
            'mean': float(np.mean(anomaly_values)),
            'std': float(np.std(anomaly_values)),
            'min': float(np.min(anomaly_values)),
            'max': float(np.max(anomaly_values)),
            'median': float(np.median(anomaly_values))
        },
        'normal': {
            'count': len(normal_values),
            'mean': float(np.mean(normal_values)),
            'std': float(np.std(normal_values)),
            'min': float(np.min(normal_values)),
            'max': float(np.max(normal_values)),
            'median': float(np.median(normal_values))
        },
        'comparison': {
            'mean_ratio': float(np.mean(anomaly_values) / np.mean(normal_values)) if np.mean(normal_values) != 0 else 0,
            'std_ratio': float(np.std(anomaly_values) / np.std(normal_values)) if np.std(normal_values) != 0 else 0
        }
    }
    
    return stats