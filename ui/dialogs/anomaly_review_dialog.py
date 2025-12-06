"""
anomaly review dialog
review and take action on detected anomalies
batch processing for efficiency
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QLineEdit,
    QFrame, QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

import config
from core.anomaly_detector import Anomaly


# ============================================================================
#                      ANOMALY REVIEW DIALOG
# ============================================================================

class AnomalyReviewDialog(QDialog):
    # dialog for reviewing anomalies and applying actions
    
    # signals
    anomalies_actioned = pyqtSignal(list)
    anomalies_corrected = pyqtSignal(list)
    navigate_to_sku = pyqtSignal(str)
    flag_for_correction = pyqtSignal(str)
    view_sku_chart = pyqtSignal(str)
    
    # ---------- CONSTANTS ----------
    ROW_HEIGHT = 40
    
    def __init__(self, anomalies: List[Anomaly], parent=None, processor=None):
        # initialize dialog
        super().__init__(parent)
        
        self._anomalies = anomalies
        self._processor = processor
        self._actions: Dict[int, str] = {}
        self._flagged_skus: set = set()
        
        self._setup_ui()
        self._populate_table()
    
    # ---------- UI SETUP ----------
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Review Anomalies")
        self.setMinimumWidth(980)
        self.setMinimumHeight(650)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # header row
        header_layout = QHBoxLayout()
        
        header = QLabel(f"Anomaly Review ({len(self._anomalies)} items)")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # type and severity filters
        header_layout.addWidget(QLabel("Filter:"))
        
        self._type_filter = QComboBox()
        self._type_filter.addItems(["All Types", "Spikes", "Drops", "Zeros", "Gaps"])
        # connect change to filter method
        self._type_filter.currentIndexChanged.connect(self._apply_filter)
        header_layout.addWidget(self._type_filter)
        
        self._severity_filter = QComboBox()
        self._severity_filter.addItems(["All Severity", "High Only (≥70%)", "Medium+ (≥40%)"])
        # connect change to filter method
        self._severity_filter.currentIndexChanged.connect(self._apply_filter)
        header_layout.addWidget(self._severity_filter)
        
        layout.addLayout(header_layout)
        
        # search row
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter anomalies by item or date...")
        # connect search change to filter method
        self._search_edit.textChanged.connect(self._apply_filter)
        search_layout.addWidget(self._search_edit)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # anomaly table
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Item", "Date", "Value", "Expected", "Type", "Severity", "Action"
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        # set taller default row height for readability
        self._table.verticalHeader().setDefaultSectionSize(self.ROW_HEIGHT)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.setSortingEnabled(True)
        
        layout.addWidget(self._table)
        
        # details section
        self._details_frame = QFrame()
        self._details_frame.setFrameStyle(QFrame.StyledPanel)
        self._details_frame.setMaximumHeight(110)
        details_layout = QHBoxLayout(self._details_frame)
        
        self._details_label = QLabel("Select an anomaly to see details")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_layout.addWidget(self._details_label)
        
        btn_col = QVBoxLayout()
        
        self._view_btn = QPushButton("View in Chart")
        self._view_btn.setEnabled(False)
        self._view_btn.clicked.connect(self._view_in_chart)
        btn_col.addWidget(self._view_btn)
        
        self._flag_btn = QPushButton("Flag for Correction")
        self._flag_btn.setEnabled(False)
        self._flag_btn.clicked.connect(self._flag_selected)
        btn_col.addWidget(self._flag_btn)
        
        details_layout.addLayout(btn_col)
        layout.addWidget(self._details_frame)
        
        # batch action row
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
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._table.selectAll)
        batch_layout.addWidget(select_all_btn)
        
        layout.addLayout(batch_layout)
        
        # summary label
        self._summary_label = QLabel("")
        layout.addWidget(self._summary_label)
        
        # bottom buttons
        bottom_layout = QHBoxLayout()
        
        export_btn = QPushButton("Export List")
        export_btn.clicked.connect(self._export_anomalies)
        bottom_layout.addWidget(export_btn)
        
        bottom_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)
        
        apply_btn = QPushButton("Apply Actions")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        bottom_layout.addWidget(apply_btn)
        
        layout.addLayout(bottom_layout)
        
        self._update_summary()
    
    # ---------- TABLE POPULATION ----------
    
    def _populate_table(self) -> None:
        # populate table with anomalies
        self._table.setRowCount(len(self._anomalies))
        
        for i, anomaly in enumerate(self._anomalies):
            # ensure row has desired height
            self._table.setRowHeight(i, self.ROW_HEIGHT)
            
            # sku column
            sku_item = QTableWidgetItem(anomaly.sku)
            sku_item.setFlags(sku_item.flags() | Qt.ItemIsSelectable)
            sku_item.setData(Qt.UserRole, anomaly)
            self._table.setItem(i, 0, sku_item)
            
            # date column
            date_item = QTableWidgetItem(str(anomaly.date))
            self._table.setItem(i, 1, date_item)
            
            # value column
            value_item = QTableWidgetItem(f"{anomaly.value:,.0f}")
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(i, 2, value_item)
            
            # expected column
            expected_item = QTableWidgetItem(f"{anomaly.expected_value:,.0f}")
            expected_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(i, 3, expected_item)
            
            # type column
            type_text = config.ANOMALY_TYPES.get(anomaly.anomaly_type, anomaly.anomaly_type)
            type_item = QTableWidgetItem(type_text)
            self._table.setItem(i, 4, type_item)
            
            # severity column
            severity_pct = int(anomaly.severity * 100)
            severity_item = QTableWidgetItem(f"{severity_pct}%")
            severity_item.setTextAlignment(Qt.AlignCenter)
            
            # set background color by severity
            if anomaly.severity >= 0.7:
                severity_item.setBackground(QBrush(QColor("#E57373")))
            elif anomaly.severity >= 0.4:
                severity_item.setBackground(QBrush(QColor("#FFD54F")))
            else:
                severity_item.setBackground(QBrush(QColor("#81C784")))
            
            self._table.setItem(i, 5, severity_item)
            
            # action combo column
            action_combo = QComboBox()
            action_combo.addItems([
                "Pending",
                "Keep",
                "Flag",
                "Auto-correct",
                "Remove"
            ])
            # store row index on widget
            action_combo.setProperty("row", i)
            action_combo.currentIndexChanged.connect(self._on_action_changed)
            self._table.setCellWidget(i, 6, action_combo)
    
    # ---------- FILTERING ----------
    
    def _apply_filter(self, *args) -> None:
        # apply type severity and search filters
        # args is ignored so method can be used for multiple signals
        
        type_index = self._type_filter.currentIndex()
        severity_index = self._severity_filter.currentIndex()
        search_text = self._search_edit.text().lower().strip()
        
        for row in range(self._table.rowCount()):
            sku_item = self._table.item(row, 0)
            if not sku_item:
                continue
            
            # get anomaly from user role
            anomaly: Anomaly = sku_item.data(Qt.UserRole)
            show = True
            
            # type filter conditions
            if type_index == 1 and anomaly.anomaly_type != "spike":
                show = False
            elif type_index == 2 and anomaly.anomaly_type != "drop":
                show = False
            elif type_index == 3 and anomaly.anomaly_type != "zero":
                show = False
            elif type_index == 4 and anomaly.anomaly_type != "gap":
                show = False
            
            # severity filter conditions
            if show:
                if severity_index == 1 and anomaly.severity < 0.7:
                    show = False
                elif severity_index == 2 and anomaly.severity < 0.4:
                    show = False
            
            # search filter conditions
            if show and search_text:
                row_match = False
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    if not item:
                        continue
                    if search_text in item.text().lower():
                        row_match = True
                        break
                if not row_match:
                    show = False
            
            # apply visibility
            self._table.setRowHidden(row, not show)
        
        self._update_summary()
    
    # ---------- ACTION STATE ----------
    
    def _on_action_changed(self) -> None:
        # update internal actions dict from combo change
        combo = self.sender()
        row = combo.property("row")
        action = combo.currentText()
        self._actions[row] = action
        self._update_summary()
    
    def _apply_batch_action(self) -> None:
        # apply one action to all selected rows
        label = self._batch_combo.currentText()
        if label == "Select action...":
            return
        
        # map human label to internal action code
        map_text = {
            "Keep value (ignore)": "Keep",
            "Flag for correction": "Flag",
            "Auto-correct (interpolate)": "Auto-correct",
            "Remove data point": "Remove"
        }
        action = map_text.get(label, "Pending")
        
        # collect unique selected rows
        selected_rows = {idx.row() for idx in self._table.selectedIndexes()}
        
        for row in selected_rows:
            combo = self._table.cellWidget(row, 6)
            if combo:
                idx = combo.findText(action)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                    self._actions[row] = action
        
        # reset batch selector
        self._batch_combo.setCurrentIndex(0)
        self._update_summary()
        
        QMessageBox.information(
            self,
            "Batch Action Applied",
            f"Applied '{action}' to {len(selected_rows)} selected anomalies."
        )
    
    def _on_selection_changed(self) -> None:
        # update details for selected anomaly
        selected = self._table.selectedItems()
        
        if not selected:
            self._details_label.setText("Select an anomaly to see details")
            self._view_btn.setEnabled(False)
            self._flag_btn.setEnabled(False)
            return
        
        row = selected[0].row()
        sku_item = self._table.item(row, 0)
        anomaly: Anomaly = sku_item.data(Qt.UserRole)
        
        self._show_details(anomaly)
        self._view_btn.setEnabled(True)
        self._flag_btn.setEnabled(True)
    
    def _show_details(self, anomaly: Anomaly) -> None:
        # show text details for anomaly
        diff = anomaly.value - anomaly.expected_value
        diff_pct = (diff / anomaly.expected_value * 100) if anomaly.expected_value != 0 else 0
        
        text = (
            f"<b>Item:</b> {anomaly.sku}<br>"
            f"<b>Date:</b> {anomaly.date}<br>"
            f"<b>Difference:</b> {diff:+,.0f} ({diff_pct:+.1f}%)<br>"
            f"<b>Detection method:</b> {anomaly.method}"
        )
        self._details_label.setText(text)
    
    # ---------- CHART AND FLAG ----------
    
    def _view_in_chart(self) -> None:
        # show sku chart with anomalies
        selected = self._table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        sku_item = self._table.item(row, 0)
        anomaly: Anomaly = sku_item.data(Qt.UserRole)
        sku = anomaly.sku
        
        # if processor is available show embedded chart dialog
        if self._processor:
            sku_data = self._processor.get_sku_data(sku)
            date_col = self._processor.get_mapped_column("date")
            qty_col = self._processor.get_mapped_column("quantity")
            
            sku_anoms = [
                {"date": a.date, "value": a.value, "type": a.anomaly_type}
                for a in self._anomalies if a.sku == sku
            ]
            
            from ui.dialogs.anomaly_chart_dialog import AnomalyChartDialog
            
            dialog = AnomalyChartDialog(
                sku, sku_data, date_col, qty_col, sku_anoms, self
            )
            dialog.exec_()
        else:
            # emit event for external chart handler
            self.view_sku_chart.emit(sku)
    
    def _flag_selected(self) -> None:
        # flag selected sku for correction
        selected = self._table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        sku_item = self._table.item(row, 0)
        anomaly: Anomaly = sku_item.data(Qt.UserRole)
        sku = anomaly.sku
        
        # set action to flag in combo
        combo = self._table.cellWidget(row, 6)
        if combo:
            idx = combo.findText("Flag")
            if idx >= 0:
                combo.setCurrentIndex(idx)
                self._actions[row] = "Flag"
        
        # track flagged sku and emit signal
        self._flagged_skus.add(sku)
        self.flag_for_correction.emit(sku)
        
        QMessageBox.information(
            self,
            "Flagged",
            f"Item '{sku}' has been flagged for correction.\n"
            "You can review flagged items later in the Data tab."
        )
    
    # ---------- SUMMARY / EXPORT ----------
    
    def _update_summary(self) -> None:
        # update summary footer text
        total = len(self._anomalies)
        visible = sum(
            0 if self._table.isRowHidden(r) else 1
            for r in range(self._table.rowCount())
        )
        actioned = sum(1 for a in self._actions.values() if a != "Pending")
        
        counts: Dict[str, int] = {}
        for a in self._actions.values():
            if a != "Pending":
                counts[a] = counts.get(a, 0) + 1
        
        if counts:
            action_text = ", ".join([f"{v} {k}" for k, v in counts.items()])
        else:
            action_text = "none"
        
        self._summary_label.setText(
            f"Showing {visible} of {total} anomalies | "
            f"{actioned} actions set ({action_text})"
        )
    
    def _export_anomalies(self) -> None:
        # export anomalies with actions to csv
        from PyQt5.QtWidgets import QFileDialog
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Anomalies",
            "anomalies.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        
        rows: List[Dict[str, Any]] = []
        for idx, anomaly in enumerate(self._anomalies):
            action = self._actions.get(idx, "Pending")
            rows.append({
                "sku": anomaly.sku,
                "date": anomaly.date,
                "value": anomaly.value,
                "expected": anomaly.expected_value,
                "type": anomaly.anomaly_type,
                "severity": anomaly.severity,
                "method": anomaly.method,
                "action": action
            })
        
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False)
        
        QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
    
    # ---------- APPLY ACTIONS ----------
    
    def _on_apply(self) -> None:
        # apply actions to underlying data
        result = []
        flagged: set = set()
        corrections: List[Dict[str, Any]] = []
        removals: List[Dict[str, Any]] = []
        action_counts: Dict[str, int] = {}
        
        # collect actions per anomaly
        for idx, anomaly in enumerate(self._anomalies):
            action = self._actions.get(idx, "Pending")
            if action == "Pending":
                continue
            
            result.append((anomaly, action))
            action_counts[action] = action_counts.get(action, 0) + 1
            
            if action == "Flag":
                flagged.add(anomaly.sku)
            elif action == "Auto-correct":
                corrections.append({
                    "sku": anomaly.sku,
                    "date": anomaly.date,
                    "new_value": anomaly.expected_value
                })
            elif action == "Remove":
                removals.append({
                    "sku": anomaly.sku,
                    "date": anomaly.date
                })
        
        # if no actions selected show info and exit
        if not result:
            QMessageBox.information(
                self,
                "No Actions",
                "No actions were applied.\nAll anomalies remain pending."
            )
            return
        
        corrections_made = 0
        removals_made = 0
        
        # apply changes to processor data when available
        if self._processor and self._processor.processed_data is not None:
            df = self._processor.processed_data
            sku_col = self._processor.get_mapped_column("sku")
            date_col = self._processor.get_mapped_column("date")
            qty_col = self._processor.get_mapped_column("quantity")
            
            if sku_col and date_col and qty_col:
                df = df.copy()
                df[date_col] = pd.to_datetime(df[date_col])
                
                # auto-correct values
                if corrections:
                    corr_df = pd.DataFrame(corrections)
                    corr_df["date"] = pd.to_datetime(corr_df["date"])
                    corr_df = corr_df.drop_duplicates(subset=["sku", "date"])
                    corr_df = corr_df.rename(
                        columns={"sku": "_sku_corr", "date": "_date_corr", "new_value": "_new_val"}
                    )
                    
                    df = df.merge(
                        corr_df,
                        left_on=[sku_col, date_col],
                        right_on=["_sku_corr", "_date_corr"],
                        how="left"
                    )
                    
                    mask = df["_new_val"].notna()
                    corrections_made = int(mask.sum())
                    if corrections_made > 0:
                        df.loc[mask, qty_col] = df.loc[mask, "_new_val"]
                    
                    df = df.drop(columns=["_sku_corr", "_date_corr", "_new_val"])
                
                # remove data points
                if removals:
                    rem_df = pd.DataFrame(removals)
                    rem_df["date"] = pd.to_datetime(rem_df["date"])
                    rem_df = rem_df.drop_duplicates(subset=["sku", "date"])
                    rem_df = rem_df.rename(
                        columns={"sku": "_sku_rem", "date": "_date_rem"}
                    )
                    
                    df = df.merge(
                        rem_df,
                        left_on=[sku_col, date_col],
                        right_on=["_sku_rem", "_date_rem"],
                        how="left",
                        indicator="_rem_flag"
                    )
                    
                    mask = df["_rem_flag"] == "both"
                    removals_made = int(mask.sum())
                    if removals_made > 0:
                        df = df[~mask]
                    
                    df = df.drop(columns=["_sku_rem", "_date_rem", "_rem_flag"])
                
                df = df.reset_index(drop=True)
                self._processor.processed_data = df
        
        # emit summary signals
        self.anomalies_actioned.emit(result)
        
        for sku in flagged:
            self.flag_for_correction.emit(sku)
        
        if corrections_made > 0:
            self.anomalies_corrected.emit(corrections)
        
        # build summary text
        lines = [f"• {v} anomalies: {k}" for k, v in action_counts.items()]
        extra = ""
        if corrections_made > 0:
            extra += f"\n\n{corrections_made} values were auto-corrected."
        if removals_made > 0:
            extra += f"\n{removals_made} data points were removed."
        if flagged:
            extra += f"\n\n{len(flagged)} unique items flagged for correction."
        
        QMessageBox.information(
            self,
            "Actions Applied Successfully",
            "Applied actions to anomalies:\n\n" +
            "\n".join(lines) +
            extra
        )
        
        # close dialog after applying actions
        self.accept()
    
    # ---------- PUBLIC HELPERS ----------
    
    def get_actions(self) -> List[tuple]:
        # return anomaly actions list
        result = []
        for idx, anomaly in enumerate(self._anomalies):
            action = self._actions.get(idx, "Pending")
            result.append((anomaly, action))
        return result
    
    def set_processor(self, processor) -> None:
        # set data processor reference
        self._processor = processor