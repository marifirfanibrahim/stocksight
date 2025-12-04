"""
anomaly review dialog
review and take action on detected anomalies
batch processing for efficiency
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QCheckBox, QSplitter,
    QFrame, QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
from typing import Dict, List, Optional

import config
from core.anomaly_detector import Anomaly


# ============================================================================
#                      ANOMALY REVIEW DIALOG
# ============================================================================

class AnomalyReviewDialog(QDialog):
    # dialog for reviewing anomalies
    
    # signals
    anomalies_actioned = pyqtSignal(list)  # list of (anomaly, action) tuples
    anomalies_corrected = pyqtSignal(list)  # list of anomalies to correct
    navigate_to_sku = pyqtSignal(str)
    flag_for_correction = pyqtSignal(str)  # sku to flag
    
    def __init__(self, anomalies: List[Anomaly], parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._anomalies = anomalies
        self._actions = {}  # anomaly index -> action
        self._setup_ui()
        self._populate_table()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Review Anomalies")
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # header
        header_layout = QHBoxLayout()
        
        header = QLabel(f"Anomaly Review ({len(self._anomalies)} detected)")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # filter controls
        header_layout.addWidget(QLabel("Filter:"))
        
        self._type_filter = QComboBox()
        self._type_filter.addItems(["All Types", "Spikes", "Drops", "Zeros", "Gaps"])
        self._type_filter.currentIndexChanged.connect(self._apply_filter)
        header_layout.addWidget(self._type_filter)
        
        self._severity_filter = QComboBox()
        self._severity_filter.addItems(["All Severity", "High Only", "Medium+"])
        self._severity_filter.currentIndexChanged.connect(self._apply_filter)
        header_layout.addWidget(self._severity_filter)
        
        layout.addLayout(header_layout)
        
        # anomaly table
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Item", "Date", "Value", "Expected", "Type", "Severity", "Action"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        
        layout.addWidget(self._table)
        
        # selected item details
        self._details_frame = QFrame()
        self._details_frame.setFrameStyle(QFrame.StyledPanel)
        self._details_frame.setMaximumHeight(100)
        details_layout = QHBoxLayout(self._details_frame)
        
        self._details_label = QLabel("Select an anomaly to see details")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_layout.addWidget(self._details_label)
        
        details_buttons = QVBoxLayout()
        
        self._view_btn = QPushButton("View in Chart")
        self._view_btn.setEnabled(False)
        self._view_btn.clicked.connect(self._view_in_chart)
        details_buttons.addWidget(self._view_btn)
        
        self._flag_btn = QPushButton("Flag for Correction")
        self._flag_btn.setEnabled(False)
        self._flag_btn.clicked.connect(self._flag_selected)
        details_buttons.addWidget(self._flag_btn)
        
        details_layout.addLayout(details_buttons)
        
        layout.addWidget(self._details_frame)
        
        # batch actions
        batch_layout = QHBoxLayout()
        
        batch_layout.addWidget(QLabel("Batch action for selected:"))
        
        self._batch_combo = QComboBox()
        self._batch_combo.addItems([
            "Select action...",
            "Keep value (ignore)",
            "Flag for correction",
            "Auto-correct (interpolate)",
            "Remove data point"
        ])
        batch_layout.addWidget(self._batch_combo)
        
        apply_batch_btn = QPushButton("Apply to Selected")
        apply_batch_btn.clicked.connect(self._apply_batch_action)
        batch_layout.addWidget(apply_batch_btn)
        
        batch_layout.addStretch()
        
        # select all
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._table.selectAll)
        batch_layout.addWidget(select_all_btn)
        
        layout.addLayout(batch_layout)
        
        # summary
        self._summary_label = QLabel("")
        layout.addWidget(self._summary_label)
        
        # buttons
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export List")
        export_btn.clicked.connect(self._export_anomalies)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply Actions")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
        
        self._update_summary()
    
    # ---------- TABLE POPULATION ----------
    
    def _populate_table(self) -> None:
        # populate table with anomalies
        self._table.setRowCount(len(self._anomalies))
        
        for i, anomaly in enumerate(self._anomalies):
            # sku - make selectable for copy
            sku_item = QTableWidgetItem(anomaly.sku)
            sku_item.setFlags(sku_item.flags() | Qt.ItemIsSelectable)
            self._table.setItem(i, 0, sku_item)
            
            # date
            date_item = QTableWidgetItem(str(anomaly.date))
            self._table.setItem(i, 1, date_item)
            
            # value
            value_item = QTableWidgetItem(f"{anomaly.value:,.0f}")
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(i, 2, value_item)
            
            # expected
            expected_item = QTableWidgetItem(f"{anomaly.expected_value:,.0f}")
            expected_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(i, 3, expected_item)
            
            # type
            type_text = config.ANOMALY_TYPES.get(anomaly.anomaly_type, anomaly.anomaly_type)
            type_item = QTableWidgetItem(type_text)
            self._table.setItem(i, 4, type_item)
            
            # severity
            severity_pct = int(anomaly.severity * 100)
            severity_item = QTableWidgetItem(f"{severity_pct}%")
            severity_item.setTextAlignment(Qt.AlignCenter)
            
            # color code severity
            if anomaly.severity >= 0.7:
                severity_item.setBackground(QBrush(QColor("#E57373")))
            elif anomaly.severity >= 0.4:
                severity_item.setBackground(QBrush(QColor("#FFD54F")))
            else:
                severity_item.setBackground(QBrush(QColor("#81C784")))
            
            self._table.setItem(i, 5, severity_item)
            
            # action dropdown
            action_combo = QComboBox()
            action_combo.addItems([
                "Pending",
                "Keep",
                "Flag",
                "Auto-correct",
                "Remove"
            ])
            action_combo.setProperty("row", i)
            action_combo.currentIndexChanged.connect(self._on_action_changed)
            self._table.setCellWidget(i, 6, action_combo)
            
            # store data for filtering
            sku_item.setData(Qt.UserRole, anomaly)
    
    # ---------- FILTERING ----------
    
    def _apply_filter(self) -> None:
        # apply filters to table
        type_filter = self._type_filter.currentText().lower()
        severity_filter = self._severity_filter.currentText()
        
        for i in range(self._table.rowCount()):
            item = self._table.item(i, 0)
            if not item:
                continue
            
            anomaly = item.data(Qt.UserRole)
            show = True
            
            # type filter
            if type_filter != "all types":
                if type_filter == "spikes" and anomaly.anomaly_type != "spike":
                    show = False
                elif type_filter == "drops" and anomaly.anomaly_type != "drop":
                    show = False
                elif type_filter == "zeros" and anomaly.anomaly_type != "zero":
                    show = False
                elif type_filter == "gaps" and anomaly.anomaly_type != "gap":
                    show = False
            
            # severity filter
            if severity_filter == "High Only" and anomaly.severity < 0.7:
                show = False
            elif severity_filter == "Medium+" and anomaly.severity < 0.4:
                show = False
            
            self._table.setRowHidden(i, not show)
        
        self._update_summary()
    
    # ---------- ACTIONS ----------
    
    def _on_action_changed(self) -> None:
        # handle action dropdown change
        combo = self.sender()
        row = combo.property("row")
        action = combo.currentText()
        self._actions[row] = action
        self._update_summary()
    
    def _apply_batch_action(self) -> None:
        # apply batch action to selected rows
        action = self._batch_combo.currentText()
        if action == "Select action...":
            return
        
        # map ui text to action key
        action_map = {
            "Keep value (ignore)": "Keep",
            "Flag for correction": "Flag",
            "Auto-correct (interpolate)": "Auto-correct",
            "Remove data point": "Remove"
        }
        action_key = action_map.get(action, "Pending")
        
        selected_rows = set()
        for item in self._table.selectedItems():
            selected_rows.add(item.row())
        
        for row in selected_rows:
            combo = self._table.cellWidget(row, 6)
            if combo:
                index = combo.findText(action_key)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    self._actions[row] = action_key
        
        self._batch_combo.setCurrentIndex(0)
        self._update_summary()
        
        # show confirmation
        QMessageBox.information(
            self,
            "Batch Action Applied",
            f"Applied '{action_key}' to {len(selected_rows)} selected anomalies."
        )
    
    def _on_selection_changed(self) -> None:
        # handle selection change
        selected = self._table.selectedItems()
        
        if selected:
            row = selected[0].row()
            item = self._table.item(row, 0)
            if item:
                anomaly = item.data(Qt.UserRole)
                self._show_details(anomaly)
                self._view_btn.setEnabled(True)
                self._flag_btn.setEnabled(True)
        else:
            self._details_label.setText("Select an anomaly to see details")
            self._view_btn.setEnabled(False)
            self._flag_btn.setEnabled(False)
    
    def _show_details(self, anomaly: Anomaly) -> None:
        # show anomaly details
        diff = anomaly.value - anomaly.expected_value
        diff_pct = (diff / anomaly.expected_value * 100) if anomaly.expected_value != 0 else 0
        
        details = (
            f"<b>Item:</b> {anomaly.sku}<br>"
            f"<b>Date:</b> {anomaly.date}<br>"
            f"<b>Difference:</b> {diff:+,.0f} ({diff_pct:+.1f}%)<br>"
            f"<b>Detection method:</b> {anomaly.method}"
        )
        
        self._details_label.setText(details)
    
    def _view_in_chart(self) -> None:
        # emit signal to view sku in chart
        selected = self._table.selectedItems()
        if selected:
            row = selected[0].row()
            item = self._table.item(row, 0)
            if item:
                anomaly = item.data(Qt.UserRole)
                self.navigate_to_sku.emit(anomaly.sku)
    
    def _flag_selected(self) -> None:
        # flag selected anomaly for correction
        selected = self._table.selectedItems()
        if selected:
            row = selected[0].row()
            item = self._table.item(row, 0)
            if item:
                anomaly = item.data(Qt.UserRole)
                
                # set action to flag
                combo = self._table.cellWidget(row, 6)
                if combo:
                    index = combo.findText("Flag")
                    if index >= 0:
                        combo.setCurrentIndex(index)
                        self._actions[row] = "Flag"
                
                # emit signal
                self.flag_for_correction.emit(anomaly.sku)
                
                QMessageBox.information(
                    self,
                    "Flagged",
                    f"Item '{anomaly.sku}' has been flagged for correction.\n"
                    "You can find it in the Data tab after closing this dialog."
                )
    
    def _update_summary(self) -> None:
        # update summary label
        total = len(self._anomalies)
        visible = sum(1 for i in range(self._table.rowCount()) if not self._table.isRowHidden(i))
        actioned = sum(1 for a in self._actions.values() if a != "Pending")
        
        # count by action type
        action_counts = {}
        for action in self._actions.values():
            if action != "Pending":
                action_counts[action] = action_counts.get(action, 0) + 1
        
        action_text = ", ".join([f"{v} {k}" for k, v in action_counts.items()]) if action_counts else "none"
        
        self._summary_label.setText(
            f"Showing {visible} of {total} anomalies | {actioned} actions set ({action_text})"
        )
    
    def _export_anomalies(self) -> None:
        # export anomaly list
        from PyQt5.QtWidgets import QFileDialog
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Anomalies", "anomalies.csv", "CSV Files (*.csv)"
        )
        
        if path:
            import pandas as pd
            
            data = []
            for i, anomaly in enumerate(self._anomalies):
                action = self._actions.get(i, "Pending")
                data.append({
                    "sku": anomaly.sku,
                    "date": anomaly.date,
                    "value": anomaly.value,
                    "expected": anomaly.expected_value,
                    "type": anomaly.anomaly_type,
                    "severity": anomaly.severity,
                    "method": anomaly.method,
                    "action": action
                })
            
            df = pd.DataFrame(data)
            df.to_csv(path, index=False)
            
            QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
    
    def _on_apply(self) -> None:
        # apply all actions
        result = []
        flagged_skus = []
        
        for i, anomaly in enumerate(self._anomalies):
            action = self._actions.get(i, "Pending")
            if action != "Pending":
                result.append((anomaly, action))
                if action == "Flag":
                    flagged_skus.append(anomaly.sku)
        
        # emit signals
        self.anomalies_actioned.emit(result)
        
        # emit flag signals for each flagged sku
        for sku in set(flagged_skus):
            self.flag_for_correction.emit(sku)
        
        # show summary
        if result:
            action_counts = {}
            for _, action in result:
                action_counts[action] = action_counts.get(action, 0) + 1
            
            summary = "\n".join([f"• {v} {k}" for k, v in action_counts.items()])
            
            QMessageBox.information(
                self,
                "Actions Applied",
                f"Applied actions:\n{summary}\n\n"
                f"Flagged items can be found in the Data tab."
            )
        
        self.accept()
    
    def get_actions(self) -> List[tuple]:
        # get list of anomaly actions
        result = []
        for i, anomaly in enumerate(self._anomalies):
            action = self._actions.get(i, "Pending")
            result.append((anomaly, action))
        return result