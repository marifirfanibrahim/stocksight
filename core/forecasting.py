"""
forecasting operations with autots
model training, evaluation, and comparison
"""


# ================ IMPORTS ================

import threading
import gc
import pickle
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
import multiprocessing

import numpy as np
import pandas as pd

from config import Paths, AutoTSConfig, DataConfig
from core.state import STATE, PipelineStage
from core.pipeline import PIPELINE
from core.data_operations import get_output_directory
from core.charting import generate_forecast_chart
from utils.preprocessing import prepare_for_autots, aggregate_by_period
from utils.export import export_dataframe


# ================ SUPPRESS WARNINGS ================

warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', message='overflow')
warnings.filterwarnings('ignore', message='divide by zero')


# ================ MEMORY MANAGEMENT ================

def force_gc():
    """
    force garbage collection
    """
    gc.collect()
    gc.collect()
    gc.collect()


def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    reduce memory usage of dataframe
    """
    for col in df.columns:
        if df[col].dtype == 'float64':
            df[col] = df[col].astype('float32')
        elif df[col].dtype == 'int64':
            df[col] = df[col].astype('int32')
    return df


# ================ SCALING ================

class DataScaler:
    """
    scale data to prevent overflow
    """
    
    def __init__(self):
        self.scale_factor = 1.0
        self.was_scaled = False
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        scale dataframe values
        """
        max_val = df.max().max()
        
        if max_val > 1e6:
            self.scale_factor = 1e6
            self.was_scaled = True
            return df / self.scale_factor
        elif max_val > 1e4:
            self.scale_factor = 1e3
            self.was_scaled = True
            return df / self.scale_factor
        
        return df
    
    def inverse_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        reverse scaling
        """
        if self.was_scaled:
            return df * self.scale_factor
        return df


# ================ METRICS ================

def calculate_metrics(actual: pd.Series, predicted: pd.Series) -> Dict[str, float]:
    """
    calculate forecast evaluation metrics
    """
    # remove nulls
    mask = actual.notna() & predicted.notna()
    actual = actual[mask]
    predicted = predicted[mask]
    
    if len(actual) == 0:
        return {}
    
    # mae
    mae = np.mean(np.abs(actual - predicted))
    
    # rmse
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))
    
    # mape
    nonzero_mask = actual != 0
    if nonzero_mask.sum() > 0:
        mape = np.mean(np.abs((actual[nonzero_mask] - predicted[nonzero_mask]) / actual[nonzero_mask])) * 100
    else:
        mape = np.nan
    
    # smape
    denominator = np.abs(actual) + np.abs(predicted)
    nonzero_denom = denominator != 0
    if nonzero_denom.sum() > 0:
        smape = np.mean(2 * np.abs(actual[nonzero_denom] - predicted[nonzero_denom]) / denominator[nonzero_denom]) * 100
    else:
        smape = np.nan
    
    return {
        'MAE': float(mae),
        'RMSE': float(rmse),
        'MAPE': float(mape) if not np.isnan(mape) else None,
        'SMAPE': float(smape) if not np.isnan(smape) else None
    }


def calculate_all_metrics(
    actual_df: pd.DataFrame,
    predicted_df: pd.DataFrame
) -> Dict[str, Dict[str, float]]:
    """
    calculate metrics for all skus
    """
    metrics = {}
    
    for col in predicted_df.columns:
        if col in actual_df.columns:
            metrics[col] = calculate_metrics(actual_df[col], predicted_df[col])
    
    # overall metrics
    if metrics:
        overall = {
            'MAE': np.mean([m['MAE'] for m in metrics.values() if m.get('MAE')]),
            'RMSE': np.mean([m['RMSE'] for m in metrics.values() if m.get('RMSE')]),
            'MAPE': np.mean([m['MAPE'] for m in metrics.values() if m.get('MAPE')]),
            'SMAPE': np.mean([m['SMAPE'] for m in metrics.values() if m.get('SMAPE')])
        }
        metrics['_overall'] = overall
    
    return metrics


# ================ FORECASTING MANAGER ================

class ForecastManager:
    """
    manage forecast operations
    """
    
    def __init__(self):
        self._is_forecasting = False
        self._lock = threading.RLock()
        self._models = {}
        self._metrics = {}
    
    # ================ MAIN FORECAST ================
    
    def run_forecast(
        self,
        df: pd.DataFrame = None,
        forecast_periods: int = None,
        granularity: str = None,
        speed: str = None,
        progress_callback: Callable = None
    ) -> Tuple[bool, str]:
        """
        run autots forecast
        """
        with self._lock:
            if self._is_forecasting:
                return False, "Forecast already in progress"
            self._is_forecasting = True
        
        STATE.reset_cancel()
        scaler = DataScaler()
        
        try:
            # get parameters
            if df is None:
                df = STATE.clean_data
            
            if df is None:
                return False, "No data available"
            
            if forecast_periods is None:
                forecast_periods = STATE.forecast_days
            
            if granularity is None:
                granularity = STATE.forecast_granularity
            
            if speed is None:
                speed = STATE.forecast_speed
            
            PIPELINE.start_stage(PipelineStage.FORECASTING, "Starting forecast...")
            
            if progress_callback:
                progress_callback(5, "Loading AutoTS...")
            
            # import autots
            try:
                from autots import AutoTS
            except ImportError:
                PIPELINE.fail_stage(PipelineStage.FORECASTING, "AutoTS not installed")
                return False, "AutoTS not installed"
            
            if progress_callback:
                progress_callback(10, "Preparing data...")
            
            # prepare data
            working_data = df.copy()
            
            if granularity != 'Daily':
                working_data = aggregate_by_period(working_data, granularity)
            
            working_data = optimize_dataframe(working_data)
            
            # pivot for autots
            df_pivot = prepare_for_autots(working_data, use_features=False)
            df_pivot = df_pivot.set_index('Date')
            
            # scale
            df_pivot = scaler.fit_transform(df_pivot)
            df_pivot = df_pivot.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            if STATE.is_cancelled():
                return False, "Forecast cancelled"
            
            if progress_callback:
                progress_callback(20, "Configuring model...")
            
            # get speed config
            speed_config = self._get_speed_config(speed)
            
            # determine frequency
            freq_map = {'Weekly': 'W-MON', 'Monthly': 'MS', 'Quarterly': 'QS'}
            frequency = freq_map.get(granularity, 'D')
            
            # calculate min train percent
            data_length = len(df_pivot)
            min_train_pct = max(0.5, 1 - (forecast_periods / data_length) if data_length > 0 else 0.5)
            
            if progress_callback:
                progress_callback(30, "Training model (this may take a while)...")
            
            # create model
            model = AutoTS(
                forecast_length=forecast_periods,
                frequency=frequency,
                ensemble=speed_config.get('ensemble'),
                max_generations=speed_config.get('max_generations', 2),
                num_validations=speed_config.get('num_validations', 1),
                validation_method='backwards',
                model_list=speed_config.get('model_list', 'fast'),
                transformer_list=speed_config.get('transformer_list', 'fast'),
                models_to_validate=speed_config.get('models_to_validate', 0.15),
                n_jobs='auto',
                min_allowed_train_percent=min_train_pct,
                no_negatives=True,
                drop_most_recent=0,
                prediction_interval=AutoTSConfig.PREDICTION_INTERVAL,
                random_seed=42,
                verbose=0
            )
            
            # fit model
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = model.fit(df_pivot)
            
            if STATE.is_cancelled():
                return False, "Forecast cancelled"
            
            if progress_callback:
                progress_callback(70, "Generating predictions...")
            
            # predict
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                prediction = model.predict()
            
            # inverse scale
            forecast_df = scaler.inverse_transform(prediction.forecast)
            upper_forecast = scaler.inverse_transform(prediction.upper_forecast)
            lower_forecast = scaler.inverse_transform(prediction.lower_forecast)
            
            # clean results
            forecast_df = forecast_df.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
            upper_forecast = upper_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
            lower_forecast = lower_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
            
            if progress_callback:
                progress_callback(85, "Storing results...")
            
            # store results
            STATE.forecast_data = forecast_df
            STATE.upper_forecast = upper_forecast
            STATE.lower_forecast = lower_forecast
            STATE.trained_models['autots'] = model
            
            # calculate metrics on validation
            self._calculate_validation_metrics(model, df_pivot)
            
            if progress_callback:
                progress_callback(90, "Generating charts...")
            
            # generate chart
            chart_base64, chart_path = generate_forecast_chart(
                df_pivot, forecast_df, upper_forecast, lower_forecast,
                granularity, dark_mode=STATE.settings.get('dark_mode', True)
            )
            
            # export data
            output_dir = get_output_directory()
            export_dataframe(forecast_df, 'forecast', output_dir=output_dir, include_timestamp=False)
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            PIPELINE.complete_stage(
                PipelineStage.FORECASTING,
                f"Forecast complete: {forecast_periods} periods, {len(forecast_df.columns)} SKUs"
            )
            
            force_gc()
            
            return True, f"Forecast complete: {forecast_periods} periods"
            
        except Exception as e:
            print(f"forecast error: {e}")
            import traceback
            traceback.print_exc()
            PIPELINE.fail_stage(PipelineStage.FORECASTING, str(e))
            return False, f"Forecast error: {str(e)}"
            
        finally:
            with self._lock:
                self._is_forecasting = False
            force_gc()
    
    def run_forecast_async(
        self,
        df: pd.DataFrame = None,
        forecast_periods: int = None,
        granularity: str = None,
        speed: str = None,
        progress_callback: Callable = None,
        complete_callback: Callable = None
    ):
        """
        run forecast in background thread
        """
        def run():
            success, message = self.run_forecast(
                df, forecast_periods, granularity, speed, progress_callback
            )
            if complete_callback:
                complete_callback(success, message)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
    
    def _get_speed_config(self, speed: str) -> Dict:
        """
        get autots config for speed setting
        """
        if speed == 'Superfast':
            return AutoTSConfig.SUPERFAST_MODE
        elif speed == 'Fast':
            return AutoTSConfig.FAST_MODE
        elif speed == 'Balanced':
            return AutoTSConfig.BALANCED_MODE
        elif speed == 'Accurate':
            return AutoTSConfig.ACCURATE_MODE
        else:
            return AutoTSConfig.FAST_MODE
    
    def _calculate_validation_metrics(self, model, df_pivot: pd.DataFrame):
        """
        calculate metrics from model validation
        """
        try:
            # get validation results from model
            if hasattr(model, 'best_model'):
                best_model_name = model.best_model.get('Model', 'Unknown')
                
                # store model info
                STATE.model_metrics['best_model'] = {
                    'name': best_model_name,
                    'transformer': model.best_model.get('TransformationParameters', {}),
                    'model_params': model.best_model.get('ModelParameters', {})
                }
            
            # get validation scores if available
            if hasattr(model, 'best_model_per_series_mape'):
                mape_scores = model.best_model_per_series_mape()
                if mape_scores is not None:
                    STATE.model_metrics['per_sku_mape'] = mape_scores.to_dict()
            
        except Exception as e:
            print(f"metrics calculation error: {e}")
    
    # ================ MODEL COMPARISON ================
    
    def compare_models(
        self,
        df: pd.DataFrame = None,
        forecast_periods: int = 30,
        models_to_test: List[str] = None,
        progress_callback: Callable = None
    ) -> Dict[str, Dict]:
        """
        compare multiple models
        """
        try:
            from autots import AutoTS
        except ImportError:
            return {'error': 'AutoTS not installed'}
        
        if df is None:
            df = STATE.clean_data
        
        if df is None:
            return {'error': 'No data available'}
        
        if models_to_test is None:
            models_to_test = ['fast', 'superfast', 'default']
        
        results = {}
        total = len(models_to_test)
        
        # prepare data
        df_pivot = prepare_for_autots(df, use_features=False).set_index('Date')
        
        # split train/test
        split_idx = len(df_pivot) - forecast_periods
        train_df = df_pivot.iloc[:split_idx]
        test_df = df_pivot.iloc[split_idx:]
        
        for i, model_list in enumerate(models_to_test):
            if STATE.is_cancelled():
                break
            
            if progress_callback:
                progress_callback(
                    int((i / total) * 100),
                    f"Testing {model_list} models..."
                )
            
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    
                    model = AutoTS(
                        forecast_length=forecast_periods,
                        frequency='infer',
                        model_list=model_list,
                        transformer_list='fast',
                        max_generations=2,
                        num_validations=1,
                        n_jobs='auto',
                        verbose=0
                    )
                    
                    model = model.fit(train_df)
                    prediction = model.predict()
                
                # calculate metrics against test set
                metrics = calculate_all_metrics(test_df, prediction.forecast)
                
                results[model_list] = {
                    'metrics': metrics.get('_overall', {}),
                    'per_sku': {k: v for k, v in metrics.items() if k != '_overall'},
                    'best_model': model.best_model.get('Model', 'Unknown') if hasattr(model, 'best_model') else 'Unknown'
                }
                
            except Exception as e:
                results[model_list] = {'error': str(e)}
        
        # store comparison results
        STATE.model_metrics['comparison'] = results
        
        return results
    
    # ================ MODEL PERSISTENCE ================
    
    def save_model(self, path: Path = None, model_name: str = None) -> Optional[Path]:
        """
        save trained model to file
        """
        if 'autots' not in STATE.trained_models:
            print("no model to save")
            return None
        
        if path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if model_name:
                filename = f"model_{model_name}_{timestamp}.pkl"
            else:
                filename = f"model_{timestamp}.pkl"
            path = Paths.MODELS_DIR / filename
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            model_data = {
                'model': STATE.trained_models['autots'],
                'metrics': STATE.model_metrics,
                'forecast_params': {
                    'forecast_days': STATE.forecast_days,
                    'granularity': STATE.forecast_granularity,
                    'speed': STATE.forecast_speed
                },
                'saved_at': datetime.now().isoformat()
            }
            
            with open(path, 'wb') as f:
                pickle.dump(model_data, f)
            
            print(f"model saved: {path}")
            return path
            
        except Exception as e:
            print(f"save error: {e}")
            return None
    
    def load_model(self, path: Path) -> Tuple[bool, str]:
        """
        load model from file
        """
        path = Path(path)
        
        if not path.exists():
            return False, f"File not found: {path}"
        
        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)
            
            # handle different formats
            if isinstance(model_data, dict) and 'model' in model_data:
                STATE.trained_models['autots'] = model_data['model']
                STATE.model_metrics = model_data.get('metrics', {})
                
                params = model_data.get('forecast_params', {})
                if 'forecast_days' in params:
                    STATE.forecast_days = params['forecast_days']
                if 'granularity' in params:
                    STATE.forecast_granularity = params['granularity']
                if 'speed' in params:
                    STATE.forecast_speed = params['speed']
            else:
                # legacy format - just the model
                STATE.trained_models['autots'] = model_data
            
            STATE.loaded_model = STATE.trained_models.get('autots')
            STATE.loaded_model_path = str(path)
            
            print(f"model loaded: {path}")
            return True, f"Model loaded: {path.name}"
            
        except Exception as e:
            print(f"load error: {e}")
            return False, f"Load error: {str(e)}"
    
    def predict_with_loaded_model(
        self,
        forecast_periods: int = None,
        progress_callback: Callable = None
    ) -> Tuple[bool, str]:
        """
        run prediction using loaded model
        """
        if 'autots' not in STATE.trained_models:
            return False, "No model loaded"
        
        model = STATE.trained_models['autots']
        
        if forecast_periods is None:
            forecast_periods = STATE.forecast_days
        
        try:
            if progress_callback:
                progress_callback(20, "Updating forecast length...")
            
            model.forecast_length = forecast_periods
            
            if progress_callback:
                progress_callback(50, "Generating predictions...")
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                prediction = model.predict()
            
            forecast_df = prediction.forecast
            upper_forecast = prediction.upper_forecast
            lower_forecast = prediction.lower_forecast
            
            # clean results
            forecast_df = forecast_df.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
            upper_forecast = upper_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
            lower_forecast = lower_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
            
            if progress_callback:
                progress_callback(80, "Storing results...")
            
            STATE.forecast_data = forecast_df
            STATE.upper_forecast = upper_forecast
            STATE.lower_forecast = lower_forecast
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            return True, f"Prediction complete: {forecast_periods} periods"
            
        except Exception as e:
            print(f"prediction error: {e}")
            return False, f"Prediction error: {str(e)}"
    
    # ================ STATUS ================
    
    def is_forecasting(self) -> bool:
        """
        check if forecast in progress
        """
        return self._is_forecasting
    
    def cancel(self):
        """
        cancel current forecast
        """
        STATE.request_cancel()
    
    def get_metrics(self) -> Dict:
        """
        get current model metrics
        """
        return STATE.model_metrics.copy()
    
    def get_forecast_summary(self) -> Dict:
        """
        get forecast summary
        """
        if STATE.forecast_data is None:
            return {}
        
        return {
            'periods': len(STATE.forecast_data),
            'skus': len(STATE.forecast_data.columns),
            'total_forecast': STATE.forecast_data.sum().sum(),
            'date_range': {
                'start': STATE.forecast_data.index.min(),
                'end': STATE.forecast_data.index.max()
            },
            'granularity': STATE.forecast_granularity,
            'metrics': STATE.model_metrics
        }


# ================ SINGLETON INSTANCE ================

FORECASTER = ForecastManager()