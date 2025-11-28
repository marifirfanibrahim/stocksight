"""
chart generation utilities
create forecast visualizations
matplotlib based plotting
"""


# ================ IMPORTS ================

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import os
import sys

# ---------- LOCAL IMPORTS ----------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Paths, ChartConfig


# ================ CHART STYLES ================

def apply_chart_style():
    """
    set matplotlib style
    consistent chart appearance
    """
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.labelsize'] = 11
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['legend.fontsize'] = 9


# ================ SINGLE SKU CHART ================

def generate_single_sku_chart(historical, forecast, sku, output_path=None):
    """
    create chart for single sku
    plot historical and forecast
    """
    # ---------- APPLY STYLE ----------
    apply_chart_style()
    
    # ---------- CREATE FIGURE ----------
    fig, ax = plt.subplots(figsize=(ChartConfig.FIGURE_WIDTH, 5))
    
    # ---------- PLOT HISTORICAL ----------
    ax.plot(
        historical.index, 
        historical[sku],
        label='Historical',
        color=ChartConfig.HISTORICAL_COLOR,
        linewidth=ChartConfig.LINE_WIDTH,
        linestyle=ChartConfig.HISTORICAL_STYLE
    )
    
    # ---------- PLOT FORECAST ----------
    ax.plot(
        forecast.index,
        forecast[sku],
        label='Forecast',
        color=ChartConfig.FORECAST_COLOR,
        linewidth=ChartConfig.LINE_WIDTH,
        linestyle=ChartConfig.FORECAST_STYLE
    )
    
    # ---------- CONNECT LINES ----------
    if len(historical) > 0 and len(forecast) > 0:
        connect_x = [historical.index[-1], forecast.index[0]]
        connect_y = [historical[sku].iloc[-1], forecast[sku].iloc[0]]
        ax.plot(connect_x, connect_y, color=ChartConfig.FORECAST_COLOR,
                linewidth=ChartConfig.LINE_WIDTH, linestyle=':')
    
    # ---------- STYLING ----------
    ax.set_title(f'Forecast: {sku}')
    ax.set_xlabel('Date')
    ax.set_ylabel('Quantity')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=ChartConfig.GRID_ALPHA)
    
    # ---------- DATE FORMATTING ----------
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.xticks(rotation=45)
    
    # ---------- SAVE ----------
    plt.tight_layout()
    
    if output_path is None:
        output_path = Paths.OUTPUT_DIR / f"forecast_{sku}.png"
    
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


# ================ MULTI SKU CHART ================

def generate_multi_sku_chart(historical, forecast, output_path=None):
    """
    create chart for all skus
    subplots per sku
    """
    # ---------- APPLY STYLE ----------
    apply_chart_style()
    
    # ---------- GET SKUS ----------
    skus = forecast.columns.tolist()
    num_skus = len(skus)
    
    # ---------- CREATE FIGURE ----------
    fig_height = ChartConfig.FIGURE_HEIGHT_PER_SKU * num_skus
    fig, axes = plt.subplots(num_skus, 1, figsize=(ChartConfig.FIGURE_WIDTH, fig_height))
    
    if num_skus == 1:
        axes = [axes]
    
    # ---------- PLOT EACH SKU ----------
    for idx, sku in enumerate(skus):
        ax = axes[idx]
        
        # ---------- HISTORICAL ----------
        if sku in historical.columns:
            ax.plot(
                historical.index,
                historical[sku],
                label='Historical',
                color=ChartConfig.HISTORICAL_COLOR,
                linewidth=ChartConfig.LINE_WIDTH,
                linestyle=ChartConfig.HISTORICAL_STYLE
            )
        
        # ---------- FORECAST ----------
        ax.plot(
            forecast.index,
            forecast[sku],
            label='Forecast',
            color=ChartConfig.FORECAST_COLOR,
            linewidth=ChartConfig.LINE_WIDTH,
            linestyle=ChartConfig.FORECAST_STYLE
        )
        
        # ---------- STYLING ----------
        ax.set_title(f'SKU: {sku}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Quantity')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=ChartConfig.GRID_ALPHA)
        
        # ---------- DATE FORMATTING ----------
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    # ---------- SAVE ----------
    plt.tight_layout()
    
    if output_path is None:
        output_path = Paths.FORECAST_CHART
    
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


# ================ COMPARISON CHART ================

def generate_comparison_chart(original, modified, sku, output_path=None):
    """
    compare original vs modified data
    scenario comparison visualization
    """
    # ---------- APPLY STYLE ----------
    apply_chart_style()
    
    # ---------- CREATE FIGURE ----------
    fig, ax = plt.subplots(figsize=(ChartConfig.FIGURE_WIDTH, 5))
    
    # ---------- PLOT ORIGINAL ----------
    ax.plot(
        original.index,
        original[sku],
        label='Original',
        color='blue',
        linewidth=ChartConfig.LINE_WIDTH
    )
    
    # ---------- PLOT MODIFIED ----------
    ax.plot(
        modified.index,
        modified[sku],
        label='Modified',
        color='orange',
        linewidth=ChartConfig.LINE_WIDTH,
        linestyle='--'
    )
    
    # ---------- STYLING ----------
    ax.set_title(f'Scenario Comparison: {sku}')
    ax.set_xlabel('Date')
    ax.set_ylabel('Quantity')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=ChartConfig.GRID_ALPHA)
    
    # ---------- FILL DIFFERENCE ----------
    ax.fill_between(
        original.index,
        original[sku],
        modified[sku],
        alpha=0.2,
        color='orange'
    )
    
    # ---------- SAVE ----------
    plt.tight_layout()
    
    if output_path is None:
        output_path = Paths.OUTPUT_DIR / f"comparison_{sku}.png"
    
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


