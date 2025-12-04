"""
date utilities module
handles date parsing and formatting
supports multiple date formats
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import re


# ============================================================================
#                              DATE UTILS
# ============================================================================

class DateUtils:
    # date parsing and manipulation utilities
    
    # common date formats to try
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y%m%d",
        "%d.%m.%Y",
        "%Y.%m.%d",
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y"
    ]
    
    @classmethod
    def parse_date(cls, date_str: str) -> Optional[datetime]:
        # parse date string to datetime
        if pd.isna(date_str):
            return None
        
        date_str = str(date_str).strip()
        
        # try each format
        for fmt in cls.DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # try pandas parser as fallback
        try:
            return pd.to_datetime(date_str).to_pydatetime()
        except Exception:
            return None
    
    @classmethod
    def detect_date_format(cls, date_series: pd.Series) -> Optional[str]:
        # detect date format from series of date strings
        sample = date_series.dropna().head(100)
        
        if len(sample) == 0:
            return None
        
        format_scores = {}
        
        for fmt in cls.DATE_FORMATS:
            valid_count = 0
            for date_str in sample:
                try:
                    datetime.strptime(str(date_str).strip(), fmt)
                    valid_count += 1
                except ValueError:
                    pass
            
            format_scores[fmt] = valid_count / len(sample)
        
        # return format with highest score
        best_format = max(format_scores, key=format_scores.get)
        
        if format_scores[best_format] > 0.8:
            return best_format
        
        return None
    
    @classmethod
    def standardize_dates(cls, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        # standardize date column to datetime
        result = df.copy()
        
        # try pandas parser first
        try:
            result[date_col] = pd.to_datetime(result[date_col], errors="coerce")
            return result
        except Exception:
            pass
        
        # detect and apply format
        fmt = cls.detect_date_format(result[date_col])
        if fmt:
            result[date_col] = pd.to_datetime(result[date_col], format=fmt, errors="coerce")
        else:
            result[date_col] = pd.to_datetime(result[date_col], errors="coerce")
        
        return result
    
    @classmethod
    def get_date_range_info(cls, dates: pd.Series) -> dict:
        # get information about date range
        dates = pd.to_datetime(dates, errors="coerce").dropna()
        
        if len(dates) == 0:
            return {}
        
        min_date = dates.min()
        max_date = dates.max()
        total_days = (max_date - min_date).days
        
        # detect frequency
        freq = cls.detect_frequency(dates)
        
        return {
            "start_date": min_date.strftime("%Y-%m-%d"),
            "end_date": max_date.strftime("%Y-%m-%d"),
            "total_days": total_days,
            "data_points": len(dates),
            "detected_frequency": freq,
            "coverage_pct": (len(dates) / max(1, total_days)) * 100 if freq == "daily" else None
        }
    
    @classmethod
    def detect_frequency(cls, dates: pd.Series) -> str:
        # detect time series frequency
        dates = pd.to_datetime(dates, errors="coerce").dropna().sort_values()
        
        if len(dates) < 2:
            return "unknown"
        
        # calculate differences
        diffs = dates.diff().dropna()
        median_diff = diffs.median().days
        
        if median_diff <= 1:
            return "daily"
        elif 6 <= median_diff <= 8:
            return "weekly"
        elif 28 <= median_diff <= 32:
            return "monthly"
        elif 89 <= median_diff <= 93:
            return "quarterly"
        elif 360 <= median_diff <= 370:
            return "yearly"
        else:
            return "irregular"
    
    @classmethod
    def fill_date_gaps(cls, 
                       df: pd.DataFrame, 
                       date_col: str, 
                       freq: str = "D") -> pd.DataFrame:
        # fill missing dates in dataframe
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
        
        # create complete date range
        date_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq=freq)
        
        # reindex to fill gaps
        df = df.reindex(date_range)
        df.index.name = date_col
        
        return df.reset_index()
    
    @classmethod
    def get_period_label(cls, date: datetime, period: str = "month") -> str:
        # get human readable period label
        if period == "day":
            return date.strftime("%Y-%m-%d")
        elif period == "week":
            return f"Week {date.isocalendar()[1]}, {date.year}"
        elif period == "month":
            return date.strftime("%B %Y")
        elif period == "quarter":
            quarter = (date.month - 1) // 3 + 1
            return f"Q{quarter} {date.year}"
        elif period == "year":
            return str(date.year)
        else:
            return date.strftime("%Y-%m-%d")
    
    @classmethod
    def get_holidays(cls, year: int, country: str = "US") -> List[datetime]:
        # get list of holidays for year
        holidays = []
        
        # us holidays
        if country == "US":
            holidays = [
                datetime(year, 1, 1),    # new years
                datetime(year, 7, 4),    # july 4th
                datetime(year, 11, 11),  # veterans day
                datetime(year, 12, 25),  # christmas
                datetime(year, 12, 31),  # new years eve
            ]
            
            # thanksgiving (4th thursday november)
            nov_first = datetime(year, 11, 1)
            days_until_thursday = (3 - nov_first.weekday()) % 7
            thanksgiving = nov_first + timedelta(days=days_until_thursday + 21)
            holidays.append(thanksgiving)
            holidays.append(thanksgiving + timedelta(days=1))  # black friday
        
        return holidays
    
    @classmethod
    def format_duration(cls, seconds: float) -> str:
        # format duration in human readable form
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} hours"