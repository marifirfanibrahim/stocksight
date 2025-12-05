"""
file handlers module
manages file input output operations
integrates with pyqt file dialogs
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import json
import pickle

import config


# ============================================================================
#                             FILE HANDLER
# ============================================================================

class FileHandler:
    # handles file operations for stocksight
    
    def __init__(self):
        # initialize file handler
        self.last_directory = str(Path.home())
        self.supported_types = config.SUPPORTED_FILE_TYPES
    
    # ---------- FILE DIALOGS ----------
    
    def get_open_filter(self) -> str:
        # get file filter string for open dialog
        filters = []
        all_extensions = []
        
        for ext, desc in self.supported_types.items():
            filters.append(desc)
            if ext == "csv":
                all_extensions.append("*.csv")
            elif ext == "excel":
                all_extensions.extend(["*.xlsx", "*.xls"])
            elif ext == "parquet":
                all_extensions.append("*.parquet")
        
        # add all files option
        all_files = "All Supported Files ({})".format(" ".join(all_extensions))
        filters.insert(0, all_files)
        filters.append("All Files (*)")
        
        return ";;".join(filters)
    
    def get_save_filter(self, format_type: str) -> str:
        # get file filter for save dialog
        export_formats = config.EXPORT_FORMATS
        
        if format_type in export_formats:
            fmt = export_formats[format_type]
            return f"{fmt['name']} (*{fmt['extension']})"
        
        return "All Files (*)"
    
    # ---------- FILE READING ----------
    
    def read_file(self, file_path: str) -> Tuple[Optional[pd.DataFrame], str]:
        # read data file and return dataframe
        path = Path(file_path)
        
        if not path.exists():
            return None, "file not found"
        
        self.last_directory = str(path.parent)
        
        try:
            suffix = path.suffix.lower()
            
            if suffix == ".csv":
                df = self._read_csv(path)
            elif suffix in [".xlsx", ".xls"]:
                df = self._read_excel(path)
            elif suffix == ".parquet":
                df = self._read_parquet(path)
            else:
                return None, f"unsupported file type: {suffix}"
            
            return df, f"loaded {len(df):,} rows"
            
        except Exception as e:
            return None, f"error reading file: {str(e)}"
    
    def _read_csv(self, path: Path) -> pd.DataFrame:
        # read csv file with encoding detection
        encodings = ["utf-8", "latin-1", "cp1252"]
        
        for encoding in encodings:
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        
        # fallback with error handling
        return pd.read_csv(path, encoding="utf-8", errors="replace")
    
    def _read_excel(self, path: Path, sheet_name: Optional[str] = None) -> pd.DataFrame:
        # read excel file with optional sheet selection
        if sheet_name:
            return pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
        return pd.read_excel(path, engine="openpyxl")
    
    def _read_parquet(self, path: Path) -> pd.DataFrame:
        # read parquet file
        return pd.read_parquet(path)
    
    # ---------- EXCEL SHEET HANDLING ----------
    
    def get_excel_sheets(self, file_path: str) -> List[str]:
        # get list of sheet names from excel file
        path = Path(file_path)
        
        if not path.exists():
            return []
        
        if path.suffix.lower() not in [".xlsx", ".xls"]:
            return []
        
        try:
            xlsx = pd.ExcelFile(path, engine="openpyxl")
            return xlsx.sheet_names
        except Exception:
            return []
    
    def get_excel_sheet_info(self, file_path: str) -> Dict[str, int]:
        # get sheet names with row counts
        path = Path(file_path)
        
        if not path.exists():
            return {}
        
        if path.suffix.lower() not in [".xlsx", ".xls"]:
            return {}
        
        try:
            xlsx = pd.ExcelFile(path, engine="openpyxl")
            sheet_info = {}
            
            for sheet_name in xlsx.sheet_names:
                try:
                    # count rows efficiently using first column only
                    df = pd.read_excel(xlsx, sheet_name=sheet_name, usecols=[0])
                    sheet_info[sheet_name] = len(df)
                except Exception:
                    sheet_info[sheet_name] = 0
            
            return sheet_info
        except Exception:
            return {}
    
    def has_multiple_sheets(self, file_path: str) -> bool:
        # check if excel file has multiple worksheets
        sheets = self.get_excel_sheets(file_path)
        return len(sheets) > 1
    
    def read_excel_sheet(self, file_path: str, sheet_name: str) -> Tuple[Optional[pd.DataFrame], str]:
        # read specific sheet from excel file
        path = Path(file_path)
        
        if not path.exists():
            return None, "file not found"
        
        try:
            df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
            return df, f"loaded {len(df):,} rows from '{sheet_name}'"
        except Exception as e:
            return None, f"error reading sheet: {str(e)}"
    
    # ---------- FILE WRITING ----------
    
    def write_csv(self, df: pd.DataFrame, file_path: str) -> Tuple[bool, str]:
        # write dataframe to csv
        try:
            df.to_csv(file_path, index=False)
            return True, f"saved {len(df):,} rows to csv"
        except Exception as e:
            return False, f"error saving csv: {str(e)}"
    
    def write_excel(self, df: pd.DataFrame, file_path: str, sheet_name: str = "Data") -> Tuple[bool, str]:
        # write dataframe to excel
        try:
            with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            return True, f"saved {len(df):,} rows to excel"
        except Exception as e:
            return False, f"error saving excel: {str(e)}"
    
    def write_parquet(self, df: pd.DataFrame, file_path: str) -> Tuple[bool, str]:
        # write dataframe to parquet
        try:
            df.to_parquet(file_path, index=False)
            return True, f"saved {len(df):,} rows to parquet"
        except Exception as e:
            return False, f"error saving parquet: {str(e)}"
    
    # ---------- SESSION FILES ----------
    
    def save_session(self, session_data: dict, file_path: str) -> Tuple[bool, str]:
        # save session state to file
        try:
            with open(file_path, "wb") as f:
                pickle.dump(session_data, f)
            return True, "session saved"
        except Exception as e:
            return False, f"error saving session: {str(e)}"
    
    def load_session(self, file_path: str) -> Tuple[Optional[dict], str]:
        # load session state from file
        try:
            with open(file_path, "rb") as f:
                session_data = pickle.load(f)
            return session_data, "session loaded"
        except Exception as e:
            return None, f"error loading session: {str(e)}"
    
    # ---------- CONFIG FILES ----------
    
    def save_config(self, config_data: dict, file_path: str) -> Tuple[bool, str]:
        # save configuration to json
        try:
            with open(file_path, "w") as f:
                json.dump(config_data, f, indent=2)
            return True, "config saved"
        except Exception as e:
            return False, f"error saving config: {str(e)}"
    
    def load_config(self, file_path: str) -> Tuple[Optional[dict], str]:
        # load configuration from json
        try:
            with open(file_path, "r") as f:
                config_data = json.load(f)
            return config_data, "config loaded"
        except Exception as e:
            return None, f"error loading config: {str(e)}"
    
    # ---------- VALIDATION ----------
    
    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        # validate file before processing
        path = Path(file_path)
        
        if not path.exists():
            return False, "file not found"
        
        # check file size
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > config.MAX_FILE_SIZE_MB:
            return False, f"file too large: {size_mb:.0f}mb"
        
        # check extension
        suffix = path.suffix.lower()
        valid_extensions = [".csv", ".xlsx", ".xls", ".parquet"]
        if suffix not in valid_extensions:
            return False, f"unsupported file type: {suffix}"
        
        return True, "file valid"
    
    def get_file_info(self, file_path: str) -> dict:
        # get file metadata
        path = Path(file_path)
        
        if not path.exists():
            return {}
        
        info = {
            "name": path.name,
            "extension": path.suffix,
            "size_mb": path.stat().st_size / (1024 * 1024),
            "directory": str(path.parent),
            "modified": path.stat().st_mtime
        }
        
        # add sheet info for excel files
        if path.suffix.lower() in [".xlsx", ".xls"]:
            sheets = self.get_excel_sheets(file_path)
            info["sheets"] = sheets
            info["sheet_count"] = len(sheets)
        
        return info