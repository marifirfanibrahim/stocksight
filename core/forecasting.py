"""
forecasting operations
autots model training and prediction
"""


# ================ IMPORTS ================

import threading
import json
import gc
import pickle
import warnings
from pathlib import Path

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
from utils.features import prepare_multicolumn_forecast


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
        
        # keep top skus by total quantity
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
        
        # ---------- PREPARE DATA ----------
        if STATE.feature_columns and STATE.use_features:
            df_base, metadata = prepare_multicolumn_forecast(
                working_data, 
                STATE.selected_features, 
                include_seasonality=True
            )
            df_pivot = prepare_for_autots(df_base, use_features=False)
            STATE.exog_data = metadata.get('exogenous')
            STATE.encoders = metadata.get('encoders')
            STATE.seasonality_info = metadata.get('seasonality', STATE.seasonality_info)
        else:
            df_pivot = prepare_for_autots(working_data, use_features=False)
        
        # ---------- FREE MEMORY ----------
        del working_data
        force_gc()
        
        # ---------- SET DATE INDEX ----------
        df_pivot = df_pivot.set_index('Date')
        
        # ---------- SCALE DATA ----------
        df_pivot = scaler.fit_transform(df_pivot)
        
        # ---------- OPTIMIZE PIVOT ----------
        df_pivot = optimize_dataframe(df_pivot)
        
        # ---------- REPLACE INF/NAN ----------
        df_pivot = df_pivot.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # ---------- CHECK DATA LENGTH ----------
        data_length = len(df_pivot)
        forecast_days = STATE.forecast_days
        
        # ---------- ADJUST FORECAST PERIODS ----------
        if STATE.forecast_granularity == 'Weekly':
            forecast_periods = max(1, forecast_days // 7)
        elif STATE.forecast_granularity == 'Monthly':
            forecast_periods = max(1, forecast_days // 30)
        elif STATE.forecast_granularity == 'Quarterly':
            forecast_periods = max(1, forecast_days // 90)
        else:
            forecast_periods = forecast_days
        
        if data_length < forecast_periods * 2:
            max_forecast = max(1, data_length // 3)
            print(f"adjusted forecast: {forecast_periods} -> {max_forecast} periods")
            forecast_periods = max_forecast
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- CALCULATE MIN TRAIN PERCENT ----------
        min_train_pct = max(0.5, 1 - (forecast_periods / data_length))
        
        # ---------- DETERMINE FREQUENCY ----------
        freq_map = {'Weekly': 'W', 'Monthly': 'MS', 'Quarterly': 'QS'}
        frequency = freq_map.get(STATE.forecast_granularity, 'infer')
        
        # ---------- CONFIGURE AUTOTS ----------
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
        
        num_skus = len(df_pivot.columns)
        print(f"training: {data_length} rows, {num_skus} skus")
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- FIT MODEL ----------
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = model.fit(df_pivot)
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- STORE MODEL ----------
        last_model = model
        
        print("generating forecast")
        
        # ---------- GENERATE FORECAST ----------
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            prediction = model.predict()
        
        forecast_df = prediction.forecast
        upper_forecast = prediction.upper_forecast
        lower_forecast = prediction.lower_forecast
        
        # ---------- INVERSE SCALE ----------
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
        
        # ---------- RESTORE SCALE FOR DISPLAY ----------
        df_pivot_display = scaler.inverse_transform(df_pivot)
        
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
        status_parts = [f"Forecast complete: {forecast_periods} periods"]
        
        if STATE.forecast_granularity != 'Daily':
            status_parts.append(f"({STATE.forecast_granularity})")
        
        if data_info['sampled'] or data_info['sku_limited']:
            status_parts.append("[reduced]")
        
        update_callback(True, " ".join(status_parts), chart_path)
        
    except MemoryError:
        print("memory error during forecast")
        force_gc()
        update_callback(False, "Out of memory - use Weekly/Monthly aggregation", None)
        
    except Exception as e:
        print(f"forecast error: {e}")
        import traceback
        traceback.print_exc()
        update_callback(False, f"Forecast error: {str(e)[:50]}", None)
    
    finally:
        STATE.is_forecasting = False
        force_gc()