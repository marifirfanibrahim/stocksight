"""
chart generation for pyqt embedding
matplotlib visualizations with base64 output
"""


# ================ IMPORTS ================

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import pandas as pd
import numpy as np
import io
import base64
import gc
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from config import ChartConfig, Paths
from core.state import STATE
from core.data_operations import get_output_directory


# ================ CLEANUP ================

def cleanup_matplotlib():
    """
    cleanup matplotlib memory
    """
    plt.close('all')
    gc.collect()


# ================ THEME ================

def apply_chart_theme(fig, ax, dark_mode: bool = True):
    """
    apply theme to chart
    """
    if dark_mode:
        theme = ChartConfig.DARK_THEME
    else:
        theme = ChartConfig.LIGHT_THEME
    
    fig.patch.set_facecolor(theme['background'])
    ax.set_facecolor(theme['background'])
    ax.tick_params(colors=theme['text'])
    ax.xaxis.label.set_color(theme['text'])
    ax.yaxis.label.set_color(theme['text'])
    ax.title.set_color(theme['text'])
    
    for spine in ax.spines.values():
        spine.set_color(theme['grid'])
    
    ax.grid(True, alpha=0.3, color=theme['grid'])


# ================ FORMATTERS ================

def format_y_axis(ax, max_value: float):
    """
    format y axis with proper number formatting
    """
    def format_func(x, pos):
        if x >= 1000000:
            return f'{x/1000000:.1f}M'
        elif x >= 1000:
            return f'{x/1000:.1f}K'
        else:
            return f'{x:,.0f}'
    
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_func))


def format_x_axis_dates(ax, grouping: str = 'Daily'):
    """
    format x axis dates based on grouping
    """
    if grouping == 'Monthly':
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
    elif grouping == 'Quarterly':
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    elif grouping == 'Weekly':
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())


# ================ CHART TO BASE64 ================

def fig_to_base64(fig) -> str:
    """
    convert matplotlib figure to base64 string
    """
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=ChartConfig.DISPLAY_DPI, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode()
    buf.close()
    return img_str


def fig_to_bytes(fig) -> bytes:
    """
    convert matplotlib figure to bytes
    """
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=ChartConfig.DISPLAY_DPI, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    buf.seek(0)
    return buf.read()


# ================ FORECAST CHART ================

