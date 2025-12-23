"""
forecaster module
generates forecasts using multiple strategies
supports daily weekly and monthly frequencies
includes model comparison functionality
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import warnings

warnings.filterwarnings("ignore")

import config
from utils.logging_config import get_logger


# ============================================================================
#                               DATA CLASSES
# ============================================================================

@dataclass
class ForecastResult:
    # forecast result for single sku
    sku: str
    model: str
    forecast: List[float]
    dates: List[str]
    lower_bound: List[float]
    upper_bound: List[float]
    metrics: Dict[str, float]
    frequency: str = "D"


# ============================================================================
#                               FORECASTER
# ============================================================================

class Forecaster:
    # generates forecasts using configurable strategies
    
    # ---------- FREQUENCY MAPPINGS ----------
    FREQUENCY_MAP = {
        "daily": "D",
        "weekly": "W",
        "monthly": "M"
    }
    
    FREQUENCY_LABELS = {
        "D": "Daily",
        "W": "Weekly",
        "M": "Monthly"
    }
    
    def __init__(self):
        # initialize with forecast configuration
        self.config = config.FORECASTING
        self.model_settings = config.MODEL_SETTINGS
        self.results = {}
        self.best_models = {}
    
    # ---------- DATA AGGREGATION ----------
    
    def aggregate_to_frequency(self,
                                df: pd.DataFrame,
                                date_col: str,
                                qty_col: str,
                                frequency: str = "D") -> pd.DataFrame:
        # aggregate data to specified frequency
        result = df.copy()
        result[date_col] = pd.to_datetime(result[date_col])
        result = result.set_index(date_col)
        
        if frequency == "D":
            # daily - resample to fill gaps
            aggregated = result[qty_col].resample("D").sum()
        elif frequency == "W":
            # weekly aggregation
            aggregated = result[qty_col].resample("W").sum()
        elif frequency == "M":
            # monthly aggregation
            aggregated = result[qty_col].resample("M").sum()
        else:
            # default to daily
            aggregated = result[qty_col].resample("D").sum()
        
        return aggregated.to_frame().reset_index()
    
    def get_horizon_periods(self, horizon_days: int, frequency: str = "D") -> int:
        # convert horizon days to periods based on frequency
        if frequency == "D":
            return horizon_days
        elif frequency == "W":
            return max(1, horizon_days // 7)
        elif frequency == "M":
            return max(1, horizon_days // 30)
        else:
            return horizon_days
    
    # ---------- MAIN FORECASTING ----------
    
    def forecast(self,
                 df: pd.DataFrame,
                 date_col: str,
                 qty_col: str,
                 strategy: str = "simple",
                 horizon: int = 30,
                 frequency: str = "D",
                 features: Optional[List[str]] = None) -> ForecastResult:
        # generate forecast for single time series
        
        # aggregate data to frequency
        aggregated = self.aggregate_to_frequency(df, date_col, qty_col, frequency)
        
        # get models for strategy
        models = self.config[strategy]["models"]
        
        # prepare data
        ts = aggregated.copy()
        ts.columns = [date_col, qty_col]
        ts[date_col] = pd.to_datetime(ts[date_col])
        ts = ts.sort_values(date_col).set_index(date_col)
        ts = ts[qty_col]
        
        # convert horizon to periods
        horizon_periods = self.get_horizon_periods(horizon, frequency)
        
        # run each model and select best
        model_results = {}
        
        for model_name in models:
            try:
                result = self._run_model(ts, model_name, horizon_periods, frequency, features, df)
                if result is not None:
                    model_results[model_name] = result
            except Exception:
                continue
        
        # select best model based on metrics
        if not model_results:
            # fallback to naive if all models fail
            result = self._naive_forecast(ts, horizon_periods, frequency)
            return ForecastResult(
                sku="",
                model="naive",
                forecast=result["forecast"],
                dates=result["dates"],
                lower_bound=result["lower"],
                upper_bound=result["upper"],
                metrics=result["metrics"],
                frequency=frequency
            )
        
        best_model = min(model_results.keys(), key=lambda x: model_results[x]["metrics"].get("mape", float("inf")))
        best_result = model_results[best_model]
        
        return ForecastResult(
            sku="",
            model=best_model,
            forecast=best_result["forecast"],
            dates=best_result["dates"],
            lower_bound=best_result["lower"],
            upper_bound=best_result["upper"],
            metrics=best_result["metrics"],
            frequency=frequency
        )
    
    def _run_model(self, 
                   ts: pd.Series, 
                   model_name: str, 
                   horizon: int,
                   frequency: str = "D",
                   features: Optional[List[str]] = None,
                   full_df: Optional[pd.DataFrame] = None) -> Optional[Dict]:
        # run specific forecasting model
        
        if model_name == "naive":
            return self._naive_forecast(ts, horizon, frequency)
        elif model_name == "seasonal_naive":
            return self._seasonal_naive_forecast(ts, horizon, frequency)
        elif model_name == "exponential_smoothing":
            return self._exponential_smoothing_forecast(ts, horizon, frequency)
        elif model_name == "arima":
            return self._arima_forecast(ts, horizon, frequency)
        elif model_name == "theta":
            return self._theta_forecast(ts, horizon, frequency)
        elif model_name == "prophet":
            return self._prophet_forecast(ts, horizon, frequency)
        elif model_name == "lightgbm":
            return self._lightgbm_forecast(ts, horizon, frequency, features, full_df)
        elif model_name == "xgboost":
            return self._xgboost_forecast(ts, horizon, frequency, features, full_df)
        elif model_name == "ensemble":
            return self._ensemble_forecast(ts, horizon, frequency, features, full_df)
        else:
            return None
    
    # ---------- SIMPLE MODELS ----------
    
    def _naive_forecast(self, ts: pd.Series, horizon: int, frequency: str = "D") -> Dict:
        # naive forecast using last value
        last_value = ts.iloc[-1] if len(ts) > 0 else 0
        last_date = ts.index[-1] if len(ts) > 0 else pd.Timestamp.now()
        
        # generate forecast dates based on frequency
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1), 
            periods=horizon, 
            freq=frequency
        )
        
        # forecast is constant
        forecast = [float(last_value)] * horizon
        
        # confidence interval based on historical std
        std = ts.std() if len(ts) > 1 else last_value * 0.1
        lower = [max(0, last_value - 1.96 * std)] * horizon
        upper = [last_value + 1.96 * std] * horizon
        
        # in-sample metrics
        fitted_values = [ts.mean()] * len(ts)
        metrics = self._calculate_metrics(ts.values, fitted_values)
        
        return {
            "forecast": forecast,
            "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
            "lower": lower,
            "upper": upper,
            "metrics": metrics
        }
    
    def _seasonal_naive_forecast(self, ts: pd.Series, horizon: int, frequency: str = "D") -> Dict:
        # seasonal naive using same period last cycle
        last_date = ts.index[-1] if len(ts) > 0 else pd.Timestamp.now()
        
        # determine season length based on frequency
        if frequency == "D":
            season_length = 7
        elif frequency == "W":
            season_length = 52
        elif frequency == "M":
            season_length = 12
        else:
            season_length = 7
        
        # generate forecast dates
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1), 
            periods=horizon, 
            freq=frequency
        )
        
        # get seasonal values
        forecast = []
        for i in range(horizon):
            idx = -(season_length - (i % season_length))
            if abs(idx) <= len(ts):
                forecast.append(float(ts.iloc[idx]))
            else:
                forecast.append(float(ts.mean()))
        
        # confidence interval
        std = ts.std() if len(ts) > 1 else np.mean(forecast) * 0.1
        lower = [max(0, f - 1.96 * std) for f in forecast]
        upper = [f + 1.96 * std for f in forecast]
        
        # in-sample metrics using seasonal fitted values
        fitted_values = []
        for i in range(len(ts)):
            if i >= season_length:
                fitted_values.append(ts.iloc[i - season_length])
            else:
                fitted_values.append(ts.mean())
        
        metrics = self._calculate_metrics(ts.values, fitted_values)
        
        return {
            "forecast": forecast,
            "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
            "lower": lower,
            "upper": upper,
            "metrics": metrics
        }
    
    def _exponential_smoothing_forecast(self, ts: pd.Series, horizon: int, frequency: str = "D") -> Dict:
        # exponential smoothing with trend and seasonality
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            
            # determine seasonal period based on frequency
            if frequency == "D":
                seasonal_periods = 7
                min_obs = 14
            elif frequency == "W":
                seasonal_periods = 52
                min_obs = 104
            elif frequency == "M":
                seasonal_periods = 12
                min_obs = 24
            else:
                seasonal_periods = 7
                min_obs = 14
            
            # fit model on all data
            use_seasonal = len(ts) >= min_obs
            model = ExponentialSmoothing(
                ts,
                trend="add",
                seasonal="add" if use_seasonal else None,
                seasonal_periods=seasonal_periods if use_seasonal else None
            )
            fitted = model.fit(optimized=True)
            
            # generate forecast
            forecast_result = fitted.forecast(horizon)
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), 
                periods=horizon, 
                freq=frequency
            )
            
            forecast = [max(0, float(v)) for v in forecast_result.values]
            
            # confidence interval from residuals
            residuals = ts - fitted.fittedvalues
            std = residuals.std()
            lower = [max(0, f - 1.96 * std) for f in forecast]
            upper = [f + 1.96 * std for f in forecast]
            
            # in-sample metrics
            metrics = self._calculate_metrics(ts.values, fitted.fittedvalues.values)
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception as e:
            logger = get_logger()
            logger.exception("ExponentialSmoothing failed: %s", e)
            return self._naive_forecast(ts, horizon, frequency)
    
    # ---------- BALANCED MODELS ----------
    
    def _arima_forecast(self, ts: pd.Series, horizon: int, frequency: str = "D") -> Dict:
        # arima model fitted on all data
        try:
            from statsmodels.tsa.arima.model import ARIMA
            
            # fit model on all data
            model = ARIMA(ts, order=(1, 1, 1))
            fitted = model.fit()
            
            # generate forecast with confidence intervals
            forecast_result = fitted.get_forecast(steps=horizon)
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), 
                periods=horizon, 
                freq=frequency
            )
            
            forecast = [max(0, float(v)) for v in forecast_result.predicted_mean.values]
            conf_int = forecast_result.conf_int()
            lower = [max(0, float(v)) for v in conf_int.iloc[:, 0].values]
            upper = [float(v) for v in conf_int.iloc[:, 1].values]
            
            # in-sample metrics
            metrics = self._calculate_metrics(ts.values, fitted.fittedvalues.values)
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            logger = get_logger()
            logger.exception("ARIMA failed for ts: falling back to ExpSmoothing")
            return self._exponential_smoothing_forecast(ts, horizon, frequency)
    
    def _theta_forecast(self, ts: pd.Series, horizon: int, frequency: str = "D") -> Dict:
        # theta method forecast
        try:
            from statsmodels.tsa.forecasting.theta import ThetaModel
            
            # fit model on all data
            model = ThetaModel(ts)
            fitted = model.fit()
            
            # generate forecast
            forecast_result = fitted.forecast(horizon)
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), 
                periods=horizon, 
                freq=frequency
            )
            
            forecast = [max(0, float(v)) for v in forecast_result.values]
            
            # confidence interval
            std = ts.std()
            lower = [max(0, f - 1.96 * std) for f in forecast]
            upper = [f + 1.96 * std for f in forecast]
            
            # in-sample fitted values
            in_sample_forecast = fitted.forecast(len(ts))
            metrics = self._calculate_metrics(ts.values, in_sample_forecast.values)
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            logger = get_logger()
            logger.exception("ThetaModel failed: falling back to ExpSmoothing")
            return self._exponential_smoothing_forecast(ts, horizon, frequency)
    
    def _prophet_forecast(self, ts: pd.Series, horizon: int, frequency: str = "D") -> Dict:
        # prophet model for time series
        try:
            from prophet import Prophet
            
            # prepare data for prophet
            df_prophet = pd.DataFrame({
                "ds": ts.index,
                "y": ts.values
            })
            
            # fit model on all data
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=(frequency == "D"),
                daily_seasonality=False
            )
            model.fit(df_prophet)
            
            # generate future dates for forecast only
            future = model.make_future_dataframe(periods=horizon, freq=frequency)
            forecast_result = model.predict(future)
            
            # extract forecast portion only
            forecast_df = forecast_result.tail(horizon)
            forecast = [max(0, float(v)) for v in forecast_df["yhat"].values]
            lower = [max(0, float(v)) for v in forecast_df["yhat_lower"].values]
            upper = [float(v) for v in forecast_df["yhat_upper"].values]
            dates = [d.strftime("%Y-%m-%d") for d in forecast_df["ds"]]
            
            # in-sample metrics from fitted portion
            in_sample = forecast_result.head(len(ts))["yhat"].values
            metrics = self._calculate_metrics(ts.values, in_sample)
            
            return {
                "forecast": forecast,
                "dates": dates,
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            logger = get_logger()
            logger.exception("Prophet failed: falling back to ExpSmoothing")
            return self._exponential_smoothing_forecast(ts, horizon, frequency)
    
    # ---------- ADVANCED MODELS ----------
    
    def _lightgbm_forecast(self, 
                           ts: pd.Series, 
                           horizon: int,
                           frequency: str = "D",
                           features: Optional[List[str]] = None,
                           full_df: Optional[pd.DataFrame] = None) -> Dict:
        # lightgbm model fitted on all data
        try:
            import lightgbm as lgb
            
            # prepare features from all data
            if full_df is None or features is None:
                df = self._create_ml_features(ts)
                feature_cols = [c for c in df.columns if c != "target"]
            else:
                df = full_df.copy()
                feature_cols = [f for f in features if f in df.columns]
                if "target" not in df.columns:
                    df["target"] = ts.values[-len(df):]
            
            # remove rows with nan
            df = df.dropna()
            
            if len(df) < 10:
                return self._exponential_smoothing_forecast(ts, horizon, frequency)
            
            # fit on all data
            X = df[feature_cols]
            y = df["target"]
            
            model = lgb.LGBMRegressor(
                n_estimators=100, 
                random_state=42, 
                verbosity=-1,
                force_col_wise=True
            )
            model.fit(X, y)
            
            # in-sample predictions for metrics
            in_sample_pred = model.predict(X)
            metrics = self._calculate_metrics(y.values, in_sample_pred)
            
            # generate forecast iteratively
            forecast = []
            last_features = df[feature_cols].iloc[-1:].copy()
            
            for i in range(horizon):
                pred = model.predict(last_features)[0]
                forecast.append(max(0, float(pred)))
                last_features = self._update_ml_features(last_features, pred, i)
            
            # dates
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), 
                periods=horizon, 
                freq=frequency
            )
            
            # confidence interval from residuals
            residuals = y.values - in_sample_pred
            std = np.std(residuals)
            lower = [max(0, f - 1.96 * std) for f in forecast]
            upper = [f + 1.96 * std for f in forecast]
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            logger = get_logger()
            logger.exception("LightGBM forecast failed: falling back to ExpSmoothing")
            return self._exponential_smoothing_forecast(ts, horizon, frequency)
    
    def _xgboost_forecast(self,
                          ts: pd.Series,
                          horizon: int,
                          frequency: str = "D",
                          features: Optional[List[str]] = None,
                          full_df: Optional[pd.DataFrame] = None) -> Dict:
        # xgboost model fitted on all data
        try:
            import xgboost as xgb
            
            # prepare features from all data
            if full_df is None or features is None:
                df = self._create_ml_features(ts)
                feature_cols = [c for c in df.columns if c != "target"]
            else:
                df = full_df.copy()
                feature_cols = [f for f in features if f in df.columns]
                if "target" not in df.columns:
                    df["target"] = ts.values[-len(df):]
            
            # remove rows with nan
            df = df.dropna()
            
            if len(df) < 10:
                return self._exponential_smoothing_forecast(ts, horizon, frequency)
            
            # fit on all data
            X = df[feature_cols]
            y = df["target"]
            
            model = xgb.XGBRegressor(
                n_estimators=100, 
                random_state=42, 
                verbosity=0
            )
            model.fit(X, y)
            
            # in-sample predictions for metrics
            in_sample_pred = model.predict(X)
            metrics = self._calculate_metrics(y.values, in_sample_pred)
            
            # generate forecast iteratively
            forecast = []
            last_features = df[feature_cols].iloc[-1:].copy()
            
            for i in range(horizon):
                pred = model.predict(last_features)[0]
                forecast.append(max(0, float(pred)))
                last_features = self._update_ml_features(last_features, pred, i)
            
            # dates
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1), 
                periods=horizon, 
                freq=frequency
            )
            
            # confidence interval from residuals
            residuals = y.values - in_sample_pred
            std = np.std(residuals)
            lower = [max(0, f - 1.96 * std) for f in forecast]
            upper = [f + 1.96 * std for f in forecast]
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            logger = get_logger()
            logger.exception("XGBoost forecast failed: falling back to ExpSmoothing")
            return self._exponential_smoothing_forecast(ts, horizon, frequency)
    
    def _ensemble_forecast(self,
                           ts: pd.Series,
                           horizon: int,
                           frequency: str = "D",
                           features: Optional[List[str]] = None,
                           full_df: Optional[pd.DataFrame] = None) -> Dict:
        # ensemble of multiple models
        models_to_combine = ["exponential_smoothing", "arima", "theta"]
        
        all_forecasts = []
        all_lowers = []
        all_uppers = []
        all_metrics = []
        
        for model_name in models_to_combine:
            try:
                result = self._run_model(ts, model_name, horizon, frequency, features, full_df)
                if result is not None:
                    all_forecasts.append(result["forecast"])
                    all_lowers.append(result["lower"])
                    all_uppers.append(result["upper"])
                    all_metrics.append(result["metrics"])
            except Exception:
                continue
        
        if not all_forecasts:
            return self._naive_forecast(ts, horizon, frequency)
        
        # combine forecasts using simple average
        ensemble_forecast = np.mean(all_forecasts, axis=0).tolist()
        ensemble_lower = np.mean(all_lowers, axis=0).tolist()
        ensemble_upper = np.mean(all_uppers, axis=0).tolist()
        
        # dates
        last_date = ts.index[-1]
        forecast_dates = pd.date_range(
            start=last_date + pd.Timedelta(days=1), 
            periods=horizon, 
            freq=frequency
        )
        
        # average metrics
        avg_mape = np.mean([m.get("mape", 0) for m in all_metrics])
        avg_mae = np.mean([m.get("mae", 0) for m in all_metrics])
        avg_rmse = np.mean([m.get("rmse", 0) for m in all_metrics])
        
        return {
            "forecast": ensemble_forecast,
            "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
            "lower": ensemble_lower,
            "upper": ensemble_upper,
            "metrics": {
                "mape": avg_mape, 
                "mae": avg_mae, 
                "rmse": avg_rmse,
                "models_combined": len(all_forecasts)
            }
        }
    
    # ---------- HELPER METHODS ----------
    
    def _create_ml_features(self, ts: pd.Series) -> pd.DataFrame:
        # create features for ml models from time series
        df = pd.DataFrame({"target": ts.values}, index=ts.index)
        
        # lag features
        df["lag_1"] = df["target"].shift(1)
        df["lag_7"] = df["target"].shift(7)
        df["lag_14"] = df["target"].shift(14)
        df["lag_28"] = df["target"].shift(28)
        
        # rolling features
        df["rolling_mean_7"] = df["target"].shift(1).rolling(7).mean()
        df["rolling_std_7"] = df["target"].shift(1).rolling(7).std()
        df["rolling_mean_28"] = df["target"].shift(1).rolling(28).mean()
        
        # date features
        df["day_of_week"] = df.index.dayofweek
        df["month"] = df.index.month
        df["day_of_month"] = df.index.day
        df["week_of_year"] = df.index.isocalendar().week.astype(int)
        
        # trend feature
        df["time_idx"] = np.arange(len(df))
        
        return df
    
    def _update_ml_features(self, features: pd.DataFrame, new_value: float, step: int) -> pd.DataFrame:
        # update features for next forecast step
        updated = features.copy()
        
        # update lag features
        # shift lag_N columns correctly: lag_k <- previous lag_{k-1}, lag_1 <- new_value
        lag_cols = [c for c in updated.columns if c.startswith("lag_")]
        if lag_cols:
            # extract numeric part and sort descending
            def lag_num(name):
                try:
                    return int(name.split("_")[1])
                except Exception:
                    return 0

            lag_cols_sorted = sorted(lag_cols, key=lag_num, reverse=True)

            # for highest lags, set them from previous lower lag values
            for col in lag_cols_sorted:
                n = lag_num(col)
                if n == 1:
                    updated[col] = new_value
                else:
                    prev_col = f"lag_{n-1}"
                    if prev_col in updated.columns:
                        updated[col] = updated[prev_col].values[0]
        
        # update time index
        if "time_idx" in updated.columns:
            updated["time_idx"] = updated["time_idx"].values[0] + 1
        
        # update date features for next period
        if "day_of_week" in updated.columns:
            updated["day_of_week"] = (updated["day_of_week"].values[0] + 1) % 7
        
        if "day_of_month" in updated.columns:
            updated["day_of_month"] = min(28, updated["day_of_month"].values[0] + 1)
        
        return updated
    
    def _calculate_metrics(self, actual: np.ndarray, predicted: np.ndarray) -> Dict[str, float]:
        # calculate forecast accuracy metrics from in-sample fit
        actual = np.array(actual).flatten()
        predicted = np.array(predicted).flatten()
        
        # align lengths
        min_len = min(len(actual), len(predicted))
        if min_len == 0:
            return {"mape": 0, "mae": 0, "rmse": 0}
        
        actual = actual[-min_len:]
        predicted = predicted[-min_len:]
        
        # mae
        mae = np.mean(np.abs(actual - predicted))
        
        # rmse
        rmse = np.sqrt(np.mean((actual - predicted) ** 2))
        
        # mape - avoid division by zero
        mask = actual != 0
        if mask.sum() > 0:
            mape = np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100
        else:
            mape = 0
        
        return {
            "mape": float(mape),
            "mae": float(mae),
            "rmse": float(rmse)
        }
    
    # ---------- BATCH FORECASTING ----------
    
    def forecast_batch(self,
                       df: pd.DataFrame,
                       sku_col: str,
                       date_col: str,
                       qty_col: str,
                       strategy: str = "simple",
                       horizon: int = 30,
                       frequency: str = "D",
                       tier_mapping: Optional[Dict[str, str]] = None,
                       features: Optional[List[str]] = None,
                       progress_callback: Optional[callable] = None,
                       parallel: bool = False,
                       max_workers: int = 4,
                       use_processes: bool = False) -> Dict[str, ForecastResult]:
        # forecast multiple skus with strategy selection
        
        results = {}
        grouped = df.groupby(sku_col)
        total = len(grouped)

        if parallel and max_workers > 1:
            if use_processes:
                from concurrent.futures import ProcessPoolExecutor, as_completed

                futures = {}
                with ProcessPoolExecutor(max_workers=max_workers) as exe:
                    for sku, sku_df in grouped:
                        sku_df = sku_df.copy()
                        # determine strategy based on tier
                        if tier_mapping and strategy == "balanced":
                            tier = tier_mapping.get(sku, "C")
                            sku_strategy = "simple" if tier == "C" else strategy
                        else:
                            sku_strategy = strategy

                        futures[exe.submit(self.forecast, sku_df, date_col, qty_col, sku_strategy, horizon, frequency, features)] = sku

                    for fut in as_completed(futures):
                        sku = futures[fut]
                        try:
                            result = fut.result()
                            result.sku = sku
                            results[sku] = result
                        except Exception as e:
                            # fallback to naive and log
                            try:
                                from utils.logging_config import get_logger
                                logger = get_logger()
                                logger.exception("Forecast failed for SKU %s in process pool: %s", sku, e)
                            except Exception:
                                pass

                            try:
                                aggregated = self.aggregate_to_frequency(df[df[sku_col] == sku], date_col, qty_col, frequency)
                                ts = aggregated.set_index(aggregated.columns[0])[aggregated.columns[1]]
                                horizon_periods = self.get_horizon_periods(horizon, frequency)
                                naive_result = self._naive_forecast(ts, horizon_periods, frequency)
                                results[sku] = ForecastResult(
                                    sku=sku,
                                    model="naive",
                                    forecast=naive_result["forecast"],
                                    dates=naive_result["dates"],
                                    lower_bound=naive_result["lower"],
                                    upper_bound=naive_result["upper"],
                                    metrics=naive_result["metrics"],
                                    frequency=frequency
                                )
                            except Exception:
                                continue

                        if progress_callback:
                            progress_callback((len(results)) / total * 100, sku)

                self.results = results
                return results
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed

                futures = {}
                with ThreadPoolExecutor(max_workers=max_workers) as exe:
                    for sku, sku_df in grouped:
                        sku_df = sku_df.copy()
                        # determine strategy based on tier
                        if tier_mapping and strategy == "balanced":
                            tier = tier_mapping.get(sku, "C")
                            sku_strategy = "simple" if tier == "C" else strategy
                        else:
                            sku_strategy = strategy

                        futures[exe.submit(self.forecast, sku_df, date_col, qty_col, sku_strategy, horizon, frequency, features)] = sku

                    for fut in as_completed(futures):
                        sku = futures[fut]
                        try:
                            result = fut.result()
                            result.sku = sku
                            results[sku] = result
                        except Exception as e:
                            try:
                                from utils.logging_config import get_logger
                                logger = get_logger()
                                logger.exception("Forecast failed for SKU %s in thread pool: %s", sku, e)
                            except Exception:
                                pass

                            try:
                                aggregated = self.aggregate_to_frequency(df[df[sku_col] == sku], date_col, qty_col, frequency)
                                ts = aggregated.set_index(aggregated.columns[0])[aggregated.columns[1]]
                                horizon_periods = self.get_horizon_periods(horizon, frequency)
                                naive_result = self._naive_forecast(ts, horizon_periods, frequency)
                                results[sku] = ForecastResult(
                                    sku=sku,
                                    model="naive",
                                    forecast=naive_result["forecast"],
                                    dates=naive_result["dates"],
                                    lower_bound=naive_result["lower"],
                                    upper_bound=naive_result["upper"],
                                    metrics=naive_result["metrics"],
                                    frequency=frequency
                                )
                            except Exception:
                                continue

                        if progress_callback:
                            progress_callback((len(results)) / total * 100, sku)

                self.results = results
                return results

        for i, (sku, sku_df) in enumerate(grouped):
            sku_df = sku_df.copy()

            # determine strategy based on tier
            if tier_mapping and strategy == "balanced":
                tier = tier_mapping.get(sku, "C")
                sku_strategy = "simple" if tier == "C" else strategy
            else:
                sku_strategy = strategy

            # generate forecast
            try:
                result = self.forecast(
                    sku_df, date_col, qty_col,
                    sku_strategy, horizon, frequency, features
                )
                result.sku = sku
                results[sku] = result
            except Exception:
                # fallback to naive
                aggregated = self.aggregate_to_frequency(sku_df, date_col, qty_col, frequency)
                ts = aggregated.set_index(aggregated.columns[0])[aggregated.columns[1]]
                horizon_periods = self.get_horizon_periods(horizon, frequency)
                naive_result = self._naive_forecast(ts, horizon_periods, frequency)
                results[sku] = ForecastResult(
                    sku=sku,
                    model="naive",
                    forecast=naive_result["forecast"],
                    dates=naive_result["dates"],
                    lower_bound=naive_result["lower"],
                    upper_bound=naive_result["upper"],
                    metrics=naive_result["metrics"],
                    frequency=frequency
                )

            # progress callback with standardized signature
            if progress_callback:
                progress_callback((i + 1) / total * 100, sku)

        self.results = results
        return results
    
    # ---------- MODEL COMPARISON ----------
    
    def compare_models(self,
                       df: pd.DataFrame,
                       sku_col: str,
                       date_col: str,
                       qty_col: str,
                       horizon: int = 30,
                       frequency: str = "D",
                       sample_size: int = 50) -> Dict[str, Any]:
        # compare performance of different models on a sample
        models_to_test = ["naive", "seasonal_naive", "exponential_smoothing", "arima", "theta"]
        results = {model: {"mape": [], "mae": [], "wins": 0} for model in models_to_test}
        
        # select sample skus
        all_skus = df[sku_col].unique()
        if len(all_skus) > sample_size:
            sample_skus = np.random.choice(all_skus, sample_size, replace=False)
        else:
            sample_skus = all_skus
        
        for sku in sample_skus:
            sku_df = df[df[sku_col] == sku].copy()
            
            # aggregate data
            aggregated = self.aggregate_to_frequency(sku_df, date_col, qty_col, frequency)
            ts = aggregated.set_index(aggregated.columns[0])[aggregated.columns[1]]
            
            # skip if too little data
            if len(ts) < 14:
                continue
            
            # split for validation (last 'horizon' points)
            train = ts[:-horizon] if len(ts) > horizon else ts[:-1]
            test = ts[-horizon:] if len(ts) > horizon else ts[-1:]
            
            if len(train) == 0 or len(test) == 0:
                continue
            
            horizon_periods = len(test)
            
            # run each model
            best_mape = float("inf")
            best_model = None
            
            for model in models_to_test:
                try:
                    forecast = self._run_model(train, model, horizon_periods, frequency)
                    if forecast:
                        # calculate out-of-sample metrics
                        metrics = self._calculate_metrics(test.values, forecast["forecast"])
                        results[model]["mape"].append(metrics["mape"])
                        results[model]["mae"].append(metrics["mae"])
                        
                        if metrics["mape"] < best_mape:
                            best_mape = metrics["mape"]
                            best_model = model
                except Exception:
                    continue
            
            if best_model:
                results[best_model]["wins"] += 1
        
        # aggregate results
        summary = {}
        for model, data in results.items():
            count = len(data["mape"])
            if count > 0:
                summary[model] = {
                    "avg_mape": np.mean(data["mape"]),
                    "avg_mae": np.mean(data["mae"]),
                    "win_rate": data["wins"] / len(sample_skus)
                }
        
        best_overall = min(summary.items(), key=lambda x: x[1]["avg_mape"])[0] if summary else "naive"
        
        return {
            "model_stats": summary,
            "best_overall": best_overall,
            "sample_size": len(sample_skus)
        }
    
    # ---------- RESULTS ANALYSIS ----------
    
    def get_forecast_summary(self) -> pd.DataFrame:
        # get summary of all forecasts
        if not self.results:
            return pd.DataFrame()
        
        data = []
        for sku, result in self.results.items():
            total_forecast = sum(result.forecast)
            avg_forecast = np.mean(result.forecast)
            
            data.append({
                "sku": sku,
                "model": result.model,
                "frequency": self.FREQUENCY_LABELS.get(result.frequency, result.frequency),
                "periods": len(result.forecast),
                "total_forecast": total_forecast,
                "avg_period_forecast": avg_forecast,
                "mape": result.metrics.get("mape", 0),
                "mae": result.metrics.get("mae", 0),
                "forecast_start": result.dates[0] if result.dates else "",
                "forecast_end": result.dates[-1] if result.dates else ""
            })
        
        return pd.DataFrame(data)
    
    def get_problem_forecasts(self, mape_threshold: float = 30) -> List[str]:
        # get skus with high forecast error
        problems = []
        
        for sku, result in self.results.items():
            if result.metrics.get("mape", 0) > mape_threshold:
                problems.append(sku)
        
        return problems
    
    def get_model_distribution(self) -> Dict[str, int]:
        # get count of each model used
        distribution = {}
        
        for result in self.results.values():
            model = result.model
            distribution[model] = distribution.get(model, 0) + 1
        
        return distribution