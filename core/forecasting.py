"""
forecasting operations
autots model training and prediction
"""


# ================ IMPORTS ================

import threading
import json
from autots import AutoTS
import dearpygui.dearpygui as dpg

from config import AutoTSConfig
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


# ================ FORECASTING ================

def run_forecast_thread(update_callback):
    """
    execute autots forecast in thread
    update_callback for ui updates
    """
    try:
        # ---------- GET WORKING DATA ----------
        working_data = STATE.clean_data.copy()
        
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
            print(f"using features: {STATE.selected_features}")
        else:
            df_pivot = prepare_for_autots(working_data, use_features=False)
        
        # ---------- SET DATE INDEX ----------
        df_pivot = df_pivot.set_index('Date')
        
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
        
        # ---------- CALCULATE MIN TRAIN PERCENT ----------
        min_train_pct = max(0.5, 1 - (forecast_periods / data_length))
        
        # ---------- DETERMINE FREQUENCY ----------
        if STATE.forecast_granularity == 'Weekly':
            frequency = 'W'
        elif STATE.forecast_granularity == 'Monthly':
            frequency = 'M'
        elif STATE.forecast_granularity == 'Quarterly':
            frequency = 'Q'
        else:
            frequency = 'infer'
        
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
            random_seed=42
        )
        
        print(f"training autots model with {data_length} data points")
        print(f"forecast periods: {forecast_periods} ({STATE.forecast_granularity})")
        print(f"prediction interval: {AutoTSConfig.PREDICTION_INTERVAL}")
        
        if STATE.seasonality_info.get('has_monthly_seasonality'):
            print("detected monthly seasonality")
        if STATE.seasonality_info.get('has_weekly_seasonality'):
            print("detected weekly seasonality")
        
        # ---------- FIT MODEL ----------
        model = model.fit(df_pivot)
        
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
        
        # ---------- GET OUTPUT DIRECTORY ----------
        output_dir = get_output_directory()
        
        # ---------- GET CHART GROUPING ----------
        try:
            chart_grouping = dpg.get_value("chart_grouping_combo")
        except:
            chart_grouping = "Daily"
        
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
        
        # ---------- EXPORT CONFIDENCE BOUNDS ----------
        upper_forecast.to_csv(output_dir / "forecast_upper.csv", index=True)
        lower_forecast.to_csv(output_dir / "forecast_lower.csv", index=True)
        
        # ---------- EXPORT SUMMARY ----------
        export_summary_report(forecast_df, STATE.clean_data, output_dir / "summary.txt")
        
        # ---------- EXPORT SEASONALITY INFO ----------
        if STATE.seasonality_info:
            with open(output_dir / "seasonality_info.json", 'w') as f:
                json.dump(STATE.seasonality_info, f, indent=2, default=str)
        
        print(f"forecast complete")
        print(f"saved to: {output_dir}")
        
        granularity_label = f" ({STATE.forecast_granularity})" if STATE.forecast_granularity != 'Daily' else ""
        update_callback(True, f"Forecast complete: {forecast_periods} periods{granularity_label} | Saved to {output_dir}", chart_path)
        
    except Exception as e:
        print(f"forecast error: {e}")
        import traceback
        traceback.print_exc()
        update_callback(False, f"Forecast error: {str(e)}", None)
    
    finally:
        STATE.is_forecasting = False