def generate_forecast_chart(
    historical: pd.DataFrame,
    forecast: pd.DataFrame,
    upper_forecast: pd.DataFrame = None,
    lower_forecast: pd.DataFrame = None,
    grouping: str = 'Daily',
    sku_filter: str = None,
    dark_mode: bool = True,
    save_to_file: bool = True
) -> Tuple[Optional[str], Optional[Path]]:
    """
    create forecast chart
    returns base64 string and file path
    """
    try:
        cleanup_matplotlib()
        
        # copy data
        forecast = forecast.copy()
        historical = historical.copy() if historical is not None else pd.DataFrame()
        upper = upper_forecast.copy() if upper_forecast is not None else None
        lower = lower_forecast.copy() if lower_forecast is not None else None
        
        # apply sku filter
        if sku_filter and sku_filter != "All SKUs":
            if sku_filter in forecast.columns:
                forecast = forecast[[sku_filter]]
                if sku_filter in historical.columns:
                    historical = historical[[sku_filter]]
                if upper is not None and sku_filter in upper.columns:
                    upper = upper[[sku_filter]]
                if lower is not None and sku_filter in lower.columns:
                    lower = lower[[sku_filter]]
        
        # limit skus
        max_skus = 10
        if len(forecast.columns) > max_skus:
            totals = forecast.sum().sort_values(ascending=False)
            top_skus = totals.head(max_skus).index.tolist()
            forecast = forecast[top_skus]
            if len(historical.columns) > 0:
                historical = historical[[c for c in top_skus if c in historical.columns]]
            if upper is not None:
                upper = upper[[c for c in top_skus if c in upper.columns]]
            if lower is not None:
                lower = lower[[c for c in top_skus if c in lower.columns]]
        
        num_plots = len(forecast.columns)
        if num_plots == 0:
            return None, None
        
        # calculate figure size
        height_per_sku = ChartConfig.FIGURE_HEIGHT_PER_SKU
        fig_height = min(height_per_sku * num_plots, ChartConfig.MAX_FIGURE_HEIGHT)
        fig_width = ChartConfig.FIGURE_WIDTH
        
        # create figure
        fig, axes = plt.subplots(num_plots, 1, figsize=(fig_width, fig_height))
        
        if num_plots == 1:
            axes = [axes]
        
        # plot each sku
        for idx, sku in enumerate(forecast.columns):
            ax = axes[idx]
            apply_chart_theme(fig, ax, dark_mode)
            
            max_val = 0
            
            # historical
            if sku in historical.columns:
                hist_vals = historical[sku].dropna()
                if len(hist_vals) > 0:
                    max_val = max(max_val, hist_vals.max())
                    ax.plot(
                        historical.index, historical[sku],
                        label='Historical',
                        color=ChartConfig.HISTORICAL_COLOR,
                        linewidth=1.5
                    )
            
            # forecast
            fore_vals = forecast[sku].dropna()
            if len(fore_vals) > 0:
                max_val = max(max_val, fore_vals.max())
                ax.plot(
                    forecast.index, forecast[sku],
                    label='Forecast',
                    color=ChartConfig.FORECAST_COLOR,
                    linewidth=1.5,
                    linestyle='--'
                )
            
            # confidence interval
            if upper is not None and lower is not None:
                if sku in upper.columns and sku in lower.columns:
                    ax.fill_between(
                        forecast.index,
                        lower[sku],
                        upper[sku],
                        color=ChartConfig.CONFIDENCE_COLOR,
                        alpha=ChartConfig.CONFIDENCE_ALPHA,
                        label='95% CI'
                    )
            
            # formatting
            if max_val > 0:
                format_y_axis(ax, max_val)
            
            format_x_axis_dates(ax, grouping)
            
            ax.set_title(sku, fontsize=10, pad=5)
            ax.set_ylabel('Qty', fontsize=9)
            ax.legend(loc='upper left', fontsize=8, framealpha=0.7)
            
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=8)
        
        plt.tight_layout()
        
        # convert to base64
        img_base64 = fig_to_base64(fig)
        
        # save to file
        file_path = None
        if save_to_file:
            output_dir = get_output_directory()
            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / "forecast.png"
            fig.savefig(str(file_path), dpi=ChartConfig.SAVE_DPI, bbox_inches='tight',
                        facecolor=fig.get_facecolor(), edgecolor='none')
        
        cleanup_matplotlib()
        
        return img_base64, file_path
        
    except Exception as e:
        print(f"chart error: {e}")
        import traceback
        traceback.print_exc()
        cleanup_matplotlib()
        return None, None


# ================ SUMMARY CHART ================

