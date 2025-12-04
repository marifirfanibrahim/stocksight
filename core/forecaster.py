"""
forecaster module
generates forecasts using multiple strategies
supports simple balanced and advanced approaches
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import warnings

warnings.filterwarnings("ignore")

import config


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


# ============================================================================
#                               FORECASTER
# ============================================================================

class Forecaster:
    # generates forecasts using configurable strategies
    
    def __init__(self):
        # initialize with forecast configuration
        self.config = config.FORECASTING
        self.model_settings = config.MODEL_SETTINGS
        self.results = {}
        self.best_models = {}
    
    # ---------- MAIN FORECASTING ----------
    
    def forecast(self,
                 df: pd.DataFrame,
                 date_col: str,
                 qty_col: str,
                 strategy: str = "simple",
                 horizon: int = 30,
                 features: Optional[List[str]] = None) -> ForecastResult:
        # generate forecast for single time series
        
        # get models for strategy
        models = self.config[strategy]["models"]
        
        # prepare data
        ts = df[[date_col, qty_col]].copy()
        ts[date_col] = pd.to_datetime(ts[date_col])
        ts = ts.sort_values(date_col).set_index(date_col)
        ts = ts[qty_col]
        
        # run each model and select best
        model_results = {}
        
        for model_name in models:
            try:
                result = self._run_model(ts, model_name, horizon, features, df)
                if result is not None:
                    model_results[model_name] = result
            except Exception as e:
                # skip failed models
                continue
        
        # select best model based on metrics
        if not model_results:
            # fallback to naive if all models fail
            result = self._naive_forecast(ts, horizon)
            return ForecastResult(
                sku="",
                model="naive",
                forecast=result["forecast"],
                dates=result["dates"],
                lower_bound=result["lower"],
                upper_bound=result["upper"],
                metrics=result["metrics"]
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
            metrics=best_result["metrics"]
        )
    
    def _run_model(self, 
                   ts: pd.Series, 
                   model_name: str, 
                   horizon: int,
                   features: Optional[List[str]] = None,
                   full_df: Optional[pd.DataFrame] = None) -> Optional[Dict]:
        # run specific forecasting model
        
        if model_name == "naive":
            return self._naive_forecast(ts, horizon)
        elif model_name == "seasonal_naive":
            return self._seasonal_naive_forecast(ts, horizon)
        elif model_name == "exponential_smoothing":
            return self._exponential_smoothing_forecast(ts, horizon)
        elif model_name == "arima":
            return self._arima_forecast(ts, horizon)
        elif model_name == "theta":
            return self._theta_forecast(ts, horizon)
        elif model_name == "prophet":
            return self._prophet_forecast(ts, horizon)
        elif model_name == "lightgbm":
            return self._lightgbm_forecast(ts, horizon, features, full_df)
        elif model_name == "xgboost":
            return self._xgboost_forecast(ts, horizon, features, full_df)
        elif model_name == "ensemble":
            return self._ensemble_forecast(ts, horizon, features, full_df)
        else:
            return None
    
    # ---------- SIMPLE MODELS ----------
    
    def _naive_forecast(self, ts: pd.Series, horizon: int) -> Dict:
        # naive forecast using last value
        last_value = ts.iloc[-1] if len(ts) > 0 else 0
        last_date = ts.index[-1] if len(ts) > 0 else pd.Timestamp.now()
        
        # generate forecast dates
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
        
        # forecast is constant
        forecast = [float(last_value)] * horizon
        
        # confidence interval based on historical std
        std = ts.std() if len(ts) > 1 else last_value * 0.1
        lower = [max(0, last_value - 1.96 * std)] * horizon
        upper = [last_value + 1.96 * std] * horizon
        
        # calculate metrics using holdout
        metrics = self._calculate_metrics(ts, forecast[:min(len(ts), horizon)])
        
        return {
            "forecast": forecast,
            "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
            "lower": lower,
            "upper": upper,
            "metrics": metrics
        }
    
    def _seasonal_naive_forecast(self, ts: pd.Series, horizon: int, season_length: int = 7) -> Dict:
        # seasonal naive using same day last period
        last_date = ts.index[-1] if len(ts) > 0 else pd.Timestamp.now()
        
        # generate forecast dates
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
        
        # get seasonal values
        forecast = []
        for i in range(horizon):
            # get value from same position in last season
            idx = -(season_length - (i % season_length))
            if abs(idx) <= len(ts):
                forecast.append(float(ts.iloc[idx]))
            else:
                forecast.append(float(ts.mean()))
        
        # confidence interval
        std = ts.std() if len(ts) > 1 else np.mean(forecast) * 0.1
        lower = [max(0, f - 1.96 * std) for f in forecast]
        upper = [f + 1.96 * std for f in forecast]
        
        # calculate metrics
        metrics = self._calculate_metrics(ts, forecast[:min(len(ts), horizon)])
        
        return {
            "forecast": forecast,
            "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
            "lower": lower,
            "upper": upper,
            "metrics": metrics
        }
    
    def _exponential_smoothing_forecast(self, ts: pd.Series, horizon: int) -> Dict:
        # exponential smoothing with trend and seasonality
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            
            # fit model
            model = ExponentialSmoothing(
                ts,
                trend="add",
                seasonal="add" if len(ts) >= 14 else None,
                seasonal_periods=7 if len(ts) >= 14 else None
            )
            fitted = model.fit(optimized=True)
            
            # generate forecast
            forecast_result = fitted.forecast(horizon)
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
            
            forecast = [max(0, float(v)) for v in forecast_result.values]
            
            # confidence interval
            residuals = ts - fitted.fittedvalues
            std = residuals.std()
            lower = [max(0, f - 1.96 * std) for f in forecast]
            upper = [f + 1.96 * std for f in forecast]
            
            # calculate metrics
            metrics = self._calculate_metrics(ts, fitted.fittedvalues)
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            return self._naive_forecast(ts, horizon)
    
    # ---------- BALANCED MODELS ----------
    
    def _arima_forecast(self, ts: pd.Series, horizon: int) -> Dict:
        # arima model with automatic order selection
        try:
            from statsmodels.tsa.arima.model import ARIMA
            
            # simple arima with default orders
            model = ARIMA(ts, order=(1, 1, 1))
            fitted = model.fit()
            
            # generate forecast with confidence intervals
            forecast_result = fitted.get_forecast(steps=horizon)
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
            
            forecast = [max(0, float(v)) for v in forecast_result.predicted_mean.values]
            conf_int = forecast_result.conf_int()
            lower = [max(0, float(v)) for v in conf_int.iloc[:, 0].values]
            upper = [float(v) for v in conf_int.iloc[:, 1].values]
            
            # calculate metrics
            metrics = self._calculate_metrics(ts, fitted.fittedvalues)
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            return self._exponential_smoothing_forecast(ts, horizon)
    
    def _theta_forecast(self, ts: pd.Series, horizon: int) -> Dict:
        # theta method forecast
        try:
            from statsmodels.tsa.forecasting.theta import ThetaModel
            
            model = ThetaModel(ts)
            fitted = model.fit()
            
            forecast_result = fitted.forecast(horizon)
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
            
            forecast = [max(0, float(v)) for v in forecast_result.values]
            
            # confidence interval
            std = ts.std()
            lower = [max(0, f - 1.96 * std) for f in forecast]
            upper = [f + 1.96 * std for f in forecast]
            
            # calculate metrics
            in_sample = fitted.forecast(len(ts))
            metrics = self._calculate_metrics(ts, in_sample)
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            return self._exponential_smoothing_forecast(ts, horizon)
    
    def _prophet_forecast(self, ts: pd.Series, horizon: int) -> Dict:
        # prophet model for time series
        try:
            from prophet import Prophet
            
            # prepare data for prophet
            df_prophet = pd.DataFrame({
                "ds": ts.index,
                "y": ts.values
            })
            
            # fit model
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=False
            )
            model.fit(df_prophet)
            
            # generate future dates
            future = model.make_future_dataframe(periods=horizon)
            forecast_result = model.predict(future)
            
            # extract forecast
            forecast_df = forecast_result.tail(horizon)
            forecast = [max(0, float(v)) for v in forecast_df["yhat"].values]
            lower = [max(0, float(v)) for v in forecast_df["yhat_lower"].values]
            upper = [float(v) for v in forecast_df["yhat_upper"].values]
            dates = [d.strftime("%Y-%m-%d") for d in forecast_df["ds"]]
            
            # calculate metrics from in-sample
            in_sample = forecast_result.head(len(ts))["yhat"].values
            metrics = self._calculate_metrics(ts, in_sample)
            
            return {
                "forecast": forecast,
                "dates": dates,
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            return self._exponential_smoothing_forecast(ts, horizon)
    
    # ---------- ADVANCED MODELS ----------
    
    def _lightgbm_forecast(self, 
                           ts: pd.Series, 
                           horizon: int,
                           features: Optional[List[str]] = None,
                           full_df: Optional[pd.DataFrame] = None) -> Dict:
        # lightgbm model with features
        try:
            import lightgbm as lgb
            
            # prepare features
            if full_df is None or features is None:
                # create basic features
                df = self._create_basic_features(ts)
                feature_cols = [c for c in df.columns if c != "target"]
            else:
                df = full_df.copy()
                feature_cols = features
            
            # split train test
            train_size = int(len(df) * 0.8)
            train = df.iloc[:train_size]
            
            X_train = train[feature_cols].fillna(0)
            y_train = train["target"] if "target" in train.columns else ts.iloc[:train_size]
            
            # train model
            model = lgb.LGBMRegressor(n_estimators=100, random_state=42, verbosity=-1)
            model.fit(X_train, y_train)
            
            # generate forecast
            forecast = []
            last_features = df[feature_cols].iloc[-1:].copy()
            
            for i in range(horizon):
                pred = model.predict(last_features.fillna(0))[0]
                forecast.append(max(0, float(pred)))
                # update features for next step
                last_features = self._update_features(last_features, pred)
            
            # dates
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
            
            # confidence interval
            std = ts.std()
            lower = [max(0, f - 1.96 * std) for f in forecast]
            upper = [f + 1.96 * std for f in forecast]
            
            # calculate metrics
            in_sample_pred = model.predict(df[feature_cols].fillna(0))
            metrics = self._calculate_metrics(ts, in_sample_pred)
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            return self._exponential_smoothing_forecast(ts, horizon)
    
    def _xgboost_forecast(self,
                          ts: pd.Series,
                          horizon: int,
                          features: Optional[List[str]] = None,
                          full_df: Optional[pd.DataFrame] = None) -> Dict:
        # xgboost model with features
        try:
            import xgboost as xgb
            
            # prepare features
            if full_df is None or features is None:
                df = self._create_basic_features(ts)
                feature_cols = [c for c in df.columns if c != "target"]
            else:
                df = full_df.copy()
                feature_cols = features
            
            # split train
            train_size = int(len(df) * 0.8)
            train = df.iloc[:train_size]
            
            X_train = train[feature_cols].fillna(0)
            y_train = train["target"] if "target" in train.columns else ts.iloc[:train_size]
            
            # train model
            model = xgb.XGBRegressor(n_estimators=100, random_state=42, verbosity=0)
            model.fit(X_train, y_train)
            
            # generate forecast
            forecast = []
            last_features = df[feature_cols].iloc[-1:].copy()
            
            for i in range(horizon):
                pred = model.predict(last_features.fillna(0))[0]
                forecast.append(max(0, float(pred)))
                last_features = self._update_features(last_features, pred)
            
            # dates
            last_date = ts.index[-1]
            forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
            
            # confidence interval
            std = ts.std()
            lower = [max(0, f - 1.96 * std) for f in forecast]
            upper = [f + 1.96 * std for f in forecast]
            
            # calculate metrics
            in_sample_pred = model.predict(df[feature_cols].fillna(0))
            metrics = self._calculate_metrics(ts, in_sample_pred)
            
            return {
                "forecast": forecast,
                "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
                "lower": lower,
                "upper": upper,
                "metrics": metrics
            }
        except Exception:
            return self._exponential_smoothing_forecast(ts, horizon)
    
    def _ensemble_forecast(self,
                           ts: pd.Series,
                           horizon: int,
                           features: Optional[List[str]] = None,
                           full_df: Optional[pd.DataFrame] = None) -> Dict:
        # ensemble of multiple models
        models_to_combine = ["exponential_smoothing", "arima", "theta"]
        
        all_forecasts = []
        all_metrics = []
        
        for model_name in models_to_combine:
            try:
                result = self._run_model(ts, model_name, horizon, features, full_df)
                if result is not None:
                    all_forecasts.append(result["forecast"])
                    all_metrics.append(result["metrics"])
            except Exception:
                continue
        
        if not all_forecasts:
            return self._naive_forecast(ts, horizon)
        
        # combine forecasts using simple average
        ensemble_forecast = np.mean(all_forecasts, axis=0).tolist()
        
        # dates
        last_date = ts.index[-1]
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon)
        
        # confidence interval
        std = np.std(all_forecasts, axis=0)
        ensemble_std = ts.std()
        lower = [max(0, f - 1.96 * ensemble_std) for f in ensemble_forecast]
        upper = [f + 1.96 * ensemble_std for f in ensemble_forecast]
        
        # average metrics
        avg_mape = np.mean([m.get("mape", 0) for m in all_metrics])
        avg_mae = np.mean([m.get("mae", 0) for m in all_metrics])
        
        return {
            "forecast": ensemble_forecast,
            "dates": [d.strftime("%Y-%m-%d") for d in forecast_dates],
            "lower": lower,
            "upper": upper,
            "metrics": {"mape": avg_mape, "mae": avg_mae, "models_combined": len(all_forecasts)}
        }
    
    # ---------- HELPER METHODS ----------
    
    def _create_basic_features(self, ts: pd.Series) -> pd.DataFrame:
        # create basic features for ml models
        df = pd.DataFrame({"target": ts.values}, index=ts.index)
        
        # lag features
        df["lag_1"] = df["target"].shift(1)
        df["lag_7"] = df["target"].shift(7)
        
        # rolling features
        df["rolling_mean_7"] = df["target"].rolling(7).mean()
        df["rolling_std_7"] = df["target"].rolling(7).std()
        
        # date features
        df["day_of_week"] = df.index.dayofweek
        df["month"] = df.index.month
        
        return df.dropna()
    
    def _update_features(self, features: pd.DataFrame, new_value: float) -> pd.DataFrame:
        # update features for next forecast step
        updated = features.copy()
        
        if "lag_1" in updated.columns:
            updated["lag_1"] = new_value
        
        return updated
    
    def _calculate_metrics(self, actual: pd.Series, predicted: Any) -> Dict[str, float]:
        # calculate forecast accuracy metrics
        if isinstance(predicted, pd.Series):
            predicted = predicted.values
        
        actual_vals = actual.values[-len(predicted):]
        predicted_vals = np.array(predicted)[:len(actual_vals)]
        
        if len(actual_vals) == 0 or len(predicted_vals) == 0:
            return {"mape": 0, "mae": 0, "rmse": 0}
        
        # mae
        mae = np.mean(np.abs(actual_vals - predicted_vals))
        
        # rmse
        rmse = np.sqrt(np.mean((actual_vals - predicted_vals) ** 2))
        
        # mape avoiding division by zero
        mask = actual_vals != 0
        if mask.sum() > 0:
            mape = np.mean(np.abs((actual_vals[mask] - predicted_vals[mask]) / actual_vals[mask])) * 100
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
                       tier_mapping: Optional[Dict[str, str]] = None,
                       features: Optional[List[str]] = None,
                       progress_callback: Optional[callable] = None) -> Dict[str, ForecastResult]:
        # forecast multiple skus with strategy selection
        
        results = {}
        skus = df[sku_col].unique()
        total = len(skus)
        
        for i, sku in enumerate(skus):
            # get sku data
            sku_df = df[df[sku_col] == sku].copy()
            
            # determine strategy based on tier
            if tier_mapping and strategy == "balanced":
                tier = tier_mapping.get(sku, "C")
                if tier == "C":
                    sku_strategy = "simple"
                else:
                    sku_strategy = strategy
            else:
                sku_strategy = strategy
            
            # generate forecast
            try:
                result = self.forecast(sku_df, date_col, qty_col, sku_strategy, horizon, features)
                result.sku = sku
                results[sku] = result
            except Exception:
                # fallback to naive
                ts = sku_df.set_index(date_col)[qty_col]
                naive_result = self._naive_forecast(ts, horizon)
                results[sku] = ForecastResult(
                    sku=sku,
                    model="naive",
                    forecast=naive_result["forecast"],
                    dates=naive_result["dates"],
                    lower_bound=naive_result["lower"],
                    upper_bound=naive_result["upper"],
                    metrics=naive_result["metrics"]
                )
            
            # progress callback
            if progress_callback:
                progress_callback((i + 1) / total * 100, sku)
        
        self.results = results
        return results
    
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
                "total_forecast": total_forecast,
                "avg_daily_forecast": avg_forecast,
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