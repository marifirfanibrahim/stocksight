"""
help dialog module
displays help information for terminology
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QFrame,
    QGroupBox, QTabWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import config


# ============================================================================
#                        CLUSTER HELP DIALOG
# ============================================================================

class ClusterHelpDialog(QDialog):
    # dialog explaining cluster terminology
    
    def __init__(self, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Cluster Terminology Help")
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header label
        header = QLabel("Understanding Cluster Types")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        # scroll area setup
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        # volume tiers section
        scroll_layout.addWidget(self._create_section(
            "📊 Volume Tiers (ABC Classification)",
            [
                ("A - High Volume", 
                 "Top 20% of items by sales volume. These items usually account for "
                 "around 80% of total demand and deserve the most detailed forecasting "
                 "and monitoring.",
                 "#4CAF50"),
                ("B - Medium Volume",
                 "Next 30% of items by sales volume. These items have moderate demand "
                 "and should be reviewed regularly but do not need the same attention "
                 "as A-items.",
                 "#FF9800"),
                ("C - Low Volume",
                 "Bottom 50% of items by sales volume. These items sell less often and "
                 "are usually suitable for simpler forecasting and bulk planning.",
                 "#F44336")
            ]
        ))
        
        # pattern types section
        scroll_layout.addWidget(self._create_section(
            "📈 Pattern Types",
            [
                ("Steady",
                 "Items with consistent demand and low variability. "
                 "These are the easiest to forecast and support stable inventory.",
                 "#4CAF50"),
                ("Variable",
                 "Items with some demand swings but still recognizable patterns. "
                 "They may need moderate safety stock and periodic review.",
                 "#2196F3"),
                ("Erratic",
                 "Items with very uneven demand. Large jumps or drops happen often. "
                 "These items are harder to forecast and may need special policies.",
                 "#FF9800"),
                ("Seasonal",
                 "Items with strong seasonal peaks, especially in Q4. "
                 "Demand is concentrated in specific months or events.",
                 "#9C27B0")
            ]
        ))
        
        # metrics section
        scroll_layout.addWidget(self._create_section(
            "📏 Key Metrics",
            [
                ("CV (Coefficient of Variation)",
                 "Standard deviation divided by mean. Measures how noisy demand is "
                 "relative to its average. Lower values mean more stable demand.",
                 "#607D8B"),
                ("Q4 Concentration",
                 "Share of annual demand that happens in October to December. "
                 "High values suggest strong holiday or end-of-year effects.",
                 "#607D8B"),
                ("MAPE (Mean Absolute Percentage Error)",
                 "Average forecast error as a percentage of actual demand. "
                 "Lower is better. Under 10% is excellent, 10-20% is good, "
                 "20-30% is fair, over 30% usually needs review.",
                 "#607D8B")
            ]
        ))
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # close button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_section(self, title: str, items: list) -> QGroupBox:
        # create help section group box
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        for name, description, color in items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)
            
            # name label with color
            name_label = QLabel(f"● {name}")
            name_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {color};")
            item_layout.addWidget(name_label)
            
            # description label
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; margin-left: 15px;")
            item_layout.addWidget(desc_label)
            
            layout.addWidget(item_widget)
        
        return group


# ============================================================================
#                       FORECAST HELP DIALOG
# ============================================================================

class ForecastHelpDialog(QDialog):
    # dialog explaining forecast terminology
    
    def __init__(self, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Forecast Terminology Help")
        self.setMinimumWidth(600)
        self.setMinimumHeight(550)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header label
        header = QLabel("Understanding Forecast Terms")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        # tab widget
        tabs = QTabWidget()
        
        # strategies tab
        strategies_widget = QWidget()
        strategies_layout = QVBoxLayout(strategies_widget)
        strategies_scroll = QScrollArea()
        strategies_scroll.setWidgetResizable(True)
        strategies_scroll.setFrameShape(QFrame.NoFrame)
        
        strategies_content = QWidget()
        strategies_content_layout = QVBoxLayout(strategies_content)
        strategies_content_layout.addWidget(self._create_section(
            "🎯 Forecasting Strategies",
            [
                ("🔵 Simple & Fast",
                 "Uses basic models such as Naive, Seasonal Naive, and Exponential "
                 "Smoothing. Suitable for quick runs, initial analysis, and for all "
                 "items when time is limited.",
                 "#2196F3"),
                ("🟡 Smart & Balanced",
                 "Uses statistical models such as ARIMA, Prophet, and Theta. Balances "
                 "accuracy and speed and is recommended for most business scenarios "
                 "and for A and B items.",
                 "#FF9800"),
                ("🔴 Advanced AI",
                 "Uses machine learning models such as LightGBM, XGBoost, and "
                 "ensembles. Gives the highest accuracy but is slower and runs only "
                 "on A-items by design.",
                 "#F44336")
            ]
        ))
        strategies_content_layout.addStretch()
        strategies_scroll.setWidget(strategies_content)
        strategies_layout.addWidget(strategies_scroll)
        tabs.addTab(strategies_widget, "Strategies")
        
        # models tab
        models_widget = QWidget()
        models_layout = QVBoxLayout(models_widget)
        models_scroll = QScrollArea()
        models_scroll.setWidgetResizable(True)
        models_scroll.setFrameShape(QFrame.NoFrame)
        
        models_content = QWidget()
        models_content_layout = QVBoxLayout(models_content)
        models_content_layout.addWidget(self._create_section(
            "🔧 Forecasting Models",
            [
                ("Naive / Simple Average",
                 "Uses the most recent value or a simple average as the forecast. "
                 "Works surprisingly well for stable demand patterns.",
                 "#607D8B"),
                ("Seasonal Naive",
                 "Repeats last year's values for the same period. Good for clear "
                 "yearly cycles.",
                 "#607D8B"),
                ("Exponential Smoothing",
                 "Gives more weight to recent data. Can follow trends and seasonality "
                 "without overreacting to noise.",
                 "#607D8B"),
                ("ARIMA",
                 "Captures relationships between past values and errors. Good for "
                 "series with trends and autocorrelation.",
                 "#607D8B"),
                ("Prophet",
                 "Model designed for business time series with holidays and missing "
                 "data. Useful when seasonality is strong and dates matter.",
                 "#607D8B"),
                ("LightGBM / XGBoost",
                 "Machine learning models that learn from many features. Good when "
                 "you have rich data and want to capture complex effects.",
                 "#607D8B"),
                ("Ensemble",
                 "Combines several models to get a more robust forecast. Often more "
                 "stable than any individual model.",
                 "#607D8B")
            ]
        ))
        models_content_layout.addStretch()
        models_scroll.setWidget(models_content)
        models_layout.addWidget(models_scroll)
        tabs.addTab(models_widget, "Models")
        
        # metrics tab
        metrics_widget = QWidget()
        metrics_layout = QVBoxLayout(metrics_widget)
        metrics_scroll = QScrollArea()
        metrics_scroll.setWidgetResizable(True)
        metrics_scroll.setFrameShape(QFrame.NoFrame)
        
        metrics_content = QWidget()
        metrics_content_layout = QVBoxLayout(metrics_content)
        metrics_content_layout.addWidget(self._create_section(
            "📊 Accuracy Metrics",
            [
                ("MAPE (Mean Absolute Percentage Error)",
                 "Average forecast error as a percentage of actual values. "
                 "Under 10% is excellent, 10-20% is good, 20-30% is fair, "
                 "and above 30% usually needs review.",
                 "#4CAF50"),
                ("MAE (Mean Absolute Error)",
                 "Average absolute error in the same units as your data, such as "
                 "units sold. Easier to interpret in simple volume terms.",
                 "#2196F3"),
                ("RMSE (Root Mean Square Error)",
                 "Square root of the average squared errors. Penalizes large misses "
                 "more than MAE and is useful to detect occasional big errors.",
                 "#9C27B0"),
                ("Confidence Interval",
                 "Range where actual demand is likely to fall, such as 95% "
                 "confidence. Wider intervals mean more uncertainty.",
                 "#FF9800")
            ]
        ))
        metrics_content_layout.addStretch()
        metrics_scroll.setWidget(metrics_content)
        metrics_layout.addWidget(metrics_scroll)
        tabs.addTab(metrics_widget, "Metrics")
        
        # frequency tab
        freq_widget = QWidget()
        freq_layout = QVBoxLayout(freq_widget)
        freq_scroll = QScrollArea()
        freq_scroll.setWidgetResizable(True)
        freq_scroll.setFrameShape(QFrame.NoFrame)
        
        freq_content = QWidget()
        freq_content_layout = QVBoxLayout(freq_content)
        freq_content_layout.addWidget(self._create_section(
            "📅 Forecast Frequency",
            [
                ("Daily",
                 "Creates day-by-day forecasts. Gives the most detail but also shows "
                 "more volatility. Good for short-term planning on high-volume items.",
                 "#4CAF50"),
                ("Weekly",
                 "Creates week-by-week forecasts. Balances detail and stability and "
                 "fits most operational planning cycles.",
                 "#2196F3"),
                ("Monthly",
                 "Creates month-by-month forecasts. Best for longer-term planning, "
                 "budgeting, and reporting.",
                 "#9C27B0")
            ]
        ))
        freq_content_layout.addStretch()
        freq_scroll.setWidget(freq_content)
        freq_layout.addWidget(freq_scroll)
        tabs.addTab(freq_widget, "Frequency")
        
        layout.addWidget(tabs)
        
        # close button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_section(self, title: str, items: list) -> QGroupBox:
        # create help section group box
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        for name, description, color in items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)
            
            # name label
            name_label = QLabel(f"● {name}")
            name_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {color};")
            item_layout.addWidget(name_label)
            
            # description label
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; margin-left: 15px;")
            item_layout.addWidget(desc_label)
            
            layout.addWidget(item_widget)
        
        return group


# ============================================================================
#                    DATA CLEANING HELP DIALOG
# ============================================================================

class DataCleaningHelpDialog(QDialog):
    # dialog explaining data cleaning and anomalies workflow
    
    def __init__(self, parent=None):
        # initialize dialog
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        # setup user interface
        self.setWindowTitle("Data Cleaning and Anomalies Guide")
        self.setMinimumWidth(650)
        self.setMinimumHeight(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # header label
        header = QLabel("Understanding Data Cleaning and Anomalies")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)
        
        # section 1 data health checks
        content_layout.addWidget(self._create_section(
            "📋 Data Health Checks (Tab 1)",
            [
                ("What is checked",
                 "Tab 1 looks for common data issues: missing values in key columns, "
                 "duplicate item + date rows, negative quantities, and very short "
                 "or patchy histories.",
                 "#607D8B"),
                ("What the fixes do",
                 "When you choose a fix (fill missing, handle duplicates, fix "
                 "negatives, remove or cap outliers), the underlying dataset used "
                 "for forecasting is updated. These changes flow through to all "
                 "later tabs.",
                 "#607D8B")
            ]
        ))
        
        # section 2 abnormal data dialog
        content_layout.addWidget(self._create_section(
            "🔎 Abnormal Data Review (Tab 1)",
            [
                ("Abnormal vs invalid",
                 "Rows shown in the Abnormal Data dialog are not always wrong. "
                 "They are simply unusual based on your current data: missing "
                 "values, duplicate dates, negative quantities, or extreme values.",
                 "#607D8B"),
                ("Remove vs adjust",
                 "Removing rows deletes those points completely. Filling or capping "
                 "keeps the time line intact but changes the values. Once removed, "
                 "a specific (item, date) pair will not appear as an anomaly again.",
                 "#607D8B")
            ]
        ))
        
        # section 3 anomaly detection logic
        content_layout.addWidget(self._create_section(
            "📉 Anomaly Detection (Tab 2)",
            [
                ("How anomalies are found",
                 "Tab 2 runs statistical checks (IQR, z-score, and rolling windows) "
                 "on the cleaned data for each item. It flags values that sit far "
                 "outside the normal range of that item's history.",
                 "#607D8B"),
                ("Why new anomalies can appear",
                 "When you remove or correct the biggest spikes and drops, the "
                 "overall spread of the data shrinks. On the next detection pass, "
                 "points that were previously \"large but not extreme\" can now "
                 "stand out and be flagged as anomalies.",
                 "#607D8B"),
                ("What to expect in practice",
                 "It is normal to do one pass of detection, fix the most obvious "
                 "issues, and then see a smaller second set of anomalies after "
                 "re-detecting. You do not need to keep repeating this many times.",
                 "#607D8B")
            ]
        ))
        
        # section 4 recommended workflow
        content_layout.addWidget(self._create_section(
            "✅ Recommended Cleaning Workflow",
            [
                ("Step 1 – Data Health",
                 "Upload your data in Tab 1, confirm the column mapping, and apply "
                 "simple fixes for clearly invalid values (missing keys, duplicates, "
                 "negative quantities that do not make sense).",
                 "#4CAF50"),
                ("Step 2 – First anomaly pass",
                 "In Tab 2, run anomaly detection and use the Review Anomalies "
                 "dialog to handle the biggest spikes or drops that are clearly "
                 "data errors or out-of-scope events.",
                 "#4CAF50"),
                ("Step 3 – Optional second pass",
                 "If needed, re-run anomaly detection once more to see the updated "
                 "picture. At this stage, you will usually keep most remaining "
                 "anomalies as real but unusual business events.",
                 "#4CAF50"),
                ("When to stop",
                 "If only a small number of points or lower-severity anomalies "
                 "remain, it is usually better to move on to forecasting rather "
                 "than keep tightening the data. Over-cleaning can remove real "
                 "business signals.",
                 "#FF9800")
            ]
        ))
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # close button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_section(self, title: str, items: list) -> QGroupBox:
        # create help section group box
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        for name, description, color in items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)
            
            # name label
            name_label = QLabel(f"● {name}")
            name_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {color};")
            item_layout.addWidget(name_label)
            
            # description label
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; margin-left: 15px;")
            item_layout.addWidget(desc_label)
            
            layout.addWidget(item_widget)
        
        return group