def generate_summary_chart(
    forecast: pd.DataFrame,
    grouping: str = 'Daily',
    dark_mode: bool = True
) -> Tuple[Optional[str], Optional[Path]]:
    """
    create bar chart summary
    """
    try:
        cleanup_matplotlib()
        
        totals = forecast.sum().sort_values(ascending=True)
        
        # limit
        max_bars = 15
        if len(totals) > max_bars:
            totals = totals.tail(max_bars)
        
        fig_height = max(4, len(totals) * 0.4)
        fig, ax = plt.subplots(figsize=(10, fig_height))
        
        apply_chart_theme(fig, ax, dark_mode)
        
        # create bars
        colors = plt.cm.viridis([i / len(totals) for i in range(len(totals))])
        bars = ax.barh(range(len(totals)), totals.values, color=colors)
        
        ax.set_yticks(range(len(totals)))
        ax.set_yticklabels([str(s) for s in totals.index])
        
        # add value labels
        for bar in bars:
            width = bar.get_width()
            if width >= 1000000:
                label = f'{width/1000000:.1f}M'
            elif width >= 1000:
                label = f'{width/1000:.1f}K'
            else:
                label = f'{width:,.0f}'
            
            ax.text(width + totals.max() * 0.01, bar.get_y() + bar.get_height() / 2,
                    label, va='center', fontsize=8,
                    color=ChartConfig.DARK_THEME['text'] if dark_mode else ChartConfig.LIGHT_THEME['text'])
        
        ax.set_title('Total Forecast by SKU', fontsize=12)
        ax.set_xlabel('Total Quantity', fontsize=10)
        
        plt.tight_layout()
        
        img_base64 = fig_to_base64(fig)
        
        output_dir = get_output_directory()
        file_path = output_dir / "summary.png"
        fig.savefig(str(file_path), dpi=ChartConfig.SAVE_DPI, bbox_inches='tight',
                    facecolor=fig.get_facecolor(), edgecolor='none')
        
        cleanup_matplotlib()
        
        return img_base64, file_path
        
    except Exception as e:
        print(f"summary chart error: {e}")
        cleanup_matplotlib()
        return None, None


# ================ TIME SERIES CHART ================

def generate_time_series_chart(
    df: pd.DataFrame,
    sku: str = None,
    value_column: str = 'Quantity',
    overlays: List[str] = None,
    anomalies: Dict = None,
    dark_mode: bool = True
) -> Optional[str]:
    """
    create time series chart with optional overlays
    """
    try:
        cleanup_matplotlib()
        
        if sku:
            plot_df = df[df['SKU'] == sku].copy()
        else:
            plot_df = df.copy()
        
        if len(plot_df) == 0:
            return None
        
        plot_df['Date'] = pd.to_datetime(plot_df['Date'])
        daily = plot_df.groupby('Date')[value_column].sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        apply_chart_theme(fig, ax, dark_mode)
        
        # main series
        ax.plot(
            daily['Date'], daily[value_column],
            color=ChartConfig.HISTORICAL_COLOR,
            linewidth=1.5,
            label=value_column
        )
        
        # overlays
        if overlays:
            overlay_colors = ['#4CAF50', '#FF9800', '#9C27B0', '#00BCD4']
            
            for i, overlay_col in enumerate(overlays):
                if overlay_col in plot_df.columns:
                    overlay_data = plot_df.groupby('Date')[overlay_col].mean().reset_index()
                    
                    ax2 = ax.twinx()
                    ax2.plot(
                        overlay_data['Date'], overlay_data[overlay_col],
                        color=overlay_colors[i % len(overlay_colors)],
                        linewidth=1,
                        linestyle='--',
                        label=overlay_col,
                        alpha=0.7
                    )
                    ax2.set_ylabel(overlay_col, fontsize=10)
        
        # anomalies
        if anomalies and 'dates' in anomalies:
            ax.scatter(
                anomalies['dates'],
                anomalies['values'],
                color=ChartConfig.ANOMALY_COLOR,
                s=50,
                zorder=5,
                label='Anomalies'
            )
        
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel(value_column, fontsize=10)
        ax.set_title(f"Time Series: {sku if sku else 'All SKUs'}", fontsize=12)
        ax.legend(loc='upper left', fontsize=9)
        
        format_x_axis_dates(ax, 'Daily')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        img_base64 = fig_to_base64(fig)
        cleanup_matplotlib()
        
        return img_base64
        
    except Exception as e:
        print(f"time series chart error: {e}")
        cleanup_matplotlib()
        return None


# ================ DECOMPOSITION CHART ================

