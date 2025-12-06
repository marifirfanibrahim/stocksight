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
        
        # header
        header = QLabel("Understanding Cluster Types")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        # scroll area
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
                 "Top 20% of items by sales volume. These are your most important items "
                 "that typically account for 80% of total sales. They deserve the most "
                 "attention and detailed forecasting.",
                 "#4CAF50"),
                ("B - Medium Volume",
                 "Next 30% of items by sales volume. These items have moderate sales and "
                 "should be monitored regularly but don't need as much individual attention as A-items.",
                 "#FF9800"),
                ("C - Low Volume",
                 "Bottom 50% of items by sales volume. These items have lower sales and "
                 "can often be forecasted in bulk with simpler methods.",
                 "#F44336")
            ]
        ))
        
        # pattern types section
        scroll_layout.addWidget(self._create_section(
            "📈 Pattern Types",
            [
                ("Steady",
                 "Items with consistent, predictable demand. Coefficient of Variation (CV) < 0.3. "
                 "These items are easy to forecast and maintain stable inventory levels.",
                 "#4CAF50"),
                ("Variable",
                 "Items with moderate demand fluctuations. CV between 0.3 and 0.8. "
                 "These items need regular monitoring and may require safety stock adjustments.",
                 "#2196F3"),
                ("Erratic",
                 "Items with highly unpredictable demand. CV > 0.8. "
                 "These items are difficult to forecast and may need special handling, "
                 "such as make-to-order or higher safety stock.",
                 "#FF9800"),
                ("Seasonal",
                 "Items with strong seasonal patterns. Q4 concentration > 60%. "
                 "These items show significant demand spikes during certain periods "
                 "(like holidays) and need seasonal forecasting approaches.",
                 "#9C27B0")
            ]
        ))
        
        # metrics section
        scroll_layout.addWidget(self._create_section(
            "📏 Key Metrics",
            [
                ("CV (Coefficient of Variation)",
                 "Standard deviation divided by mean. Measures relative variability. "
                 "Lower CV means more stable demand.",
                 "#607D8B"),
                ("Q4 Concentration",
                 "Percentage of annual sales occurring in Q4 (Oct-Dec). "
                 "High concentration indicates holiday seasonality.",
                 "#607D8B"),
                ("MAPE (Mean Absolute Percentage Error)",
                 "Average forecast error as a percentage. Lower is better. "
                 "Under 10% is excellent, 10-20% is good, over 30% needs review.",
                 "#607D8B")
            ]
        ))
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_section(self, title: str, items: list) -> QGroupBox:
        # create help section
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        for name, description, color in items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)
            
            # name with color indicator
            name_label = QLabel(f"● {name}")
            name_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {color};")
            item_layout.addWidget(name_label)
            
            # description
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
        
        # header
        header = QLabel("Understanding Forecast Terms")
        header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(header)
        
        # tabs for different sections
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
                 "Uses basic models (Naive, Seasonal Naive, Exponential Smoothing). "
                 "Best for initial analysis or when time is limited. "
                 "Runs on ALL items quickly.",
                 "#2196F3"),
                ("🟡 Smart & Balanced",
                 "Uses advanced statistical models (ARIMA, Prophet, Theta). "
                 "Best balance of accuracy and speed for most business scenarios. "
                 "Recommended for A and B items.",
                 "#FF9800"),
                ("🔴 Advanced AI",
                 "Uses machine learning models (LightGBM, XGBoost, Ensemble). "
                 "Maximum accuracy but slower. "
                 "⚠ ONLY runs on A-items (high volume) automatically.",
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
                 "Uses the most recent value or average as the forecast. "
                 "Simple but effective for stable items.",
                 "#607D8B"),
                ("Seasonal Naive",
                 "Repeats last year's pattern. Good for items with clear yearly cycles.",
                 "#607D8B"),
                ("Exponential Smoothing",
                 "Weights recent data more heavily. Adapts to trends and seasonality.",
                 "#607D8B"),
                ("ARIMA",
                 "Statistical model that captures trends, seasonality, and autocorrelation. "
                 "Good for complex patterns.",
                 "#607D8B"),
                ("Prophet",
                 "Facebook's model designed for business time series. "
                 "Handles holidays and missing data well.",
                 "#607D8B"),
                ("LightGBM / XGBoost",
                 "Machine learning models that learn complex patterns from features. "
                 "Most powerful but requires good data.",
                 "#607D8B"),
                ("Ensemble",
                 "Combines multiple models for more robust forecasts. "
                 "Often more accurate than any single model.",
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
                 "Average error as a percentage of actual values. "
                 "Under 10% = Excellent, 10-20% = Good, 20-30% = Fair, Over 30% = Review needed. "
                 "Lower is better.",
                 "#4CAF50"),
                ("MAE (Mean Absolute Error)",
                 "Average error in the same units as your data (e.g., units sold). "
                 "Easier to interpret than MAPE for low-volume items.",
                 "#2196F3"),
                ("RMSE (Root Mean Square Error)",
                 "Similar to MAE but penalizes large errors more. "
                 "Good for detecting occasional big misses.",
                 "#9C27B0"),
                ("Confidence Interval",
                 "Range where actual values are likely to fall (e.g., 95% confidence). "
                 "Wider interval = more uncertainty.",
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
                 "Day-by-day forecasts. Best for short-term planning and high-volume items. "
                 "More detail but also more variability.",
                 "#4CAF50"),
                ("Weekly",
                 "Week-by-week forecasts. Good balance for most planning needs. "
                 "Smooths out daily noise while maintaining detail.",
                 "#2196F3"),
                ("Monthly",
                 "Month-by-month forecasts. Best for longer-term planning and reporting. "
                 "Less detail but more stable forecasts.",
                 "#9C27B0")
            ]
        ))
        freq_content_layout.addStretch()
        freq_scroll.setWidget(freq_content)
        freq_layout.addWidget(freq_scroll)
        tabs.addTab(freq_widget, "Frequency")
        
        layout.addWidget(tabs)
        
        # close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_section(self, title: str, items: list) -> QGroupBox:
        # create help section
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        for name, description, color in items:
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(4)
            
            # name with color indicator
            name_label = QLabel(f"● {name}")
            name_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            name_label.setStyleSheet(f"color: {color};")
            item_layout.addWidget(name_label)
            
            # description
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #555; margin-left: 15px;")
            item_layout.addWidget(desc_label)
            
            layout.addWidget(item_widget)
        
        return group