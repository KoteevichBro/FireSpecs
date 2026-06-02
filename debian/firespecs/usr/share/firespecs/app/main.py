import os
import sys


def main():
    # Root worker mode: launched via pkexec to perform privileged actions only.
    if "--privileged-helper" in sys.argv:
        from app.privileged_helper import run_helper

        sys.exit(run_helper())

    from app.window_chrome import configure_linux_qt_platform

    configure_linux_qt_platform()

    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QIcon
    from PyQt5.QtWidgets import QApplication

    from app.paths import get_icon_path
    from app.ui import FireSpecsWindow

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("FireSpecs")
    app.setOrganizationName("Firekernel")

    logo_path = get_icon_path("logo.png")
    icon = QIcon(logo_path)
    if os.path.exists(logo_path) and not icon.isNull():
        app.setWindowIcon(icon)

    window = FireSpecsWindow()
    if os.path.exists(logo_path) and not icon.isNull():
        window.setWindowIcon(icon)
        if getattr(window, "custom_title_bar", None):
            window.custom_title_bar.set_window_icon(icon)

    window.show()
    sys.exit(app.exec_())
