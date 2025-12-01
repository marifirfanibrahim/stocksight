"""
forecasting operations
autots model training and prediction
supports heterogeneous per-sku features
"""


# ================ IMPORTS ================

import threading
import gc
import pickle
import warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

import numpy as np
import pandas as pd
from autots import AutoTS

from config import AutoTSConfig, LargeDataConfig
from core.state import STATE
from core.data_operations import get_output_directory
from core.charting import generate_forecast_chart
from utils.preprocessing import (
    prepare_for_autots,
    export_forecast_csv,
    export_summary_report,
    aggregate_before_forecast
)
from utils.features import (
    prepare_multicolumn_forecast,
    prepare_sku_forecast_data,
    detect_seasonality_pattern,
    analyze_feature_importance,
    FeatureEncoderManager
)


# ================ SUPPRESS WARNINGS ================

warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', message='overflow')
warnings.filterwarnings('ignore', message='divide by zero')
warnings.filterwarnings('ignore', message='invalid value')


# ================ MEMORY MANAGEMENT ================

def force_gc():
    # force garbage collection
    gc.collect()
    gc.collect()
    gc.collect()


def optimize_dataframe(df):
    # reduce memory usage of dataframe
    for col in df.columns:
        if df[col].dtype == 'float64':
            df[col] = df[col].astype('float32')
        elif df[col].dtype == 'int64':
            df[col] = df[col].astype('int32')
    return df


def check_and_reduce_data(df):
    # check data size and reduce if needed
    # return reduced df and info dict
    info = {
        'original_rows': len(df),
        'original_skus': df['SKU'].nunique(),
        'sampled': False,
        'sku_limited': False
    }
    
    # ---------- SAMPLE ROWS IF NEEDED ----------
    if len(df) > LargeDataConfig.MAX_ROWS:
        print(f"sampling data: {len(df)} -> {LargeDataConfig.SAMPLE_ROWS} rows")
        
        if LargeDataConfig.KEEP_RECENT:
            df = df.sort_values('Date').tail(LargeDataConfig.SAMPLE_ROWS)
        else:
            df = df.sample(n=LargeDataConfig.SAMPLE_ROWS, random_state=42)
        
        info['sampled'] = True
        info['sampled_rows'] = len(df)
    
    return df, info


# ================ SCALING ================

class DataScaler:
    # scale data to prevent overflow
    def __init__(self):
        self.scale_factor = 1.0
        self.was_scaled = False
    
    def fit_transform(self, df):
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
    
    def inverse_transform(self, df):
        if self.was_scaled:
            return df * self.scale_factor
        return df


# ================ HELPER FUNCTIONS ================

def _prepare_working_data(clean_data, granularity):
    # prepare and reduce data for forecasting
    working_data = clean_data.copy()
    working_data, data_info = check_and_reduce_data(working_data)
    working_data = optimize_dataframe(working_data)
    
    if granularity != 'Daily':
        working_data = aggregate_before_forecast(working_data, granularity)
    
    return working_data, data_info


def _build_status_message(forecast_periods, granularity, use_parallel, results, skus_with_features, data_info):
    # build completion status message
    parts = [f"Forecast: {forecast_periods} periods"]
    
    if granularity != 'Daily':
        parts.append(f"({granularity})")
    
    if use_parallel:
        parts.append(f"[{len(results)} SKUs]")
        if skus_with_features > 0:
            parts.append(f"[{skus_with_features} with features]")
    
    if data_info['sampled']:
        parts.append("[sampled]")
    
    return " ".join(parts)


# ================ MODEL LOADING ================

def load_saved_model(model_path):
    # load previously saved model single or dict
    try:
        with open(model_path, 'rb') as f:
            content = pickle.load(f)
        
        if isinstance(content, dict) and 'sku_models' in content:
            # parallel model dict
            STATE.saved_models = content['sku_models']
            STATE.loaded_model = None
            STATE.has_loaded_models = True
            message = f"Loaded parallel models for {len(STATE.saved_models)} SKUs"
            print(message)
            STATE.loaded_model_path = str(model_path)
            return True, message
        else:
            # single model
            STATE.loaded_model = content
            STATE.saved_models = {}
            STATE.has_loaded_models = True
            message = "Single model loaded successfully"
            print(f"single model loaded: {model_path}")
            STATE.loaded_model_path = str(model_path)
            return True, message
        
    except Exception as e:
        print(f"model load error: {e}")
        return False, f"Error loading model: {e}"


# ================ PREDICT WITH SINGLE MODEL ================

