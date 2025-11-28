"""
chart generation functions
matplotlib visualizations
"""


# ================ IMPORTS ================

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from config import ChartConfig
from core.data_operations import get_output_directory
from core.state import STATE
from utils.preprocessing import group_forecast_by_period


# ================ CHART GENERATION ================

def generate_forecast_chart(historical, forecast, upper_forecast=None, lower_forecast=None, grouping='Daily'):
    """
    create matplotlib chart with confidence intervals
    supports date grouping
    save to output folder
    """
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
    
    # ---------- DETERMINE DATE FORMAT ----------
    if grouping == 'Daily':
        date_format = '%Y-%m-%d'
    elif grouping == 'Weekly':
        date_format = '%Y-%m-%d'
    elif grouping == 'Monthly':
        date_format = '%Y-%m'
    elif grouping == 'Quarterly':
        date_format = '%Y-Q%q'
    else:
        date_format = '%Y-%m-%d'
    
    # ---------- PLOT EACH SKU ----------
    for idx, sku in enumerate(forecast.columns):
        ax = axes[idx]
        
        # ---------- HISTORICAL DATA ----------
        if sku in historical.columns:
            ax.plot(historical.index, historical[sku], 
                   label='Historical', color=ChartConfig.HISTORICAL_COLOR, 
                   linewidth=ChartConfig.LINE_WIDTH,
                   marker='o' if grouping != 'Daily' else None,
                   markersize=4)
        
        # ---------- FORECAST DATA ----------
        ax.plot(forecast.index, forecast[sku], 
               label='Forecast', color=ChartConfig.FORECAST_COLOR, 
               linewidth=ChartConfig.LINE_WIDTH, 
               linestyle=ChartConfig.FORECAST_STYLE,
               marker='s' if grouping != 'Daily' else None,
               markersize=4)
        
        # ---------- CONFIDENCE INTERVAL ----------
        if upper_forecast is not None and lower_forecast is not None:
            if sku in upper_forecast.columns and sku in lower_forecast.columns:
                ax.fill_between(
                    forecast.index,
                    lower_forecast[sku],
                    upper_forecast[sku],
                    color=ChartConfig.CONFIDENCE_COLOR,
                    alpha=ChartConfig.CONFIDENCE_ALPHA,
                    label='95% Confidence'
                )
        
        # ---------- STYLING ----------
        grouping_label = f" ({grouping})" if grouping != 'Daily' else ""
        ax.set_title(f'SKU: {sku}{grouping_label}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Quantity')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=ChartConfig.GRID_ALPHA)
        
        # ---------- DATE FORMATTING ----------
        if grouping == 'Monthly':
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
        elif grouping == 'Quarterly':
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        elif grouping == 'Weekly':
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # ---------- SAVE CHART ----------
    plt.tight_layout()
    
    output_path = get_output_directory() / "forecast.png"
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    print(f"chart saved to {output_path} (grouping: {grouping})")
    
    return output_path


def group_historical_by_period(historical, period='Weekly'):
    """
    group historical data by period
    """
    if period == 'Daily':
        return historical
    
    hist_copy = historical.copy()
    hist_copy.index = pd.to_datetime(hist_copy.index)
    
    if period == 'Weekly':
        freq = 'W'
    elif period == 'Monthly':
        freq = 'M'
    elif period == 'Quarterly':
        freq = 'Q'
    else:
        return historical
    
    grouped = hist_copy.resample(freq).sum()
    
    return grouped


def generate_comparison_chart(original_forecast, modified_forecast, sku, grouping='Daily'):
    """
    create comparison chart for scenario analysis
    """
    # ---------- APPLY GROUPING ----------
    if grouping != 'Daily':
        # Create dummy upper/lower for grouping function
        original_grouped, _, _, _ = group_forecast_by_period(
            original_forecast, original_forecast, original_forecast, grouping
        )
        modified_grouped, _, _, _ = group_forecast_by_period(
            modified_forecast, modified_forecast, modified_forecast, grouping
        )
    else:
        original_grouped = original_forecast
        modified_grouped = modified_forecast
    
    # ---------- SETUP FIGURE ----------
    fig, ax = plt.subplots(figsize=(ChartConfig.FIGURE_WIDTH, 5))
    
    # ---------- PLOT DATA ----------
    if sku in original_grouped.columns:
        ax.plot(original_grouped.index, original_grouped[sku], 
               label='Original', color='blue', 
               linewidth=ChartConfig.LINE_WIDTH,
               marker='o' if grouping != 'Daily' else None,
               markersize=4)
    
    if sku in modified_grouped.columns:
        ax.plot(modified_grouped.index, modified_grouped[sku], 
               label='Modified', color='orange', 
               linewidth=ChartConfig.LINE_WIDTH, 
               linestyle='--',
               marker='s' if grouping != 'Daily' else None,
               markersize=4)
    
    # ---------- STYLING ----------
    grouping_label = f" ({grouping})" if grouping != 'Daily' else ""
    ax.set_title(f'Scenario Comparison: {sku}{grouping_label}')
    ax.set_xlabel('Date')
    ax.set_ylabel('Quantity')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=ChartConfig.GRID_ALPHA)
    
    # ---------- DATE FORMATTING ----------
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # ---------- SAVE CHART ----------
    plt.tight_layout()
    
    output_path = get_output_directory() / "comparison.png"
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    return output_path


def generate_sku_summary_chart(forecast, grouping='Daily'):
    """
    create bar chart summary of all skus
    """
    # ---------- APPLY GROUPING ----------
    if grouping != 'Daily':
        forecast_grouped, _, _, _ = group_forecast_by_period(
            forecast, forecast, forecast, grouping
        )
    else:
        forecast_grouped = forecast
    
    # ---------- CALCULATE TOTALS ----------
    totals = forecast_grouped.sum().sort_values(ascending=True)
    
    # ---------- SETUP FIGURE ----------
    fig, ax = plt.subplots(figsize=(10, max(4, len(totals) * 0.5)))
    
    # ---------- COLORS ----------
    colors = plt.cm.viridis([i / len(totals) for i in range(len(totals))])
    
    # ---------- PLOT BARS ----------
    bars = ax.barh(totals.index, totals.values, color=colors)
    
    # ---------- ADD VALUES ----------
    for bar in bars:
        width = bar.get_width()
        ax.text(width + totals.max() * 0.01, bar.get_y() + bar.get_height() / 2,
               f'{width:,.0f}', va='center', fontsize=9)
    
    # ---------- STYLING ----------
    grouping_label = f" ({grouping})" if grouping != 'Daily' else ""
    ax.set_title(f'Total Forecast by SKU{grouping_label}')
    ax.set_xlabel('Total Quantity')
    ax.set_ylabel('SKU')
    ax.grid(True, alpha=ChartConfig.GRID_ALPHA, axis='x')
    
    # ---------- SAVE CHART ----------
    plt.tight_layout()
    
    output_path = get_output_directory() / "sku_summary.png"
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    return output_path