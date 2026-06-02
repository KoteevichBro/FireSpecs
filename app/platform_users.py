"""Helpers for resolving the desktop user when the app runs as root."""

import os
import pwd


def get_desktop_username():
    """
    Return the username of the interactive desktop session, or None.
    Works when FireSpecs is started via pkexec/sudo.
    """
    for key in ("SUDO_USER", "PKEXEC_UID"):
        value = os.environ.get(key)
        if not value:
            continue
        if key == "PKEXEC_UID":
            try:
                return pwd.getpwuid(int(value)).pw_name
            except (ValueError, KeyError, TypeError):
                continue
        if value != "root":
            return value

    try:
        return pwd.getpwuid(1000).pw_name
    except KeyError:
        pass

    for entry in pwd.getpwall():
        if entry.pw_uid >= 1000 and entry.pw_dir.startswith("/home"):
            return entry.pw_name

    return None


def get_desktop_env(extra_display=True):
    """Environment dict for launching GUI apps as the desktop user."""
    username = get_desktop_username()
    env = os.environ.copy()

    if username:
        try:
            pw = pwd.getpwnam(username)
            env["HOME"] = pw.pw_dir
            env["USER"] = username
            env["LOGNAME"] = username
        except KeyError:
            pass

    if extra_display:
        env.setdefault("DISPLAY", ":0")
        for key in ("XAUTHORITY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "DBUS_SESSION_BUS_ADDRESS"):
            if key in os.environ:
                env[key] = os.environ[key]

    return env, username
