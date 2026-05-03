"""
Aria — clean black/white UI theme with rounded borders.
"""

# Login dialog styling
LOGIN_STYLE = """
* {
    font-family: 'Segoe UI', 'Noto Sans', sans-serif;
}
QLabel, QCheckBox, QLineEdit, QComboBox, QCheckBox::indicator,
QComboBox QAbstractItemView, QAbstractItemView
{
    color: #e0e0e0;
    font-size: 13px;
}
#dialogTitle {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
}
#statusLabel {
    color: #999999;
    font-size: 12px;
}
#statusLabel[error="true"] {
    color: #ff5555;
}
QLineEdit,
QComboBox,
QComboBox QAbstractItemView, QAbstractItemView
{
    background-color: #1e1e1e;
    border: 1px solid #444444;
    border-radius: 8px;
    padding: 6px 10px;
    color: #e0e0e0;
    selection-background-color: #3a3a3a;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #888888;
    color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #444444;
    border-radius: 8px;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 4px 10px;
    min-height: 24px;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #333333;
    color: #ffffff;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QScrollBar:vertical {
    border: none;
    background: #0d0d0d;
    width: 10px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #444444;
    min-height: 24px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #666666;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    height: 0;
}
QPushButton {
    background-color: #ffffff;
    color: #0d0d0d;
    text-transform: uppercase;
    text-align: center;
    min-width: 120px;
    height: 38px;
    border: none;
    border-radius: 10px;
    font-weight: bold;
    font-size: 13px;
    padding: 6px 20px;
}
QPushButton:hover {
    background-color: #d0d0d0;
}
QPushButton:pressed {
    background-color: #b0b0b0;
}
QPushButton:disabled {
    background-color: #333333;
    color: #666666;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #555555;
    border-radius: 4px;
    background: #1e1e1e;
}
QCheckBox::indicator:checked {
    background: #ffffff;
}
QCheckBox:disabled { color: #555; }
QDialog {
    background-color: #0d0d0d;
    border: 1px solid #333333;
    border-radius: 12px;
}
QGroupBox {
    margin-top: 2ex;
    border: 1px solid #444444;
    border-radius: 8px;
}
QGroupBox::title {
    color: #e0e0e0;
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 6px;
    background: #0d0d0d;
}
"""

# Main game window styling
GAME_WINDOW_STYLE = """
* {
    font-family: 'Segoe UI', 'Noto Sans', sans-serif;
}
QMainWindow {
    background-color: #0d0d0d;
}
#centralWidget {
    background-color: #0d0d0d;
}
QMenuBar {
    background-color: #141414;
    color: #cccccc;
    spacing: 0;
    border-bottom: 1px solid #2a2a2a;
    font-size: 12px;
}
QMenuBar::item {
    spacing: 2px;
    padding: 5px 10px;
    background: transparent;
    border-radius: 6px;
}
QMenuBar::item:selected {
    background-color: #2a2a2a;
}
QMenu {
    background-color: #1a1a1a;
    border: 1px solid #333333;
    border-radius: 8px;
    color: #cccccc;
    padding: 4px;
}
QMenu::item {
    padding: 5px 24px 5px 16px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #2a2a2a;
    color: #ffffff;
}
QStatusBar {
    background-color: #0d0d0d;
    color: #888888;
    border-top: 1px solid #2a2a2a;
    font-size: 11px;
}
QMessageBox {
    background-color: #1a1a1a;
    color: #e0e0e0;
}
QMessageBox QPushButton {
    min-width: 80px;
    height: 32px;
}
"""