def forecast_with_loaded_model(update_callback):
    # run forecast using pre-loaded single model
    try:
        print(f"forecast_with_loaded_model called, STATE.loaded_model = {STATE.loaded_model}")
        
        if STATE.loaded_model is None:
            update_callback(False, "No single model loaded.", None)
            return
            
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        working_data, _ = _prepare_working_data(STATE.clean_data, STATE.forecast_granularity)
        
        df_pivot = prepare_for_autots(working_data, use_features=False)
        df_pivot = df_pivot.set_index('Date')
        
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        print("generating forecast with loaded model")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # use number of periods directly
            STATE.loaded_model.forecast_length = STATE.forecast_days
            prediction = STATE.loaded_model.predict()
        
        forecast_df = prediction.forecast
        upper_forecast = prediction.upper_forecast
        lower_forecast = prediction.lower_forecast
        
        STATE.forecast_data = forecast_df
        STATE.upper_forecast = upper_forecast
        STATE.lower_forecast = lower_forecast
        
        output_dir = get_output_directory()
        chart_grouping = STATE.chart_grouping
        
        chart_path = generate_forecast_chart(
            df_pivot, forecast_df, upper_forecast, lower_forecast, chart_grouping
        )
        
        export_forecast_csv(forecast_df, output_dir / "forecast_data.csv")
        
        update_callback(True, "Forecast complete (used loaded model)", chart_path)
        
    except Exception as e:
        print(f"forecast error with loaded model: {e}")
        import traceback
        traceback.print_exc()
        update_callback(False, f"Forecast error: {e}", None)
    
    finally:
        STATE.is_forecasting = False
        force_gc()


# ================ PREDICT WITH PARALLEL MODELS ================

def predict_single_sku_with_model(sku, model, forecast_periods):
    # predict using a single loaded model for one sku
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            model.forecast_length = forecast_periods
            prediction = model.predict()
            
            if sku in prediction.forecast.columns:
                forecast = prediction.forecast[sku]
                upper = prediction.upper_forecast[sku]
                lower = prediction.lower_forecast[sku]
            else:
                # model might have different column name
                forecast = prediction.forecast.iloc[:, 0]
                upper = prediction.upper_forecast.iloc[:, 0]
                lower = prediction.lower_forecast.iloc[:, 0]
            
            return (sku, forecast, upper, lower, None)
            
    except Exception as e:
        return (sku, None, None, None, str(e))


def forecast_with_parallel_models(update_callback):
    # run forecast using pre-loaded parallel models
    try:
        print(f"forecast_with_parallel_models called, {len(STATE.saved_models)} models")
        
        if not STATE.saved_models:
            update_callback(False, "No parallel models loaded.", None)
            return
            
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        working_data, _ = _prepare_working_data(STATE.clean_data, STATE.forecast_granularity)
        df_pivot = prepare_for_autots(working_data, use_features=False).set_index('Date')
        
        # use number of periods directly
        forecast_periods = STATE.forecast_days
        
        print(f"predicting {len(STATE.saved_models)} skus with loaded models")
        
        forecast_dict = {}
        upper_dict = {}
        lower_dict = {}
        errors = {}
        
        # run predictions
        max_workers = min(multiprocessing.cpu_count(), 8)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            for sku, model in STATE.saved_models.items():
                if STATE.is_cancelled():
                    break
                
                future = executor.submit(
                    predict_single_sku_with_model,
                    sku,
                    model,
                    forecast_periods
                )
                futures[future] = sku
            
            for future in futures:
                if STATE.is_cancelled():
                    break
                
                sku = futures[future]
                
                try:
                    result_sku, forecast, upper, lower, error = future.result()
                    
                    if error:
                        errors[sku] = error
                        print(f"sku {sku} error: {error}")
                    else:
                        forecast_dict[sku] = forecast
                        upper_dict[sku] = upper
                        lower_dict[sku] = lower
                        
                except Exception as e:
                    errors[sku] = str(e)[:50]
        
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        if not forecast_dict:
            update_callback(False, f"No successful predictions. Errors: {len(errors)}", None)
            return
        
        # combine results
        forecast_df = pd.DataFrame(forecast_dict)
        upper_forecast = pd.DataFrame(upper_dict)
        lower_forecast = pd.DataFrame(lower_dict)
        
        # clean results
        forecast_df = forecast_df.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        upper_forecast = upper_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        lower_forecast = lower_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        
        STATE.forecast_data = forecast_df
        STATE.upper_forecast = upper_forecast
        STATE.lower_forecast = lower_forecast
        
        # generate outputs
        output_dir = get_output_directory()
        chart_grouping = STATE.chart_grouping
        
        chart_path = generate_forecast_chart(
            df_pivot, forecast_df, upper_forecast, lower_forecast, chart_grouping
        )
        
        export_forecast_csv(forecast_df, output_dir / "forecast_data.csv")
        upper_forecast.to_csv(output_dir / "forecast_upper.csv", index=True)
        lower_forecast.to_csv(output_dir / "forecast_lower.csv", index=True)
        
        success_count = len(forecast_dict)
        error_count = len(errors)
        message = f"Forecast complete (loaded models): {success_count} SKUs"
        if error_count > 0:
            message += f", {error_count} errors"
        
        update_callback(True, message, chart_path)
        
    except Exception as e:
        print(f"forecast error with parallel models: {e}")
        import traceback
        traceback.print_exc()
        update_callback(False, f"Forecast error: {e}", None)
    
    finally:
        STATE.is_forecasting = False
        force_gc()


