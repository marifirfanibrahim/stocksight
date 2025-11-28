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
import os

from config import ChartConfig
from core.data_operations import get_output_directory
from core.state import STATE
from utils.preprocessing import group_forecast_by_period


# ================ HELPER FUNCTIONS ================

def format_y_axis(ax, max_value):
    """
    format y axis with proper number formatting
    follows thousands separator
    """
    def format_func(x, pos):
        if x >= 1000000:
            return f'{x/1000000:.1f}M'
        elif x >= 1000:
            return f'{x/1000:.1f}K'
        else:
            return f'{x:,.0f}'
    
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_func))


def group_historical_by_period(historical, period='Weekly'):
    """
    group historical data by period
    """
    if period == 'Daily':
        return historical
    
    hist_copy = historical.copy()
    hist_copy.index = pd.to_datetime(hist_copy.index)
    
    freq_map = {'Weekly': 'W', 'Monthly': 'M', 'Quarterly': 'Q'}
    freq = freq_map.get(period, 'D')
    
    return hist_copy.resample(freq).sum()


# ================ CHART GENERATION ================

def generate_forecast_chart(historical, forecast, upper_forecast=None, lower_forecast=None, grouping='Daily'):
    """
    create matplotlib chart with confidence intervals
    """
    try:
        # ---------- APPLY GROUPING ----------
        if grouping != 'Daily' and upper_forecast is not None and lower_forecast is not None:
            forecast, upper_forecast, lower_forecast, _ = group_forecast_by_period(
                forecast, upper_forecast, lower_forecast, grouping
            )
            historical = group_historical_by_period(historical, grouping)
        
        # ---------- SETUP FIGURE ----------
        num_skus = len(forecast.columns)
        fig_height = ChartConfig.FIGURE_HEIGHT_PER_SKU * num_skus
        fig, axes = plt.subplots(num_skus, 1, figsize=(ChartConfig.FIGURE_WIDTH, fig_height))
        
        if num_skus == 1:
            axes = [axes]
        
        # ---------- PLOT EACH SKU ----------
        for idx, sku in enumerate(forecast.columns):
            ax = axes[idx]
            
            # calculate max for y-axis formatting
            max_val = 0
            
            # historical
            if sku in historical.columns:
                hist_vals = historical[sku]
                max_val = max(max_val, hist_vals.max())
                
                ax.plot(historical.index, hist_vals, 
                       label='Historical', color=ChartConfig.HISTORICAL_COLOR, 
                       linewidth=ChartConfig.LINE_WIDTH,
                       marker='o' if grouping != 'Daily' else None,
                       markersize=4)
            
            # forecast
            fore_vals = forecast[sku]
            max_val = max(max_val, fore_vals.max())
            
            ax.plot(forecast.index, fore_vals, 
                   label='Forecast', color=ChartConfig.FORECAST_COLOR, 
                   linewidth=ChartConfig.LINE_WIDTH, 
                   linestyle=ChartConfig.FORECAST_STYLE,
                   marker='s' if grouping != 'Daily' else None,
                   markersize=4)
            
            # confidence interval
            if upper_forecast is not None and lower_forecast is not None:
                if sku in upper_forecast.columns and sku in lower_forecast.columns:
                    max_val = max(max_val, upper_forecast[sku].max())
                    
                    ax.fill_between(
                        forecast.index,
                        lower_forecast[sku],
                        upper_forecast[sku],
                        color=ChartConfig.CONFIDENCE_COLOR,
                        alpha=ChartConfig.CONFIDENCE_ALPHA,
                        label='95% Confidence'
                    )
            
            # ---------- FORMAT Y AXIS ----------
            format_y_axis(ax, max_val)
            
            # styling
            grouping_label = f" ({grouping})" if grouping != 'Daily' else ""
            ax.set_title(f'SKU: {sku}{grouping_label}')
            ax.set_xlabel('Date')
            ax.set_ylabel('Quantity')
            ax.legend(loc='upper left')
            ax.grid(True, alpha=ChartConfig.GRID_ALPHA)
            
            # date formatting
            if grouping == 'Monthly':
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            elif grouping == 'Quarterly':
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # ---------- SAVE CHART ----------
        plt.tight_layout()
        
        output_dir = get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = output_dir / "forecast.png"
        plt.savefig(str(output_path), dpi=ChartConfig.SAVE_DPI, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close(fig)
        
        print(f"chart saved: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"chart error: {e}")
        import traceback
        traceback.print_exc()
        plt.close('all')
        raise


def generate_sku_summary_chart(forecast, grouping='Daily'):
    """
    create bar chart summary
    """
    try:
        if grouping != 'Daily':
            forecast_grouped, _, _, _ = group_forecast_by_period(
                forecast, forecast, forecast, grouping
            )
        else:
            forecast_grouped = forecast
        
        totals = forecast_grouped.sum().sort_values(ascending=True)
        
        fig, ax = plt.subplots(figsize=(10, max(4, len(totals) * 0.5)))
        
        colors = plt.cm.viridis([i / len(totals) for i in range(len(totals))])
        bars = ax.barh(totals.index, totals.values, color=colors)
        
        # format with K/M
        for bar in bars:
            width = bar.get_width()
            if width >= 1000000:
                label = f'{width/1000000:.1f}M'
            elif width >= 1000:
                label = f'{width/1000:.1f}K'
            else:
                label = f'{width:,.0f}'
            
            ax.text(width + totals.max() * 0.01, bar.get_y() + bar.get_height() / 2,
                   label, va='center', fontsize=9)
        
        # format x axis
        format_y_axis(ax, totals.max())
        
        grouping_label = f" ({grouping})" if grouping != 'Daily' else ""
        ax.set_title(f'Total Forecast by SKU{grouping_label}')
        ax.set_xlabel('Total Quantity')
        ax.set_ylabel('SKU')
        ax.grid(True, alpha=ChartConfig.GRID_ALPHA, axis='x')
        
        plt.tight_layout()
        
        output_dir = get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = output_dir / "sku_summary.png"
        plt.savefig(str(output_path), dpi=ChartConfig.SAVE_DPI, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close(fig)
        
        return output_path
        
    except Exception as e:
        print(f"summary error: {e}")
        plt.close('all')
        raise