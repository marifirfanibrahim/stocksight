"""
autoviz exploration wrapper
interactive visualization and anomaly detection
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable, Tuple
from pathlib import Path
import threading
import warnings
import io
import base64

from config import Paths, ExplorationConfig, ChartConfig
from core.state import STATE, PipelineStage
from core.pipeline import PIPELINE
from core.alerts import ALERTS, AlertSeverity
from utils.anomaly import detect_anomalies, AnomalyMethod


# ================ EXPLORATION MANAGER ================

class ExplorationManager:
    """
    manage data exploration and visualization
    """
    
    def __init__(self):
        # ---------- STATE ----------
        self._charts = {}
        self._decomposition = {}
        self._anomalies = {}
        self._is_exploring = False
        self._lock = threading.RLock()
    
    # ================ AUTOVIZ EXPLORATION ================
    
    def run_autoviz(
        self,
        df: pd.DataFrame = None,
        target_column: str = 'Quantity',
        progress_callback: Callable = None
    ) -> bool:
        """
        run autoviz exploration
        """
        with self._lock:
            if self._is_exploring:
                print("exploration already in progress")
                return False
            self._is_exploring = True
        
        try:
            if df is None:
                df = STATE.clean_data
            
            if df is None:
                print("no data for exploration")
                return False
            
            PIPELINE.start_stage(PipelineStage.EXPLORATION, "Running AutoViz...")
            
            if progress_callback:
                progress_callback(10, "Loading AutoViz...")
            
            # import autoviz
            try:
                from autoviz import AutoViz_Class
            except ImportError:
                print("autoviz not installed")
                PIPELINE.fail_stage(PipelineStage.EXPLORATION, "autoviz not installed")
                return False
            
            if progress_callback:
                progress_callback(20, "Preparing data...")
            
            # prepare data
            viz_df = self._prepare_for_viz(df)
            
            if progress_callback:
                progress_callback(30, "Generating visualizations...")
            
            # run autoviz
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                av = AutoViz_Class()
                
                # save charts to memory
                chart_dir = Paths.CACHE_DIR / "autoviz_charts"
                chart_dir.mkdir(parents=True, exist_ok=True)
                
                # run visualization
                av.AutoViz(
                    filename="",
                    sep=",",
                    depVar=target_column if target_column in viz_df.columns else "",
                    dfte=viz_df,
                    header=0,
                    verbose=0,
                    lowess=False,
                    chart_format=ExplorationConfig.CHART_FORMAT,
                    max_rows_analyzed=min(len(viz_df), 10000),
                    max_cols_analyzed=min(len(viz_df.columns), 30),
                    save_plot_dir=str(chart_dir)
                )
            
            if progress_callback:
                progress_callback(60, "Processing charts...")
            
            # collect generated charts
            self._collect_charts(chart_dir)
            
            if progress_callback:
                progress_callback(80, "Storing results...")
            
            # store in state
            STATE.exploration_charts = self._charts
            
            PIPELINE.complete_stage(PipelineStage.EXPLORATION, "Exploration complete")
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            return True
            
        except Exception as e:
            print(f"exploration error: {e}")
            import traceback
            traceback.print_exc()
            PIPELINE.fail_stage(PipelineStage.EXPLORATION, str(e))
            return False
            
        finally:
            with self._lock:
                self._is_exploring = False
    
    def _prepare_for_viz(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        prepare dataframe for autoviz
        """
        viz_df = df.copy()
        
        # ensure date is datetime
        if 'Date' in viz_df.columns:
            viz_df['Date'] = pd.to_datetime(viz_df['Date'])
        
        # limit size
        if len(viz_df) > 50000:
            viz_df = viz_df.sample(n=50000, random_state=42)
        
        return viz_df
    
    def _collect_charts(self, chart_dir: Path):
        """
        collect generated chart files
        """
        self._charts = {}
        
        if not chart_dir.exists():
            return
        
        for chart_file in chart_dir.glob("*.svg"):
            chart_name = chart_file.stem
            
            with open(chart_file, 'r') as f:
                svg_content = f.read()
            
            self._charts[chart_name] = {
                'type': 'svg',
                'content': svg_content,
                'path': str(chart_file)
            }
        
        for chart_file in chart_dir.glob("*.png"):
            chart_name = chart_file.stem
            
            with open(chart_file, 'rb') as f:
                png_content = base64.b64encode(f.read()).decode()
            
            self._charts[chart_name] = {
                'type': 'png',
                'content': png_content,
                'path': str(chart_file)
            }
    
    # ================ TIME SERIES PLOTS ================
    
    def generate_time_series_plot(
        self,
        df: pd.DataFrame = None,
        sku: str = None,
        overlays: List[str] = None,
        show_anomalies: bool = True
    ) -> Optional[str]:
        """
        generate interactive time series plot
        returns base64 encoded image
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            if df is None:
                df = STATE.clean_data
            
            if df is None:
                return None
            
            # filter by sku if specified
            if sku:
                plot_df = df[df['SKU'] == sku].copy()
            else:
                plot_df = df.copy()
            
            if len(plot_df) == 0:
                return None
            
            # aggregate by date
            plot_df['Date'] = pd.to_datetime(plot_df['Date'])
            daily = plot_df.groupby('Date')['Quantity'].sum().reset_index()
            
            # create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # apply theme
            if STATE.settings.get('dark_mode', True):
                plt.style.use('dark_background')
                fig.patch.set_facecolor(ChartConfig.DARK_THEME['background'])
                ax.set_facecolor(ChartConfig.DARK_THEME['background'])
            
            # plot main series
            ax.plot(
                daily['Date'],
                daily['Quantity'],
                color=ChartConfig.HISTORICAL_COLOR,
                linewidth=1.5,
                label='Quantity'
            )
            
            # add overlays
            if overlays:
                overlay_colors = ['#4CAF50', '#FF9800', '#9C27B0', '#00BCD4']
                
                for i, overlay_col in enumerate(overlays):
                    if overlay_col in plot_df.columns:
                        overlay_data = plot_df.groupby('Date')[overlay_col].mean().reset_index()
                        
                        ax2 = ax.twinx()
                        ax2.plot(
                            overlay_data['Date'],
                            overlay_data[overlay_col],
                            color=overlay_colors[i % len(overlay_colors)],
                            linewidth=1,
                            linestyle='--',
                            label=overlay_col,
                            alpha=0.7
                        )
                        ax2.set_ylabel(overlay_col, fontsize=10)
            
            # add anomalies
            if show_anomalies and sku in STATE.anomalies:
                anomaly_dates = STATE.anomalies[sku].get('dates', [])
                anomaly_values = STATE.anomalies[sku].get('values', [])
                
                if anomaly_dates:
                    ax.scatter(
                        anomaly_dates,
                        anomaly_values,
                        color=ChartConfig.ANOMALY_COLOR,
                        s=50,
                        zorder=5,
                        label='Anomalies'
                    )
            
            # formatting
            ax.set_xlabel('Date', fontsize=10)
            ax.set_ylabel('Quantity', fontsize=10)
            ax.set_title(f"Time Series: {sku if sku else 'All SKUs'}", fontsize=12)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            plt.xticks(rotation=45)
            ax.legend(loc='upper left')
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # convert to base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            
            return base64.b64encode(buf.read()).decode()
            
        except Exception as e:
            print(f"time series plot error: {e}")
            return None
    
    # ================ SEASONALITY DECOMPOSITION ================
    
    def decompose_seasonality(
        self,
        df: pd.DataFrame = None,
        sku: str = None,
        period: int = None,
        model: str = None
    ) -> Dict:
        """
        perform seasonal decomposition
        """
        try:
            from statsmodels.tsa.seasonal import seasonal_decompose
            
            if df is None:
                df = STATE.clean_data
            
            if df is None:
                return {}
            
            if period is None:
                period = ExplorationConfig.SEASONAL_PERIOD
            
            if model is None:
                model = ExplorationConfig.DECOMPOSITION_MODEL
            
            # filter by sku
            if sku:
                ts_df = df[df['SKU'] == sku].copy()
            else:
                ts_df = df.copy()
            
            if len(ts_df) < period * 2:
                return {'error': 'insufficient data for decomposition'}
            
            # create time series
            ts_df['Date'] = pd.to_datetime(ts_df['Date'])
            daily = ts_df.groupby('Date')['Quantity'].sum()
            daily = daily.asfreq('D', fill_value=0)
            
            # decompose
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                result = seasonal_decompose(
                    daily,
                    model=model,
                    period=period,
                    extrapolate_trend='freq'
                )
            
            decomposition = {
                'trend': result.trend.dropna().to_dict(),
                'seasonal': result.seasonal.dropna().to_dict(),
                'residual': result.resid.dropna().to_dict(),
                'observed': result.observed.to_dict(),
                'period': period,
                'model': model
            }
            
            # store in state
            key = sku if sku else 'all'
            self._decomposition[key] = decomposition
            STATE.decomposition_results[key] = decomposition
            
            return decomposition
            
        except Exception as e:
            print(f"decomposition error: {e}")
            return {'error': str(e)}
    
    def generate_decomposition_plot(self, sku: str = None) -> Optional[str]:
        """
        generate decomposition plot
        returns base64 encoded image
        """
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            
            key = sku if sku else 'all'
            
            if key not in self._decomposition:
                self.decompose_seasonality(sku=sku)
            
            if key not in self._decomposition:
                return None
            
            decomp = self._decomposition[key]
            
            if 'error' in decomp:
                return None
            
            # create figure
            fig, axes = plt.subplots(4, 1, figsize=(12, 10))
            
            if STATE.settings.get('dark_mode', True):
                plt.style.use('dark_background')
                fig.patch.set_facecolor(ChartConfig.DARK_THEME['background'])
            
            # plot components
            components = ['observed', 'trend', 'seasonal', 'residual']
            titles = ['Observed', 'Trend', 'Seasonal', 'Residual']
            
            for ax, comp, title in zip(axes, components, titles):
                data = decomp.get(comp, {})
                if data:
                    dates = pd.to_datetime(list(data.keys()))
                    values = list(data.values())
                    ax.plot(dates, values, color=ChartConfig.HISTORICAL_COLOR, linewidth=1)
                ax.set_ylabel(title, fontsize=10)
                ax.grid(True, alpha=0.3)
            
            axes[0].set_title(f"Seasonal Decomposition: {sku if sku else 'All SKUs'}", fontsize=12)
            axes[-1].set_xlabel('Date', fontsize=10)
            
            plt.tight_layout()
            
            # convert to base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            
            return base64.b64encode(buf.read()).decode()
            
        except Exception as e:
            print(f"decomposition plot error: {e}")
            return None
    
    # ================ ANOMALY DETECTION ================
    
    def detect_sku_anomalies(
        self,
        df: pd.DataFrame = None,
        sku: str = None,
        method: str = None,
        contamination: float = None
    ) -> Dict:
        """
        detect anomalies for specific sku
        """
        if df is None:
            df = STATE.clean_data
        
        if df is None:
            return {}
        
        if method is None:
            method = ExplorationConfig.DEFAULT_ANOMALY_METHOD
        
        if contamination is None:
            contamination = ExplorationConfig.ANOMALY_CONTAMINATION
        
        # filter by sku
        if sku:
            sku_df = df[df['SKU'] == sku].copy()
        else:
            sku_df = df.copy()
        
        if len(sku_df) < 10:
            return {'error': 'insufficient data'}
        
        # detect anomalies
        anomaly_method = AnomalyMethod(method) if method in [m.value for m in AnomalyMethod] else AnomalyMethod.ISOLATION_FOREST
        
        result = detect_anomalies(
            sku_df,
            method=anomaly_method,
            contamination=contamination
        )
        
        # store results
        key = sku if sku else 'all'
        self._anomalies[key] = result
        STATE.anomalies[key] = result
        
        # generate alert if anomalies found
        anomaly_count = result.get('count', 0)
        if anomaly_count > 0 and sku:
            ALERTS.create_anomaly_alert(sku, anomaly_count)
        
        return result
    
    def detect_all_anomalies(
        self,
        df: pd.DataFrame = None,
        method: str = None,
        progress_callback: Callable = None
    ) -> Dict[str, Dict]:
        """
        detect anomalies for all skus
        """
        if df is None:
            df = STATE.clean_data
        
        if df is None:
            return {}
        
        skus = df['SKU'].unique().tolist()
        total = len(skus)
        results = {}
        
        for i, sku in enumerate(skus):
            if STATE.is_cancelled():
                break
            
            if progress_callback:
                progress_callback(
                    int((i / total) * 100),
                    f"Analyzing {sku}..."
                )
            
            results[sku] = self.detect_sku_anomalies(df, sku, method)
        
        return results
    
    def get_anomaly_summary(self) -> Dict:
        """
        get summary of all detected anomalies
        """
        summary = {
            'total_skus': len(self._anomalies),
            'skus_with_anomalies': 0,
            'total_anomalies': 0,
            'by_sku': {}
        }
        
        for sku, result in self._anomalies.items():
            count = result.get('count', 0)
            if count > 0:
                summary['skus_with_anomalies'] += 1
                summary['total_anomalies'] += count
                summary['by_sku'][sku] = count
        
        return summary
    
    def flag_anomalies(self, sku: str, anomaly_indices: List[int]):
        """
        flag specific anomalies for review
        """
        if sku not in self._anomalies:
            return
        
        flagged = {
            'sku': sku,
            'indices': anomaly_indices,
            'data': self._anomalies[sku]
        }
        
        STATE.flagged_anomalies.append(flagged)
        
        # create alert
        ALERTS.create_alert(
            alert_type='anomaly',
            message=f"Flagged {len(anomaly_indices)} anomalies in {sku} for review",
            severity=AlertSeverity.MEDIUM,
            source_tab='exploration',
            related_skus=[sku]
        )
    
    # ================ GETTERS ================
    
    def get_charts(self) -> Dict:
        """
        get all generated charts
        """
        return self._charts.copy()
    
    def get_decomposition(self, sku: str = None) -> Dict:
        """
        get decomposition results
        """
        key = sku if sku else 'all'
        return self._decomposition.get(key, {})
    
    def get_anomalies(self, sku: str = None) -> Dict:
        """
        get anomaly detection results
        """
        if sku:
            return self._anomalies.get(sku, {})
        return self._anomalies.copy()
    
    def is_exploring(self) -> bool:
        """
        check if exploration in progress
        """
        return self._is_exploring


# ================ SINGLETON INSTANCE ================

EXPLORER = ExplorationManager()