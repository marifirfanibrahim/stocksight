"""
feature engineering for forecasting
extract features from additional columns
handle categorical and numeric variables
supports per-sku dynamic feature sets
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler


# ================ CONSTANTS ================

MIN_FEATURE_COVERAGE = 0.5  # feature must have 50% non-null values to be used
MIN_FEATURE_VARIANCE = 0.01  # feature must have some variance


# ================ FEATURE EXTRACTION ================

def detect_additional_columns(df, required_cols=['Date', 'SKU', 'Quantity']):
    """
    find columns beyond required set
    return list of feature columns
    """
    all_cols = df.columns.tolist()
    feature_cols = [col for col in all_cols if col not in required_cols]
    
    return feature_cols


def categorize_column_type(series):
    """
    determine if series is categorical or numeric
    return type string
    """
    # drop nulls for analysis
    clean = series.dropna()
    
    if len(clean) == 0:
        return 'empty'
    
    dtype = clean.dtype
    unique_count = clean.nunique()
    
    if dtype == 'object' or dtype.name == 'category':
        return 'categorical'
    elif unique_count < 20 and unique_count < len(clean) * 0.5:
        return 'categorical'
    else:
        return 'numeric'


def get_feature_coverage(series):
    """
    calculate percentage of non-null values
    """
    if len(series) == 0:
        return 0.0
    return series.notna().sum() / len(series)


def get_feature_variance(series):
    """
    calculate variance for numeric or unique ratio for categorical
    """
    clean = series.dropna()
    
    if len(clean) == 0:
        return 0.0
    
    col_type = categorize_column_type(clean)
    
    if col_type == 'numeric':
        if clean.std() == 0:
            return 0.0
        return clean.var() / (clean.mean() ** 2) if clean.mean() != 0 else clean.var()
    else:
        # for categorical, use unique ratio
        return clean.nunique() / len(clean)


# ================ PER-SKU FEATURE DETECTION ================

def detect_sku_features(df, sku, all_feature_columns):
    """
    detect which features are valid for specific sku
    returns list of usable feature columns
    """
    sku_data = df[df['SKU'] == sku]
    
    if len(sku_data) == 0:
        return []
    
    valid_features = []
    
    for col in all_feature_columns:
        if col not in sku_data.columns:
            continue
        
        series = sku_data[col]
        
        # check coverage
        coverage = get_feature_coverage(series)
        if coverage < MIN_FEATURE_COVERAGE:
            continue
        
        # check variance
        variance = get_feature_variance(series)
        if variance < MIN_FEATURE_VARIANCE:
            continue
        
        valid_features.append(col)
    
    return valid_features


def build_sku_feature_map(df, all_feature_columns):
    """
    build mapping of sku -> valid features
    returns dict
    """
    sku_feature_map = {}
    
    for sku in df['SKU'].unique():
        valid_features = detect_sku_features(df, sku, all_feature_columns)
        sku_feature_map[sku] = {
            'features': valid_features,
            'count': len(valid_features)
        }
    
    return sku_feature_map


def analyze_feature_availability(df, all_feature_columns):
    """
    analyze which features are available across skus
    returns summary dict
    """
    summary = {
        'total_skus': df['SKU'].nunique(),
        'total_features': len(all_feature_columns),
        'feature_coverage': {},
        'sku_coverage': {}
    }
    
    # per-feature coverage
    for col in all_feature_columns:
        if col not in df.columns:
            continue
        
        skus_with_feature = 0
        for sku in df['SKU'].unique():
            sku_data = df[df['SKU'] == sku]
            coverage = get_feature_coverage(sku_data[col])
            if coverage >= MIN_FEATURE_COVERAGE:
                skus_with_feature += 1
        
        summary['feature_coverage'][col] = {
            'skus_covered': skus_with_feature,
            'coverage_pct': skus_with_feature / summary['total_skus'] * 100
        }
    
    # per-sku coverage
    sku_feature_map = build_sku_feature_map(df, all_feature_columns)
    for sku, info in sku_feature_map.items():
        summary['sku_coverage'][sku] = info['count']
    
    return summary


# ================ PER-SKU ENCODERS ================

class SKUFeatureEncoder:
    """
    handles encoding for single sku
    stores only relevant encoders
    """
    
    def __init__(self, sku):
        self.sku = sku
        self.encoders = {}
        self.feature_columns = []
        self.is_fitted = False
    
    def fit(self, sku_data, feature_columns):
        """
        fit encoders for sku-specific features
        """
        self.feature_columns = []
        self.encoders = {}
        
        for col in feature_columns:
            if col not in sku_data.columns:
                continue
            
            series = sku_data[col]
            coverage = get_feature_coverage(series)
            
            if coverage < MIN_FEATURE_COVERAGE:
                continue
            
            col_type = categorize_column_type(series)
            clean = series.dropna()
            
            if col_type == 'empty':
                continue
            elif col_type == 'categorical':
                try:
                    encoder = LabelEncoder()
                    encoder.fit(clean.astype(str))
                    self.encoders[col] = {
                        'type': 'categorical',
                        'encoder': encoder,
                        'classes': encoder.classes_.tolist(),
                        'default': 0
                    }
                    self.feature_columns.append(col)
                except Exception:
                    pass
            else:
                try:
                    if clean.std() > 0:
                        scaler = StandardScaler()
                        scaler.fit(clean.values.reshape(-1, 1))
                        self.encoders[col] = {
                            'type': 'numeric',
                            'scaler': scaler,
                            'mean': float(scaler.mean_[0]),
                            'std': float(scaler.scale_[0]),
                            'default': 0.0
                        }
                        self.feature_columns.append(col)
                except Exception:
                    pass
        
        self.is_fitted = True
        return self
    
    def transform(self, sku_data):
        """
        transform sku data using fitted encoders
        returns exogenous dataframe
        """
        if not self.is_fitted or not self.feature_columns:
            return None
        
        exog = pd.DataFrame()
        exog['Date'] = sku_data['Date']
        
        for col in self.feature_columns:
            if col not in sku_data.columns:
                continue
            
            series = sku_data[col]
            info = self.encoders[col]
            
            if info['type'] == 'categorical':
                # handle unseen categories
                encoded = []
                for val in series:
                    if pd.isna(val):
                        encoded.append(info['default'])
                    else:
                        try:
                            encoded.append(info['encoder'].transform([str(val)])[0])
                        except ValueError:
                            encoded.append(info['default'])
                exog[col] = encoded
            else:
                # handle nulls for numeric
                values = series.fillna(info['mean']).values.reshape(-1, 1)
                exog[col] = info['scaler'].transform(values).flatten()
        
        # aggregate by date
        exog_agg = exog.groupby('Date').mean().reset_index()
        exog_agg = exog_agg.set_index('Date')
        
        return exog_agg
    
    def get_last_values(self, exog_df):
        """
        get last known values for future prediction
        """
        if exog_df is None or len(exog_df) == 0:
            return {}
        
        return exog_df.iloc[-1].to_dict()
    
    def create_future_exog(self, last_values, future_dates):
        """
        create exogenous for future periods
        """
        if not last_values or not self.feature_columns:
            return None
        
        future_exog = pd.DataFrame(index=future_dates)
        
        for col in self.feature_columns:
            if col in last_values:
                future_exog[col] = last_values[col]
            else:
                future_exog[col] = self.encoders[col]['default']
        
        return future_exog


# ================ GLOBAL ENCODER MANAGER ================

class FeatureEncoderManager:
    """
    manages encoders for all skus
    handles heterogeneous feature sets
    """
    
    def __init__(self):
        self.sku_encoders = {}
        self.all_feature_columns = []
        self.sku_feature_map = {}
        self.feature_summary = {}
    
    def fit(self, df, feature_columns):
        """
        fit encoders for all skus
        """
        self.all_feature_columns = feature_columns
        self.sku_encoders = {}
        self.sku_feature_map = {}
        
        skus = df['SKU'].unique()
        
        for sku in skus:
            sku_data = df[df['SKU'] == sku]
            
            encoder = SKUFeatureEncoder(sku)
            encoder.fit(sku_data, feature_columns)
            
            self.sku_encoders[sku] = encoder
            self.sku_feature_map[sku] = {
                'features': encoder.feature_columns,
                'count': len(encoder.feature_columns)
            }
        
        # build summary
        self.feature_summary = analyze_feature_availability(df, feature_columns)
        
        return self
    
    def get_sku_encoder(self, sku):
        """
        get encoder for specific sku
        """
        return self.sku_encoders.get(sku)
    
    def transform_sku(self, df, sku):
        """
        transform data for specific sku
        """
        encoder = self.get_sku_encoder(sku)
        if encoder is None:
            return None
        
        sku_data = df[df['SKU'] == sku]
        return encoder.transform(sku_data)
    
    def get_summary(self):
        """
        get feature availability summary
        """
        return self.feature_summary
    
    def print_summary(self):
        """
        print human readable summary
        """
        print(f"total skus: {self.feature_summary['total_skus']}")
        print(f"total features: {self.feature_summary['total_features']}")
        print("")
        print("feature coverage:")
        for col, info in self.feature_summary['feature_coverage'].items():
            print(f"  {col}: {info['skus_covered']} skus ({info['coverage_pct']:.1f}%)")
        print("")
        
        # sku coverage distribution
        counts = list(self.feature_summary['sku_coverage'].values())
        if counts:
            print(f"features per sku: min={min(counts)}, max={max(counts)}, avg={sum(counts)/len(counts):.1f}")


# ================ SEASONALITY DETECTION ================

def extract_date_features(df):
    """
    extract temporal features from date
    day of week month quarter
    """
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    
    # ---------- TEMPORAL FEATURES ----------
    df['DayOfWeek'] = df['Date'].dt.dayofweek
    df['DayOfMonth'] = df['Date'].dt.day
    df['DayOfYear'] = df['Date'].dt.dayofyear
    df['Month'] = df['Date'].dt.month
    df['Quarter'] = df['Date'].dt.quarter
    df['Year'] = df['Date'].dt.year
    df['WeekOfYear'] = df['Date'].dt.isocalendar().week
    
    # ---------- CYCLICAL ENCODING ----------
    df['Month_Sin'] = np.sin(2 * np.pi * df['Month'] / 12)
    df['Month_Cos'] = np.cos(2 * np.pi * df['Month'] / 12)
    df['DayOfWeek_Sin'] = np.sin(2 * np.pi * df['DayOfWeek'] / 7)
    df['DayOfWeek_Cos'] = np.cos(2 * np.pi * df['DayOfWeek'] / 7)
    
    # ---------- WEEKEND FLAG ----------
    df['IsWeekend'] = (df['DayOfWeek'] >= 5).astype(int)
    
    return df


def detect_seasonality_pattern(df, sku=None):
    """
    analyze data for seasonal patterns
    return seasonality info
    """
    if sku:
        data = df[df['SKU'] == sku].copy()
    else:
        data = df.copy()
    
    if len(data) == 0:
        return {
            'has_monthly_seasonality': False,
            'has_weekly_seasonality': False,
            'monthly_cv': 0,
            'weekly_cv': 0,
            'monthly_pattern': {},
            'weekly_pattern': {}
        }
    
    data = extract_date_features(data)
    
    # ---------- MONTHLY SEASONALITY ----------
    monthly_avg = data.groupby('Month')['Quantity'].mean()
    monthly_std = monthly_avg.std()
    monthly_mean = monthly_avg.mean()
    monthly_cv = monthly_std / monthly_mean if monthly_mean > 0 else 0
    
    # ---------- WEEKLY SEASONALITY ----------
    weekly_avg = data.groupby('DayOfWeek')['Quantity'].mean()
    weekly_std = weekly_avg.std()
    weekly_mean = weekly_avg.mean()
    weekly_cv = weekly_std / weekly_mean if weekly_mean > 0 else 0
    
    # ---------- SEASONALITY DETECTION ----------
    has_monthly = monthly_cv > 0.15
    has_weekly = weekly_cv > 0.10
    
    seasonality_info = {
        'has_monthly_seasonality': has_monthly,
        'has_weekly_seasonality': has_weekly,
        'monthly_cv': monthly_cv,
        'weekly_cv': weekly_cv,
        'monthly_pattern': monthly_avg.to_dict(),
        'weekly_pattern': weekly_avg.to_dict()
    }
    
    return seasonality_info


# ================ PER-SKU FORECAST PREPARATION ================

def prepare_sku_forecast_data(df, sku, encoder_manager=None):
    """
    prepare all data needed for single sku forecast
    handles sku-specific features
    returns dict with pivot data, exog data, metadata
    """
    sku_data = df[df['SKU'] == sku].copy()
    
    if len(sku_data) == 0:
        return None
    
    result = {
        'sku': sku,
        'data_points': len(sku_data),
        'date_range': (sku_data['Date'].min(), sku_data['Date'].max()),
    }
    
    # prepare time series
    sku_pivot = sku_data.pivot_table(
        index='Date',
        values='Quantity',
        aggfunc='sum'
    ).fillna(0)
    sku_pivot.columns = [sku]
    result['pivot'] = sku_pivot
    
    # prepare exogenous if encoder exists
    if encoder_manager is not None:
        encoder = encoder_manager.get_sku_encoder(sku)
        
        if encoder is not None and encoder.is_fitted and encoder.feature_columns:
            exog = encoder.transform(sku_data)
            result['exogenous'] = exog
            result['encoder'] = encoder
            result['feature_columns'] = encoder.feature_columns
            
            if exog is not None and len(exog) > 0:
                result['last_exog_values'] = encoder.get_last_values(exog)
        else:
            result['exogenous'] = None
            result['feature_columns'] = []
    
    # detect seasonality
    result['seasonality'] = detect_seasonality_pattern(sku_data)
    
    return result


# ================ FEATURE IMPORTANCE ================

def analyze_feature_importance(df, feature_columns):
    """
    analyze which features correlate with quantity
    returns importance scores
    """
    if not feature_columns:
        return {}
    
    importance = {}
    
    for col in feature_columns:
        if col not in df.columns:
            continue
        
        # check coverage first
        coverage = get_feature_coverage(df[col])
        if coverage < MIN_FEATURE_COVERAGE:
            importance[col] = {
                'type': 'low_coverage',
                'coverage': coverage
            }
            continue
        
        col_type = categorize_column_type(df[col])
        
        if col_type == 'numeric':
            # correlation for numeric
            clean_df = df[[col, 'Quantity']].dropna()
            if len(clean_df) > 0:
                corr = clean_df[col].corr(clean_df['Quantity'])
                importance[col] = {
                    'type': 'numeric',
                    'correlation': corr if not pd.isna(corr) else 0,
                    'abs_correlation': abs(corr) if not pd.isna(corr) else 0,
                    'coverage': coverage
                }
        elif col_type == 'categorical':
            # variance ratio for categorical
            clean_df = df[[col, 'Quantity']].dropna()
            if len(clean_df) > 0:
                group_means = clean_df.groupby(col)['Quantity'].mean()
                overall_var = clean_df['Quantity'].var()
                between_var = group_means.var() * len(group_means)
                
                var_ratio = between_var / overall_var if overall_var > 0 else 0
                importance[col] = {
                    'type': 'categorical',
                    'variance_ratio': var_ratio,
                    'num_categories': df[col].nunique(),
                    'coverage': coverage
                }
    
    return importance


# ================ LEGACY COMPATIBILITY ================

def encode_categorical_features(df, column):
    """
    encode categorical column
    return encoded dataframe and encoder
    """
    encoder = LabelEncoder()
    encoded = encoder.fit_transform(df[column].astype(str))
    
    return encoded, encoder


def normalize_numeric_features(df, column):
    """
    normalize numeric column
    return normalized values and scaler
    """
    scaler = StandardScaler()
    values = df[column].values.reshape(-1, 1)
    normalized = scaler.fit_transform(values)
    
    return normalized.flatten(), scaler


def prepare_exogenous_features(df, feature_columns):
    """
    prepare features for autots
    create exogenous variable dataframe
    legacy function for backwards compatibility
    """
    if not feature_columns:
        return None, {}
    
    exog_data = pd.DataFrame()
    exog_data['Date'] = df['Date']
    
    encoders = {}
    
    for col in feature_columns:
        if col not in df.columns:
            continue
        
        coverage = get_feature_coverage(df[col])
        if coverage < MIN_FEATURE_COVERAGE:
            continue
        
        col_type = categorize_column_type(df[col])
        
        if col_type == 'categorical':
            encoded, encoder = encode_categorical_features(df, col)
            exog_data[col] = encoded
            encoders[col] = {'type': 'categorical', 'encoder': encoder}
            
        elif col_type == 'numeric':
            normalized, scaler = normalize_numeric_features(df, col)
            exog_data[col] = normalized
            encoders[col] = {'type': 'numeric', 'scaler': scaler}
    
    exog_agg = exog_data.groupby('Date').mean().reset_index()
    
    return exog_agg, encoders


def prepare_multicolumn_forecast(df, feature_columns=None, include_seasonality=True):
    """
    prepare data for forecasting with multiple features
    return processed dataframe and metadata
    """
    df_processed = df.copy()
    metadata = {}
    
    if include_seasonality:
        df_processed = extract_date_features(df_processed)
        metadata['seasonality'] = detect_seasonality_pattern(df_processed)
    
    if feature_columns:
        exog_data, encoders = prepare_exogenous_features(df_processed, feature_columns)
        metadata['exogenous'] = exog_data
        metadata['encoders'] = encoders
    
    base_cols = ['Date', 'SKU', 'Quantity']
    df_base = df_processed[base_cols].copy()
    
    metadata['feature_columns'] = feature_columns
    metadata['original_shape'] = df.shape
    metadata['processed_shape'] = df_processed.shape
    
    return df_base, metadata