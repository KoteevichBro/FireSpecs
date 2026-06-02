"""
Window geometry persistence for FireSpecs.

The session file only remembers the window's last size and position so the app
reopens where the user left it. No display-scaling state is stored: the GUI
always runs as the desktop user, so the compositor handles scaling natively.
"""

import json
import os
import pwd
import tempfile

SESSION_VERSION = 5
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 800
DEFAULT_X = 100
DEFAULT_Y = 100


def _desktop_uid():
    for key in ("SUDO_UID", "PKEXEC_UID"):
        value = os.environ.get(key)
        if value and value.isdigit() and int(value) > 0:
            return int(value)
    return os.getuid()


def _config_session_path(uid):
    try:
        home = pwd.getpwuid(uid).pw_dir
    except KeyError:
        return None
    return os.path.join(home, ".config", "firespecs", "ui_session.json")


def get_session_paths():
    """Candidate session files, most volatile first."""
    uid = _desktop_uid()
    paths = [f"/tmp/firespecs-{uid}-ui_session.json"]
    config = _config_session_path(uid)
    if config:
        paths.append(config)
    return paths


def get_session_path():
    return get_session_paths()[0]


def _default_session():
    return {
        "version": SESSION_VERSION,
        "window_width": DEFAULT_WIDTH,
        "window_height": DEFAULT_HEIGHT,
        "window_x": DEFAULT_X,
        "window_y": DEFAULT_Y,
        "language": "en",
        "theme": "system",
    }


def session_file_exists():
    return any(os.path.isfile(path) for path in get_session_paths())


def load_ui_session():
    for path in get_session_paths():
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict):
            return {**_default_session(), **data}
    return _default_session()


def _write_session_file(path, payload):
    directory = os.path.dirname(path)
    os.makedirs(directory, mode=0o755, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".session-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def save_ui_session(session):
    payload = {**_default_session(), **session, "version": SESSION_VERSION}
    for path in get_session_paths():
        try:
            _write_session_file(path, payload)
        except OSError:
            continue


def capture_session_from_window(window):
    session = load_ui_session()
    geom = window.geometry()
    session["window_width"] = int(geom.width())
    session["window_height"] = int(geom.height())
    session["window_x"] = int(geom.x())
    session["window_y"] = int(geom.y())
    save_ui_session(session)
    return session


def resolve_window_geometry():
    session = load_ui_session()
    return (
        int(session.get("window_x", DEFAULT_X)),
        int(session.get("window_y", DEFAULT_Y)),
        max(800, int(session.get("window_width", DEFAULT_WIDTH))),
        max(600, int(session.get("window_height", DEFAULT_HEIGHT))),
    )
