"""Client-side window title bar (Linux Wayland / Qt without native dark decorations)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt5.QtCore import QPoint, Qt, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

if TYPE_CHECKING:
    from PyQt5.QtGui import QIcon
    from PyQt5.QtWidgets import QMainWindow, QWidget as QWidgetType


class CustomTitleBar(QWidget):
    """In-window title bar: icon, title, minimize, maximize, close."""

    HEIGHT = 36

    def __init__(self, window: QWidgetType, *, dialog_mode: bool = False):
        super().__init__(window)
        self._window = window
        self._dialog_mode = dialog_mode
        self._drag_offset: QPoint | None = None

        self.setObjectName("custom_title_bar")
        self.setFixedHeight(self.HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(6)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setScaledContents(True)
        layout.addWidget(self.icon_label, 0, Qt.AlignVCenter)

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 10))
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.title_label, 1, Qt.AlignVCenter)

        self.min_btn = self._make_chrome_button("—", "title_bar_minimize")
        self.max_btn = self._make_chrome_button("□", "title_bar_maximize")
        self.close_btn = self._make_chrome_button("×", "title_bar_close")

        if dialog_mode:
            self.min_btn.hide()
            self.max_btn.hide()
            self.close_btn.clicked.connect(self._close_window)
        else:
            self.min_btn.clicked.connect(self._window.showMinimized)
            self.max_btn.clicked.connect(self._toggle_maximize)
            self.close_btn.clicked.connect(self._close_window)

        layout.addWidget(self.min_btn, 0, Qt.AlignVCenter)
        layout.addWidget(self.max_btn, 0, Qt.AlignVCenter)
        layout.addWidget(self.close_btn, 0, Qt.AlignVCenter)

        self._sync_window_icon()

    def _make_chrome_button(self, label: str, object_name: str) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName(object_name)
        button.setFixedSize(40, self.HEIGHT)
        button.setFlat(True)
        button.setFont(QFont("Arial", 12))
        return button

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)
        self._window.setWindowTitle(text)

    def set_window_icon(self, icon: QIcon) -> None:
        if icon is not None and not icon.isNull():
            pixmap = icon.pixmap(QSize(20, 20))
            if not pixmap.isNull():
                self.icon_label.setPixmap(pixmap)
                return
        self.icon_label.clear()

    def _sync_window_icon(self) -> None:
        icon = self._window.windowIcon()
        if icon is not None and not icon.isNull():
            self.set_window_icon(icon)

    def apply_theme(self, theme: dict, font_family: str = "Arial") -> None:
        background = theme["header"]
        text = theme["text_primary"]
        hover = theme["background_hover"]
        pressed = theme["background_secondary"]
        close_hover = "#e81123"
        close_pressed = "#bf0f1d"

        self.setStyleSheet(
            f"""
            QWidget#custom_title_bar {{
                background-color: {background};
                border-bottom: 1px solid {theme["border"]};
            }}
            QLabel {{
                color: {text};
                background: transparent;
                font-family: {font_family};
            }}
            QPushButton {{
                color: {text};
                background: transparent;
                border: none;
                font-family: {font_family};
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
            QPushButton#title_bar_close:hover {{
                background-color: {close_hover};
                color: #ffffff;
            }}
            QPushButton#title_bar_close:pressed {{
                background-color: {close_pressed};
                color: #ffffff;
            }}
            """
        )
        self.title_label.setFont(QFont(font_family, 10))

    def _close_window(self) -> None:
        if isinstance(self._window, QDialog):
            self._window.reject()
        else:
            self._window.close()

    def _toggle_maximize(self) -> None:
        if self._dialog_mode:
            return
        if self._window.isMaximized():
            self._window.showNormal()
            self.max_btn.setText("□")
        else:
            self._window.showMaximized()
            self.max_btn.setText("❐")

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)

        handle = self._window.windowHandle()
        if handle is not None and hasattr(handle, "startSystemMove"):
            handle.startSystemMove()
            event.accept()
            return

        if self._window.isMaximized():
            self._window.showNormal()
        self._drag_offset = event.globalPos() - self._window.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is None or not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)
        self._window.move(event.globalPos() - self._drag_offset)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not self._dialog_mode and event.button() == Qt.LeftButton:
            self._toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)
