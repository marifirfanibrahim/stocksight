"""
column mapping dialog
allows user to confirm or adjust column detection
uses plain language for column types
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QGroupBox, QFormLayout,
    QFrame, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from typing import Dict, List, Optional

import config


# ============================================================================
#                       COLUMN MAPPING DIALOG
# ============================================================================

class ColumnMappingDialog(QDialog):
    # dialog for mapping data columns
    
    # signals
    mapping_confirmed = pyqtSignal(dict)
    
    def __init__(self, columns: List[str], detections: Dict, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._columns = columns
        self._detections = detections
        self._combos = {}
        
        self._setup_ui()
        self._populate_detections()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Map Your Columns")
        self.setMinimumWidth(550)
        self.setMinimumHeight(450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header
        header = QLabel("Tell us which columns contain your data")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(header)
        
        desc = QLabel("We've detected your columns automatically. Please confirm or adjust the mappings below.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray;")
        layout.addWidget(desc)
        
        # separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #ddd;")
        layout.addWidget(line)
        
        # scroll area for mappings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        
        # required columns
        required_group = QGroupBox("Required Columns")
        required_layout = QFormLayout(required_group)
        required_layout.setSpacing(10)
        
        required_mappings = [
            ("date", "Date Column", "Which column contains dates?"),
            ("sku", "Item/SKU Column", "Which column identifies your items?"),
            ("quantity", "Sales/Quantity Column", "Which column has the numbers to forecast?")
        ]
        
        for key, label, hint in required_mappings:
            row = self._create_mapping_row(key, label, hint, required=True)
            required_layout.addRow(row)
        
        scroll_layout.addWidget(required_group)
        
        # optional columns
        optional_group = QGroupBox("Optional Columns (Influence Factors)")
        optional_layout = QFormLayout(optional_group)
        optional_layout.setSpacing(10)
        
        optional_mappings = [
            ("category", "Category Column", "How are your items grouped?"),
            ("price", "Price Column", "Price can affect demand"),
            ("promo", "Promotion Column", "Promotions impact sales")
        ]
        
        for key, label, hint in optional_mappings:
            row = self._create_mapping_row(key, label, hint, required=False)
            optional_layout.addRow(row)
        
        scroll_layout.addWidget(optional_group)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # validation message
        self._validation_label = QLabel("")
        self._validation_label.setStyleSheet("color: red;")
        layout.addWidget(self._validation_label)
        
        # buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton("Confirm Mapping")
        confirm_btn.setDefault(True)
        confirm_btn.clicked.connect(self._on_confirm)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
    
    def _create_mapping_row(self, key: str, label: str, hint: str, required: bool) -> QWidget:
        # create single mapping row
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        
        # label with required indicator
        label_text = f"{label} *" if required else label
        label_widget = QLabel(label_text)
        label_widget.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(label_widget)
        
        # hint
        hint_label = QLabel(hint)
        hint_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(hint_label)
        
        # combo and confidence
        combo_layout = QHBoxLayout()
        
        combo = QComboBox()
        combo.addItem("-- Not Mapped --", None)
        for col in self._columns:
            combo.addItem(col, col)
        combo.setMinimumWidth(200)
        combo_layout.addWidget(combo)
        
        confidence_label = QLabel("")
        confidence_label.setMinimumWidth(100)
        combo_layout.addWidget(confidence_label)
        
        combo_layout.addStretch()
        
        layout.addLayout(combo_layout)
        
        # store references
        self._combos[key] = {
            "combo": combo,
            "confidence": confidence_label,
            "required": required
        }
        
        return widget
    
    def _populate_detections(self) -> None:
        # populate combos with detected mappings
        # find best column for each type
        best_mapping = {}
        used_columns = set()
        
        # priority order
        priority = ["date", "sku", "quantity", "category", "price", "promo"]
        
        for col_type in priority:
            if col_type not in self._combos:
                continue
            
            best_col = None
            best_score = 0
            
            for col, info in self._detections.items():
                if col in used_columns:
                    continue
                
                score = info.get("all_scores", {}).get(col_type, 0)
                if score > best_score and score >= 0.5:
                    best_col = col
                    best_score = score
            
            if best_col:
                best_mapping[col_type] = (best_col, best_score)
                used_columns.add(best_col)
        
        # apply mappings to combos
        for col_type, combo_info in self._combos.items():
            combo = combo_info["combo"]
            confidence_label = combo_info["confidence"]
            
            if col_type in best_mapping:
                col, score = best_mapping[col_type]
                
                # select column in combo
                index = combo.findData(col)
                if index >= 0:
                    combo.setCurrentIndex(index)
                
                # show confidence
                confidence_pct = int(score * 100)
                if confidence_pct >= 80:
                    color = config.UI_COLORS["success"]
                    text = f"✓ {confidence_pct}% confident"
                elif confidence_pct >= 60:
                    color = config.UI_COLORS["warning"]
                    text = f"? {confidence_pct}% confident"
                else:
                    color = config.UI_COLORS["danger"]
                    text = f"! {confidence_pct}% confident"
                
                confidence_label.setText(text)
                confidence_label.setStyleSheet(f"color: {color};")
    
    # ---------- VALIDATION ----------
    
    def _validate(self) -> tuple:
        # validate mapping
        errors = []
        mapping = {}
        used = set()
        
        for col_type, combo_info in self._combos.items():
            combo = combo_info["combo"]
            required = combo_info["required"]
            
            selected = combo.currentData()
            
            if required and selected is None:
                errors.append(f"{col_type.title()} column is required")
            elif selected is not None:
                if selected in used:
                    errors.append(f"Column '{selected}' is used multiple times")
                else:
                    used.add(selected)
                    mapping[col_type] = selected
        
        return len(errors) == 0, errors, mapping
    
    def _on_confirm(self) -> None:
        # handle confirm button
        valid, errors, mapping = self._validate()
        
        if not valid:
            self._validation_label.setText("\n".join(errors))
            return
        
        self._validation_label.setText("")
        self.mapping_confirmed.emit(mapping)
        self.accept()
    
    def get_mapping(self) -> Dict[str, str]:
        # get current mapping
        _, _, mapping = self._validate()
        return mapping