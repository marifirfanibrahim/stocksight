"""
chart generation functions
matplotlib visualizations
"""


# ================ IMPORTS ================

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import pandas as pd
import numpy as np
import os
import gc

from config import ChartConfig, LargeDataConfig
from core.data_operations import get_output_directory
from core.state import STATE
from utils.preprocessing import group_forecast_by_period


# ================ CONSTANTS ================

MAX_SKUS_PER_PAGE = 8
MAX_IMAGE_HEIGHT_PIXELS = 3000


# ================ HELPER FUNCTIONS ================

def cleanup_matplotlib():
    """
    cleanup matplotlib memory
    """
    plt.close('all')
    gc.collect()


def format_y_axis(ax, max_value):
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


def format_x_axis_dates(ax, grouping='Daily'):
    """
    format x axis dates based on grouping
    daily: 12 Jan 2025
    weekly: 12 Jan 2025
    monthly: Jan 2025
    quarterly: Q1 2025
    """
    if grouping == 'Monthly':
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
    elif grouping == 'Quarterly':
        ax.xaxis.set_major_formatter(mdates.DateFormatter('Q%q %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    elif grouping == 'Weekly':
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %Y'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0))
    else:
        # daily
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b %Y'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())


def group_historical_by_period(historical, period='Weekly'):
    """
    group historical data by period
    """
    if period == 'Daily':
        return historical
    
    hist_copy = historical.copy()
    hist_copy.index = pd.to_datetime(hist_copy.index)
    
    freq_map = {'Weekly': 'W', 'Monthly': 'MS', 'Quarterly': 'QS'}
    freq = freq_map.get(period, 'D')
    
    return hist_copy.resample(freq).sum()


def get_top_skus(forecast, n):
    """
    get top n skus by total forecast
    """
    totals = forecast.sum().sort_values(ascending=False)
    return totals.head(n).index.tolist()


# ================ CHART GENERATION ================

def generate_forecast_chart(historical, forecast, upper_forecast=None, lower_forecast=None, grouping='Daily', sku_filter=None):
    """
    create matplotlib chart with confidence intervals
    limits skus to prevent memory issues
    """
    try:
        cleanup_matplotlib()
        
        # ---------- COPY DATA TO AVOID MODIFICATION ----------
        forecast = forecast.copy()
        historical = historical.copy() if historical is not None else pd.DataFrame()
        upper_forecast = upper_forecast.copy() if upper_forecast is not None else None
        lower_forecast = lower_forecast.copy() if lower_forecast is not None else None
        
        # ---------- APPLY SKU FILTER ----------
        if sku_filter and sku_filter != "All SKUs":
            # filter forecast
            if sku_filter in forecast.columns:
                forecast = forecast[[sku_filter]]
            else:
                print(f"SKU {sku_filter} not found in forecast")
                return None
            
            # filter historical if exists
            if sku_filter in historical.columns:
                historical = historical[[sku_filter]]
            else:
                # create empty historical for this SKU
                historical = pd.DataFrame(index=historical.index if len(historical) > 0 else forecast.index[:0])
                historical[sku_filter] = 0
            
            # filter confidence bands
            if upper_forecast is not None:
                if sku_filter in upper_forecast.columns:
                    upper_forecast = upper_forecast[[sku_filter]]
                else:
                    upper_forecast = None
                    
            if lower_forecast is not None:
                if sku_filter in lower_forecast.columns:
                    lower_forecast = lower_forecast[[sku_filter]]
                else:
                    lower_forecast = None
        
        # ---------- APPLY GROUPING ----------
        if grouping != 'Daily':
            if upper_forecast is not None and lower_forecast is not None:
                forecast, upper_forecast, lower_forecast, _ = group_forecast_by_period(
                    forecast, upper_forecast, lower_forecast, grouping
                )
            else:
                # handle case where confidence bands don't exist
                forecast, _, _, _ = group_forecast_by_period(
                    forecast, forecast.copy(), forecast.copy(), grouping
                )
            historical = group_historical_by_period(historical, grouping)
        
        # ---------- LIMIT SKUS STRICTLY ----------
        num_skus = len(forecast.columns)
        max_skus = min(MAX_SKUS_PER_PAGE, LargeDataConfig.MAX_SKUS_CHART)
        
        if num_skus > max_skus:
            skus_to_plot = get_top_skus(forecast, max_skus)
            skus_limited = True
            print(f"chart: showing top {max_skus} of {num_skus} skus")
        else:
            skus_to_plot = forecast.columns.tolist()
            skus_limited = False
        
        num_plots = len(skus_to_plot)
        
        if num_plots == 0:
            print("no skus to plot")
            return None
        
        # ---------- CALCULATE FIGURE SIZE ----------
        height_per_sku = 2.5
        fig_height = min(height_per_sku * num_plots, 20)
        fig_width = 10
        
        # calculate expected pixel height
        dpi = 80
        pixel_height = fig_height * dpi
        
        if pixel_height > MAX_IMAGE_HEIGHT_PIXELS:
            fig_height = MAX_IMAGE_HEIGHT_PIXELS / dpi
        
        # ---------- SETUP FIGURE ----------
        fig, axes = plt.subplots(num_plots, 1, figsize=(fig_width, fig_height))
        
        if num_plots == 1:
            axes = [axes]
        
        # ---------- PLOT EACH SKU ----------
        for idx, sku in enumerate(skus_to_plot):
            ax = axes[idx]
            max_val = 0
            
            # historical
            if sku in historical.columns:
                hist_vals = historical[sku]
                if len(hist_vals) > 0 and not hist_vals.isna().all():
                    max_val = max(max_val, hist_vals.max())
                    ax.plot(historical.index, hist_vals, 
                           label='Historical', color=ChartConfig.HISTORICAL_COLOR, 
                           linewidth=1.2)
            
            # forecast
            if sku in forecast.columns:
                fore_vals = forecast[sku]
                if len(fore_vals) > 0 and not fore_vals.isna().all():
                    max_val = max(max_val, fore_vals.max())
                    ax.plot(forecast.index, fore_vals, 
                           label='Forecast', color=ChartConfig.FORECAST_COLOR, 
                           linewidth=1.2, 
                           linestyle='--')
            
            # confidence interval
            if upper_forecast is not None and lower_forecast is not None:
                if sku in upper_forecast.columns and sku in lower_forecast.columns:
                    upper_vals = upper_forecast[sku]
                    lower_vals = lower_forecast[sku]
                    if not upper_vals.isna().all():
                        max_val = max(max_val, upper_vals.max())
                        ax.fill_between(
                            forecast.index,
                            lower_vals,
                            upper_vals,
                            color=ChartConfig.CONFIDENCE_COLOR,
                            alpha=ChartConfig.CONFIDENCE_ALPHA,
                            label='95% CI'
                        )
            
            # format axes
            if max_val > 0:
                format_y_axis(ax, max_val)
            
            format_x_axis_dates(ax, grouping)
            
            # compact styling
            ax.set_title(f'{sku}', fontsize=8, pad=2)
            ax.set_xlabel('')
            ax.set_ylabel('Qty', fontsize=7)
            ax.legend(loc='upper left', fontsize=6, framealpha=0.7)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='both', labelsize=6)
            
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=30, ha='right', fontsize=6)
        
        # ---------- ADD INFO TEXT ----------
        info_parts = []
        if grouping != 'Daily':
            info_parts.append(grouping)
        if skus_limited:
            info_parts.append(f"Top {max_skus} of {num_skus} SKUs")
        if sku_filter and sku_filter != "All SKUs":
            info_parts.append(f"Filter: {sku_filter}")
        
        if info_parts:
            fig.text(0.5, 0.01, ' | '.join(info_parts), 
                    ha='center', fontsize=7, color='gray')
            plt.subplots_adjust(bottom=0.05)
        
        # ---------- SAVE CHART ----------
        plt.tight_layout()
        
        output_dir = get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = output_dir / "forecast.png"
        plt.savefig(str(output_path), dpi=dpi, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        
        cleanup_matplotlib()
        
        print(f"chart saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"chart error: {e}")
        import traceback
        traceback.print_exc()
        cleanup_matplotlib()
        raise


def generate_sku_summary_chart(forecast, grouping='Daily'):
    """
    create bar chart summary
    """
    try:
        cleanup_matplotlib()
        
        if grouping != 'Daily':
            forecast_grouped, _, _, _ = group_forecast_by_period(
                forecast, forecast, forecast, grouping
            )
        else:
            forecast_grouped = forecast
        
        totals = forecast_grouped.sum().sort_values(ascending=True)
        
        # limit to top 15
        max_bars = 15
        if len(totals) > max_bars:
            totals = totals.tail(max_bars)
            limited = True
        else:
            limited = False
        
        fig_height = max(3, len(totals) * 0.3)
        fig, ax = plt.subplots(figsize=(8, fig_height))
        
        colors = plt.cm.viridis([i / len(totals) for i in range(len(totals))])
        sku_names = [str(sku) for sku in totals.index.tolist()]
        bars = ax.barh(sku_names, totals.values, color=colors)
        
        for bar in bars:
            width = bar.get_width()
            if width >= 1000000:
                label = f'{width/1000000:.1f}M'
            elif width >= 1000:
                label = f'{width/1000:.1f}K'
            else:
                label = f'{width:,.0f}'
            
            ax.text(width + totals.max() * 0.01, bar.get_y() + bar.get_height() / 2,
                   label, va='center', fontsize=7)
        
        format_y_axis(ax, totals.max())
        
        title = f'Forecast by SKU'
        if limited:
            title += f' (Top {max_bars})'
        ax.set_title(title, fontsize=9)
        ax.set_xlabel('Total Quantity', fontsize=8)
        ax.grid(True, alpha=0.3, axis='x')
        ax.tick_params(axis='both', labelsize=7)
        
        plt.tight_layout()
        
        output_dir = get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = output_dir / "sku_summary.png"
        plt.savefig(str(output_path), dpi=80, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        
        cleanup_matplotlib()
        
        return output_path
        
    except Exception as e:
        print(f"summary error: {e}")
        cleanup_matplotlib()
        raise


def generate_seasonality_chart(seasonality_info, output_path=None):
    """
    create seasonality visualization
    """
    try:
        cleanup_matplotlib()
        
        fig, axes = plt.subplots(1, 2, figsize=(10, 3))
        
        # ---------- MONTHLY PATTERN ----------
        ax1 = axes[0]
        monthly = seasonality_info.get('monthly_pattern', {})
        if monthly:
            months = list(monthly.keys())
            values = list(monthly.values())
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            
            labels = [month_names[m-1] if 1 <= m <= 12 else str(m) for m in months]
            
            if max(values) > min(values):
                colors = plt.cm.Blues([0.3 + 0.5 * (v - min(values)) / (max(values) - min(values)) for v in values])
            else:
                colors = plt.cm.Blues([0.5] * len(values))
            
            ax1.bar(labels, values, color=colors)
            ax1.set_title('Monthly Pattern', fontsize=9)
            ax1.set_ylabel('Avg Quantity', fontsize=8)
            ax1.tick_params(axis='both', labelsize=7)
            ax1.grid(True, alpha=0.3, axis='y')
            
            cv = seasonality_info.get('monthly_cv', 0)
            has_seasonal = seasonality_info.get('has_monthly_seasonality', False)
            status = "Seasonal" if has_seasonal else "Stable"
            ax1.set_xlabel(f'{status} (CV: {cv:.2f})', fontsize=7)
        
        # ---------- WEEKLY PATTERN ----------
        ax2 = axes[1]
        weekly = seasonality_info.get('weekly_pattern', {})
        if weekly:
            days = list(weekly.keys())
            values = list(weekly.values())
            day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            
            labels = [day_names[d] if 0 <= d <= 6 else str(d) for d in days]
            
            if max(values) > min(values):
                colors = plt.cm.Greens([0.3 + 0.5 * (v - min(values)) / (max(values) - min(values)) for v in values])
            else:
                colors = plt.cm.Greens([0.5] * len(values))
            
            ax2.bar(labels, values, color=colors)
            ax2.set_title('Weekly Pattern', fontsize=9)
            ax2.set_ylabel('Avg Quantity', fontsize=8)
            ax2.tick_params(axis='both', labelsize=7)
            ax2.grid(True, alpha=0.3, axis='y')
            
            cv = seasonality_info.get('weekly_cv', 0)
            has_seasonal = seasonality_info.get('has_weekly_seasonality', False)
            status = "Seasonal" if has_seasonal else "Stable"
            ax2.set_xlabel(f'{status} (CV: {cv:.2f})', fontsize=7)
        
        plt.tight_layout()
        
        if output_path is None:
            output_dir = get_output_directory()
            output_path = output_dir / "seasonality.png"
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(str(output_path), dpi=80, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        
        cleanup_matplotlib()
        
        return output_path
        
    except Exception as e:
        print(f"seasonality chart error: {e}")
        cleanup_matplotlib()
        return None