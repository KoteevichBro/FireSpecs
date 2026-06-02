"""
Root-side worker for FireSpecs.

Launched once via pkexec (see app.privilege.PrivilegeManager). Communicates with
the unprivileged GUI over line-delimited JSON on stdin/stdout, so the application
never has to relaunch its whole window as root. Each request performs one
privileged action and returns a structured result.

Protocol (one JSON object per line):
    request : {"action": "<name>", ...args}
    response: {"ok": <bool>, "message": "<text>", "data": <optional>}
"""

import json
import os
import shutil
import sys


def do_delete(path):
    """Delete a file or directory tree as root."""
    path = os.path.expanduser(path or "")
    if not path:
        return False, "No path provided"
    if not os.path.lexists(path):
        return False, f"File not found: {path}"
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True, "Deleted successfully"
    except OSError as exc:
        return False, f"Failed to delete: {exc}"


def do_detach_usb(bus, device):
    """Detach a USB device by writing to sysfs as root."""
    from app.hardware import detach_usb_device

    return detach_usb_device(bus, device)


def do_hardware_info():
    """Collect hardware info as root (DMI fields readable only for root)."""
    from app.hardware import get_all_hardware_info

    return get_all_hardware_info()


def handle_request(request):
    action = request.get("action")
    if action == "ping":
        return {"ok": True, "message": "pong"}
    if action == "delete":
        ok, message = do_delete(request.get("path"))
        return {"ok": ok, "message": message}
    if action == "detach_usb":
        ok, message = do_detach_usb(request.get("bus"), request.get("device"))
        return {"ok": ok, "message": message}
    if action == "hardware_info":
        try:
            return {"ok": True, "message": "ok", "data": do_hardware_info()}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}
    return {"ok": False, "message": f"Unknown action: {action}"}


def run_helper():
    """Read requests until stdin closes or a 'quit' action arrives."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        if request.get("action") == "quit":
            break
        response = handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()
    return 0
