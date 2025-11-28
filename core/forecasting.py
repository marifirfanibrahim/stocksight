"""
forecasting operations
autots model training and prediction
"""


# ================ IMPORTS ================

import threading
import json
import gc
import pickle
from pathlib import Path
from autots import AutoTS
import dearpygui.dearpygui as dpg
import pandas as pd

from config import AutoTSConfig, DataConfig
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


# ================ MODEL STORAGE ================

last_model = None


# ================ MEMORY MANAGEMENT ================

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


def check_data_size(df, max_rows=50000):
    """
    check if data needs sampling
    return sampled df if too large
    """
    if len(df) > max_rows:
        print(f"large dataset detected: {len(df)} rows, sampling to {max_rows}")
        
        # sample while keeping date order
        df_sorted = df.sort_values('Date')
        
        # keep recent data
        df_sampled = df_sorted.tail(max_rows)
        
        return df_sampled, True
    
    return df, False


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
    global last_model
    
    try:
        if STATE.loaded_model is None:
            update_callback(False, "No model loaded", None)
            return
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- PREPARE DATA ----------
        working_data = STATE.clean_data.copy()
        
        if STATE.forecast_granularity != 'Daily':
            working_data = aggregate_before_forecast(working_data, STATE.forecast_granularity)
        
        df_pivot = prepare_for_autots(working_data, use_features=False)
        df_pivot = df_pivot.set_index('Date')
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        print("generating forecast with loaded model")
        
        # ---------- GENERATE FORECAST ----------
        prediction = STATE.loaded_model.predict()
        forecast_df = prediction.forecast
        upper_forecast = prediction.upper_forecast
        lower_forecast = prediction.lower_forecast
        
        # ---------- STORE RESULTS ----------
        STATE.forecast_data = forecast_df
        STATE.upper_forecast = upper_forecast
        STATE.lower_forecast = lower_forecast
        
        # ---------- GENERATE OUTPUTS ----------
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
        gc.collect()


# ================ FORECASTING ================

