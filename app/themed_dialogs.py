"""Themed message and dialog windows matching the main window chrome.

Use ``information``, ``warning``, ``question``, or ``show_about`` for standard
prompts. Subclass ``ThemedDialog`` for new dialogs so they pick up the same
title bar, border, and palette automatically.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.custom_title_bar import CustomTitleBar
from app.paths import get_base_path
from app.window_chrome import should_use_custom_title_bar

if TYPE_CHECKING:
    from app.ui import FireSpecsWindow


def information(parent: FireSpecsWindow, title: str, text: str) -> None:
    if should_use_custom_title_bar():
        ThemedMessageDialog(parent, title, text, buttons=QMessageBox.Ok).exec_()
    else:
        QMessageBox.information(parent, title, text)


def warning(parent: FireSpecsWindow, title: str, text: str) -> None:
    if should_use_custom_title_bar():
        ThemedMessageDialog(parent, title, text, buttons=QMessageBox.Ok).exec_()
    else:
        QMessageBox.warning(parent, title, text)


def question(parent: FireSpecsWindow, title: str, text: str) -> int:
    if should_use_custom_title_bar():
        dialog = ThemedMessageDialog(
            parent,
            title,
            text,
            buttons=QMessageBox.Yes | QMessageBox.No,
        )
        dialog.exec_()
        return dialog.result_role()
    return QMessageBox.question(
        parent,
        title,
        text,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )


def show_about(parent: FireSpecsWindow) -> None:
    if should_use_custom_title_bar():
        ThemedAboutDialog(parent).exec_()
    else:
        _show_about_native(parent)


def resolve_window_theme(parent: FireSpecsWindow) -> tuple[dict, str]:
    from app.ui import ThemeManager

    theme_name = getattr(parent, "current_theme", "dark")
    if theme_name == "light":
        return ThemeManager.LIGHT, "Arial"
    if theme_name == "matrix":
        return ThemeManager.MATRIX, "monospace"
    return ThemeManager.DARK, "Arial"


class ThemedDialog(QDialog):
    """Base dialog with custom title bar (Wayland) and themed border."""

    def __init__(self, parent: FireSpecsWindow, title: str):
        super().__init__(parent)
        self._main_window = parent
        self._theme, self._font_family = resolve_window_theme(parent)
        self._result = QMessageBox.No

        self.setModal(True)
        if should_use_custom_title_bar():
            self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
            self.title_bar = CustomTitleBar(self, dialog_mode=True)
            self.title_bar.set_title(title)
            icon = parent.windowIcon()
            if icon is not None and not icon.isNull():
                self.title_bar.set_window_icon(icon)
        else:
            self.title_bar = None
            self.setWindowTitle(title)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        if self.title_bar is not None:
            root.addWidget(self.title_bar)

        self.content_host = QWidget()
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(20, 16, 20, 16)
        self.content_layout.setSpacing(12)
        root.addWidget(self.content_host, 1)

        self.button_bar = QWidget()
        self.button_layout = QHBoxLayout(self.button_bar)
        self.button_layout.setContentsMargins(20, 0, 20, 16)
        self.button_layout.setSpacing(8)
        self.button_layout.addStretch(1)
        root.addWidget(self.button_bar)

        self._apply_chrome()

    def add_button(
        self,
        label: str,
        role: int,
        *,
        default: bool = False,
    ) -> QPushButton:
        button = QPushButton(label)
        if default:
            button.setDefault(True)
            button.setAutoDefault(True)
        button.clicked.connect(lambda _checked=False, r=role: self._finish(r))
        self.button_layout.addWidget(button)
        return button

    def _finish(self, role: int) -> None:
        self._result = role
        self.accept()

    def result_role(self) -> int:
        return self._result

    def _apply_chrome(self) -> None:
        theme = self._theme
        font = self._font_family

        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {theme["background_main"]};
                border: 1px solid {theme["border"]};
            }}
            QWidget {{
                color: {theme["text_primary"]};
                font-family: {font};
            }}
            QLabel {{
                color: {theme["text_primary"]};
                background: transparent;
            }}
            QPushButton {{
                background-color: {theme["button"]};
                color: {theme["text_primary"]};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 72px;
                font-family: {font};
            }}
            QPushButton:hover {{
                background-color: {theme["button_hover"]};
            }}
            QPushButton:pressed {{
                background-color: {theme["button_pressed"]};
            }}
            """
        )
        if self.title_bar is not None:
            self.title_bar.apply_theme(theme, font)


