"""
export wizard widget
multi-step wizard for exporting data
supports multiple export formats
"""

from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QRadioButton, QButtonGroup, QCheckBox,
    QLineEdit, QPushButton, QFileDialog, QGroupBox,
    QComboBox, QListWidget, QListWidgetItem, QTextEdit
    , QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Dict, List, Optional, Any
from pathlib import Path

import config


# ============================================================================
#                           EXPORT WIZARD
# ============================================================================

class ExportWizard(QWizard):
    # multi-step export wizard
    
    # signals
    export_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        # initialize wizard
        super().__init__(parent)
        
        self.setWindowTitle("Export Wizard")
        self.setMinimumSize(600, 450)
        self.setWizardStyle(QWizard.ModernStyle)
        
        # add pages
        self.addPage(FormatPage())
        self.addPage(ContentPage())
        self.addPage(OptionsPage())
        self.addPage(SummaryPage())
        
        # connect finish signal
        self.finished.connect(self._on_finished)
    
    def _on_finished(self, result: int) -> None:
        # handle wizard completion
        if result == QWizard.Accepted:
            export_config = self.get_export_config()
            self.export_requested.emit(export_config)
    
    def get_export_config(self) -> Dict[str, Any]:
        # get export configuration from all pages
        config = {}
        
        for i in range(self.pageIds().__len__()):
            page = self.page(i)
            if hasattr(page, "get_config"):
                config.update(page.get_config())
        
        return config
    
    def set_available_data(self, data_types: List[str]) -> None:
        # set available data for export
        content_page = self.page(1)
        if isinstance(content_page, ContentPage):
            content_page.set_available_data(data_types)


# ============================================================================
#                            FORMAT PAGE
# ============================================================================

class FormatPage(QWizardPage):
    # page for selecting export format
    
    def __init__(self):
        # initialize page
        super().__init__()
        
        self.setTitle("Select Export Format")
        self.setSubTitle("Choose the format for your export file")
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        
        # format options
        self._format_group = QButtonGroup(self)
        
        formats = [
            ("csv", "CSV File", "For ERP systems and data analysis", "csv"),
            ("excel", "Excel Workbook", "For spreadsheet analysis with formatting", "xlsx"),
            ("ppt", "PowerPoint Presentation", "3-slide summary for management", "pptx"),
            ("pdf", "PDF Report", "Executive summary document", "pdf")
        ]
        
        for i, (key, name, desc, ext) in enumerate(formats):
            group = QGroupBox()
            group_layout = QHBoxLayout(group)
            
            radio = QRadioButton(name)
            radio.setProperty("format_key", key)
            self._format_group.addButton(radio, i)
            group_layout.addWidget(radio)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: gray;")
            group_layout.addWidget(desc_label)
            
            group_layout.addStretch()
            
            ext_label = QLabel(f".{ext}")
            ext_label.setStyleSheet("font-weight: bold;")
            group_layout.addWidget(ext_label)
            
            layout.addWidget(group)
            
            if i == 0:
                radio.setChecked(True)
        
        layout.addStretch()
        
        # register field
        self.registerField("format*", self._format_group.buttons()[0])
    
    def get_config(self) -> Dict[str, Any]:
        # get page configuration
        selected = self._format_group.checkedButton()
        format_key = selected.property("format_key") if selected else "csv"
        return {"format": format_key}


# ============================================================================
#                           CONTENT PAGE
# ============================================================================

class ContentPage(QWizardPage):
    # page for selecting export content
    
    def __init__(self):
        # initialize page
        super().__init__()
        
        self.setTitle("Select Content")
        self.setSubTitle("Choose what data to include in the export")
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        
        # content options
        content_group = QGroupBox("Include in Export")
        content_layout = QVBoxLayout(content_group)
        
        self._content_checks = {}
        
        content_options = [
            ("forecasts", "Forecast Results", True),
            ("summary", "Summary Statistics", True),
            ("metrics", "Model Performance Metrics", True),
            ("clusters", "Cluster Assignments", False),
            ("anomalies", "Detected Anomalies", False),
            ("raw_data", "Raw Data Sample", False)
        ]
        
        for key, label, default in content_options:
            check = QCheckBox(label)
            check.setChecked(default)
            self._content_checks[key] = check
            content_layout.addWidget(check)
        
        layout.addWidget(content_group)
        
        # item selection
        items_group = QGroupBox("Item Selection")
        items_layout = QVBoxLayout(items_group)
        
        self._items_combo = QComboBox()
        self._items_combo.addItems([
            "All Items",
            "A-Items Only (High Volume)",
            "Top 100 Items",
            "Bookmarked Items",
            "Custom Selection"
        ])
        items_layout.addWidget(self._items_combo)
        
        layout.addWidget(items_group)
        
        layout.addStretch()
    
    def set_available_data(self, data_types: List[str]) -> None:
        # enable only available content types
        for key, check in self._content_checks.items():
            check.setEnabled(key in data_types)
            if key not in data_types:
                check.setChecked(False)
    
    def get_config(self) -> Dict[str, Any]:
        # get page configuration
        content = [key for key, check in self._content_checks.items() if check.isChecked()]
        item_selection = self._items_combo.currentText()
        
        return {
            "content": content,
            "item_selection": item_selection
        }


