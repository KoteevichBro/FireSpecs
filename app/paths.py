"""Application path helpers for dev, pip, deb, and frozen installs."""

import os
import sys


def get_base_path():
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        return "/opt/firespecs"

    appdir = os.environ.get("APPDIR")
    if appdir:
        share = os.path.join(appdir, "usr", "share", "firespecs")
        if os.path.isdir(share):
            return share
        if os.path.isdir(os.path.join(appdir, "icons")):
            return appdir

    share = "/usr/share/firespecs"
    if os.path.isfile(os.path.join(share, "firespecs.py")):
        return share

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_icon_path(*parts):
    return os.path.join(get_base_path(), "icons", *parts)
