"""
anomaly detector module
identifies unusual values in time series
uses statistical methods for detection
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import config


# ============================================================================
#                               DATA CLASSES
# ============================================================================

@dataclass
class Anomaly:
    # single anomaly record
    sku: str
    date: str
    value: float
    expected_value: float
    anomaly_type: str
    severity: float
    method: str


# ============================================================================
#                           ANOMALY DETECTOR
# ============================================================================

class AnomalyDetector:
    # detects anomalies in time series data
    
    def __init__(self):
        # initialize with detection configuration
        self.config = config.ANOMALY_DETECTION
        self.anomalies = []
        self.flagged_for_review = []
    
    # ---------- MAIN DETECTION ----------
    
    def detect_anomalies(self,
                         df: pd.DataFrame,
                         date_col: str,
                         qty_col: str,
                         method: str = "iqr") -> List[Anomaly]:
        # detect anomalies in single time series
        
        if method == "iqr":
            return self._detect_iqr(df, date_col, qty_col)
        elif method == "zscore":
            return self._detect_zscore(df, date_col, qty_col)
        elif method == "rolling":
            return self._detect_rolling(df, date_col, qty_col)
        else:
            return self._detect_iqr(df, date_col, qty_col)
    
    def _detect_iqr(self, df: pd.DataFrame, date_col: str, qty_col: str) -> List[Anomaly]:
        # detect anomalies using interquartile range
        anomalies = []
        multiplier = self.config["methods"]["iqr"]["multiplier"]
        
        values = df[qty_col].dropna()
        
        if len(values) < 4:
            return anomalies
        
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        median = values.median()
        
        for idx, row in df.iterrows():
            value = row[qty_col]
            date = row[date_col]
            
            if pd.isna(value):
                continue
            
            if value < lower_bound:
                severity = abs(value - lower_bound) / (iqr + 1)
                anomalies.append(Anomaly(
                    sku="",
                    date=str(date),
                    value=float(value),
                    expected_value=float(median),
                    anomaly_type="drop" if value >= 0 else "negative",
                    severity=min(1.0, float(severity)),
                    method="iqr"
                ))
            elif value > upper_bound:
                severity = abs(value - upper_bound) / (iqr + 1)
                anomalies.append(Anomaly(
                    sku="",
                    date=str(date),
                    value=float(value),
                    expected_value=float(median),
                    anomaly_type="spike",
                    severity=min(1.0, float(severity)),
                    method="iqr"
                ))
        
        return anomalies
    
    def _detect_zscore(self, df: pd.DataFrame, date_col: str, qty_col: str) -> List[Anomaly]:
        # detect anomalies using z-score method
        anomalies = []
        threshold = self.config["methods"]["zscore"]["threshold"]
        
        values = df[qty_col].dropna()
        
        if len(values) < 3:
            return anomalies
        
        mean = values.mean()
        std = values.std()
        
        if std == 0:
            return anomalies
        
        for idx, row in df.iterrows():
            value = row[qty_col]
            date = row[date_col]
            
            if pd.isna(value):
                continue
            
            zscore = abs(value - mean) / std
            
            if zscore > threshold:
                severity = min(1.0, zscore / (threshold * 2))
                anomaly_type = "spike" if value > mean else "drop"
                
                anomalies.append(Anomaly(
                    sku="",
                    date=str(date),
                    value=float(value),
                    expected_value=float(mean),
                    anomaly_type=anomaly_type,
                    severity=float(severity),
                    method="zscore"
                ))
        
        return anomalies
    
    def _detect_rolling(self, df: pd.DataFrame, date_col: str, qty_col: str) -> List[Anomaly]:
        # detect anomalies using rolling window
        anomalies = []
        window = self.config["methods"]["rolling"]["window"]
        threshold = self.config["methods"]["rolling"]["threshold"]
        
        values = df[qty_col].copy()
        
        if len(values) < window + 1:
            return anomalies
        
        # calculate rolling statistics
        rolling_mean = values.rolling(window=window, center=True).mean()
        rolling_std = values.rolling(window=window, center=True).std()
        
        for idx, row in df.iterrows():
            value = row[qty_col]
            date = row[date_col]
            
            if pd.isna(value):
                continue
            
            rm = rolling_mean.get(idx)
            rs = rolling_std.get(idx)
            
            if pd.isna(rm) or pd.isna(rs) or rs == 0:
                continue
            
            zscore = abs(value - rm) / rs
            
            if zscore > threshold:
                severity = min(1.0, zscore / (threshold * 2))
                anomaly_type = "spike" if value > rm else "drop"
                
                anomalies.append(Anomaly(
                    sku="",
                    date=str(date),
                    value=float(value),
                    expected_value=float(rm),
                    anomaly_type=anomaly_type,
                    severity=float(severity),
                    method="rolling"
                ))
        
        return anomalies
    
    # ---------- BATCH DETECTION ----------
    
    def detect_batch(self,
                     df: pd.DataFrame,
                     sku_col: str,
                     date_col: str,
                     qty_col: str,
                     method: str = "iqr",
                     progress_callback: Optional[callable] = None) -> Dict[str, List[Anomaly]]:
        # detect anomalies for all skus
        
        all_anomalies = {}
        skus = df[sku_col].unique()
        total = len(skus)
        
        for i, sku in enumerate(skus):
            sku_df = df[df[sku_col] == sku].copy()
            anomalies = self.detect_anomalies(sku_df, date_col, qty_col, method)
            
            # set sku for each anomaly
            for a in anomalies:
                a.sku = sku
            
            if anomalies:
                all_anomalies[sku] = anomalies
            
            # progress callback
            if progress_callback and i % 100 == 0:
                progress_callback((i + 1) / total * 100)
        
        self.anomalies = all_anomalies
        return all_anomalies
    
    # ---------- SPECIAL DETECTIONS ----------
    
    def detect_zeros(self, df: pd.DataFrame, date_col: str, qty_col: str, min_consecutive: int = 3) -> List[Anomaly]:
        # detect suspicious zero periods
        anomalies = []
        
        values = df[qty_col].values
        dates = df[date_col].values
        
        # find consecutive zeros
        zero_start = None
        zero_count = 0
        
        for i, (value, date) in enumerate(zip(values, dates)):
            if value == 0:
                if zero_start is None:
                    zero_start = i
                zero_count += 1
            else:
                if zero_count >= min_consecutive:
                    anomalies.append(Anomaly(
                        sku="",
                        date=str(dates[zero_start]),
                        value=0,
                        expected_value=df[qty_col].mean(),
                        anomaly_type="zero",
                        severity=min(1.0, zero_count / 10),
                        method="zero_detection"
                    ))
                zero_start = None
                zero_count = 0
        
        # check final sequence
        if zero_count >= min_consecutive:
            anomalies.append(Anomaly(
                sku="",
                date=str(dates[zero_start]),
                value=0,
                expected_value=df[qty_col].mean(),
                anomaly_type="zero",
                severity=min(1.0, zero_count / 10),
                method="zero_detection"
            ))
        
        return anomalies
    
    def detect_gaps(self, df: pd.DataFrame, date_col: str, expected_freq: str = "D") -> List[Anomaly]:
        # detect missing date gaps
        anomalies = []
        
        dates = pd.to_datetime(df[date_col]).sort_values()
        
        if len(dates) < 2:
            return anomalies
        
        # create expected date range
        expected_dates = pd.date_range(start=dates.min(), end=dates.max(), freq=expected_freq)
        missing_dates = expected_dates.difference(dates)
        
        # group consecutive missing dates
        if len(missing_dates) == 0:
            return anomalies
        
        gap_start = missing_dates[0]
        gap_count = 1
        
        for i in range(1, len(missing_dates)):
            diff = (missing_dates[i] - missing_dates[i-1]).days
            if diff == 1:
                gap_count += 1
            else:
                if gap_count >= 1:
                    anomalies.append(Anomaly(
                        sku="",
                        date=str(gap_start),
                        value=0,
                        expected_value=0,
                        anomaly_type="gap",
                        severity=min(1.0, gap_count / 7),
                        method="gap_detection"
                    ))
                gap_start = missing_dates[i]
                gap_count = 1
        
        # check final gap
        if gap_count >= 1:
            anomalies.append(Anomaly(
                sku="",
                date=str(gap_start),
                value=0,
                expected_value=0,
                anomaly_type="gap",
                severity=min(1.0, gap_count / 7),
                method="gap_detection"
            ))
        
        return anomalies
    
    # ---------- ANOMALY MANAGEMENT ----------
    
    def flag_for_review(self, sku: str, anomaly_idx: int) -> None:
        # flag anomaly for user review
        self.flagged_for_review.append((sku, anomaly_idx))
    
    def get_anomaly_playlist(self, min_severity: float = 0.5) -> List[Anomaly]:
        # get list of high severity anomalies for review
        playlist = []
        
        for sku, anomalies in self.anomalies.items():
            for anomaly in anomalies:
                if anomaly.severity >= min_severity:
                    playlist.append(anomaly)
        
        # sort by severity
        playlist.sort(key=lambda x: x.severity, reverse=True)
        
        return playlist
    
    def get_summary(self) -> Dict[str, Any]:
        # get anomaly detection summary
        total_anomalies = sum(len(a) for a in self.anomalies.values())
        
        # count by type
        type_counts = {}
        severity_sum = 0
        
        for anomalies in self.anomalies.values():
            for a in anomalies:
                type_counts[a.anomaly_type] = type_counts.get(a.anomaly_type, 0) + 1
                severity_sum += a.severity
        
        return {
            "total_anomalies": total_anomalies,
            "skus_with_anomalies": len(self.anomalies),
            "by_type": type_counts,
            "avg_severity": severity_sum / total_anomalies if total_anomalies > 0 else 0,
            "flagged_count": len(self.flagged_for_review)
        }
    
    def export_anomalies(self) -> pd.DataFrame:
        # export all anomalies as dataframe
        data = []
        
        for sku, anomalies in self.anomalies.items():
            for a in anomalies:
                data.append({
                    "sku": a.sku,
                    "date": a.date,
                    "value": a.value,
                    "expected_value": a.expected_value,
                    "type": a.anomaly_type,
                    "severity": a.severity,
                    "method": a.method
                })
        
        return pd.DataFrame(data)