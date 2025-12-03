"""
unified export utilities
csv, excel, json, parquet, api
"""


# ================ IMPORTS ================

import pandas as pd
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from config import Paths, ExportConfig, DisplayConfig
from core.state import STATE


# ================ EXPORT FORMATS ================

class ExportFormat:
    """
    export format constants
    """
    CSV = 'csv'
    EXCEL = 'xlsx'
    JSON = 'json'
    PARQUET = 'parquet'


# ================ FILE EXPORT ================

def export_dataframe(
    df: pd.DataFrame,
    filename: str,
    export_format: str = ExportFormat.CSV,
    output_dir: Path = None,
    include_timestamp: bool = True,
    **kwargs
) -> Path:
    """
    export dataframe to file
    """
    if output_dir is None:
        output_dir = Paths.USER_OUTPUT
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # add timestamp if requested
    if include_timestamp:
        timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
        base_name = f"{filename}_{timestamp}"
    else:
        base_name = filename
    
    # determine file path
    file_path = output_dir / f"{base_name}.{export_format}"
    
    # export based on format
    if export_format == ExportFormat.CSV:
        df.to_csv(
            file_path,
            index=kwargs.get('index', ExportConfig.CSV_INDEX),
            encoding=kwargs.get('encoding', ExportConfig.CSV_ENCODING)
        )
    
    elif export_format == ExportFormat.EXCEL:
        df.to_excel(
            file_path,
            index=kwargs.get('index', ExportConfig.CSV_INDEX),
            engine=ExportConfig.EXCEL_ENGINE
        )
    
    elif export_format == ExportFormat.JSON:
        df.to_json(
            file_path,
            orient=kwargs.get('orient', 'records'),
            date_format=kwargs.get('date_format', 'iso'),
            indent=kwargs.get('indent', 2)
        )
    
    elif export_format == ExportFormat.PARQUET:
        df.to_parquet(file_path, index=kwargs.get('index', False))
    
    else:
        raise ValueError(f"unsupported format: {export_format}")
    
    print(f"exported: {file_path}")
    return file_path


def export_forecast(
    forecast_df: pd.DataFrame,
    upper_df: pd.DataFrame = None,
    lower_df: pd.DataFrame = None,
    export_format: str = ExportFormat.CSV,
    output_dir: Path = None,
    include_confidence: bool = True
) -> Dict[str, Path]:
    """
    export forecast results
    """
    if output_dir is None:
        output_dir = Paths.FORECASTS_DIR
    
    paths = {}
    
    # export main forecast
    paths['forecast'] = export_dataframe(
        forecast_df,
        'forecast',
        export_format,
        output_dir
    )
    
    # export confidence intervals
    if include_confidence:
        if upper_df is not None:
            paths['upper'] = export_dataframe(
                upper_df,
                'forecast_upper',
                export_format,
                output_dir
            )
        
        if lower_df is not None:
            paths['lower'] = export_dataframe(
                lower_df,
                'forecast_lower',
                export_format,
                output_dir
            )
    
    return paths


def export_profile_report(
    report_html: str,
    filename: str = 'profile_report',
    output_dir: Path = None
) -> Path:
    """
    export profiling report as html
    """
    if output_dir is None:
        output_dir = Paths.PROFILES_DIR
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
    file_path = output_dir / f"{filename}_{timestamp}.html"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(report_html)
    
    print(f"exported profile report: {file_path}")
    return file_path


def export_features(
    feature_df: pd.DataFrame,
    importance_dict: Dict = None,
    export_format: str = ExportFormat.CSV,
    output_dir: Path = None
) -> Dict[str, Path]:
    """
    export feature data and importance
    """
    if output_dir is None:
        output_dir = Paths.FEATURES_DIR
    
    paths = {}
    
    # export feature data
    paths['features'] = export_dataframe(
        feature_df,
        'features',
        export_format,
        output_dir
    )
    
    # export importance
    if importance_dict:
        importance_df = pd.DataFrame([
            {'feature': k, 'importance': v}
            for k, v in importance_dict.items()
        ]).sort_values('importance', ascending=False)
        
        paths['importance'] = export_dataframe(
            importance_df,
            'feature_importance',
            export_format,
            output_dir
        )
    
    return paths


def export_model_metrics(
    metrics: Dict[str, Dict],
    export_format: str = ExportFormat.CSV,
    output_dir: Path = None
) -> Path:
    """
    export model evaluation metrics
    """
    if output_dir is None:
        output_dir = Paths.FORECASTS_DIR
    
    # convert to dataframe
    rows = []
    for model_name, model_metrics in metrics.items():
        row = {'model': model_name}
        row.update(model_metrics)
        rows.append(row)
    
    metrics_df = pd.DataFrame(rows)
    
    return export_dataframe(
        metrics_df,
        'model_metrics',
        export_format,
        output_dir
    )


# ================ SUMMARY EXPORT ================

