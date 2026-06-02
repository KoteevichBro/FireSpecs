"""Window decoration: native hints where possible, custom title bar on Linux Wayland."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from app.system_theme import _run_command

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget


def should_use_custom_title_bar() -> bool:
    """Qt on Wayland draws its own title bar; GTK hints do not restyle it."""
    if not sys.platform.startswith("linux"):
        return False
    app = QApplication.instance()
    if app is None:
        return False
    return app.platformName() == "wayland"


def chrome_variant_for_theme(app_theme: str) -> str:
    if app_theme == "light":
        return "light"
    return "dark"


def gtk_theme_name_for_app_theme(app_theme: str) -> str | None:
    """Return a GTK_THEME value for menus/native widgets, or None for OS default."""
    base = _read_gtk_theme_from_desktop()
    if not base:
        return None

    if app_theme == "light":
        if base.endswith("-dark"):
            light_name = base[: -len("-dark")]
            if _gtk_theme_installed(light_name):
                return light_name
        if base.lower().endswith(" dark"):
            light_name = base[: -len(" dark")]
            if _gtk_theme_installed(light_name):
                return light_name
        if ":dark" in base:
            return base.split(":", 1)[0]
        return base

    if "dark" in base.lower():
        return base

    dark_name = f"{base}-dark"
    if _gtk_theme_installed(dark_name):
        return dark_name

    dark_name_spaced = f"{base} Dark"
    if _gtk_theme_installed(dark_name_spaced):
        return dark_name_spaced

    if ":" not in base:
        return f"{base}:dark"
    return base


def _configure_qt_plugin_path() -> None:
    """Point Qt at bundled plugins (AppImage / pip PyQt5) before QApplication."""
    if os.environ.get("QT_PLUGIN_PATH"):
        return
    try:
        import PyQt5
    except ImportError:
        return

    plugins = os.path.join(os.path.dirname(PyQt5.__file__), "Qt5", "plugins")
    if os.path.isdir(plugins):
        os.environ["QT_PLUGIN_PATH"] = plugins


def _configure_qpa_platform() -> None:
    """Use native Wayland when the session is Wayland (avoids Qt X11 warning on GNOME)."""
    if os.environ.get("QT_QPA_PLATFORM"):
        return
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        os.environ["QT_QPA_PLATFORM"] = "wayland"


def configure_linux_qt_platform(app_theme: str | None = None) -> None:
    """Apply Linux/Qt GTK integration before QApplication (menus, dialogs)."""
    if not sys.platform.startswith("linux"):
        return

    _configure_qt_plugin_path()
    _configure_qpa_platform()

    from app.display_scale import configure_qt_hidpi_env

    configure_qt_hidpi_env()

    platform_theme = os.environ.get("QT_QPA_PLATFORMTHEME", "").strip().lower()
    if platform_theme in ("qt5ct", "qt6ct"):
        return

    if not platform_theme:
        os.environ["QT_QPA_PLATFORMTHEME"] = "gtk3"

    if app_theme is None:
        from app.system_theme import resolve_startup_theme
        from app.ui_session import load_ui_session

        session = load_ui_session()
        app_theme = resolve_startup_theme(session.get("theme"))

    gtk_theme = gtk_theme_name_for_app_theme(app_theme)
    if gtk_theme:
        os.environ["GTK_THEME"] = gtk_theme
    else:
        os.environ.pop("GTK_THEME", None)


def apply_native_window_chrome(window: QWidget, app_theme: str) -> None:
    """Update native SSD title bar (X11 and Windows). No-op on Linux Wayland."""
    if should_use_custom_title_bar():
        return

    variant = chrome_variant_for_theme(app_theme)

    if sys.platform.startswith("linux"):
        _apply_gtk_theme_variant(window, variant)
    elif sys.platform == "win32":
        _apply_windows_dark_titlebar(window, variant == "dark")


def setup_window_decorations(main_window) -> None:
    """Enable frameless mode + custom title bar when native chrome cannot follow theme."""
    if not should_use_custom_title_bar():
        return

    flags = main_window.windowFlags()
    main_window.setWindowFlags(flags | Qt.FramelessWindowHint)


def _read_gtk_theme_from_desktop() -> str | None:
    text = _run_command(
        ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]
    )
    if text:
        return text.strip("'\"")

    for command in (
        [
            "kreadconfig6",
            "--file",
            "kdeglobals",
            "--group",
            "General",
            "--key",
            "ColorScheme",
        ],
        [
            "kreadconfig5",
            "--file",
            "kdeglobals",
            "--group",
            "General",
            "--key",
            "ColorScheme",
        ],
    ):
        text = _run_command(command)
        if text:
            return text.strip()

    return None


def _gtk_theme_installed(name: str) -> bool:
    if not name:
        return False
    for root in ("/usr/share/themes", os.path.expanduser("~/.themes")):
        if os.path.isdir(os.path.join(root, name)):
            return True
    return False


def _apply_gtk_theme_variant(window: QWidget, variant: str) -> None:
    window.setProperty("_GTK_THEME_VARIANT", variant)

    handle = window.windowHandle() if hasattr(window, "windowHandle") else None
    if handle is not None:
        handle.setProperty("_GTK_THEME_VARIANT", variant)

    style = window.style()
    if style is not None:
        style.unpolish(window)
        style.polish(window)
    window.update()


def _apply_windows_dark_titlebar(window: QWidget, dark: bool) -> None:
    try:
        import ctypes

        hwnd = int(window.winId())
        attribute = 20
        value = ctypes.c_int(1 if dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            attribute,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except (AttributeError, OSError, ValueError):
        return
