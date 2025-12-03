"""
ydata profiling wrapper
generate data quality reports
"""


# ================ IMPORTS ================

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import threading
import warnings

from config import Paths, ProfilingConfig
from core.state import STATE, PipelineStage
from core.pipeline import PIPELINE
from core.alerts import ALERTS, AlertSeverity


# ================ PROFILING MANAGER ================

class ProfilingManager:
    """
    manage ydata profiling operations
    """
    
    def __init__(self):
        # ---------- STATE ----------
        self._report = None
        self._summary = {}
        self._is_profiling = False
        self._lock = threading.RLock()
    
    # ================ REPORT GENERATION ================
    
    def generate_report(
        self,
        df: pd.DataFrame = None,
        title: str = None,
        minimal: bool = None,
        progress_callback: Callable = None
    ) -> bool:
        """
        generate profiling report
        """
        with self._lock:
            if self._is_profiling:
                print("profiling already in progress")
                return False
            self._is_profiling = True
        
        try:
            # use state data if not provided
            if df is None:
                df = STATE.clean_data if STATE.clean_data is not None else STATE.raw_data
            
            if df is None:
                print("no data available for profiling")
                return False
            
            # start pipeline stage
            PIPELINE.start_stage(PipelineStage.DATA_QUALITY, "Generating profile report...")
            
            if progress_callback:
                progress_callback(10, "Loading profiling library...")
            
            # import ydata profiling
            try:
                from ydata_profiling import ProfileReport
            except ImportError:
                print("ydata-profiling not installed")
                PIPELINE.fail_stage(PipelineStage.DATA_QUALITY, "ydata-profiling not installed")
                return False
            
            if progress_callback:
                progress_callback(20, "Preparing data...")
            
            # sample large datasets
            sample_df = self._prepare_data(df)
            
            if progress_callback:
                progress_callback(30, "Analyzing data structure...")
            
            # configure report
            config = self._get_config(minimal)
            report_title = title or ProfilingConfig.TITLE
            
            if progress_callback:
                progress_callback(40, "Computing statistics...")
            
            # generate report with warnings suppressed
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                
                self._report = ProfileReport(
                    sample_df,
                    title=report_title,
                    **config
                )
            
            if progress_callback:
                progress_callback(70, "Building report...")
            
            # extract summary
            self._extract_summary()
            
            if progress_callback:
                progress_callback(90, "Finalizing...")
            
            # store in state
            STATE.profile_report = self._report
            STATE.profile_summary = self._summary
            STATE.data_quality_score = self._calculate_quality_score()
            
            # generate alerts for issues
            self._generate_quality_alerts()
            
            PIPELINE.complete_stage(PipelineStage.DATA_QUALITY, "Profile report complete")
            
            if progress_callback:
                progress_callback(100, "Complete")
            
            return True
            
        except Exception as e:
            print(f"profiling error: {e}")
            import traceback
            traceback.print_exc()
            PIPELINE.fail_stage(PipelineStage.DATA_QUALITY, str(e))
            return False
            
        finally:
            with self._lock:
                self._is_profiling = False
    
    def generate_report_async(
        self,
        df: pd.DataFrame = None,
        title: str = None,
        minimal: bool = None,
        progress_callback: Callable = None,
        complete_callback: Callable = None
    ):
        """
        generate report in background thread
        """
        def run():
            success = self.generate_report(df, title, minimal, progress_callback)
            if complete_callback:
                complete_callback(success)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
    
    # ================ DATA PREPARATION ================
    
    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        prepare data for profiling
        sample if too large
        """
        # check size
        if len(df) > ProfilingConfig.LARGE_THRESHOLD and ProfilingConfig.SAMPLE_FOR_LARGE:
            print(f"sampling data: {len(df)} -> {ProfilingConfig.SAMPLE_SIZE} rows")
            return df.sample(n=ProfilingConfig.SAMPLE_SIZE, random_state=42)
        
        return df.copy()
    
    def _get_config(self, minimal: bool = None) -> Dict:
        """
        get profiling configuration
        """
        if minimal is None:
            minimal = ProfilingConfig.MINIMAL
        
        config = {
            'minimal': minimal,
            'explorative': ProfilingConfig.EXPLORATIVE and not minimal,
            'correlations': {
                'auto': {'threshold': ProfilingConfig.CORRELATION_THRESHOLD}
            },
            'missing_diagrams': {
                'bar': True,
                'matrix': not minimal,
                'heatmap': not minimal
            },
            'duplicates': {
                'head': 10 if ProfilingConfig.CHECK_DUPLICATES else 0
            },
            'samples': {
                'head': 10,
                'tail': 10,
                'random': 10
            },
            'progress_bar': False
        }
        
        return config
    
    # ================ SUMMARY EXTRACTION ================
    
    def _extract_summary(self):
        """
        extract summary statistics from report
        """
        if self._report is None:
            return
        
        try:
            # get description
            desc = self._report.get_description()
            
            # table stats
            table = desc.get('table', {})
            self._summary['table'] = {
                'rows': table.get('n', 0),
                'columns': table.get('n_var', 0),
                'missing_cells': table.get('n_cells_missing', 0),
                'missing_pct': table.get('p_cells_missing', 0) * 100,
                'duplicate_rows': table.get('n_duplicates', 0),
                'duplicate_pct': table.get('p_duplicates', 0) * 100,
                'memory_size': table.get('memory_size', 0)
            }
            
            # variable stats
            variables = desc.get('variables', {})
            self._summary['variables'] = {}
            self._summary['warnings'] = []
            
            for var_name, var_info in variables.items():
                var_summary = {
                    'type': var_info.get('type', 'unknown'),
                    'missing': var_info.get('n_missing', 0),
                    'missing_pct': var_info.get('p_missing', 0) * 100,
                    'distinct': var_info.get('n_distinct', 0),
                    'unique_pct': var_info.get('p_distinct', 0) * 100
                }
                
                # add numeric stats if applicable
                if 'mean' in var_info:
                    var_summary.update({
                        'mean': var_info.get('mean'),
                        'std': var_info.get('std'),
                        'min': var_info.get('min'),
                        'max': var_info.get('max'),
                        'median': var_info.get('median')
                    })
                
                self._summary['variables'][var_name] = var_summary
                
                # check for warnings
                if var_summary['missing_pct'] > ProfilingConfig.MISSING_THRESHOLD * 100:
                    self._summary['warnings'].append({
                        'type': 'missing',
                        'column': var_name,
                        'value': var_summary['missing_pct'],
                        'message': f"{var_name}: {var_summary['missing_pct']:.1f}% missing values"
                    })
            
            # correlations
            correlations = desc.get('correlations', {})
            self._summary['correlations'] = {}
            
            if 'auto' in correlations and correlations['auto'] is not None:
                corr_matrix = correlations['auto']
                high_corrs = []
                
                if hasattr(corr_matrix, 'items'):
                    for col1, row in corr_matrix.items():
                        if hasattr(row, 'items'):
                            for col2, val in row.items():
                                if col1 != col2 and abs(val) > ProfilingConfig.CORRELATION_THRESHOLD:
                                    if (col2, col1) not in [(c[0], c[1]) for c in high_corrs]:
                                        high_corrs.append((col1, col2, val))
                
                self._summary['correlations']['high'] = high_corrs
                
                for col1, col2, val in high_corrs:
                    self._summary['warnings'].append({
                        'type': 'correlation',
                        'columns': [col1, col2],
                        'value': val,
                        'message': f"High correlation ({val:.2f}) between {col1} and {col2}"
                    })
            
        except Exception as e:
            print(f"summary extraction error: {e}")
            self._summary = {'error': str(e)}
    
    def _calculate_quality_score(self) -> float:
        """
        calculate overall data quality score 0-100
        """
        if not self._summary or 'table' not in self._summary:
            return 0.0
        
        score = 100.0
        
        # penalize missing values
        missing_pct = self._summary['table'].get('missing_pct', 0)
        score -= min(missing_pct * 2, 30)
        
        # penalize duplicates
        dup_pct = self._summary['table'].get('duplicate_pct', 0)
        score -= min(dup_pct * 1.5, 20)
        
        # penalize warnings
        warning_count = len(self._summary.get('warnings', []))
        score -= min(warning_count * 2, 20)
        
        return max(score, 0.0)
    
    def _generate_quality_alerts(self):
        """
        generate alerts for data quality issues
        """
        if not self._summary or 'warnings' not in self._summary:
            return
        
        for warning in self._summary['warnings']:
            if warning['type'] == 'missing':
                ALERTS.create_data_quality_alert(
                    issue=f"Missing values in {warning['column']}",
                    affected_rows=int(warning['value'] * STATE.clean_data.shape[0] / 100)
                    if STATE.clean_data is not None else 0
                )
            elif warning['type'] == 'correlation':
                ALERTS.create_alert(
                    alert_type='data_quality',
                    message=warning['message'],
                    severity=AlertSeverity.LOW,
                    source_tab='data_quality'
                )
    
    # ================ REPORT ACCESS ================
    
    def get_report(self):
        """
        get generated report object
        """
        return self._report
    
    def get_summary(self) -> Dict:
        """
        get summary statistics
        """
        return self._summary.copy()
    
    def get_html(self) -> str:
        """
        get report as html string
        """
        if self._report is None:
            return ""
        
        try:
            return self._report.to_html()
        except Exception as e:
            print(f"html generation error: {e}")
            return ""
    
    def get_json(self) -> str:
        """
        get report as json string
        """
        if self._report is None:
            return "{}"
        
        try:
            return self._report.to_json()
        except Exception as e:
            print(f"json generation error: {e}")
            return "{}"
    
    def get_widgets(self):
        """
        get report as widgets for embedding
        """
        if self._report is None:
            return None
        
        try:
            return self._report.to_widgets()
        except Exception as e:
            print(f"widgets generation error: {e}")
            return None
    
    # ================ EXPORT ================
    
    def export_html(self, output_path: Path = None) -> Optional[Path]:
        """
        export report to html file
        """
        if self._report is None:
            return None
        
        if output_path is None:
            from datetime import datetime
            from config import ExportConfig
            
            timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
            output_path = Paths.PROFILES_DIR / f"profile_{timestamp}.html"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self._report.to_file(output_path)
            print(f"exported profile report: {output_path}")
            return output_path
        except Exception as e:
            print(f"export error: {e}")
            return None
    
    def export_json(self, output_path: Path = None) -> Optional[Path]:
        """
        export report to json file
        """
        if self._report is None:
            return None
        
        if output_path is None:
            from datetime import datetime
            from config import ExportConfig
            
            timestamp = datetime.now().strftime(ExportConfig.TIMESTAMP_FORMAT)
            output_path = Paths.PROFILES_DIR / f"profile_{timestamp}.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            json_str = self._report.to_json()
            with open(output_path, 'w') as f:
                f.write(json_str)
            print(f"exported profile json: {output_path}")
            return output_path
        except Exception as e:
            print(f"export error: {e}")
            return None
    
    # ================ QUICK STATS ================
    
    def get_quick_stats(self, df: pd.DataFrame = None) -> Dict:
        """
        get quick statistics without full report
        """
        if df is None:
            df = STATE.clean_data if STATE.clean_data is not None else STATE.raw_data
        
        if df is None:
            return {}
        
        stats = {
            'rows': len(df),
            'columns': len(df.columns),
            'memory_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
            'missing_total': df.isna().sum().sum(),
            'missing_pct': (df.isna().sum().sum() / df.size) * 100,
            'duplicates': df.duplicated().sum(),
            'column_types': df.dtypes.value_counts().to_dict()
        }
        
        # convert dtypes to strings for serialization
        stats['column_types'] = {str(k): v for k, v in stats['column_types'].items()}
        
        return stats
    
    def is_profiling(self) -> bool:
        """
        check if profiling is in progress
        """
        return self._is_profiling


# ================ SINGLETON INSTANCE ================

PROFILER = ProfilingManager()