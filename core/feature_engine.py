"""
feature engineering with tsfresh and featuretools
automated feature extraction per sku
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable, Tuple
from pathlib import Path
import threading
import warnings
import gc

from config import Paths, FeatureConfig
from core.state import STATE, PipelineStage
from core.pipeline import PIPELINE
from core.alerts import ALERTS, AlertSeverity


# ================ FEATURE ENGINE ================

class FeatureEngine:
    """
    manage feature extraction and selection
    """
    
    def __init__(self):
        # ---------- STATE ----------
        self._features = None
        self._importance = {}
        self._selected = []
        self._is_extracting = False
        self._lock = threading.RLock()
    
    # ================ TSFRESH EXTRACTION ================
    
    def extract_tsfresh_features(
        self,
        df: pd.DataFrame = None,
        column_id: str = 'SKU',
        column_sort: str = 'Date',
        column_value: str = 'Quantity',
        extraction_settings: str = None,
        progress_callback: Callable = None
    ) -> Optional[pd.DataFrame]:
        """
        extract features using tsfresh
        """
        with self._lock:
            if self._is_extracting:
                print("feature extraction already in progress")
                return None
            self._is_extracting = True
        
        try:
            if df is None:
                df = STATE.clean_data
            
            if df is None:
                print("no data for feature extraction")
                return None
            
            PIPELINE.start_stage(PipelineStage.FEATURES, "Extracting features...")
            
            if progress_callback:
                progress_callback(5, "Loading tsfresh...")
            
            # import tsfresh
            try:
                from tsfresh import extract_features
                from tsfresh.feature_extraction import (
                    EfficientFCParameters,
                    MinimalFCParameters,
                    ComprehensiveFCParameters
                )
                from tsfresh.utilities.dataframe_functions import impute
            except ImportError:
                print("tsfresh not installed")
                PIPELINE.fail_stage(PipelineStage.FEATURES, "tsfresh not installed")
                return None
            
            if progress_callback:
                progress_callback(10, "Preparing data...")
            
            # prepare data
            ts_df = self._prepare_for_tsfresh(df, column_id, column_sort, column_value)
            
            if progress_callback:
                progress_callback(20, "Selecting extraction settings...")
            
            # get extraction settings
            if extraction_settings is None:
                extraction_settings = FeatureConfig.TSFRESH_DEFAULTS
            
            if extraction_settings == 'minimal':
                fc_params = MinimalFCParameters()
            elif extraction_settings == 'comprehensive':
                fc_params = ComprehensiveFCParameters()
            else:
                fc_params = EfficientFCParameters()
            
            if progress_callback:
                progress_callback(30, "Extracting features (this may take a while)...")
            
            # extract features
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                features = extract_features(
                    ts_df,
                    column_id=column_id,
                    column_sort=column_sort,
                    column_value=column_value,
                    default_fc_parameters=fc_params,
                    n_jobs=0,
                    disable_progressbar=True
                )
            
            if progress_callback:
                progress_callback(70, "Imputing missing values...")
            
            # impute missing values
            features = impute(features)
            
            if progress_callback:
                progress_callback(80, "Cleaning features...")
            
            # remove constant features
            features = self._remove_constant_features(features)
            
            # limit features
            if len(features.columns) > FeatureConfig.MAX_FEATURES:
                features = features.iloc[:, :FeatureConfig.MAX_FEATURES]
            
            if progress_callback:
                progress_callback(90, "Storing results...")
            
            # store results
            self._features = features
            STATE.feature_data = features
            STATE.available_features = features.columns.tolist()
            STATE.feature_extraction_complete = True
            
            PIPELINE.complete_stage(
                PipelineStage.FEATURES,
                f"Extracted {len(features.columns)} features"
            )
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            gc.collect()
            
            return features
            
        except Exception as e:
            print(f"feature extraction error: {e}")
            import traceback
            traceback.print_exc()
            PIPELINE.fail_stage(PipelineStage.FEATURES, str(e))
            return None
            
        finally:
            with self._lock:
                self._is_extracting = False
    
    def _prepare_for_tsfresh(
        self,
        df: pd.DataFrame,
        column_id: str,
        column_sort: str,
        column_value: str
    ) -> pd.DataFrame:
        """
        prepare dataframe for tsfresh
        """
        ts_df = df[[column_id, column_sort, column_value]].copy()
        
        # ensure proper types
        ts_df[column_sort] = pd.to_datetime(ts_df[column_sort])
        ts_df[column_value] = pd.to_numeric(ts_df[column_value], errors='coerce').fillna(0)
        
        # sort by id and time
        ts_df = ts_df.sort_values([column_id, column_sort])
        
        # add time index for each group
        ts_df['time_idx'] = ts_df.groupby(column_id).cumcount()
        
        return ts_df
    
    def _remove_constant_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        remove features with zero variance
        """
        variance = features.var()
        non_constant = variance[variance > 0].index
        return features[non_constant]
    
    # ================ FEATURETOOLS EXTRACTION ================
    
    def extract_featuretools_features(
        self,
        df: pd.DataFrame = None,
        entity_id: str = 'SKU',
        time_index: str = 'Date',
        max_depth: int = None,
        progress_callback: Callable = None
    ) -> Optional[pd.DataFrame]:
        """
        extract features using featuretools
        """
        with self._lock:
            if self._is_extracting:
                print("feature extraction already in progress")
                return None
            self._is_extracting = True
        
        try:
            if df is None:
                df = STATE.clean_data
            
            if df is None:
                print("no data for feature extraction")
                return None
            
            PIPELINE.start_stage(PipelineStage.FEATURES, "Extracting features with Featuretools...")
            
            if progress_callback:
                progress_callback(5, "Loading featuretools...")
            
            # import featuretools
            try:
                import featuretools as ft
            except ImportError:
                print("featuretools not installed")
                PIPELINE.fail_stage(PipelineStage.FEATURES, "featuretools not installed")
                return None
            
            if progress_callback:
                progress_callback(10, "Creating entityset...")
            
            # prepare data
            ft_df = df.copy()
            ft_df[time_index] = pd.to_datetime(ft_df[time_index])
            ft_df['transaction_id'] = range(len(ft_df))
            
            # create entityset
            es = ft.EntitySet(id='inventory')
            
            # add transactions entity
            es = es.add_dataframe(
                dataframe_name='transactions',
                dataframe=ft_df,
                index='transaction_id',
                time_index=time_index
            )
            
            # normalize to create sku entity
            es = es.normalize_dataframe(
                base_dataframe_name='transactions',
                new_dataframe_name='skus',
                index=entity_id
            )
            
            if progress_callback:
                progress_callback(30, "Running deep feature synthesis...")
            
            # set max depth
            if max_depth is None:
                max_depth = FeatureConfig.MAX_DEPTH
            
            # define primitives
            primitives = FeatureConfig.PRIMITIVES
            
            # run dfs
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                features, feature_defs = ft.dfs(
                    entityset=es,
                    target_dataframe_name='skus',
                    max_depth=max_depth,
                    agg_primitives=primitives,
                    n_jobs=1,
                    verbose=False
                )
            
            if progress_callback:
                progress_callback(80, "Processing features...")
            
            # clean features
            features = features.replace([np.inf, -np.inf], np.nan)
            features = features.fillna(0)
            features = self._remove_constant_features(features)
            
            # limit features
            if len(features.columns) > FeatureConfig.MAX_FEATURES:
                features = features.iloc[:, :FeatureConfig.MAX_FEATURES]
            
            if progress_callback:
                progress_callback(90, "Storing results...")
            
            # store results
            self._features = features
            STATE.feature_data = features
            STATE.available_features = features.columns.tolist()
            STATE.feature_extraction_complete = True
            
            PIPELINE.complete_stage(
                PipelineStage.FEATURES,
                f"Extracted {len(features.columns)} features"
            )
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            gc.collect()
            
            return features
            
        except Exception as e:
            print(f"featuretools extraction error: {e}")
            import traceback
            traceback.print_exc()
            PIPELINE.fail_stage(PipelineStage.FEATURES, str(e))
            return None
            
        finally:
            with self._lock:
                self._is_extracting = False
    
    # ================ FEATURE SELECTION ================
    
    def calculate_importance(
        self,
        features: pd.DataFrame = None,
        target: pd.Series = None,
        progress_callback: Callable = None
    ) -> Dict[str, float]:
        """
        calculate feature importance using tsfresh relevance
        """
        try:
            if features is None:
                features = self._features
            
            if features is None:
                print("no features available")
                return {}
            
            if progress_callback:
                progress_callback(10, "Loading relevance calculator...")
            
            # import tsfresh selection
            try:
                from tsfresh.feature_selection.relevance import calculate_relevance_table
            except ImportError:
                print("tsfresh not available for importance calculation")
                return self._calculate_variance_importance(features)
            
            if progress_callback:
                progress_callback(30, "Calculating relevance scores...")
            
            # create target if not provided
            if target is None:
                if STATE.clean_data is not None and 'Quantity' in STATE.clean_data.columns:
                    target = STATE.clean_data.groupby('SKU')['Quantity'].sum()
                    target = target.reindex(features.index).fillna(0)
                else:
                    return self._calculate_variance_importance(features)
            
            # calculate relevance
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                relevance_table = calculate_relevance_table(
                    features,
                    target,
                    ml_task='regression',
                    n_jobs=0
                )
            
            if progress_callback:
                progress_callback(80, "Processing results...")
            
            # extract importance scores
            importance = {}
            for _, row in relevance_table.iterrows():
                feature_name = row['feature']
                p_value = row['p_value']
                
                # convert p-value to importance score
                importance[feature_name] = max(0, 1 - p_value)
            
            # sort by importance
            importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
            
            # store results
            self._importance = importance
            STATE.feature_importance = importance
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            return importance
            
        except Exception as e:
            print(f"importance calculation error: {e}")
            return self._calculate_variance_importance(features)
    
    def _calculate_variance_importance(self, features: pd.DataFrame) -> Dict[str, float]:
        """
        fallback importance calculation using variance
        """
        variance = features.var().sort_values(ascending=False)
        
        # normalize to 0-1
        if variance.max() > 0:
            normalized = variance / variance.max()
        else:
            normalized = variance
        
        importance = normalized.to_dict()
        
        self._importance = importance
        STATE.feature_importance = importance
        
        return importance
    
    def select_features(
        self,
        threshold: float = None,
        max_features: int = None
    ) -> List[str]:
        """
        select features based on importance threshold
        """
        if not self._importance:
            self.calculate_importance()
        
        if not self._importance:
            return []
        
        if threshold is None:
            threshold = FeatureConfig.RELEVANCE_THRESHOLD
        
        if max_features is None:
            max_features = FeatureConfig.MAX_FEATURES
        
        # filter by threshold
        selected = [
            name for name, score in self._importance.items()
            if score >= threshold
        ]
        
        # limit count
        selected = selected[:max_features]
        
        self._selected = selected
        STATE.selected_features = selected
        
        return selected
    
    def set_selected_features(self, features: List[str]):
        """
        manually set selected features
        """
        self._selected = features
        STATE.selected_features = features
    
    def toggle_feature(self, feature_name: str, enabled: bool):
        """
        toggle single feature on/off
        """
        if enabled:
            if feature_name not in self._selected:
                self._selected.append(feature_name)
        else:
            if feature_name in self._selected:
                self._selected.remove(feature_name)
        
        STATE.selected_features = self._selected
    
    # ================ FEATURE GROUPS ================
    
    def get_feature_groups(self) -> Dict[str, List[str]]:
        """
        group features by type/category
        """
        if self._features is None:
            return {}
        
        groups = {
            'statistical': [],
            'temporal': [],
            'frequency': [],
            'entropy': [],
            'other': []
        }
        
        for col in self._features.columns:
            col_lower = col.lower()
            
            if any(s in col_lower for s in ['mean', 'std', 'var', 'median', 'min', 'max', 'sum']):
                groups['statistical'].append(col)
            elif any(s in col_lower for s in ['lag', 'autocorr', 'partial', 'trend']):
                groups['temporal'].append(col)
            elif any(s in col_lower for s in ['fft', 'cwt', 'spectral', 'frequency']):
                groups['frequency'].append(col)
            elif any(s in col_lower for s in ['entropy', 'complexity', 'binned']):
                groups['entropy'].append(col)
            else:
                groups['other'].append(col)
        
        # remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def enable_feature_group(self, group_name: str, enabled: bool):
        """
        enable/disable entire feature group
        """
        groups = self.get_feature_groups()
        
        if group_name not in groups:
            return
        
        for feature in groups[group_name]:
            self.toggle_feature(feature, enabled)
    
    # ================ GETTERS ================
    
    def get_features(self) -> Optional[pd.DataFrame]:
        """
        get extracted features
        """
        return self._features
    
    def get_selected_features(self) -> List[str]:
        """
        get selected feature names
        """
        return self._selected.copy()
    
    def get_importance(self) -> Dict[str, float]:
        """
        get feature importance scores
        """
        return self._importance.copy()
    
    def get_feature_stats(self) -> Dict:
        """
        get feature extraction statistics
        """
        if self._features is None:
            return {}
        
        return {
            'total_features': len(self._features.columns),
            'selected_features': len(self._selected),
            'total_samples': len(self._features),
            'groups': {k: len(v) for k, v in self.get_feature_groups().items()}
        }
    
    def is_extracting(self) -> bool:
        """
        check if extraction in progress
        """
        return self._is_extracting
    
    # ================ EXPORT ================
    
    def export_features(
        self,
        output_path: Path = None,
        format: str = 'csv',
        include_importance: bool = True
    ) -> Optional[Path]:
        """
        export features to file
        """
        if self._features is None:
            return None
        
        if output_path is None:
            from datetime import datetime
            from config import ExportConfig
            
            timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
            output_path = Paths.FEATURES_DIR / f"features_{timestamp}.{format}"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format == 'csv':
                self._features.to_csv(output_path)
            elif format == 'parquet':
                self._features.to_parquet(output_path)
            elif format == 'pickle':
                self._features.to_pickle(output_path)
            else:
                self._features.to_csv(output_path)
            
            # export importance if requested
            if include_importance and self._importance:
                imp_path = output_path.with_name(f"{output_path.stem}_importance.csv")
                imp_df = pd.DataFrame([
                    {'feature': k, 'importance': v}
                    for k, v in self._importance.items()
                ])
                imp_df.to_csv(imp_path, index=False)
            
            print(f"features exported: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"export error: {e}")
            return None
    
    # ================ RESET ================
    
    def reset(self):
        """
        reset feature engine state
        """
        self._features = None
        self._importance = {}
        self._selected = []
        STATE.reset_features()


# ================ SINGLETON INSTANCE ================

FEATURES = FeatureEngine()