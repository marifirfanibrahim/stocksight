"""
forecasting operations
autots model training and prediction
supports heterogeneous per-sku features
"""


# ================ IMPORTS ================

import threading
import json
import gc
import pickle
import warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

import numpy as np
import pandas as pd
from autots import AutoTS
import dearpygui.dearpygui as dpg

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


# ================ MODEL STORAGE ================

last_model = None


# ================ MEMORY MANAGEMENT ================

def force_gc():
    """
    force garbage collection
    """
    gc.collect()
    gc.collect()
    gc.collect()


def optimize_dataframe(df):
    """
    reduce memory usage of dataframe
    """
    for col in df.columns:
        if df[col].dtype == 'float64':
            df[col] = df[col].astype('float32')
        elif df[col].dtype == 'int64':
            df[col] = df[col].astype('int32')
    return df


def check_and_reduce_data(df):
    """
    check data size and reduce if needed
    return reduced df and info dict
    """
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
    
    # ---------- LIMIT SKUS IF NEEDED ----------
    num_skus = df['SKU'].nunique()
    if num_skus > LargeDataConfig.MAX_SKUS:
        print(f"limiting skus: {num_skus} -> {LargeDataConfig.MAX_SKUS}")
        
        top_skus = df.groupby('SKU')['Quantity'].sum().nlargest(LargeDataConfig.MAX_SKUS).index.tolist()
        df = df[df['SKU'].isin(top_skus)]
        
        info['sku_limited'] = True
        info['limited_skus'] = len(top_skus)
    
    return df, info


# ================ SCALING ================

class DataScaler:
    """
    scale data to prevent overflow
    """
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


# ================ MODEL LOADING ================

def load_saved_model(model_path):
    """
    load previously saved model
    """
    global last_model
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        last_model = model
        STATE.loaded_model = model
        STATE.loaded_model_path = str(model_path)
        
        print(f"model loaded: {model_path}")
        return True, "Model loaded successfully"
        
    except Exception as e:
        print(f"model load error: {e}")
        return False, f"Error loading model: {e}"


def forecast_with_loaded_model(update_callback):
    """
    run forecast using loaded model
    """
    try:
        if STATE.loaded_model is None:
            update_callback(False, "No model loaded", None)
            return
        
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        working_data = STATE.clean_data.copy()
        
        if STATE.forecast_granularity != 'Daily':
            working_data = aggregate_before_forecast(working_data, STATE.forecast_granularity)
        
        df_pivot = prepare_for_autots(working_data, use_features=False)
        df_pivot = df_pivot.set_index('Date')
        
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        print("generating forecast with loaded model")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            prediction = STATE.loaded_model.predict()
        
        forecast_df = prediction.forecast
        upper_forecast = prediction.upper_forecast
        lower_forecast = prediction.lower_forecast
        
        STATE.forecast_data = forecast_df
        STATE.upper_forecast = upper_forecast
        STATE.lower_forecast = lower_forecast
        
        output_dir = get_output_directory()
        chart_grouping = dpg.get_value("chart_grouping_combo") if dpg.does_item_exist("chart_grouping_combo") else "Daily"
        
        chart_path = generate_forecast_chart(
            df_pivot, forecast_df, upper_forecast, lower_forecast, chart_grouping
        )
        
        export_forecast_csv(forecast_df, output_dir / "forecast_data.csv")
        
        update_callback(True, "Forecast complete (loaded model)", chart_path)
        
    except Exception as e:
        print(f"forecast error: {e}")
        import traceback
        traceback.print_exc()
        update_callback(False, f"Forecast error: {e}", None)
    
    finally:
        STATE.is_forecasting = False
        force_gc()


# ================ SINGLE SKU FORECAST ================

