"""Detect the desktop environment's preferred light/dark appearance."""

from __future__ import annotations

import os
import re
import subprocess
from typing import Callable, Literal

ThemeMode = Literal["dark", "light"]

_DETECTORS: tuple[Callable[[], ThemeMode | None], ...] = ()


def detect_preferred_theme() -> ThemeMode:
    """Return ``dark`` or ``light`` based on OS/desktop settings."""
    for detector in _DETECTORS:
        theme = detector()
        if theme is not None:
            return theme
    return "dark"


def resolve_startup_theme(session_theme: str | None) -> str:
    """Map session preference to a concrete theme name for startup."""
    preference = (session_theme or "system").strip().lower()
    if preference in ("dark", "light", "matrix"):
        return preference
    return detect_preferred_theme()


def _run_command(args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    output = (proc.stdout or "").strip()
    return output or None


def _from_freedesktop_portal() -> ThemeMode | None:
    text = _run_command(
        [
            "dbus-send",
            "--session",
            "--print-reply=literal",
            "--dest=org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Settings",
            "Read",
            "string:org.freedesktop.appearance",
            "string:color-scheme",
        ]
    )
    if not text:
        return None
    match = re.search(r"uint32\s+(\d+)", text)
    if not match:
        return None
    value = int(match.group(1))
    if value == 1:
        return "dark"
    if value == 2:
        return "light"
    return None


def _from_gnome_color_scheme() -> ThemeMode | None:
    text = _run_command(
        ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"]
    )
    if not text:
        return None
    lowered = text.strip("'\"").lower()
    if "dark" in lowered:
        return "dark"
    if "light" in lowered:
        return "light"
    return None


def _from_gnome_gtk_theme() -> ThemeMode | None:
    text = _run_command(
        ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]
    )
    if not text:
        return None
    name = text.strip("'\"").lower()
    if "dark" in name:
        return "dark"
    if name:
        return "light"
    return None


def _from_kde_color_scheme() -> ThemeMode | None:
    for command in (
        ["kreadconfig6", "--file", "kdeglobals", "--group", "General", "--key", "ColorScheme"],
        ["kreadconfig5", "--file", "kdeglobals", "--group", "General", "--key", "ColorScheme"],
    ):
        text = _run_command(command)
        if not text:
            continue
        name = text.lower()
        if "dark" in name:
            return "dark"
        return "light"
    return None


def _from_env() -> ThemeMode | None:
    gtk_theme = os.environ.get("GTK_THEME", "").strip().lower()
    if not gtk_theme:
        return None
    if "dark" in gtk_theme:
        return "dark"
    return "light"


_DETECTORS = (
    _from_freedesktop_portal,
    _from_gnome_color_scheme,
    _from_gnome_gtk_theme,
    _from_kde_color_scheme,
    _from_env,
)