def run_forecast_thread(update_callback):
    """
    execute autots forecast in thread
    """
    global last_model
    
    try:
        STATE.reset_cancel_flag()
        
        # ---------- GET WORKING DATA ----------
        working_data = STATE.clean_data.copy()
        
        # ---------- CHECK DATA SIZE ----------
        working_data, was_sampled = check_data_size(working_data)
        if was_sampled:
            print("data was sampled for memory efficiency")
        
        # ---------- OPTIMIZE MEMORY ----------
        working_data = optimize_dataframe(working_data)
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- PRE-AGGREGATE IF NEEDED ----------
        if STATE.forecast_granularity != 'Daily':
            working_data = aggregate_before_forecast(working_data, STATE.forecast_granularity)
            print(f"forecasting at {STATE.forecast_granularity} granularity")
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
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
            print(f"using features: {STATE.selected_features}")
        else:
            df_pivot = prepare_for_autots(working_data, use_features=False)
        
        # ---------- SET DATE INDEX ----------
        df_pivot = df_pivot.set_index('Date')
        
        # ---------- OPTIMIZE PIVOT ----------
        df_pivot = optimize_dataframe(df_pivot)
        
        # ---------- CHECK DATA LENGTH ----------
        data_length = len(df_pivot)
        forecast_days = STATE.forecast_days
        
        # ---------- ADJUST FORECAST PERIODS FOR GRANULARITY ----------
        if STATE.forecast_granularity == 'Weekly':
            forecast_periods = max(1, forecast_days // 7)
        elif STATE.forecast_granularity == 'Monthly':
            forecast_periods = max(1, forecast_days // 30)
        elif STATE.forecast_granularity == 'Quarterly':
            forecast_periods = max(1, forecast_days // 90)
        else:
            forecast_periods = forecast_days
        
        # ---------- ADJUST IF NEEDED ----------
        if data_length < forecast_periods * 2:
            max_forecast = max(1, data_length // 3)
            print(f"adjusted forecast from {forecast_periods} to {max_forecast} periods")
            forecast_periods = max_forecast
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- CALCULATE MIN TRAIN PERCENT ----------
        min_train_pct = max(0.5, 1 - (forecast_periods / data_length))
        
        # ---------- DETERMINE FREQUENCY ----------
        if STATE.forecast_granularity == 'Weekly':
            frequency = 'W'
        elif STATE.forecast_granularity == 'Monthly':
            frequency = 'MS'
        elif STATE.forecast_granularity == 'Quarterly':
            frequency = 'QS'
        else:
            frequency = 'infer'
        
        # ---------- LIMIT SKU COUNT FOR MEMORY ----------
        num_skus = len(df_pivot.columns)
        if num_skus > 50:
            print(f"limiting skus from {num_skus} to 50 for memory")
            top_skus = df_pivot.sum().nlargest(50).index.tolist()
            df_pivot = df_pivot[top_skus]
        
        # ---------- CONFIGURE AUTOTS ----------
        model = AutoTS(
            forecast_length=forecast_periods,
            frequency=frequency,
            ensemble='simple',
            max_generations=AutoTSConfig.FAST_MODE['max_generations'],
            num_validations=0,
            validation_method='backwards',
            model_list=AutoTSConfig.FAST_MODE['model_list'],
            transformer_list=AutoTSConfig.FAST_MODE['transformer_list'],
            n_jobs='auto',
            min_allowed_train_percent=min_train_pct,
            no_negatives=True,
            constraint=None,
            drop_most_recent=0,
            prediction_interval=AutoTSConfig.PREDICTION_INTERVAL,
            random_seed=42,
            verbose=0
        )
        
        print(f"training autots model with {data_length} data points, {len(df_pivot.columns)} skus")
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- FIT MODEL ----------
        model = model.fit(df_pivot)
        
        # ---------- CHECK CANCELLATION ----------
        if STATE.is_cancelled():
            update_callback(False, "Forecast cancelled", None)
            return
        
        # ---------- STORE MODEL ----------
        last_model = model
        
        print("generating forecast")
        
        # ---------- GENERATE FORECAST ----------
        prediction = model.predict()
        forecast_df = prediction.forecast
        upper_forecast = prediction.upper_forecast
        lower_forecast = prediction.lower_forecast
        
        # ---------- STORE RESULTS ----------
        STATE.forecast_data = forecast_df
        STATE.upper_forecast = upper_forecast
        STATE.lower_forecast = lower_forecast
        
        # ---------- CLEANUP MEMORY ----------
        del working_data
        gc.collect()
        
        # ---------- GET OUTPUT DIRECTORY ----------
        output_dir = get_output_directory()
        
        # ---------- GET CHART GROUPING ----------
        chart_grouping = dpg.get_value("chart_grouping_combo") if dpg.does_item_exist("chart_grouping_combo") else "Daily"
        
        # ---------- GENERATE CHART WITH GROUPING ----------
        chart_path = generate_forecast_chart(
            df_pivot, 
            forecast_df, 
            upper_forecast, 
            lower_forecast,
            chart_grouping
        )
        
        # ---------- EXPORT DATA ----------
        export_forecast_csv(forecast_df, output_dir / "forecast_data.csv")
        upper_forecast.to_csv(output_dir / "forecast_upper.csv", index=True)
        lower_forecast.to_csv(output_dir / "forecast_lower.csv", index=True)
        
        # ---------- EXPORT SUMMARY ----------
        export_summary_report(forecast_df, STATE.clean_data, output_dir / "summary.txt")
        
        # ---------- EXPORT SEASONALITY INFO ----------
        if STATE.seasonality_info:
            with open(output_dir / "seasonality_info.json", 'w') as f:
                json.dump(STATE.seasonality_info, f, indent=2, default=str)
        
        granularity_label = f" ({STATE.forecast_granularity})" if STATE.forecast_granularity != 'Daily' else ""
        update_callback(True, f"Forecast complete: {forecast_periods} periods{granularity_label}", chart_path)
        
    except MemoryError:
        print("memory error during forecast")
        gc.collect()
        update_callback(False, "Out of memory - try smaller dataset or aggregation", None)
        
    except Exception as e:
        print(f"forecast error: {e}")
        import traceback
        traceback.print_exc()
        update_callback(False, f"Forecast error: {e}", None)
    
    finally:
        STATE.is_forecasting = False
        gc.collect()