def export_summary_report(
    output_dir: Path = None
) -> Path:
    """
    export comprehensive summary report
    """
    if output_dir is None:
        output_dir = Paths.USER_OUTPUT
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
    file_path = output_dir / f"summary_{timestamp}.txt"
    
    lines = []
    lines.append("=" * 60)
    lines.append("STOCKSIGHT FORECAST SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().strftime(DisplayConfig.DATETIME_FORMAT)}")
    lines.append("")
    
    # data summary
    if STATE.clean_data is not None:
        lines.append("DATA SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Records: {len(STATE.clean_data):,}")
        lines.append(f"Unique SKUs: {len(STATE.sku_list):,}")
        
        if 'Date' in STATE.clean_data.columns:
            min_date = STATE.clean_data['Date'].min()
            max_date = STATE.clean_data['Date'].max()
            lines.append(f"Date Range: {min_date} to {max_date}")
        
        lines.append("")
    
    # forecast summary
    if STATE.forecast_data is not None:
        lines.append("FORECAST SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Forecast Periods: {len(STATE.forecast_data)}")
        lines.append(f"Granularity: {STATE.forecast_granularity}")
        lines.append(f"Total Forecast: {STATE.forecast_data.sum().sum():,.2f}")
        lines.append("")
    
    # model metrics
    if STATE.model_metrics:
        lines.append("MODEL METRICS")
        lines.append("-" * 40)
        for model_name, metrics in STATE.model_metrics.items():
            lines.append(f"{model_name}:")
            for metric_name, value in metrics.items():
                lines.append(f"  {metric_name}: {value:.4f}")
        lines.append("")
    
    # alerts summary
    alert_count = STATE.get_alert_count()
    if alert_count > 0:
        lines.append("ACTIVE ALERTS")
        lines.append("-" * 40)
        lines.append(f"Total Alerts: {alert_count}")
        
        for alert in STATE.get_alerts()[:5]:
            lines.append(f"  [{alert.severity.value.upper()}] {alert.message}")
        
        if alert_count > 5:
            lines.append(f"  ... and {alert_count - 5} more")
        lines.append("")
    
    lines.append("=" * 60)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"exported summary: {file_path}")
    return file_path


# ================ BATCH EXPORT ================

def export_all(
    export_format: str = ExportFormat.CSV,
    output_dir: Path = None,
    include_data: bool = True,
    include_forecast: bool = True,
    include_features: bool = True,
    include_summary: bool = True
) -> Dict[str, Path]:
    """
    export all available data
    """
    if output_dir is None:
        output_dir = Paths.USER_OUTPUT
    
    timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
    batch_dir = Path(output_dir) / f"export_{timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    paths = {}
    
    # export cleaned data
    if include_data and STATE.clean_data is not None:
        paths['data'] = export_dataframe(
            STATE.clean_data,
            'cleaned_data',
            export_format,
            batch_dir,
            include_timestamp=False
        )
    
    # export forecast
    if include_forecast and STATE.forecast_data is not None:
        forecast_paths = export_forecast(
            STATE.forecast_data,
            STATE.upper_forecast,
            STATE.lower_forecast,
            export_format,
            batch_dir
        )
        paths.update(forecast_paths)
    
    # export features
    if include_features and STATE.feature_data is not None:
        feature_paths = export_features(
            STATE.feature_data,
            STATE.feature_importance,
            export_format,
            batch_dir
        )
        paths.update(feature_paths)
    
    # export summary
    if include_summary:
        paths['summary'] = export_summary_report(batch_dir)
    
    # export metrics
    if STATE.model_metrics:
        paths['metrics'] = export_model_metrics(
            STATE.model_metrics,
            export_format,
            batch_dir
        )
    
    print(f"batch export complete: {batch_dir}")
    return paths


# ================ API EXPORT ================

def format_for_api(
    df: pd.DataFrame,
    date_format: str = 'iso'
) -> List[Dict]:
    """
    format dataframe for api response
    """
    # convert dates
    df_copy = df.copy()
    
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            if date_format == 'iso':
                df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                df_copy[col] = df_copy[col].dt.strftime(date_format)
    
    return df_copy.to_dict(orient='records')


def export_to_json_string(
    df: pd.DataFrame,
    orient: str = 'records',
    indent: int = 2
) -> str:
    """
    export dataframe to json string
    """
    return df.to_json(orient=orient, date_format='iso', indent=indent)


# ================ UTILITIES ================

def get_export_path(
    filename: str,
    export_format: str,
    output_dir: Path = None,
    include_timestamp: bool = True
) -> Path:
    """
    generate export file path
    """
    if output_dir is None:
        output_dir = Paths.USER_OUTPUT
    
    output_dir = Path(output_dir)
    
    if include_timestamp:
        timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
        return output_dir / f"{filename}_{timestamp}.{export_format}"
    
    return output_dir / f"{filename}.{export_format}"


def get_available_formats() -> List[str]:
    """
    get list of available export formats
    """
    return ExportConfig.AVAILABLE_FORMATS


def validate_export_format(export_format: str) -> bool:
    """
    validate export format
    """
    return export_format.lower() in ExportConfig.AVAILABLE_FORMATS