# ================ SUMMARY CHART ================

def generate_summary_chart(forecast, output_path=None):
    """
    create summary bar chart
    total forecast per sku
    """
    # ---------- APPLY STYLE ----------
    apply_chart_style()
    
    # ---------- CALCULATE TOTALS ----------
    totals = forecast.sum().sort_values(ascending=True)
    
    # ---------- CREATE FIGURE ----------
    fig, ax = plt.subplots(figsize=(10, max(5, len(totals) * 0.5)))
    
    # ---------- PLOT BARS ----------
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(totals)))
    bars = ax.barh(totals.index, totals.values, color=colors)
    
    # ---------- ADD VALUES ----------
    for bar, value in zip(bars, totals.values):
        ax.text(
            bar.get_width() + totals.max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f'{value:,.0f}',
            va='center',
            fontsize=9
        )
    
    # ---------- STYLING ----------
    ax.set_title('Total Forecast by SKU')
    ax.set_xlabel('Total Quantity')
    ax.set_ylabel('SKU')
    ax.grid(True, alpha=ChartConfig.GRID_ALPHA, axis='x')
    
    # ---------- SAVE ----------
    plt.tight_layout()
    
    if output_path is None:
        output_path = Paths.OUTPUT_DIR / "forecast_summary.png"
    
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    return str(output_path)


# ================ TREND CHART ================

def generate_trend_chart(historical, output_path=None):
    """
    visualize historical trends
    moving averages overlay
    """
    # ---------- APPLY STYLE ----------
    apply_chart_style()
    
    # ---------- GET SKUS ----------
    skus = historical.columns.tolist()
    num_skus = len(skus)
    
    # ---------- CREATE FIGURE ----------
    fig_height = ChartConfig.FIGURE_HEIGHT_PER_SKU * num_skus
    fig, axes = plt.subplots(num_skus, 1, figsize=(ChartConfig.FIGURE_WIDTH, fig_height))
    
    if num_skus == 1:
        axes = [axes]
    
    # ---------- PLOT EACH SKU ----------
    for idx, sku in enumerate(skus):
        ax = axes[idx]
        
        # ---------- RAW DATA ----------
        ax.plot(
            historical.index,
            historical[sku],
            label='Actual',
            color='lightblue',
            linewidth=1,
            alpha=0.7
        )
        
        # ---------- MOVING AVERAGE ----------
        ma_7 = historical[sku].rolling(window=7, min_periods=1).mean()
        ax.plot(
            historical.index,
            ma_7,
            label='7-day MA',
            color='blue',
            linewidth=ChartConfig.LINE_WIDTH
        )
        
        # ---------- STYLING ----------
        ax.set_title(f'Trend Analysis: {sku}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Quantity')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=ChartConfig.GRID_ALPHA)
    
    # ---------- SAVE ----------
    plt.tight_layout()
    
    if output_path is None:
        output_path = Paths.OUTPUT_DIR / "trend_analysis.png"
    
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    return str(output_path)

# ================ FORECAST WITH CONFIDENCE ================

def generate_forecast_with_confidence(historical, forecast, upper_forecast, 
                                      lower_forecast, output_path=None):
    """
    create forecast chart with confidence intervals
    show prediction uncertainty
    """
    # ---------- APPLY STYLE ----------
    apply_chart_style()
    
    # ---------- GET SKUS ----------
    skus = forecast.columns.tolist()
    num_skus = len(skus)
    
    # ---------- CREATE FIGURE ----------
    fig_height = ChartConfig.FIGURE_HEIGHT_PER_SKU * num_skus
    fig, axes = plt.subplots(num_skus, 1, figsize=(ChartConfig.FIGURE_WIDTH, fig_height))
    
    if num_skus == 1:
        axes = [axes]
    
    # ---------- PLOT EACH SKU ----------
    for idx, sku in enumerate(skus):
        ax = axes[idx]
        
        # ---------- HISTORICAL ----------
        if sku in historical.columns:
            ax.plot(
                historical.index,
                historical[sku],
                label='Historical',
                color=ChartConfig.HISTORICAL_COLOR,
                linewidth=ChartConfig.LINE_WIDTH,
                linestyle=ChartConfig.HISTORICAL_STYLE
            )
        
        # ---------- FORECAST ----------
        ax.plot(
            forecast.index,
            forecast[sku],
            label='Forecast',
            color=ChartConfig.FORECAST_COLOR,
            linewidth=ChartConfig.LINE_WIDTH,
            linestyle=ChartConfig.FORECAST_STYLE
        )
        
        # ---------- CONFIDENCE INTERVAL ----------
        if upper_forecast is not None and lower_forecast is not None:
            ax.fill_between(
                forecast.index,
                lower_forecast[sku],
                upper_forecast[sku],
                color=ChartConfig.CONFIDENCE_COLOR,
                alpha=ChartConfig.CONFIDENCE_ALPHA,
                label='95% Confidence'
            )
        
        # ---------- STYLING ----------
        ax.set_title(f'SKU: {sku}')
        ax.set_xlabel('Date')
        ax.set_ylabel('Quantity')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=ChartConfig.GRID_ALPHA)
        
        # ---------- DATE FORMATTING ----------
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    # ---------- SAVE ----------
    plt.tight_layout()
    
    if output_path is None:
        output_path = Paths.FORECAST_CHART
    
    plt.savefig(output_path, dpi=ChartConfig.SAVE_DPI, bbox_inches='tight')
    plt.close()
    
    return str(output_path)