def forecast_single_sku(sku_data_dict, forecast_periods, frequency):
    """
    forecast single sku with its own features
    returns tuple of (sku_name, forecast, upper, lower, metadata, error)
    """
    sku_name = sku_data_dict['sku']
    
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # get pivot data
            df = sku_data_dict['pivot'].copy()
            df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # skip if all zeros
            if df[sku_name].sum() == 0:
                return (sku_name, None, None, None, None, "all zeros")
            
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
                
                # align exog with pivot index
                common_idx = df.index.intersection(exog.index)
                if len(common_idx) >= data_length * 0.5:
                    df = df.loc[common_idx]
                    exog = exog.loc[common_idx]
                    
                    # create future exog
                    if 'encoder' in sku_data_dict and 'last_exog_values' in sku_data_dict:
                        encoder = sku_data_dict['encoder']
                        last_date = df.index.max()
                        
                        if frequency == 'W':
                            future_dates = pd.date_range(
                                start=last_date + pd.Timedelta(weeks=1), 
                                periods=forecast_periods, 
                                freq='W'
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
                    # not enough overlap
                    exog = None
                    used_features = []
            
            # configure model
            model = AutoTS(
                forecast_length=forecast_periods,
                frequency=frequency,
                ensemble='simple',
                max_generations=1,
                num_validations=0,
                validation_method='backwards',
                model_list='fast_parallel',
                transformer_list='fast',
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
            
            return (sku_name, forecast, upper, lower, metadata, None)
            
    except Exception as e:
        return (sku_name, None, None, None, None, str(e))


# ================ PARALLEL FORECASTING ================

def run_parallel_forecast_heterogeneous(df, encoder_manager, forecast_periods, frequency, max_workers=None):
    """
    run forecasts for all skus in parallel
    each sku uses its own feature set
    """
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
                result_sku, forecast, upper, lower, metadata, error = future.result()
                
                if error:
                    STATE.skipped_skus[sku_name] = error
                else:
                    results[sku_name] = {
                        'forecast': forecast,
                        'upper': upper,
                        'lower': lower,
                        'metadata': metadata
                    }
                    STATE.successful_skus.append(sku_name)
                    if metadata and metadata.get('feature_count', 0) > 0:
                        with_features += 1
                    
            except Exception as e:
                STATE.skipped_skus[sku_name] = str(e)[:50]
    
    return results


# ================ FORECASTING ================

def run_forecast_thread(update_callback):
    """
    execute autots forecast in thread
    """
    global last_model
    
    scaler = DataScaler()
    
    try:
        STATE.reset_cancel_flag()
        force_gc()
        
        # ---------- GET WORKING DATA ----------
        working_data = STATE.clean_data.copy()
        
        # ---------- CHECK AND REDUCE DATA ----------
        working_data, data_info = check_and_reduce_data(working_data)
        
        if data_info['sampled']:
            print(f"data sampled: {data_info['original_rows']} -> {data_info['sampled_rows']} rows")
        if data_info['sku_limited']:
            print(f"skus limited: {data_info['original_skus']} -> {data_info['limited_skus']}")
        
        # ---------- OPTIMIZE MEMORY ----------
        working_data = optimize_dataframe(working_data)
        force_gc()
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- PRE-AGGREGATE IF NEEDED ----------
        if STATE.forecast_granularity != 'Daily':
            working_data = aggregate_before_forecast(working_data, STATE.forecast_granularity)
            print(f"forecasting at {STATE.forecast_granularity} granularity")
        
        # ---------- DETERMINE FREQUENCY ----------
        freq_map = {'Weekly': 'W', 'Monthly': 'MS', 'Quarterly': 'QS'}
        frequency = freq_map.get(STATE.forecast_granularity, 'infer')
        
        # ---------- CALCULATE FORECAST PERIODS ----------
        forecast_days = STATE.forecast_days
        if STATE.forecast_granularity == 'Weekly':
            forecast_periods = max(1, forecast_days // 7)
        elif STATE.forecast_granularity == 'Monthly':
            forecast_periods = max(1, forecast_days // 30)
        elif STATE.forecast_granularity == 'Quarterly':
            forecast_periods = max(1, forecast_days // 90)
        else:
            forecast_periods = forecast_days
        
        # ---------- PREPARE ENCODER MANAGER ----------
        encoder_manager = None
        feature_columns = STATE.selected_features if STATE.use_features else []
        
        if feature_columns:
            print(f"building per-sku encoders for {len(feature_columns)} potential features")
            encoder_manager = FeatureEncoderManager()
            encoder_manager.fit(working_data, feature_columns)
            encoder_manager.print_summary()
            STATE.encoders = encoder_manager
            
            # analyze importance
            importance = analyze_feature_importance(working_data, feature_columns)
            print("feature importance:")
            for col, info in importance.items():
                if info.get('type') == 'numeric':
                    print(f"  {col}: corr={info.get('correlation', 0):.3f}, coverage={info.get('coverage', 0):.1%}")
                elif info.get('type') == 'categorical':
                    print(f"  {col}: var_ratio={info.get('variance_ratio', 0):.3f}, cats={info.get('num_categories', 0)}, coverage={info.get('coverage', 0):.1%}")
                elif info.get('type') == 'low_coverage':
                    print(f"  {col}: LOW COVERAGE ({info.get('coverage', 0):.1%}) - skipped")
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- DETERMINE FORECAST METHOD ----------
        num_skus = working_data['SKU'].nunique()
        use_parallel = num_skus > 10
        
        if use_parallel:
            # ---------- PARALLEL FORECAST ----------
            print(f"using parallel forecast for {num_skus} skus")
            
            results = run_parallel_forecast_heterogeneous(
                working_data, 
                encoder_manager,
                forecast_periods, 
                frequency
            )
            
            if STATE.is_cancelled():
                update_callback(False, "Forecast cancelled", None)
                return
            
            if not results:
                update_callback(False, "No successful forecasts", None)
                return
            
            # combine results into dataframes
            forecast_dict = {}
            upper_dict = {}
            lower_dict = {}
            metadata_dict = {}
            
            for sku, data in results.items():
                forecast_dict[sku] = data['forecast']
                upper_dict[sku] = data['upper']
                lower_dict[sku] = data['lower']
                metadata_dict[sku] = data['metadata']
            
            forecast_df = pd.DataFrame(forecast_dict)
            upper_forecast = pd.DataFrame(upper_dict)
            lower_forecast = pd.DataFrame(lower_dict)
            
            # store metadata
            STATE.sku_feature_map = metadata_dict
            
            # count skus using features
            skus_with_features = sum(1 for m in metadata_dict.values() if m and m.get('feature_count', 0) > 0)
            
            last_model = None
            
        else:
            # ---------- SINGLE MODEL FORECAST ----------
            print(f"using single model for {num_skus} skus")
            
            skus_with_features = 0
            
            # prepare data
            if feature_columns and STATE.use_features:
                df_base, metadata = prepare_multicolumn_forecast(
                    working_data, 
                    feature_columns, 
                    include_seasonality=True
                )
                df_pivot = prepare_for_autots(df_base, use_features=False)
                STATE.exog_data = metadata.get('exogenous')
                STATE.seasonality_info = metadata.get('seasonality', STATE.seasonality_info)
            else:
                df_pivot = prepare_for_autots(working_data, use_features=False)
            
            # set date index
            df_pivot = df_pivot.set_index('Date')
            
            # scale data
            df_pivot = scaler.fit_transform(df_pivot)
            df_pivot = optimize_dataframe(df_pivot)
            df_pivot = df_pivot.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            data_length = len(df_pivot)
            
            if data_length < forecast_periods * 2:
                max_forecast = max(1, data_length // 3)
                print(f"adjusted forecast: {forecast_periods} -> {max_forecast} periods")
                forecast_periods = max_forecast
            
            if STATE.is_cancelled():
                update_callback(False, "Forecast cancelled", None)
                return
            
            min_train_pct = max(0.5, 1 - (forecast_periods / data_length))
            
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
            
            print(f"training: {data_length} rows, {num_skus} skus")
            
            if STATE.is_cancelled():
                update_callback(False, "Forecast cancelled", None)
                return
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = model.fit(df_pivot)
            
            if STATE.is_cancelled():
                update_callback(False, "Forecast cancelled", None)
                return
            
            last_model = model
            
            print("generating forecast")
            
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                prediction = model.predict()
            
            forecast_df = prediction.forecast
            upper_forecast = prediction.upper_forecast
            lower_forecast = prediction.lower_forecast
            
            # inverse scale
            forecast_df = scaler.inverse_transform(forecast_df)
            upper_forecast = scaler.inverse_transform(upper_forecast)
            lower_forecast = scaler.inverse_transform(lower_forecast)
        
        # ---------- CLEAN RESULTS ----------
        forecast_df = forecast_df.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        upper_forecast = upper_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        lower_forecast = lower_forecast.replace([np.inf, -np.inf], np.nan).fillna(0).clip(lower=0)
        
        # ---------- STORE RESULTS ----------
        STATE.forecast_data = forecast_df
        STATE.upper_forecast = upper_forecast
        STATE.lower_forecast = lower_forecast
        
        force_gc()
        
        # ---------- GET OUTPUT DIRECTORY ----------
        output_dir = get_output_directory()
        
        # ---------- GET CHART GROUPING ----------
        chart_grouping = dpg.get_value("chart_grouping_combo") if dpg.does_item_exist("chart_grouping_combo") else "Daily"
        
        # ---------- PREPARE HISTORICAL FOR CHART ----------
        df_pivot_display = prepare_for_autots(working_data, use_features=False)
        df_pivot_display = df_pivot_display.set_index('Date')
        
        # ---------- GENERATE CHART ----------
        chart_path = generate_forecast_chart(
            df_pivot_display, forecast_df, upper_forecast, lower_forecast, chart_grouping
        )
        
        # ---------- EXPORT DATA ----------
        export_forecast_csv(forecast_df, output_dir / "forecast_data.csv")
        upper_forecast.to_csv(output_dir / "forecast_upper.csv", index=True)
        lower_forecast.to_csv(output_dir / "forecast_lower.csv", index=True)
        
        # ---------- EXPORT SUMMARY ----------
        export_summary_report(forecast_df, STATE.clean_data, output_dir / "summary.txt")
        
        # ---------- BUILD STATUS MESSAGE ----------
        status_parts = [f"Forecast: {forecast_periods} periods"]
        
        if STATE.forecast_granularity != 'Daily':
            status_parts.append(f"({STATE.forecast_granularity})")
        
        if use_parallel:
            status_parts.append(f"[{len(results)} SKUs]")
            if skus_with_features > 0:
                status_parts.append(f"[{skus_with_features} with features]")
        
        if data_info['sampled'] or data_info['sku_limited']:
            status_parts.append("[reduced]")
        
        update_callback(True, " ".join(status_parts), chart_path)
        
    except MemoryError:
        print("memory error during forecast")
        force_gc()
        update_callback(False, "Out of memory - reduce SKUs or use aggregation", None)
        
    except Exception as e:
        print(f"forecast error: {e}")
        import traceback
        traceback.print_exc()
        update_callback(False, f"Forecast error: {str(e)[:50]}", None)
    
    finally:
        STATE.is_forecasting = False
        force_gc()