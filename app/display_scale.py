"""HiDPI / desktop scale detection (especially for bundled AppImage Qt).

Footer/graph sizes use ``scaled()`` with ``ui_scale``; that factor stays at 1.0
because Qt handles display scaling. Only ``configure_qt_hidpi_env()`` adjusts Qt env.
"""

from __future__ import annotations

import os
import re
import sys

from app.system_theme import _run_command


def scaled(value, scale=1.0):
    return int(round(value * scale))


def is_bundled_pyqt_runtime() -> bool:
    if os.environ.get("APPIMAGE") or os.environ.get("APPDIR"):
        return True
    try:
        import PyQt5
    except ImportError:
        return False
    return "site-packages" in os.path.dirname(PyQt5.__file__)


def _gnome_primary_monitor_scale() -> float | None:
    raw = _run_command(
        [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.gnome.Mutter.DisplayConfig",
            "--object-path",
            "/org/gnome/Mutter/DisplayConfig",
            "--method",
            "org.gnome.Mutter.DisplayConfig.GetCurrentState",
        ]
    )
    if not raw:
        return None

    match = re.search(
        r"\(\s*-?\d+\s*,\s*-?\d+\s*,\s*([\d.]+)\s*,\s*uint32\s+\d+\s*,\s*true",
        raw,
        re.IGNORECASE,
    )
    if match:
        return float(match.group(1))

    match = re.search(r"\(\s*-?\d+\s*,\s*-?\d+\s*,\s*([\d.]+)\s*,", raw)
    if match:
        return float(match.group(1))
    return None


def desktop_ui_scale_factor() -> float:
    """Combine session env, GNOME text scale, and primary monitor scale."""
    for key in ("QT_SCALE_FACTOR", "GDK_SCALE"):
        value = os.environ.get(key)
        if value:
            try:
                factor = float(value)
                if factor > 0:
                    return factor
            except ValueError:
                pass

    text_scale = 1.0
    text = _run_command(
        ["gsettings", "get", "org.gnome.desktop.interface", "text-scaling-factor"]
    )
    if text:
        try:
            parsed = float(text.strip())
            if parsed > 0:
                text_scale = parsed
        except ValueError:
            pass

    monitor_scale = _gnome_primary_monitor_scale()
    if monitor_scale and monitor_scale > 0:
        return text_scale * monitor_scale
    return text_scale


def configure_qt_hidpi_env() -> None:
    """Apply Qt HiDPI env vars before QApplication (required for AppImage)."""
    if not sys.platform.startswith("linux"):
        return

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    if os.environ.get("QT_SCALE_FACTOR"):
        return

    if not is_bundled_pyqt_runtime():
        return

    # On native Wayland, Qt reads monitor scale from the compositor.
    platform = os.environ.get("QT_QPA_PLATFORM", "")
    if platform.startswith("wayland") or (
        not platform
        and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    ):
        return

    factor = desktop_ui_scale_factor()
    if factor > 1.01:
        os.environ["QT_SCALE_FACTOR"] = f"{factor:g}"


def resolve_ui_scale(app=None) -> float:
    """Layout scale for footer/graphs.

    Always 1.0: Qt HiDPI (``configure_qt_hidpi_env``) already scales the window.
    Multiplying sizes here again would make graphs and footer huge on HiDPI displays.
    """
    return 1.0
