"""
Map dialog — displays bundled game maps with category tabs.

Replicates the MapDialog observed in LegendOnline.exe strings.
"""

import logging
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QScrollArea,
    QWidget,
    QComboBox,
)

from .config import MAPS_DIR, MAP_CATEGORIES

log = logging.getLogger("maps")


class MapDialog(QDialog):
    """Map viewer with category tabs, matching original MapDialog behavior."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mapka (courtesy of DimensionHelper)")
        self.resize(800, 700)

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        for category, numbers in MAP_CATEGORIES.items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)

            selector = QComboBox()
            for n in numbers:
                selector.addItem(f"{category} Map {n}", n)
            tab_layout.addWidget(selector)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            scroll.setWidget(img_label)
            tab_layout.addWidget(scroll)

            selector.currentIndexChanged.connect(
                lambda idx, cat=category, sel=selector, lbl=img_label:
                    self._load_map(cat, sel.itemData(idx), lbl)
            )

            label_name = "Basic" if category == "Basic" else (
                "Advanced-Intermediate" if category == "Advanced-Intermediate" else "Expert"
            )
            self._tabs.addTab(tab, label_name)

            # Load first map
            if numbers:
                self._load_map(category, numbers[0], img_label)

    def _load_map(self, category: str, number: int, label: QLabel):
        filename = f"{category}Map{number}.jpg"
        path = MAPS_DIR / filename
        if path.exists():
            pixmap = QPixmap(str(path))
            label.setPixmap(pixmap)
        else:
            label.setText(f"Map not found: {filename}")
            log.warning("Missing map: %s", path)