# ================ SINGLE SKU FORECAST ================

def forecast_single_sku(sku_data_dict, forecast_periods, frequency):
    # forecast single sku with its own features
    # returns tuple of sku_name forecast upper lower metadata model error
    sku_name = sku_data_dict['sku']
    
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # get pivot data
            df = sku_data_dict['pivot'].copy()
            df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # skip if all zeros
            if df[sku_name].sum() == 0:
                return (sku_name, None, None, None, None, None, "all zeros")
            
            # calculate min train percent
            data_length = len(df)
            min_train_pct = max(0.5, 1 - (forecast_periods / data_length))
            
            # check for sku-specific exogenous
            exog = None
            future_exog = None
            used_features = []
            
            if 'exogenous' in sku_data_dict and sku_data_dict['exogenous'] is not None:
                exog = sku_data_dict['exogenous']
                used_features = sku_data_dict.get('feature_columns', [])
                
                common_idx = df.index.intersection(exog.index)
                if len(common_idx) >= data_length * 0.5:
                    df = df.loc[common_idx]
                    exog = exog.loc[common_idx]
                    
                    if 'encoder' in sku_data_dict and 'last_exog_values' in sku_data_dict:
                        encoder = sku_data_dict['encoder']
                        last_date = df.index.max()
                        
                        if frequency == 'W-MON':
                            future_dates = pd.date_range(
                                start=last_date + pd.Timedelta(weeks=1), 
                                periods=forecast_periods, 
                                freq='W-MON'
                            )
                        elif frequency == 'MS':
                            future_dates = pd.date_range(
                                start=last_date + pd.DateOffset(months=1), 
                                periods=forecast_periods, 
                                freq='MS'
                            )
                        else:
                            future_dates = pd.date_range(
                                start=last_date + pd.Timedelta(days=1), 
                                periods=forecast_periods, 
                                freq='D'
                            )
                        
                        future_exog = encoder.create_future_exog(
                            sku_data_dict['last_exog_values'],
                            future_dates
                        )
                else:
                    exog = None
                    used_features = []
            
            # get speed config from state
            speed_config = STATE.get_speed_config()
            
            # configure model based on speed
            model = AutoTS(
                forecast_length=forecast_periods,
                frequency=frequency,
                ensemble=speed_config.get('ensemble'),
                max_generations=speed_config.get('max_generations', 1),
                num_validations=speed_config.get('num_validations', 0),
                validation_method='backwards',
                model_list=speed_config.get('model_list', 'superfast'),
                transformer_list=speed_config.get('transformer_list', 'superfast'),
                models_to_validate=speed_config.get('models_to_validate', 0.15),
                n_jobs=1,
                min_allowed_train_percent=min_train_pct,
                no_negatives=True,
                drop_most_recent=0,
                prediction_interval=AutoTSConfig.PREDICTION_INTERVAL,
                random_seed=42,
                verbose=0
            )
            
            # fit model
            if exog is not None and len(exog.columns) > 0:
                model = model.fit(df, future_regressor=exog)
            else:
                model = model.fit(df)
            
            # predict
            if future_exog is not None and len(future_exog.columns) > 0:
                prediction = model.predict(future_regressor=future_exog)
            else:
                prediction = model.predict()
            
            forecast = prediction.forecast[sku_name]
            upper = prediction.upper_forecast[sku_name]
            lower = prediction.lower_forecast[sku_name]
            
            # build metadata
            metadata = {
                'data_points': data_length,
                'used_features': used_features,
                'feature_count': len(used_features),
                'seasonality': sku_data_dict.get('seasonality', {})
            }
            
            return (sku_name, forecast, upper, lower, metadata, model, None)
            
    except Exception as e:
        return (sku_name, None, None, None, None, None, str(e))


