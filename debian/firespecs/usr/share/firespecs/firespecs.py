#!/usr/bin/env python3
import os
import sys
import traceback

# Qt platform/scale must be set before PyQt5 is imported.
if sys.platform.startswith("linux"):
    if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" and not os.environ.get(
        "QT_QPA_PLATFORM"
    ):
        os.environ["QT_QPA_PLATFORM"] = "wayland"

# Add local bin to PATH for pip packages
local_bin = os.path.expanduser("~/.local/bin")
if local_bin not in os.environ.get("PATH", ""):
    os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")

# Add current directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    from app.main import main
    main()
except ImportError as e:
    print(f"Error: {e}")
    print("\nPlease install PyQt5:")
    print("  sudo apt install python3-pyqt5")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)
