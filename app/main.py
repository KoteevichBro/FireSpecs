from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from app.ui import FireSpecsWindow
import sys
import os

def main():
    app = QApplication(sys.argv)
    app.setApplicationName('FireSpecs')
    app.setOrganizationName('Firekernel')
    
    logo_path = os.path.join(sys.path[0], 'icons', 'logo.png')
    
    icon = QIcon(logo_path)
    
    if os.path.exists(logo_path) and not icon.isNull():
        app.setWindowIcon(icon)
    
    window = FireSpecsWindow()
    window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec_())