# ================ PARALLEL FORECASTING ================

def run_parallel_forecast_heterogeneous(df, encoder_manager, forecast_periods, frequency, max_workers=None):
    # run forecasts for all skus in parallel
    # each sku uses its own feature set
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), 8)
    
    skus = df['SKU'].unique().tolist()
    total_skus = len(skus)
    
    print(f"parallel forecast: {total_skus} skus, {max_workers} workers")
    
    # prepare all sku data first
    print("preparing sku data...")
    sku_data_list = []
    feature_counts = []
    
    for sku in skus:
        sku_data = prepare_sku_forecast_data(df, sku, encoder_manager)
        if sku_data is not None:
            sku_data_list.append(sku_data)
            feature_counts.append(len(sku_data.get('feature_columns', [])))
        else:
            STATE.skipped_skus[sku] = "no valid data"
    
    print(f"prepared {len(sku_data_list)} skus")
    
    if STATE.is_cancelled():
        return {}
    
    results = {}
    with_features = 0
    
    # run parallel forecasts
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        
        for sku_data in sku_data_list:
            if STATE.is_cancelled():
                break
            
            future = executor.submit(
                forecast_single_sku, 
                sku_data, 
                forecast_periods, 
                frequency
            )
            futures[future] = sku_data['sku']
        
        for future in futures:
            if STATE.is_cancelled():
                break
            
            sku_name = futures[future]
            
            try:
                result_sku, forecast, upper, lower, metadata, model, error = future.result()
                
                if error:
                    STATE.skipped_skus[sku_name] = error
                else:
                    results[sku_name] = {
                        'forecast': forecast,
                        'upper': upper,
                        'lower': lower,
                        'metadata': metadata,
                        'model': model
                    }
                    STATE.successful_skus.append(sku_name)
                    if metadata and metadata.get('feature_count', 0) > 0:
                        with_features += 1
                    
            except Exception as e:
                STATE.skipped_skus[sku_name] = str(e)[:50]
    
    return results


# ================ FORECASTING ================