class ThemedMessageDialog(ThemedDialog):
    """Information, warning, or Yes/No question dialog."""

    def __init__(
        self,
        parent: FireSpecsWindow,
        title: str,
        text: str,
        *,
        rich_text: bool = False,
        buttons: int = QMessageBox.Ok,
    ):
        super().__init__(parent, title)
        self.setMinimumWidth(420)

        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Preferred
        )
        if rich_text:
            self.message_label.setTextFormat(Qt.RichText)
            self.message_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        else:
            self.message_label.setTextFormat(Qt.PlainText)
        self.message_label.setText(text)
        self.content_layout.addWidget(self.message_label)

        if buttons & QMessageBox.Yes:
            self.add_button(
                parent.tr("dialog.yes"),
                QMessageBox.Yes,
                default=True,
            )
        if buttons & QMessageBox.No:
            self.add_button(parent.tr("dialog.no"), QMessageBox.No)
        if buttons & QMessageBox.Ok:
            self.add_button(
                parent.tr("dialog.ok"),
                QMessageBox.Ok,
                default=not (buttons & QMessageBox.Yes),
            )


class ThemedAboutDialog(ThemedDialog):
    """About dialog with logo and rich text."""

    def __init__(self, parent: FireSpecsWindow):
        super().__init__(parent, parent.tr("about.title"))
        self.setMinimumWidth(460)

        theme = self._theme
        icon_path = os.path.join(get_base_path(), "icons", "logo.png")

        body = QHBoxLayout()
        body.setSpacing(20)

        if os.path.exists(icon_path):
            logo = QLabel()
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                logo.setPixmap(
                    pixmap.scaled(
                        96,
                        96,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
            logo.setAlignment(Qt.AlignTop)
            body.addWidget(logo, 0, Qt.AlignTop)

        about_text = f"""
        <center>
        <h2 style='color: {theme["text_primary"]};'>{parent.tr("about.heading")}</h2>
        <p style='color: {theme["text_primary"]};'>{parent.tr("about.description")}</p>
        <p style='color: {theme["text_primary"]};'>{parent.tr("about.copyright")}</p>
        <br>
        <a href='https://firespecs.sourceforge.io/' style='color: {theme["accent"]};'>
        https://firespecs.sourceforge.io/</a>
        </center>
        """

        text_label = QLabel(about_text)
        text_label.setTextFormat(Qt.RichText)
        text_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        text_label.setWordWrap(True)
        text_label.setOpenExternalLinks(True)
        body.addWidget(text_label, 1)

        self.content_layout.addLayout(body)
        self.add_button(parent.tr("dialog.ok"), QMessageBox.Ok, default=True)


def _show_about_native(parent: FireSpecsWindow) -> None:
    theme, _font = resolve_window_theme(parent)
    icon_path = os.path.join(get_base_path(), "icons", "logo.png")

    msg = QMessageBox(parent)
    msg.setWindowTitle(parent.tr("about.title"))
    msg.setTextFormat(Qt.RichText)
    msg.setWindowIcon(QIcon(icon_path))
    msg.setIconPixmap(QPixmap(icon_path))
    msg.setStyleSheet(
        f"""
        QMessageBox {{
            background-color: {theme["background_main"]};
            border: 1px solid {theme["border"]};
        }}
        QMessageBox QLabel {{
            color: {theme["text_primary"]};
        }}
        QMessageBox QPushButton {{
            background-color: {theme["button"]};
            color: {theme["text_primary"]};
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            min-width: 60px;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {theme["button_hover"]};
        }}
        """
    )

    about_text = f"""
    <center>
    <h2 style='color: {theme["text_primary"]};'>{parent.tr("about.heading")}</h2>
    <p style='color: {theme["text_primary"]};'>{parent.tr("about.description")}</p>
    <p style='color: {theme["text_primary"]};'>{parent.tr("about.copyright")}</p>
    <br>
    <a href='https://firespecs.sourceforge.io/' style='color: {theme["accent"]};'>
    https://firespecs.sourceforge.io/</a>
    </center>
    """
    msg.setText(about_text)
    msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()