# ============================================================================
#                           OPTIONS PAGE
# ============================================================================

class OptionsPage(QWizardPage):
    # page for export options
    
    def __init__(self):
        # initialize page
        super().__init__()
        
        self.setTitle("Export Options")
        self.setSubTitle("Configure additional export options")
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        
        # file location
        location_group = QGroupBox("Save Location")
        location_layout = QHBoxLayout(location_group)
        
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select save location...")
        location_layout.addWidget(self._path_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_location)
        location_layout.addWidget(browse_btn)
        
        layout.addWidget(location_group)
        
        # format options
        options_group = QGroupBox("Format Options")
        options_layout = QVBoxLayout(options_group)
        
        self._include_headers = QCheckBox("Include column headers")
        self._include_headers.setChecked(True)
        options_layout.addWidget(self._include_headers)
        
        self._include_bounds = QCheckBox("Include confidence intervals")
        self._include_bounds.setChecked(True)
        options_layout.addWidget(self._include_bounds)
        
        self._format_numbers = QCheckBox("Format numbers with thousand separators")
        self._format_numbers.setChecked(True)
        options_layout.addWidget(self._format_numbers)
        
        layout.addWidget(options_group)
        
        # date format
        date_group = QGroupBox("Date Format")
        date_layout = QHBoxLayout(date_group)
        
        date_layout.addWidget(QLabel("Format:"))
        
        self._date_format = QComboBox()
        self._date_format.addItems([
            "YYYY-MM-DD",
            "MM/DD/YYYY",
            "DD/MM/YYYY",
            "YYYY/MM/DD"
        ])
        date_layout.addWidget(self._date_format)
        
        date_layout.addStretch()
        
        layout.addWidget(date_group)
        
        layout.addStretch()
        
        # set default path
        self._set_default_path()
    
    def _browse_location(self) -> None:
        # browse for save location
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Export",
            self._path_edit.text(),
            "All Files (*)"
        )
        if path:
            self._path_edit.setText(path)
    
    def _set_default_path(self) -> None:
        # set default save path
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = Path.home() / f"stocksight_export_{timestamp}.csv"
        self._path_edit.setText(str(default_path))
    
    def get_config(self) -> Dict[str, Any]:
        # get page configuration
        return {
            "file_path": self._path_edit.text(),
            "include_headers": self._include_headers.isChecked(),
            "include_bounds": self._include_bounds.isChecked(),
            "format_numbers": self._format_numbers.isChecked(),
            "date_format": self._date_format.currentText()
        }
    
    def validatePage(self) -> bool:
        # validate page before proceeding
        if not self._path_edit.text():
            return False
        return True


# ============================================================================
#                           SUMMARY PAGE
# ============================================================================

class SummaryPage(QWizardPage):
    # page showing export summary
    
    def __init__(self):
        # initialize page
        super().__init__()
        
        self.setTitle("Export Summary")
        self.setSubTitle("Review your export settings")
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        layout = QVBoxLayout(self)
        
        # summary text
        self._summary_text = QTextEdit()
        self._summary_text.setReadOnly(True)
        try:
            app = QApplication.instance()
            base_font = app.font() if app is not None else QFont()
            # use a monospace-like size; keep Consolas as fallback
            summ_font = QFont(base_font.family(), max(9, base_font.pointSize()))
            self._summary_text.setFont(summ_font)
        except Exception:
            self._summary_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self._summary_text)
        
        # note
        note_label = QLabel("Click Finish to create the export file.")
        note_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note_label)
    
    def initializePage(self) -> None:
        # initialize page when shown
        self._update_summary()
    
    def _update_summary(self) -> None:
        # update summary text
        wizard = self.wizard()
        if not isinstance(wizard, ExportWizard):
            return
        
        config = wizard.get_export_config()
        
        lines = [
            "=== Export Configuration ===",
            "",
            f"Format: {config.get('format', 'csv').upper()}",
            f"File: {config.get('file_path', 'Not specified')}",
            "",
            "Content:",
        ]
        
        for content in config.get("content", []):
            lines.append(f"  • {content.replace('_', ' ').title()}")
        
        lines.extend([
            "",
            f"Item Selection: {config.get('item_selection', 'All Items')}",
            "",
            "Options:",
            f"  • Headers: {'Yes' if config.get('include_headers', True) else 'No'}",
            f"  • Confidence Intervals: {'Yes' if config.get('include_bounds', True) else 'No'}",
            f"  • Number Formatting: {'Yes' if config.get('format_numbers', True) else 'No'}",
            f"  • Date Format: {config.get('date_format', 'YYYY-MM-DD')}"
        ])
        
        self._summary_text.setText("\n".join(lines))
    
    def get_config(self) -> Dict[str, Any]:
        # no additional config from this page
        return {}