def generate_decomposition_chart(
    decomposition: Dict,
    dark_mode: bool = True
) -> Optional[str]:
    """
    create seasonal decomposition chart
    """
    try:
        cleanup_matplotlib()
        
        if 'error' in decomposition:
            return None
        
        fig, axes = plt.subplots(4, 1, figsize=(12, 10))
        
        components = ['observed', 'trend', 'seasonal', 'residual']
        titles = ['Observed', 'Trend', 'Seasonal', 'Residual']
        
        for ax, comp, title in zip(axes, components, titles):
            apply_chart_theme(fig, ax, dark_mode)
            
            data = decomposition.get(comp, {})
            if data:
                dates = pd.to_datetime(list(data.keys()))
                values = list(data.values())
                ax.plot(dates, values, color=ChartConfig.HISTORICAL_COLOR, linewidth=1)
            
            ax.set_ylabel(title, fontsize=10)
        
        axes[0].set_title('Seasonal Decomposition', fontsize=12)
        axes[-1].set_xlabel('Date', fontsize=10)
        
        plt.tight_layout()
        
        img_base64 = fig_to_base64(fig)
        cleanup_matplotlib()
        
        return img_base64
        
    except Exception as e:
        print(f"decomposition chart error: {e}")
        cleanup_matplotlib()
        return None


# ================ FEATURE IMPORTANCE CHART ================

def generate_feature_importance_chart(
    importance: Dict[str, float],
    max_features: int = 20,
    dark_mode: bool = True
) -> Optional[str]:
    """
    create feature importance bar chart
    """
    try:
        cleanup_matplotlib()
        
        if not importance:
            return None
        
        # sort and limit
        sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
        sorted_imp = sorted_imp[:max_features]
        
        names = [item[0] for item in sorted_imp]
        values = [item[1] for item in sorted_imp]
        
        # truncate long names
        names = [n[:30] + '...' if len(n) > 30 else n for n in names]
        
        fig_height = max(6, len(names) * 0.4)
        fig, ax = plt.subplots(figsize=(10, fig_height))
        
        apply_chart_theme(fig, ax, dark_mode)
        
        colors = plt.cm.RdYlGn([v for v in values])
        bars = ax.barh(range(len(names)), values, color=colors)
        
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names)
        ax.invert_yaxis()
        
        ax.set_xlabel('Importance Score', fontsize=10)
        ax.set_title('Feature Importance', fontsize=12)
        
        plt.tight_layout()
        
        img_base64 = fig_to_base64(fig)
        cleanup_matplotlib()
        
        return img_base64
        
    except Exception as e:
        print(f"feature importance chart error: {e}")
        cleanup_matplotlib()
        return None


# ================ MODEL COMPARISON CHART ================

def generate_model_comparison_chart(
    metrics: Dict[str, Dict[str, float]],
    metric_name: str = 'MAE',
    dark_mode: bool = True
) -> Optional[str]:
    """
    create model comparison bar chart
    """
    try:
        cleanup_matplotlib()
        
        if not metrics:
            return None
        
        models = list(metrics.keys())
        values = [metrics[m].get(metric_name, 0) for m in models]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        apply_chart_theme(fig, ax, dark_mode)
        
        colors = plt.cm.viridis([i / len(models) for i in range(len(models))])
        bars = ax.bar(range(len(models)), values, color=colors)
        
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(models, rotation=45, ha='right')
        
        ax.set_ylabel(metric_name, fontsize=10)
        ax.set_title(f'Model Comparison - {metric_name}', fontsize=12)
        
        # add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{height:.4f}', ha='center', va='bottom', fontsize=9,
                    color=ChartConfig.DARK_THEME['text'] if dark_mode else ChartConfig.LIGHT_THEME['text'])
        
        plt.tight_layout()
        
        img_base64 = fig_to_base64(fig)
        cleanup_matplotlib()
        
        return img_base64
        
    except Exception as e:
        print(f"model comparison chart error: {e}")
        cleanup_matplotlib()
        return None