def run_forecast_thread(update_callback):
    # execute autots forecast in thread
    scaler = DataScaler()
    
    try:
        STATE.reset_cancel_flag()
        force_gc()
        
        # ---------- DATA PREPARATION ----------
        working_data, data_info = _prepare_working_data(
            STATE.clean_data, STATE.forecast_granularity
        )
        
        if data_info['sampled']:
            print(f"data sampled: {data_info['original_rows']} -> {data_info['sampled_rows']} rows")
            
        force_gc()
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- DETERMINE FREQUENCY & PERIODS ----------
        freq_map = {'Weekly': 'W-MON', 'Monthly': 'MS', 'Quarterly': 'QS'}
        frequency = freq_map.get(STATE.forecast_granularity, 'D')
        forecast_periods = STATE.forecast_days
        
        # ---------- FEATURE ENGINEERING ----------
        encoder_manager = None
        feature_columns = STATE.selected_features if STATE.use_features else []
        
        if feature_columns:
            print(f"building per-sku encoders for {len(feature_columns)} potential features")
            encoder_manager = FeatureEncoderManager()
            encoder_manager.fit(working_data, feature_columns)
            encoder_manager.print_summary()
            STATE.encoders = encoder_manager
            
            importance = analyze_feature_importance(working_data, feature_columns)
            print("feature importance analysis complete")
        
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- FORECAST METHOD SELECTION ----------
        num_skus = working_data['SKU'].nunique()
        use_parallel = num_skus > 10
        results = {}
        skus_with_features = 0
        
        if use_parallel:
            # ---------- PARALLEL FORECAST ----------
            print(f"using parallel forecast for {num_skus} skus")
            
            results = run_parallel_forecast_heterogeneous(
                working_data, encoder_manager, forecast_periods, frequency
            )
            
            if STATE.is_cancelled():
                update_callback(False, "Forecast cancelled", None)
                return
            
            if not results:
                update_callback(False, "No successful forecasts", None)
                return
            
            # combine results
            forecast_dict = {k: v['forecast'] for k, v in results.items()}
            upper_dict = {k: v['upper'] for k, v in results.items()}
            lower_dict = {k: v['lower'] for k, v in results.items()}
            metadata_dict = {k: v['metadata'] for k, v in results.items()}
            
            # store parallel models dont overwrite loaded_model
            if not STATE.has_loaded_models:
                STATE.saved_models = {k: v['model'] for k, v in results.items()}
            
            forecast_df = pd.DataFrame(forecast_dict)
            upper_forecast = pd.DataFrame(upper_dict)
            lower_forecast = pd.DataFrame(lower_dict)
            
            STATE.sku_feature_map = metadata_dict
            skus_with_features = sum(1 for m in metadata_dict.values() if m and m.get('feature_count', 0) > 0)
            
        else:
            # ---------- SINGLE MODEL FORECAST ----------
            print(f"using single model for {num_skus} skus")
            
            if feature_columns and STATE.use_features:
                df_base, metadata = prepare_multicolumn_forecast(
                    working_data, feature_columns, include_seasonality=True
                )
                df_pivot = prepare_for_autots(df_base, use_features=False)
                STATE.exog_data = metadata.get('exogenous')
                STATE.seasonality_info = metadata.get('seasonality', STATE.seasonality_info)
            else:
                df_pivot = prepare_for_autots(working_data, use_features=False)
            
            df_pivot = df_pivot.set_index('Date')
            df_pivot = scaler.fit_transform(df_pivot)
            df_pivot = optimize_dataframe(df_pivot)
            df_pivot = df_pivot.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            data_length = len(df_pivot)
            min_train_pct = max(0.5, 1 - (forecast_periods / data_length) if data_length > 0 else 0.5)

            
            # callback function to check for cancellation during model fitting
            def autots_callback(status_dict):
                if STATE.is_cancelled():
                    raise InterruptedError("Forecast cancelled by user.")

            model = AutoTS(
                forecast_length=forecast_periods,
                frequency=frequency,
                ensemble='simple',
                max_generations=2,
                num_validations=0,
                validation_method='backwards',
                model_list='fast',
                transformer_list='fast',
                n_jobs='auto',
                min_allowed_train_percent=min_train_pct,
                no_negatives=True,
                drop_most_recent=0,
                prediction_interval=AutoTSConfig.PREDICTION_INTERVAL,
                random_seed=42,
                verbose=0
            )
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = model.fit(df_pivot, callback=autots_callback)
            
            # store as last trained model dont overwrite loaded_model
            STATE.last_trained_model = model
            if not STATE.has_loaded_models:
                STATE.saved_models = {}
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                prediction = model.predict()
            
            forecast_df = scaler.inverse_transform(prediction.forecast)
            upper_forecast = scaler.inverse_transform(prediction.upper_forecast)
            lower_forecast = scaler.inverse_transform(prediction.lower_forecast)
        
        # ---------- STORE RESULTS ----------
        forecast_df = forecast_df.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        upper_forecast = upper_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        lower_forecast = lower_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        
        STATE.forecast_data = forecast_df
        STATE.upper_forecast = upper_forecast
        STATE.lower_forecast = lower_forecast
        
        force_gc()
        
        # ---------- GENERATE OUTPUTS ----------
        output_dir = get_output_directory()
        chart_grouping = STATE.chart_grouping
        
        df_pivot_display = prepare_for_autots(working_data, use_features=False).set_index('Date')
        
        chart_path = generate_forecast_chart(
            df_pivot_display, forecast_df, upper_forecast, lower_forecast, chart_grouping
        )
        
        export_forecast_csv(forecast_df, output_dir / "forecast_data.csv")
        upper_forecast.to_csv(output_dir / "forecast_upper.csv", index=True)
        lower_forecast.to_csv(output_dir / "forecast_lower.csv", index=True)
        export_summary_report(forecast_df, STATE.clean_data, output_dir / "summary.txt")
        
        status_msg = _build_status_message(
            forecast_periods, STATE.forecast_granularity, use_parallel, 
            results, skus_with_features, data_info
        )
        
        update_callback(True, status_msg, chart_path)
        
    except InterruptedError:
        print("forecast cancelled by callback")
        force_gc()
        update_callback(False, "Forecast cancelled", None)
        
    except MemoryError:
        print("memory error during forecast")
        force_gc()
        update_callback(False, "Out of memory - reduce data size", None)
        
    except Exception as e:
        print(f"forecast error: {e}")
        import traceback
        traceback.print_exc()
        update_callback(False, f"Forecast error: {str(e)[:50]}", None)
    
    finally:
        STATE.is_forecasting = False
        force_gc()