"""
In-place privilege escalation for FireSpecs.

The GUI always runs as the desktop user, so its scaling, fonts and theme are
always correct — there is never a second root window to keep in sync. When an
administrative action is needed, a small root worker is started once via pkexec
(one password prompt per session) and reused for every privileged request.

If the application itself happens to run as root (e.g. ``sudo ./run.sh``), the
actions are executed directly in-process and no helper is spawned.
"""

import json
import os
import subprocess
import sys

from app.paths import get_base_path


def _helper_command():
    appimage = os.environ.get("APPIMAGE")
    if appimage and os.path.isfile(appimage):
        return ["pkexec", appimage, "--privileged-helper"]

    if os.path.isfile("/usr/bin/firespecs"):
        return ["pkexec", "/usr/bin/firespecs", "--privileged-helper"]

    script = os.path.join(get_base_path(), "firespecs.py")
    python = sys.executable or "python3"
    return ["pkexec", python, script, "--privileged-helper"]


class PrivilegeManager:
    """Owns the lifecycle of the root worker and routes privileged actions."""

    def __init__(self):
        self._proc = None

    @property
    def active(self):
        if os.geteuid() == 0:
            return True
        return self._proc is not None and self._proc.poll() is None

    def unlock(self):
        """Start the root worker (prompts for a password). Returns (ok, message)."""
        if self.active:
            return True, "Full access is already enabled"
        try:
            self._proc = subprocess.Popen(
                _helper_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            self._proc = None
            return False, f"Could not start privileged helper: {exc}"

        ok, message, _data = self._request({"action": "ping"})
        if not ok:
            self.lock()
            return False, message or "Authentication failed or cancelled"
        return True, "Full access enabled"

    def lock(self):
        """Stop the root worker, dropping privileges for the session."""
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None and proc.stdin:
                proc.stdin.write(json.dumps({"action": "quit"}) + "\n")
                proc.stdin.flush()
        except (OSError, ValueError):
            pass
        try:
            proc.terminate()
        except OSError:
            pass

    def delete_path(self, path):
        if os.geteuid() == 0:
            from app.privileged_helper import do_delete

            return do_delete(path)
        ok, message, _data = self._request({"action": "delete", "path": path})
        return ok, message

    def detach_usb(self, bus, device):
        if os.geteuid() == 0:
            from app.privileged_helper import do_detach_usb

            return do_detach_usb(bus, device)
        ok, message, _data = self._request(
            {"action": "detach_usb", "bus": bus, "device": device}
        )
        return ok, message

    def fetch_hardware_info(self):
        """Return full hardware snapshot using root when the helper is active."""
        if os.geteuid() == 0:
            from app.hardware import get_all_hardware_info

            return get_all_hardware_info()

        ok, _message, data = self._request({"action": "hardware_info"})
        if ok and isinstance(data, dict):
            return data
        return None

    def _request(self, payload):
        if self._proc is None or self._proc.poll() is not None:
            return False, "Privileged helper is not running"
        try:
            self._proc.stdin.write(json.dumps(payload) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
        except (OSError, ValueError) as exc:
            return False, str(exc)
        if not line:
            return False, "Privileged helper closed unexpectedly"
        try:
            response = json.loads(line)
        except json.JSONDecodeError:
            return False, "Malformed response from privileged helper"
        return (
            bool(response.get("ok")),
            response.get("message", ""),
            response.get("data"),
        )
