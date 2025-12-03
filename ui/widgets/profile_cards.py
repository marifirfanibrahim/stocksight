"""
profile summary cards
display data quality metrics
"""


# ================ IMPORTS ================

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QGridLayout, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from typing import Dict, List, Optional


# ================ PROFILE CARD ================

class ProfileCard(QFrame):
    """
    single profile metric card
    """
    
    clicked = pyqtSignal(str)
    
    def __init__(
        self,
        title: str,
        value: str = "--",
        subtitle: str = "",
        color: str = None,
        parent=None
    ):
        super().__init__(parent)
        
        self._title = title
        self._value = value
        self._subtitle = subtitle
        self._color = color
        
        self._create_ui()
    
    def _create_ui(self):
        """
        create card ui
        """
        self.setProperty("card", True)
        self.setStyleSheet("""
            QFrame[card="true"] {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 12px;
            }
            QFrame[card="true"]:hover {
                border-color: #0078d4;
            }
        """)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        # title
        self.lbl_title = QLabel(self._title)
        self.lbl_title.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.lbl_title)
        
        # value
        self.lbl_value = QLabel(self._value)
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        self.lbl_value.setFont(font)
        
        if self._color:
            self.lbl_value.setStyleSheet(f"color: {self._color};")
        
        layout.addWidget(self.lbl_value)
        
        # subtitle
        if self._subtitle:
            self.lbl_subtitle = QLabel(self._subtitle)
            self.lbl_subtitle.setStyleSheet("color: gray; font-size: 10px;")
            layout.addWidget(self.lbl_subtitle)
    
    def set_value(self, value: str, color: str = None):
        """
        set card value
        """
        self._value = value
        self.lbl_value.setText(value)
        
        if color:
            self._color = color
            self.lbl_value.setStyleSheet(f"color: {color};")
    
    def set_subtitle(self, subtitle: str):
        """
        set card subtitle
        """
        self._subtitle = subtitle
        if hasattr(self, 'lbl_subtitle'):
            self.lbl_subtitle.setText(subtitle)
    
    def mousePressEvent(self, event):
        """
        handle click
        """
        self.clicked.emit(self._title)
        super().mousePressEvent(event)


# ================ PROGRESS CARD ================

class ProgressCard(QFrame):
    """
    card with progress bar
    """
    
    def __init__(
        self,
        title: str,
        value: float = 0,
        max_value: float = 100,
        suffix: str = "%",
        parent=None
    ):
        super().__init__(parent)
        
        self._title = title
        self._value = value
        self._max_value = max_value
        self._suffix = suffix
        
        self._create_ui()
    
    def _create_ui(self):
        """
        create card ui
        """
        self.setProperty("card", True)
        self.setStyleSheet("""
            QFrame[card="true"] {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # header
        header = QHBoxLayout()
        
        self.lbl_title = QLabel(self._title)
        self.lbl_title.setStyleSheet("color: gray; font-size: 11px;")
        header.addWidget(self.lbl_title)
        
        header.addStretch()
        
        self.lbl_value = QLabel(f"{self._value:.1f}{self._suffix}")
        self.lbl_value.setStyleSheet("font-weight: bold;")
        header.addWidget(self.lbl_value)
        
        layout.addLayout(header)
        
        # progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, int(self._max_value))
        self.progress.setValue(int(self._value))
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        layout.addWidget(self.progress)
    
    def set_value(self, value: float):
        """
        set progress value
        """
        self._value = value
        self.lbl_value.setText(f"{value:.1f}{self._suffix}")
        self.progress.setValue(int(value))
        
        # color based on value
        if value >= 80:
            color = "#4caf50"
        elif value >= 60:
            color = "#ff9800"
        else:
            color = "#f44336"
        
        self.progress.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)


# ================ PROFILE CARDS PANEL ================

class ProfileCardsPanel(QWidget):
    """
    panel containing multiple profile cards
    """
    
    card_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._cards = {}
        self._create_ui()
    
    def _create_ui(self):
        """
        create panel ui
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # content widget
        content = QWidget()
        self.grid_layout = QGridLayout(content)
        self.grid_layout.setSpacing(10)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def add_card(
        self,
        key: str,
        title: str,
        value: str = "--",
        subtitle: str = "",
        color: str = None,
        row: int = None,
        col: int = None
    ) -> ProfileCard:
        """
        add a profile card
        """
        card = ProfileCard(title, value, subtitle, color)
        card.clicked.connect(lambda t: self.card_clicked.emit(key))
        
        self._cards[key] = card
        
        # auto position if not specified
        if row is None or col is None:
            count = len(self._cards) - 1
            row = count // 3
            col = count % 3
        
        self.grid_layout.addWidget(card, row, col)
        
        return card
    
    def add_progress_card(
        self,
        key: str,
        title: str,
        value: float = 0,
        max_value: float = 100,
        suffix: str = "%",
        row: int = None,
        col: int = None
    ) -> ProgressCard:
        """
        add a progress card
        """
        card = ProgressCard(title, value, max_value, suffix)
        
        self._cards[key] = card
        
        # auto position if not specified
        if row is None or col is None:
            count = len(self._cards) - 1
            row = count // 3
            col = count % 3
        
        self.grid_layout.addWidget(card, row, col)
        
        return card
    
    def update_card(self, key: str, value: str, subtitle: str = None, color: str = None):
        """
        update card value
        """
        if key in self._cards:
            card = self._cards[key]
            
            if isinstance(card, ProfileCard):
                card.set_value(value, color)
                if subtitle:
                    card.set_subtitle(subtitle)
            elif isinstance(card, ProgressCard):
                card.set_value(float(value))
    
    def get_card(self, key: str) -> Optional[QFrame]:
        """
        get card by key
        """
        return self._cards.get(key)
    
    def clear(self):
        """
        clear all cards
        """
        for card in self._cards.values():
            card.deleteLater()
        
        self._cards = {}
    
    def set_from_summary(self, summary: Dict):
        """
        populate cards from summary dict
        """
        self.clear()
        
        # table stats
        if 'table' in summary:
            table = summary['table']
            
            self.add_card('rows', 'Total Rows', f"{table.get('rows', 0):,}")
            self.add_card('columns', 'Columns', f"{table.get('columns', 0)}")
            
            self.add_progress_card(
                'missing',
                'Missing Values',
                table.get('missing_pct', 0),
                100,
                '%'
            )
            
            self.add_progress_card(
                'duplicates',
                'Duplicates',
                table.get('duplicate_pct', 0),
                100,
                '%'
            )