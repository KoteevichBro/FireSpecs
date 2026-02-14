from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTabWidget,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QProgressBar,
    QGroupBox,
    QScrollArea,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QFrame,
    QSizePolicy,
    QMessageBox,
    QMenu,
    QAction,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPointF, QRect, QSize, QUrl
from PyQt5.QtGui import (
    QFont,
    QColor,
    QBrush,
    QPainter,
    QPen,
    QPolygonF,
    QPixmap,
    QIcon,
    QDesktopServices,
)
from PyQt5.QtCore import QPointF
import os
import sys
import subprocess


def get_base_path():
    if getattr(sys, "frozen", False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, "_MEIPASS"):
            return sys._MEIPASS
        else:
            return "/opt/firespecs"
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ThemeManager:
    DARK = {
        "background_main": "#1e1e1e",
        "background_secondary": "#2d2d2d",
        "background_tertiary": "#252525",
        "background_hover": "#3d3d3d",
        "text_primary": "#d4d4d4",
        "text_secondary": "#808080",
        "border": "#3d3d3d",
        "accent": "#ff6b00",
        "button": "#505050",
        "button_hover": "#606060",
        "button_pressed": "#404040",
        "header": "#2d2d2d",
        "selected_tab_text": "#d4d4d4",
        "graph_cpu": "#ff6b00",
        "graph_gpu": "#2196F3",
        "graph_ram": "#4CAF50",
        "graph_swap": "#2E7D32",
    }

    LIGHT = {
        "background_main": "#f5f5f5",
        "background_secondary": "#ffffff",
        "background_tertiary": "#ffffff",
        "background_hover": "#e5e5e5",
        "text_primary": "#333333",
        "text_secondary": "#666666",
        "border": "#cccccc",
        "accent": "#ff6b00",
        "button": "#e5e5e5",
        "button_hover": "#d5d5d5",
        "button_pressed": "#c5c5c5",
        "header": "#ffffff",
        "selected_tab_text": "#ffffff",
        "graph_cpu": "#ff6b00",
        "graph_gpu": "#2196F3",
        "graph_ram": "#4CAF50",
        "graph_swap": "#2E7D32",
    }

    MATRIX = {
        "background_main": "#0a0a0a",
        "background_secondary": "#0d1a0d",
        "background_tertiary": "#051405",
        "background_hover": "#1a331a",
        "text_primary": "#00ff41",
        "text_secondary": "#008800",
        "border": "#003300",
        "accent": "#00ff41",
        "button": "#0d330d",
        "button_hover": "#1a441a",
        "button_pressed": "#052205",
        "header": "#0d1f0d",
        "selected_tab_text": "#000000",
        "graph_cpu": "#00ff41",
        "graph_gpu": "#00cc33",
        "graph_ram": "#008800",
        "graph_swap": "#004400",
    }


from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPointF, QRect, QSize, QUrl
from PyQt5.QtGui import (
    QFont,
    QColor,
    QBrush,
    QPainter,
    QPen,
    QPolygonF,
    QPixmap,
    QIcon,
    QDesktopServices,
)
import os
import subprocess
import shutil


class StatsUpdateThread(QThread):
    stats_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        import time

        while self.running:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_temp = 0
                try:
                    cpu_temp = psutil.sensors_temperatures()
                    if cpu_temp:
                        temps = []
                        for name, entries in cpu_temp.items():
                            if "coretemp" in name or "cpu" in name.lower():
                                for entry in entries:
                                    if hasattr(entry, "current"):
                                        temps.append(entry.current)
                        if temps:
                            cpu_temp = sum(temps) / len(temps)
                except:
                    pass

                cpu_freq = psutil.cpu_freq()
                freq_text = ""
                if cpu_freq:
                    freq_text = f" | Freq: {cpu_freq.current:.0f} MHz"

                ram = psutil.virtual_memory()
                swap = psutil.swap_memory()

                gpu_utilization = 0
                gpu_vram_used = 0
                gpu_vram_total = 0
                gpu_temp = 0

                try:
                    import glob

                    card_paths = glob.glob("/sys/class/drm/card*")
                    for card_path in card_paths:
                        if not card_path.endswith("-"):
                            gpu_busy_path = os.path.join(
                                card_path, "device", "gpu_busy_percent"
                            )
                            vram_total_path = os.path.join(
                                card_path, "device", "mem_info_vram_total"
                            )
                            vram_used_path = os.path.join(
                                card_path, "device", "mem_info_vram_used"
                            )

                            if os.path.exists(vram_total_path) and os.path.exists(
                                vram_used_path
                            ):
                                try:
                                    with open(vram_total_path, "r") as f:
                                        vram_total = int(f.read().strip())
                                    with open(vram_used_path, "r") as f:
                                        vram_used = int(f.read().strip())

                                    gpu_vram_total = vram_total / (1024**3)
                                    gpu_vram_used = vram_used / (1024**3)

                                    if os.path.exists(gpu_busy_path):
                                        with open(gpu_busy_path, "r") as f:
                                            gpu_utilization = int(f.read().strip())
                                    break
                                except:
                                    continue
                except:
                    pass

                gpu_text = "N/A"
                if gpu_vram_total > 0:
                    vram_text = f"VRAM: {gpu_vram_used:.2f}/{gpu_vram_total:.2f} GB"
                    gpu_text = f"{gpu_utilization:.1f}% | {vram_text}"

                gpu_temp = get_gpu_temp()

                self.stats_updated.emit(
                    {
                        "cpu_percent": cpu_percent,
                        "cpu_temp": cpu_temp,
                        "cpu_freq_text": freq_text,
                        "ram_used": ram.used / (1024**3),
                        "ram_total": ram.total / (1024**3),
                        "ram_percent": ram.percent,
                        "swap_used": swap.used / (1024**3),
                        "swap_total": swap.total / (1024**3),
                        "swap_percent": swap.percent,
                        "gpu_text": gpu_text,
                        "gpu_percent": gpu_utilization,
                        "gpu_temp": gpu_temp,
                    }
                )

            except Exception as e:
                self.stats_updated.emit(
                    {
                        "cpu_percent": 0,
                        "cpu_temp": 0,
                        "cpu_freq_text": "",
                        "ram_used": 0,
                        "ram_total": 0,
                        "ram_percent": 0,
                        "swap_used": 0,
                        "swap_total": 0,
                        "swap_percent": 0,
                        "gpu_text": "N/A",
                        "gpu_percent": 0,
                        "gpu_temp": 0,
                    }
                )

            time.sleep(1)

    def stop(self):
        self.running = False
        self.wait()


class HistoryGraph(QFrame):
    def __init__(self, color, show_temp=False, swap_color=None):
        super().__init__()
        self.color = color
        self.swap_color = swap_color
        self.history = [0] * 60
        self.swap_history = [0] * 60 if swap_color else None
        self.temperature = 0
        self.show_temp = show_temp
        self.setFixedHeight(40)
        self.setFrameShape(QFrame.StyledPanel)
        self.dark_theme = True
        self.text_color = QColor("#d4d4d4")
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)

    def set_theme(self, theme):
        if theme == "matrix":
            bg_color = "#0a0a0a"
            border_color = "#003300"
            text_color = "#00ff41"
        elif theme == "light":
            bg_color = "#e5e5e5"
            border_color = "#cccccc"
            text_color = "#666666"
        else:
            bg_color = "#1e1e1e"
            border_color = "#3d3d3d"
            text_color = "#d4d4d4"
        self.text_color = QColor(text_color)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
            }}
        """)

    def set_color(self, color, swap_color=None):
        self.color = QColor(color)
        if swap_color:
            self.swap_color = swap_color
        self.update()

    def add_value(self, value, temp=0, swap_value=0):
        self.history.pop(0)
        self.history.append(value)
        if self.swap_history is not None:
            self.swap_history.pop(0)
            self.swap_history.append(swap_value)
        self.temperature = temp
        self.update()

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        if len(self.history) < 2:
            return

        graph_width = width
        if self.show_temp:
            graph_width = width - 50

        points = []
        for i, value in enumerate(self.history):
            x = (i / (len(self.history) - 1)) * graph_width
            y = height - (value / 100) * height
            points.append(QPointF(x, y))

        pen = QPen(self.color, 2)
        painter.setPen(pen)
        painter.drawPolyline(QPolygonF(points))

        if self.swap_history is not None and len(self.swap_history) >= 2:
            swap_points = []
            for i, value in enumerate(self.swap_history):
                x = (i / (len(self.swap_history) - 1)) * graph_width
                y = height - (value / 100) * height
                swap_points.append(QPointF(x, y))

            swap_color = QColor(self.swap_color)
            swap_color.setAlpha(100)
            swap_pen = QPen(swap_color, 2)
            painter.setPen(swap_pen)
            painter.drawPolyline(QPolygonF(swap_points))

        if self.show_temp:
            rect_size = 30
            rect_x = width - rect_size - 5
            rect_y = (height - rect_size) // 2

            temp_text = "-"

            if self.temperature > 0:
                temp_text = f"{int(self.temperature)}°C"
                if self.temperature > 80:
                    painter.setPen(QColor("#ff4444"))
                else:
                    painter.setPen(self.text_color)
            else:
                painter.setPen(self.text_color)

            text_rect = QRect(int(rect_x), int(rect_y), rect_size, rect_size)
            painter.setFont(QFont("Arial", 9, QFont.Bold))
            fm = painter.fontMetrics()
            text_width = fm.width(temp_text)
            text_height = fm.height()
            text_x = rect_x + (rect_size - text_width) / 2
            text_y = rect_y + (rect_size - text_height) / 2 + fm.ascent()
            painter.drawText(int(text_x), int(text_y), temp_text)


from app.hardware import (
    get_all_hardware_info,
    get_gpu_info,
    get_gpu_temp,
    get_usb_devices,
    detach_usb_device,
)
from app.storage import get_all_storage_info, get_largest_files
import psutil


def get_device_icon(device_name, device_type):
    """
    Get icon path based on device name and type (cpu/gpu).
    Returns None if no matching icon is found.
    """
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_dir = os.path.join(script_dir, "icons")

    device_name_lower = device_name.lower()

    if device_type == "cpu":
        if "intel" in device_name_lower:
            icon_path = os.path.join(icons_dir, "cpu", "intel.png")
        elif "amd" in device_name_lower:
            icon_path = os.path.join(icons_dir, "cpu", "amd.png")
        else:
            return None

        if os.path.exists(icon_path):
            return icon_path

    elif device_type == "gpu":
        if (
            "nvidia" in device_name_lower
            or "geforce" in device_name_lower
            or "rtx" in device_name_lower
            or "gtx" in device_name_lower
        ):
            icon_path = os.path.join(icons_dir, "gpu", "nvidia.png")
        elif "amd" in device_name_lower or "radeon" in device_name_lower:
            icon_path = os.path.join(icons_dir, "gpu", "amd_radeon.png")
        elif "intel" in device_name_lower:
            icon_path = os.path.join(icons_dir, "gpu", "intel.png")
        else:
            return None

        if os.path.exists(icon_path):
            return icon_path

    return None


def create_icon_item(text, icon_path, table):
    """
    Create a table widget item with icon and text.
    """
    widget = QWidget()
    widget.setStyleSheet("background: transparent;")
    widget.setMinimumHeight(30)

    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    layout.setAlignment(Qt.AlignTop)

    label = QLabel(text)
    layout.addWidget(label)

    if icon_path and os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            icon_label = QLabel()
            icon_label.setStyleSheet("background: transparent;")
            scaled_pixmap = pixmap.scaledToHeight(24)
            icon_label.setPixmap(scaled_pixmap)
            layout.addWidget(icon_label)

    layout.addStretch()

    return widget


class DiskTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, values, item_type):
        super().__init__(values)
        self.item_type = item_type


class FileScannerThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, path, limit=10, min_size_mb=1):
        super().__init__()
        self.path = path
        self.limit = limit
        self.min_size_mb = min_size_mb

    def run(self):
        files = get_largest_files(
            self.path, limit=self.limit, min_size_mb=self.min_size_mb
        )
        self.finished.emit(files)


class FireSpecsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FireSpecs - by Firekernel")
        self.setGeometry(100, 100, 1200, 800)

        self.scan_animation_chars = ["|", "/", "-", "\\"]
        self.scan_animation_index = 0
        self.scan_animation_timer = QTimer()
        self.scan_animation_timer.timeout.connect(self.update_scan_button_animation)
        self.is_scanning = False
        self.scan_button_original_text = "Scan for Largest Files"

        self.stats_thread = StatsUpdateThread()
        self.stats_thread.stats_updated.connect(self.update_graphs)
        self.stats_thread.start()
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QTabWidget::pane { border: 1px solid #3d3d3d; }
            QTabBar::tab { 
                background-color: #2d2d2d; 
                color: #d4d4d4; 
                padding: 12px 24px;
                margin-right: 2px;
                border: none;
            }
            QTabBar::tab:hover { background-color: #3d3d3d; }
            QTabBar::tab:selected { background-color: #ff6b00; color: #d4d4d4; }
            QLabel { color: #d4d4d4; }
            QGroupBox { 
                color: #d4d4d4; 
                border: 1px solid #3d3d3d; 
                margin-top: 10px;
                font-weight: bold;
                border-radius: 6px;
            }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; }
            QTableWidget { 
                background-color: #252525; 
                color: #d4d4d4;
                gridline-color: #3d3d3d;
                border: none;
                border-radius: 6px;
            }
            QTableWidget::item { padding: 10px; }
            QTableWidget::item:selected { background-color: #252525; color: #d4d4d4; }
            QHeaderView::section { 
                background-color: #2d2d2d; 
                color: #d4d4d4; 
                padding: 12px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background-color: #505050;
                color: #d4d4d4;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #606060; }
            QPushButton:pressed { background-color: #404040; }
            QProgressBar {
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                text-align: center;
                background-color: #252525;
            }
            QProgressBar::chunk {
                background-color: #505050;
                border-radius: 5px;
            }
            QTabWidget QToolBar {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()

        icons_dir = os.path.join(get_base_path(), "icons", "ui")

        self.hardware_icon = QIcon(os.path.join(icons_dir, "hardware-icon.png"))
        self.hardware_icon_black = self._create_black_icon(
            os.path.join(icons_dir, "hardware-icon.png")
        )
        self.hardware_icon_white = self._create_white_icon(
            os.path.join(icons_dir, "hardware-icon.png")
        )

        self.usb_icon = QIcon(os.path.join(icons_dir, "usb-devices.png"))
        self.usb_icon_black = self._create_black_icon(
            os.path.join(icons_dir, "usb-devices.png")
        )
        self.usb_icon_white = self._create_white_icon(
            os.path.join(icons_dir, "usb-devices.png")
        )

        self.storage_icon = QIcon(os.path.join(icons_dir, "diskette.png"))
        self.storage_icon_black = self._create_black_icon(
            os.path.join(icons_dir, "diskette.png")
        )
        self.storage_icon_white = self._create_white_icon(
            os.path.join(icons_dir, "diskette.png")
        )

        # Green icons for Matrix theme
        self.hardware_icon_green = self._create_green_icon(
            os.path.join(icons_dir, "hardware-icon.png")
        )
        self.usb_icon_green = self._create_green_icon(
            os.path.join(icons_dir, "usb-devices.png")
        )
        self.storage_icon_green = self._create_green_icon(
            os.path.join(icons_dir, "diskette.png")
        )
        self.settings_icon_green = self._create_green_icon(
            os.path.join(get_base_path(), "icons", "ui", "settings.png")
        )
        self.up_arrow_icon_green = self._create_green_icon(
            os.path.join(get_base_path(), "icons", "ui", "up-arrow.png")
        )
        self.folder_icon_green = self._create_green_icon(
            os.path.join(get_base_path(), "icons", "ui", "folder.png")
        )
        self.trash_icon_green = self._create_green_icon(
            os.path.join(get_base_path(), "icons", "ui", "trash.png")
        )
        self.remove_icon_green = self._create_green_icon(
            os.path.join(get_base_path(), "icons", "ui", "remove.png")
        )

        is_root = os.geteuid() == 0

        access_widget = QWidget()
        access_widget.setStyleSheet("background: transparent;")
        access_layout = QHBoxLayout(access_widget)
        access_layout.setContentsMargins(10, 2, 15, 2)
        access_layout.setSpacing(10)
        access_layout.setAlignment(Qt.Alignment(Qt.AlignmentFlag.AlignVCenter))

        self.access_label = QLabel()
        self.access_label.setFont(QFont("Arial", 11))

        if is_root:
            self.access_label.setText("Full Access")
            self.access_label.setStyleSheet(
                "color: #ffffff; font-weight: bold; margin-top: -4px;"
            )
        else:
            self.access_label.setText("Limited Access")
            self.access_label.setStyleSheet(
                "color: #ff5252; font-weight: bold; margin-top: -4px;"
            )

        self.restart_as_root_btn = QPushButton()
        self.restart_as_root_btn.setIcon(
            QIcon(os.path.join(get_base_path(), "icons", "ui", "up-arrow.png"))
        )
        self.restart_as_root_btn.setFixedSize(28, 28)
        self.restart_as_root_btn.setIconSize(QSize(14, 14))
        self.restart_as_root_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:pressed { background-color: #2d2d2d; }
        """)
        self.restart_as_root_btn.setToolTip(
            "Restart with full access (requires password)"
        )
        self.restart_as_root_btn.clicked.connect(self.restart_as_root)

        self.settings_btn = QPushButton()
        self.settings_btn.setIcon(
            QIcon(os.path.join(get_base_path(), "icons", "ui", "settings.png"))
        )
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.setIconSize(QSize(16, 16))
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:pressed { background-color: #2d2d2d; }
        """)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.clicked.connect(self.show_settings_menu)

        self.current_theme = "dark"

        access_layout.addStretch()
        access_layout.addWidget(self.access_label, 0, Qt.AlignmentFlag.AlignVCenter)
        if not is_root:
            access_layout.addWidget(
                self.restart_as_root_btn, 0, Qt.AlignmentFlag.AlignVCenter
            )
        access_layout.addWidget(self.settings_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.tabs)
        self.tabs.setCornerWidget(access_widget)

        self.tabs.currentChanged.connect(self.update_tab_icons)

        self.create_hardware_tab()
        self.create_usb_tab()
        self.create_storage_tab()

        self.update_tab_icons(0)

        self.create_footer()
        layout.addWidget(self.footer)

        self.apply_theme()

    def create_hardware_tab(self):
        hardware_tab = QWidget()
        layout = QHBoxLayout(hardware_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hw_info = get_all_hardware_info()

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: none;
                outline: none;
            }
            QListWidget::item {
                color: #d4d4d4;
                padding: 12px 20px;
                border: none;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #ff6b00;
                border: none;
            }
        """)

        items = [
            "System Information",
            "CPU",
            "RAM",
            "GPU",
            "Motherboard",
            "BIOS Information",
            "Network",
            "Display",
            "Drives",
            "Battery",
        ]

        for item_text in items:
            item = QListWidgetItem(item_text)
            self.sidebar.addItem(item)

        self.content_stack = QStackedWidget()

        system_widget = self.create_info_widget(
            "System Information",
            {
                "Distribution": hw_info["system"]["distribution"],
                "Version": hw_info["system"]["version"],
                "Kernel": hw_info["system"]["kernel"],
                "Codename": hw_info["system"]["codename"],
                "Hostname": hw_info["system"]["hostname"],
                "Architecture": hw_info["system"]["architecture"],
            },
        )

        cpu_data = {
            "Model": hw_info["cpu"]["model"],
            "Physical Cores": hw_info["cpu"]["cores_physical"],
            "Logical Cores": hw_info["cpu"]["cores_logical"],
            "Max Frequency": hw_info["cpu"].get("frequency_max", "N/A"),
            "Min Frequency": hw_info["cpu"].get("frequency_min", "N/A"),
            "Current Frequency": hw_info["cpu"].get("frequency_current", "N/A"),
        }
        if "cache" in hw_info["cpu"]:
            cpu_data["Cache"] = hw_info["cpu"]["cache"]
        cpu_widget = self.create_info_widget(
            "CPU", cpu_data, icon_type="cpu", icon_key="Model"
        )

        memory_widget = self.create_memory_widget(
            hw_info["memory"], hw_info.get("ram_sticks", [])
        )

        mb_widget = self.create_info_widget(
            "Motherboard",
            {
                "Manufacturer": hw_info["motherboard"]["manufacturer"],
                "Product Name": hw_info["motherboard"]["product_name"],
                "Version": hw_info["motherboard"]["version"],
                "Serial Number": hw_info["motherboard"]["serial_number"],
                "Asset Tag": hw_info["motherboard"]["asset_tag"],
            },
        )

        bios_widget = self.create_info_widget(
            "BIOS Information",
            {
                "Vendor": hw_info["bios"]["vendor"],
                "Version": hw_info["bios"]["version"],
                "Release Date": hw_info["bios"]["release_date"],
                "Revision": hw_info["bios"]["revision"],
            },
        )

        gpu_widget = self.create_gpu_widget(hw_info["gpu"])

        network_widget = self.create_network_widget(hw_info.get("network", []))

        display_widget = self.create_display_widget(hw_info.get("display", []))

        drives_widget = self.create_drives_widget(hw_info.get("drives", []))

        battery_widget = self.create_battery_widget(hw_info.get("battery", {}))

        # Wrap all hardware widgets in scroll areas
        self.content_stack.addWidget(self.wrap_in_scroll_area(system_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(cpu_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(memory_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(gpu_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(mb_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(bios_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(network_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(display_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(drives_widget))
        self.content_stack.addWidget(self.wrap_in_scroll_area(battery_widget))

        self.sidebar.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        layout.addWidget(self.sidebar)
        layout.addWidget(self.content_stack)

        self.tabs.addTab(
            hardware_tab,
            QIcon(os.path.join(get_base_path(), "icons", "ui", "hardware-icon.png")),
            "Hardware",
        )

    def wrap_in_scroll_area(self, widget):
        """Wrap widget in QScrollArea with vertical scrolling."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Ensure widget doesn't expand beyond its content
        widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        scroll_area.setWidget(widget)
        return scroll_area

    def set_table_fixed_height(self, table):
        """Set table height to fit exactly its content (all rows)."""
        # Calculate height: header + sum of all row heights + padding
        header_height = table.horizontalHeader().height()
        total_height = header_height

        for i in range(table.rowCount()):
            total_height += table.rowHeight(i)

        # Add padding for borders, grid lines and ensure all content is visible
        total_height += 18

        table.setFixedHeight(total_height)

    def set_tree_fixed_height(self, tree):
        """Set tree widget height to fit exactly its content."""
        # Calculate height: header + (visible items * row height) + padding
        header_height = tree.header().height()

        # Count all visible items (including expanded children)
        def count_visible_items(item):
            count = 1  # Count this item
            if item.isExpanded():
                for i in range(item.childCount()):
                    count += count_visible_items(item.child(i))
            return count

        visible_count = 0
        for i in range(tree.topLevelItemCount()):
            visible_count += count_visible_items(tree.topLevelItem(i))

        # Use sizeHintForRow to get proper row height
        row_height = tree.sizeHintForRow(0) if tree.topLevelItemCount() > 0 else 25
        if row_height <= 0:
            row_height = 25

        total_height = header_height + (visible_count * row_height)

        # Add padding for borders and ensure all content is visible
        total_height += 18

        tree.setFixedHeight(total_height)

    def create_info_widget(self, title, data, icon_type=None, icon_key=None):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(data))
        table.setColumnWidth(0, 180)

        for i, (key, value) in enumerate(data.items()):
            table.setItem(i, 0, QTableWidgetItem(key))

            if icon_type and icon_key and key == icon_key:
                icon_path = get_device_icon(str(value), icon_type)
                icon_widget = create_icon_item(str(value), icon_path, table)
                table.setCellWidget(i, 1, icon_widget)
                icon_widget.show()
                table.update()
                QApplication.processEvents()
                table.resizeRowToContents(i)
                table.setRowHeight(i, 30)
            else:
                table.setItem(i, 1, QTableWidgetItem(str(value)))

        table.resizeRowsToContents()
        self.set_table_fixed_height(table)

        layout.addWidget(table)
        layout.addStretch()
        return widget

    def create_memory_widget(self, memory_info, ram_sticks):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("RAM")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        memory_data = {
            "Total RAM": memory_info["total"],
        }

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(memory_data))
        table.setColumnWidth(0, 180)

        for i, (key, value) in enumerate(memory_data.items()):
            table.setItem(i, 0, QTableWidgetItem(key))
            table.setItem(i, 1, QTableWidgetItem(str(value)))

        table.resizeRowsToContents()
        self.set_table_fixed_height(table)

        layout.addWidget(table)

        if ram_sticks:
            sticks_group = QGroupBox("RAM Sticks")
            sticks_layout = QVBoxLayout()

            sticks_table = QTableWidget()
            sticks_table.setColumnCount(7)
            sticks_table.setHorizontalHeaderLabels(
                [
                    "Size",
                    "Locator",
                    "Type",
                    "Speed",
                    "Manufacturer",
                    "Part Number",
                    "Serial",
                ]
            )
            sticks_table.horizontalHeader().setStretchLastSection(True)
            sticks_table.verticalHeader().setVisible(False)
            sticks_table.setRowCount(len(ram_sticks))
            sticks_table.setColumnWidth(0, 80)
            sticks_table.setColumnWidth(1, 80)
            sticks_table.setColumnWidth(2, 80)
            sticks_table.setColumnWidth(3, 80)
            sticks_table.setColumnWidth(4, 120)
            sticks_table.setColumnWidth(5, 120)

            for i, stick in enumerate(ram_sticks):
                sticks_table.setItem(i, 0, QTableWidgetItem(stick["size"]))
                sticks_table.setItem(i, 1, QTableWidgetItem(stick["locator"]))
                sticks_table.setItem(i, 2, QTableWidgetItem(stick["type"]))
                sticks_table.setItem(i, 3, QTableWidgetItem(stick["speed"]))
                sticks_table.setItem(i, 4, QTableWidgetItem(stick["manufacturer"]))
                sticks_table.setItem(i, 5, QTableWidgetItem(stick["part_number"]))
                sticks_table.setItem(i, 6, QTableWidgetItem(stick["serial"]))

            sticks_table.resizeRowsToContents()
            self.set_table_fixed_height(sticks_table)

            sticks_layout.addWidget(sticks_table)
            sticks_group.setLayout(sticks_layout)
            layout.addWidget(sticks_group)

        layout.addStretch()
        return widget

    def create_gpu_widget(self, gpu_data):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("GPU")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        for gpu in gpu_data:
            group = QGroupBox(f"GPU {gpu_data.index(gpu) + 1}")
            group_layout = QVBoxLayout()

            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Property", "Value"])
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)

            gpu_items = []
            gpu_items.append(("Device", gpu.get("device", "Unknown")))
            gpu_items.append(("Bus", gpu.get("bus", "Unknown")))
            if "renderer" in gpu:
                gpu_items.append(("OpenGL Renderer", gpu["renderer"]))
            if "driver" in gpu:
                gpu_items.append(("Driver Version", gpu["driver"]))

            table.setRowCount(len(gpu_items))

            for j, (key, value) in enumerate(gpu_items):
                table.setItem(j, 0, QTableWidgetItem(key))

                if key == "Device":
                    icon_path = get_device_icon(str(value), "gpu")
                    icon_widget = create_icon_item(str(value), icon_path, table)
                    table.setCellWidget(j, 1, icon_widget)
                else:
                    table.setItem(j, 1, QTableWidgetItem(str(value)))

            table.resizeRowsToContents()
            self.set_table_fixed_height(table)

            group_layout.addWidget(table)
            group.setLayout(group_layout)
            layout.addWidget(group)

        layout.addStretch()
        return widget

    def create_network_widget(self, network_data):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Network")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Interface", "IP Address", "MAC Address"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(network_data))
        table.setColumnWidth(0, 120)
        table.setColumnWidth(1, 150)

        for i, net in enumerate(network_data):
            table.setItem(i, 0, QTableWidgetItem(net["interface"]))
            table.setItem(i, 1, QTableWidgetItem(net["ip"]))
            table.setItem(i, 2, QTableWidgetItem(net["mac"]))

        table.resizeRowsToContents()
        self.set_table_fixed_height(table)

        layout.addWidget(table)
        layout.addStretch()

        return widget

    def create_display_widget(self, display_data):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Display")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        if not display_data or (
            len(display_data) == 1
            and display_data[0].get("name") == "No displays detected"
        ):
            no_display_label = QLabel("No displays detected or xrandr not available.")
            no_display_label.setObjectName("secondary_label")
            layout.addWidget(no_display_label)
        else:
            for i, display in enumerate(display_data, 1):
                group = QGroupBox(f"Display {i}")
                group_layout = QVBoxLayout()

                table = QTableWidget()
                table.setColumnCount(2)
                table.setHorizontalHeaderLabels(["Property", "Value"])
                table.horizontalHeader().setStretchLastSection(True)
                table.verticalHeader().setVisible(False)
                table.setColumnWidth(0, 180)

                display_items = []
                display_items.append(("Name", display.get("name", "Unknown")))
                display_items.append(("Model", display.get("model", "Unknown")))
                vendor = display.get("vendor", "Unknown")
                if vendor != "Unknown":
                    display_items.append(("Vendor ID", vendor))
                if "serial" in display and display["serial"] != "Unknown":
                    display_items.append(("Serial", display["serial"]))
                if "current_resolution" in display:
                    display_items.append(
                        ("Current Resolution", display["current_resolution"])
                    )
                if "max_resolution" in display:
                    display_items.append(("Max Resolution", display["max_resolution"]))
                if "max_refresh_rate" in display:
                    display_items.append(
                        ("Max Refresh Rate", display["max_refresh_rate"])
                    )
                if "physical_size" in display:
                    display_items.append(("Physical Size", display["physical_size"]))
                if (
                    "manufacture_date" in display
                    and display["manufacture_date"] != "Unknown"
                ):
                    display_items.append(
                        ("Manufacture Date", display["manufacture_date"])
                    )
                if "rotation" in display:
                    display_items.append(("Rotation", display["rotation"]))
                if "primary" in display:
                    display_items.append(("Primary", display["primary"]))

                table.setRowCount(len(display_items))

                for j, (key, value) in enumerate(display_items):
                    table.setItem(j, 0, QTableWidgetItem(key))
                    table.setItem(j, 1, QTableWidgetItem(str(value)))

                table.resizeRowsToContents()
                self.set_table_fixed_height(table)

                group_layout.addWidget(table)
                group.setLayout(group_layout)
                layout.addWidget(group)

        layout.addStretch()
        return widget

    def create_drives_widget(self, drives_data):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Drives")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        if not drives_data or (
            len(drives_data) == 1 and drives_data[0].get("name") == "No drives detected"
        ):
            no_drives_label = QLabel("No drives detected or lsblk not available.")
            no_drives_label.setObjectName("secondary_label")
            layout.addWidget(no_drives_label)
        else:
            for i, drive in enumerate(drives_data, 1):
                group = QGroupBox(f"Drive {i}")
                group_layout = QVBoxLayout()

                table = QTableWidget()
                table.setColumnCount(2)
                table.setHorizontalHeaderLabels(["Property", "Value"])
                table.horizontalHeader().setStretchLastSection(True)
                table.verticalHeader().setVisible(False)

                drive_items = []
                drive_items.append(("Name", drive.get("name", "Unknown")))
                drive_items.append(("Model", drive.get("model", "Unknown")))
                if "serial" in drive and drive["serial"] != "N/A":
                    drive_items.append(("Serial", drive["serial"]))
                if "size" in drive:
                    drive_items.append(("Size", drive["size"]))
                if "type" in drive:
                    drive_items.append(("Type", drive["type"]))
                if "mountpoint" in drive and drive["mountpoint"] != "N/A":
                    drive_items.append(("Mount Point", drive["mountpoint"]))
                if "readonly" in drive:
                    drive_items.append(("Read Only", drive["readonly"]))
                if "removable" in drive:
                    drive_items.append(("Removable", drive["removable"]))

                table.setRowCount(len(drive_items))

                for j, (key, value) in enumerate(drive_items):
                    table.setItem(j, 0, QTableWidgetItem(key))
                    table.setItem(j, 1, QTableWidgetItem(str(value)))

                table.resizeRowsToContents()
                self.set_table_fixed_height(table)

                group_layout.addWidget(table)
                group.setLayout(group_layout)
                layout.addWidget(group)

        layout.addStretch()
        return widget

    def create_battery_widget(self, battery_data):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignTop)

        title_label = QLabel("Battery")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        if not battery_data.get("present", False):
            no_battery_label = QLabel("No battery detected")
            no_battery_label.setObjectName("secondary_label")
            layout.addWidget(no_battery_label)
        else:
            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Property", "Value"])
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
            table.setColumnWidth(0, 180)

            battery_items = []
            battery_items.append(("Status", battery_data.get("status", "Unknown")))
            battery_items.append(
                ("Charge Level", battery_data.get("percent", "Unknown"))
            )
            battery_items.append(
                ("Power Plugged", battery_data.get("power_plugged", "Unknown"))
            )
            battery_items.append(
                ("Time Remaining", battery_data.get("time_left", "Unknown"))
            )

            if battery_data.get("health") != "N/A":
                battery_items.append(("Health", battery_data.get("health")))
            if battery_data.get("technology") != "N/A":
                battery_items.append(("Technology", battery_data.get("technology")))
            if battery_data.get("cycle_count") != "N/A":
                battery_items.append(("Cycle Count", battery_data.get("cycle_count")))

            table.setRowCount(len(battery_items))

            for j, (key, value) in enumerate(battery_items):
                table.setItem(j, 0, QTableWidgetItem(key))
                table.setItem(j, 1, QTableWidgetItem(str(value)))

            table.resizeRowsToContents()
            self.set_table_fixed_height(table)
            layout.addWidget(table)

        layout.addStretch()
        return widget

    def create_usb_tab(self, insert_at_index=None):
        usb_tab = QWidget()
        layout = QVBoxLayout(usb_tab)

        usb_data = get_usb_devices()

        title_label = QLabel("USB Devices")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            ["№", "Vendor", "Product", "ID", "Serial", "Class", "Speed", "Actions"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(usb_data))
        table.setColumnWidth(0, 50)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 200)
        table.setColumnWidth(3, 90)
        table.setColumnWidth(4, 120)
        table.setColumnWidth(5, 100)
        table.setColumnWidth(6, 120)
        table.setColumnWidth(7, 50)

        for i, usb in enumerate(usb_data):
            table.setItem(i, 0, QTableWidgetItem(str(usb.get("number", i + 1))))
            table.setItem(i, 1, QTableWidgetItem(usb.get("vendor", "N/A")))
            table.setItem(i, 2, QTableWidgetItem(usb.get("product", "N/A")))
            table.setItem(i, 3, QTableWidgetItem(usb.get("id", "N/A")))
            table.setItem(i, 4, QTableWidgetItem(usb.get("serial", "N/A")))
            table.setItem(i, 5, QTableWidgetItem(usb.get("device_class", "N/A")))
            table.setItem(i, 6, QTableWidgetItem(usb.get("speed", "N/A")))

            if usb.get("bus") != "N/A" and usb.get("device") != "N/A":
                actions_widget = QWidget()
                actions_widget.setStyleSheet("background: transparent;")
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(4, 0, 4, 0)
                actions_layout.setSpacing(8)

                remove_btn = QPushButton()
                # Use green icon for Matrix theme
                if self.current_theme == "matrix" and hasattr(
                    self, "remove_icon_green"
                ):
                    remove_btn.setIcon(self.remove_icon_green)
                else:
                    remove_icon_path = os.path.join(
                        get_base_path(), "icons", "ui", "remove.png"
                    )
                    if os.path.exists(remove_icon_path):
                        remove_btn.setIcon(QIcon(remove_icon_path))
                remove_btn.setIconSize(QSize(18, 18))
                remove_btn.setFixedSize(28, 28)
                remove_btn.setToolTip("Detach USB device")
                # Set style based on current theme
                if self.current_theme == "matrix":
                    remove_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #1a331a;
                        }
                    """)
                elif self.current_theme == "light":
                    remove_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #e5e5e5;
                        }
                    """)
                else:
                    remove_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #505050;
                        }
                    """)

                bus = usb.get("bus")
                device = usb.get("device")
                remove_btn.clicked.connect(
                    lambda checked, b=bus, d=device: self.detach_usb_device_handler(
                        b, d
                    )
                )

                actions_layout.addWidget(remove_btn)
                actions_layout.addStretch()

                table.setCellWidget(i, 7, actions_widget)
            else:
                table.setItem(i, 7, QTableWidgetItem("N/A"))

        table.resizeRowsToContents()
        self.set_table_fixed_height(table)

        # Save reference to table for theme updates
        self.usb_table = table

        # Wrap table in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setWidget(table)
        layout.addWidget(scroll_area)

        usb_icon = QIcon(
            os.path.join(get_base_path(), "icons", "ui", "usb-devices.png")
        )

        if insert_at_index is not None:
            self.tabs.insertTab(insert_at_index, usb_tab, usb_icon, "USB Devices")
        else:
            self.tabs.addTab(usb_tab, usb_icon, "USB Devices")

    def detach_usb_device_handler(self, bus, device):
        from PyQt5.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Detach USB Device",
            f"Are you sure you want to detach USB device {bus}-{device}?\n\n"
            "This will safely disconnect the device from the system.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            success, message = detach_usb_device(bus, device)

            if success:
                QMessageBox.information(self, "Success", message)
                self.refresh_usb_tab()
            else:
                QMessageBox.warning(self, "Error", message)

    def refresh_usb_tab(self):
        usb_index = -1
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "USB Devices":
                usb_index = i
                break

        if usb_index >= 0:
            old_tab = self.tabs.widget(usb_index)
            self.tabs.removeTab(usb_index)
            old_tab.deleteLater()
            # Recreate tab at the same position
            self.create_usb_tab(insert_at_index=usb_index)
            # Stay on USB Devices tab
            self.tabs.setCurrentIndex(usb_index)

    def create_storage_tab(self):
        storage_tab = QWidget()
        main_layout = QVBoxLayout(storage_tab)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create content widget to hold all elements
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        storage_info = get_all_storage_info()

        partitions_group = QGroupBox("Disk Partitions")
        lsblk_tree = self.create_lsblk_tree(storage_info["lsblk"])
        partitions_layout = QVBoxLayout()
        partitions_layout.addWidget(lsblk_tree)
        partitions_layout.setContentsMargins(5, 5, 5, 5)
        partitions_group.setLayout(partitions_layout)
        partitions_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(partitions_group)

        files_group = QGroupBox("Largest Files")
        files_layout = QVBoxLayout()

        files_layout.addWidget(
            QLabel('Enter a directory path and click "Scan" to find largest files:')
        )

        path_input_layout = QHBoxLayout()
        path_input_layout.addWidget(QLabel("Path:"))
        self.path_input = QLineEdit("/")
        self.path_input.setStyleSheet("""
            QLineEdit {
                background-color: #252525;
                color: #d4d4d4;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #505050;
            }
        """)
        path_input_layout.addWidget(self.path_input)
        files_layout.addLayout(path_input_layout)

        self.scan_btn = QPushButton("Scan for Largest Files")
        self.scan_btn.clicked.connect(self.scan_files)
        files_layout.addWidget(self.scan_btn)
        # Set initial style based on theme
        self.update_scan_button_idle_style()

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels(["File Path", "Size", "Actions"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.verticalHeader().setVisible(False)
        files_layout.addWidget(self.files_table)
        self.files_table.setColumnWidth(0, 700)
        self.files_table.setColumnWidth(1, 120)
        self.files_table.setColumnWidth(2, 70)

        files_group.setLayout(files_layout)
        # Files group should expand to take remaining space
        files_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout.addWidget(files_group)

        # Wrap content in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        self.tabs.addTab(
            storage_tab,
            QIcon(os.path.join(get_base_path(), "icons", "ui", "diskette.png")),
            "Storage",
        )

    def scan_files(self):
        path = self.path_input.text().strip()
        if not path:
            path = "/"
        self.files_table.setRowCount(0)
        self.files_table.setEnabled(False)

        self.is_scanning = True
        self.scan_animation_index = 0
        self.scan_animation_timer.start(100)
        self.scan_btn.setEnabled(False)
        self.path_input.setEnabled(False)

        self.scanner_thread = FileScannerThread(path, limit=20)
        self.scanner_thread.finished.connect(self.on_scan_complete)
        self.scanner_thread.start()

    def update_scan_button_animation(self):
        if self.is_scanning:
            char = self.scan_animation_chars[self.scan_animation_index]
            self.scan_btn.setText(f"Scanning {char}")
            # Scanning animation style based on theme
            if self.current_theme == "matrix":
                self.scan_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #00ff41;
                        color: #000000;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-weight: bold;
                    }
                """)
            else:
                self.scan_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ff6b00;
                        color: #ffffff;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        font-weight: bold;
                    }
                """)
            self.scan_animation_index = (self.scan_animation_index + 1) % len(
                self.scan_animation_chars
            )

    def update_scan_button_idle_style(self):
        """Update scan button style based on current theme."""
        if self.current_theme == "light":
            # Light theme - lighter gray
            self.scan_btn.setStyleSheet("""
                QPushButton {
                    background-color: #b8b8b8;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #a8a8a8;
                }
                QPushButton:pressed {
                    background-color: #989898;
                }
                QPushButton:disabled {
                    background-color: #d0d0d0;
                }
            """)
        elif self.current_theme == "matrix":
            # Matrix theme - dark green
            self.scan_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0d4d0d;
                    color: #00ff41;
                    border: 1px solid #00ff41;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1a661a;
                }
                QPushButton:pressed {
                    background-color: #052d05;
                }
                QPushButton:disabled {
                    background-color: #0a1f0a;
                    color: #005500;
                    border: 1px solid #005500;
                }
            """)
        else:
            # Dark theme - darker gray
            self.scan_btn.setStyleSheet("""
                QPushButton {
                    background-color: #707070;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #606060;
                }
                QPushButton:pressed {
                    background-color: #505050;
                }
                QPushButton:disabled {
                    background-color: #999999;
                }
            """)

    def on_scan_complete(self, files):
        self.is_scanning = False
        self.scan_animation_timer.stop()
        self.scan_btn.setText(self.scan_button_original_text)
        # Return to idle mode with theme-appropriate style
        self.update_scan_button_idle_style()
        self.scan_btn.setEnabled(True)
        self.path_input.setEnabled(True)

        if not files:
            # No files found - show message
            self.files_table.setRowCount(1)
            self.files_table.setItem(0, 0, QTableWidgetItem("No files found"))
            self.files_table.setItem(0, 1, QTableWidgetItem(""))
            self.files_table.setItem(0, 2, QTableWidgetItem(""))
            self.files_table.setSpan(0, 0, 1, 3)
        else:
            # Display files
            self.files_table.setRowCount(len(files))
            for i, file_info in enumerate(files):
                self.files_table.setItem(i, 0, QTableWidgetItem(file_info["path"]))
                self.files_table.setItem(
                    i, 1, QTableWidgetItem(self.format_file_size(file_info["size_mb"]))
                )
                self.files_table.setRowHeight(i, 40)

                # Create actions widget
                actions_widget = QWidget()
                actions_widget.setStyleSheet("background: transparent;")
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)
                actions_layout.setSpacing(8)

                # Open folder button
                folder_btn = QPushButton()
                # Use green icon for Matrix theme
                if self.current_theme == "matrix" and hasattr(
                    self, "folder_icon_green"
                ):
                    folder_btn.setIcon(self.folder_icon_green)
                else:
                    folder_icon = QIcon(
                        os.path.join(get_base_path(), "icons", "ui", "folder.png")
                    )
                    folder_btn.setIcon(folder_icon)
                folder_btn.setIconSize(QSize(18, 18))
                folder_btn.setFixedSize(20, 20)
                folder_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #404040;
                    }
                """)
                if self.current_theme == "light":
                    folder_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #e5e5e5;
                        }
                    """)
                elif self.current_theme == "matrix":
                    folder_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #1a331a;
                        }
                    """)
                else:
                    folder_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #404040;
                        }
                    """)
                folder_btn.setToolTip("Open folder")
                folder_btn.clicked.connect(
                    lambda checked, path=file_info["path"]: self.open_file_folder(path)
                )

                # Delete button
                delete_btn = QPushButton()
                # Use green icon for Matrix theme
                if self.current_theme == "matrix" and hasattr(self, "trash_icon_green"):
                    delete_btn.setIcon(self.trash_icon_green)
                else:
                    trash_icon = QIcon(
                        os.path.join(get_base_path(), "icons", "ui", "trash.png")
                    )
                    delete_btn.setIcon(trash_icon)
                delete_btn.setIconSize(QSize(18, 18))
                delete_btn.setFixedSize(20, 20)
                if self.current_theme == "light":
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #e5e5e5;
                        }
                    """)
                elif self.current_theme == "matrix":
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #1a331a;
                        }
                    """)
                else:
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: transparent;
                            border: none;
                            border-radius: 3px;
                        }
                        QPushButton:hover {
                            background-color: #404040;
                        }
                    """)
                delete_btn.setToolTip("Delete file")
                delete_btn.clicked.connect(
                    lambda checked, path=file_info["path"], row=i: self.delete_file(
                        path, row
                    )
                )

                actions_layout.addWidget(folder_btn)
                actions_layout.addWidget(delete_btn)

                self.files_table.setCellWidget(i, 2, actions_widget)

            self.files_table.resizeRowsToContents()
            self.set_table_fixed_height(self.files_table)

        self.files_table.setEnabled(True)

    def format_file_size(self, size_mb):
        size_bytes = size_mb * 1024 * 1024

        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024

        return f"{size_bytes:.2f} EB"

    def open_file_folder(self, file_path):
        file_path = os.path.expanduser(file_path)

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            return

        try:
            folder_path = os.path.dirname(file_path)

            # Detect available file managers
            file_managers = [
                "nautilus",  # GNOME
                "dolphin",  # KDE
                "thunar",  # XFCE
                "pcmanfm",  # LXDE/LXQt
                "nemo",  # Cinnamon
                "caja",  # MATE
                "xdg-open",  # Fallback
            ]

            selected_fm = None
            for fm in file_managers:
                result = subprocess.run(["which", fm], capture_output=True, text=True)
                if result.returncode == 0:
                    selected_fm = fm
                    break

            if not selected_fm:
                QMessageBox.warning(self, "Error", "No file manager found")
                return

            if os.geteuid() == 0:
                import pwd

                try:
                    username = pwd.getpwuid(1000).pw_name
                    user_home = pwd.getpwuid(1000).pw_dir
                    env = os.environ.copy()
                    env["HOME"] = user_home
                    env["DISPLAY"] = os.environ.get("DISPLAY", ":0")

                    subprocess.Popen(
                        ["sudo", "-u", username, "-E", selected_fm, folder_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                    )
                    print(
                        f"Opening folder with {selected_fm} as user {username}: {folder_path}"
                    )
                except Exception as e:
                    print(f"Failed to run as user: {str(e)}")
                    # Fallback: try without sudo
                    env = os.environ.copy()
                    env["DISPLAY"] = os.environ.get("DISPLAY", ":0")
                    subprocess.Popen(
                        [selected_fm, folder_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                    )
                    print(f"Opening folder with {selected_fm}: {folder_path}")
            else:
                subprocess.Popen(
                    [selected_fm, folder_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"Opening folder with {selected_fm}: {folder_path}")

        except Exception as e:
            print(f"Exception: {str(e)}")
            QMessageBox.warning(self, "Error", f"Failed to open folder: {str(e)}")

    def delete_file(self, file_path, row):
        file_path = os.path.expanduser(file_path)

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", f"File not found: {file_path}")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete:\n{file_path}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)

                QMessageBox.information(self, "Success", "File deleted successfully")

                self.files_table.removeRow(row)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete file: {str(e)}")

    def create_info_table(self, data):
        layout = QVBoxLayout()
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(data))
        table.setColumnWidth(0, 180)

        for i, (key, value) in enumerate(data.items()):
            table.setItem(i, 0, QTableWidgetItem(key))
            table.setItem(i, 1, QTableWidgetItem(str(value)))

        layout.addWidget(table)
        return layout

    def create_partitions_table(self, partitions):
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Device", "Mount Point", "Type", "Total", "Used", "Free"]
        )
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(partitions))
        table.setColumnWidth(0, 120)
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 80)
        table.setColumnWidth(3, 80)
        table.setColumnWidth(4, 80)

        for i, part in enumerate(partitions):
            table.setItem(i, 0, QTableWidgetItem(part["device"]))
            table.setItem(i, 1, QTableWidgetItem(part["mountpoint"]))
            table.setItem(i, 2, QTableWidgetItem(part["fstype"]))
            table.setItem(i, 3, QTableWidgetItem(part["total"]))
            table.setItem(i, 4, QTableWidgetItem(part["used"]))
            table.setItem(i, 5, QTableWidgetItem(part["free"]))

        return table

    def create_lsblk_tree(self, devices):
        tree = QTreeWidget()
        tree.setColumnCount(10)
        tree.setHeaderLabels(
            [
                "NAME",
                "MAJ:MIN",
                "RM",
                "SIZE",
                "RO",
                "TYPE",
                "MOUNTPOINTS",
                "FSTYPE",
                "LABEL",
                "MODEL",
            ]
        )
        tree.setSelectionMode(QTreeWidget.SingleSelection)

        def add_device(device, parent=None):
            values = [
                device.get("name", ""),
                device.get("maj:min", ""),
                str(device.get("rm", "")),
                device.get("size", ""),
                str(device.get("ro", "")),
                device.get("type", ""),
                ", ".join(device.get("mountpoints", []) or []),
                device.get("fstype", ""),
                device.get("label", ""),
                device.get("model", "") or device.get("serial", ""),
            ]

            item = DiskTreeWidgetItem(values, device.get("type", ""))

            if parent:
                parent.addChild(item)
            else:
                tree.addTopLevelItem(item)

            if "children" in device:
                for child in device["children"]:
                    add_device(child, item)

        for device in devices:
            add_device(device)

        tree.expandAll()

        for i in range(tree.columnCount()):
            tree.resizeColumnToContents(i)
            tree.setColumnWidth(i, max(tree.columnWidth(i), 80))

        header = tree.header()
        if header:
            header.setStretchLastSection(True)

        # Calculate actual height based on visible items
        def count_all_items(item):
            count = 1
            for i in range(item.childCount()):
                count += count_all_items(item.child(i))
            return count

        total_items = 0
        for i in range(tree.topLevelItemCount()):
            total_items += count_all_items(tree.topLevelItem(i))

        # Calculate height: header + (rows * row_height) + padding
        header_height = 28  # Standard header height
        row_height = 33  # Increased row height (was 22, now 1.5x)
        total_height = header_height + (total_items * row_height) + 20

        tree.setFixedHeight(total_height)

        return tree

    def create_footer(self):
        self.footer = QWidget()
        self.footer.setFixedHeight(80)
        self.footer.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-top: 1px solid #3d3d3d;
            }
            QLabel {
                color: #d4d4d4;
                font-size: 11px;
                padding: 2px;
            }
        """)

        layout = QHBoxLayout(self.footer)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(20)

        cpu_layout = QVBoxLayout()
        cpu_layout.setSpacing(5)
        cpu_layout.setStretch(1, 1)
        self.cpu_label = QLabel("CPU: -")
        self.cpu_graph = HistoryGraph(QColor("#ff6b00"), show_temp=True)
        cpu_layout.addWidget(self.cpu_label)
        cpu_layout.addWidget(self.cpu_graph)

        gpu_layout = QVBoxLayout()
        gpu_layout.setSpacing(5)
        gpu_layout.setStretch(1, 1)
        self.gpu_label = QLabel("GPU: -")
        self.gpu_graph = HistoryGraph(QColor("#2196F3"), show_temp=True)
        gpu_layout.addWidget(self.gpu_label)
        gpu_layout.addWidget(self.gpu_graph)

        ram_layout = QVBoxLayout()
        ram_layout.setSpacing(5)
        ram_layout.setStretch(1, 1)
        self.ram_label = QLabel("RAM: -")
        self.ram_graph = HistoryGraph(
            QColor("#4CAF50"), show_temp=False, swap_color="#2E7D32"
        )
        ram_layout.addWidget(self.ram_label)
        ram_layout.addWidget(self.ram_graph)

        layout.addLayout(cpu_layout)
        layout.addLayout(gpu_layout)
        layout.addLayout(ram_layout)

    def update_graphs(self, stats):
        try:
            self.cpu_label.setText(
                f"CPU: {stats['cpu_percent']:.1f}%{stats['cpu_freq_text']}"
            )
            self.cpu_graph.add_value(stats["cpu_percent"], stats["cpu_temp"])

            self.gpu_label.setText(f"GPU: {stats['gpu_text']}")
            self.gpu_graph.add_value(stats["gpu_percent"], stats["gpu_temp"])

            self.ram_label.setText(
                f"RAM: {stats['ram_used']:.1f}/{stats['ram_total']:.1f} GB | SWAP: {stats['swap_used']:.1f}/{stats['swap_total']:.1f} GB"
            )
            self.ram_graph.add_value(
                stats["ram_percent"], swap_value=stats["swap_percent"]
            )
        except:
            pass

    def restart_as_root(self):
        try:
            display = os.environ.get("DISPLAY", ":0")
            xauth = os.environ.get("XAUTHORITY", "")

            env_vars = [f"DISPLAY={display}"]
            if xauth:
                env_vars.append(f"XAUTHORITY={xauth}")

            # Check if running from AppImage
            appimage_path = os.environ.get("APPIMAGE", "")
            if appimage_path and os.path.exists(appimage_path):
                # Running from AppImage - use pkexec with AppImage path
                cmd = ["pkexec", "env"] + env_vars + [appimage_path]
            elif getattr(sys, "frozen", False):
                binary_path = "/opt/firespecs/firespecs"
                cmd = ["pkexec", "env"] + env_vars + [binary_path]
            elif os.path.exists("/usr/bin/firespecs"):
                # Installed as deb package
                cmd = ["pkexec", "env"] + env_vars + ["/usr/bin/firespecs"]
            else:
                # Running from source
                script_path = os.path.join(get_base_path(), "firespecs.py")
                cmd = ["pkexec", "env"] + env_vars + ["python3", script_path]

            # Start new instance as root (in background)
            # Old instance continues running - user can close it manually if needed
            subprocess.Popen(cmd, start_new_session=True, close_fds=True)
        except:
            pass

    def _create_black_icon(self, icon_path):
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            return QIcon(icon_path)

        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(0, 0, 0))
        painter.end()

        icon = QIcon(pixmap)
        return icon

    def _create_white_icon(self, icon_path):
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            return QIcon(icon_path)

        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(255, 255, 255))
        painter.end()

        icon = QIcon(pixmap)
        return icon

    def _create_green_icon(self, icon_path):
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            return QIcon(icon_path)

        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(0, 255, 65))  # Matrix green
        painter.end()

        icon = QIcon(pixmap)
        return icon

    def update_tab_icons(self, index):
        icons = [
            (
                0,
                self.hardware_icon,
                self.hardware_icon_black,
                self.hardware_icon_white,
                self.hardware_icon_green,
            ),
            (
                1,
                self.usb_icon,
                self.usb_icon_black,
                self.usb_icon_white,
                self.usb_icon_green,
            ),
            (
                2,
                self.storage_icon,
                self.storage_icon_black,
                self.storage_icon_white,
                self.storage_icon_green,
            ),
        ]

        for tab_index, normal_icon, black_icon, white_icon, green_icon in icons:
            if tab_index == index:
                # Selected tab - use black icon so it doesn't blend with green background
                if self.current_theme == "light":
                    self.tabs.setTabIcon(tab_index, black_icon)
                else:
                    self.tabs.setTabIcon(tab_index, black_icon)
            else:
                # Unselected tab - use theme appropriate icon
                if self.current_theme == "matrix":
                    self.tabs.setTabIcon(tab_index, green_icon)
                else:
                    self.tabs.setTabIcon(tab_index, normal_icon)

    def show_settings_menu(self):
        if self.current_theme == "dark":
            theme = ThemeManager.DARK
        elif self.current_theme == "light":
            theme = ThemeManager.LIGHT
        else:
            theme = ThemeManager.MATRIX
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme["background_secondary"]};
                border: 1px solid {theme["border"]};
                border-radius: 4px;
                padding: 5px;
            }}
            QMenu::item {{
                background-color: transparent;
                color: {theme["text_primary"]};
                padding: 8px 25px;
                border-radius: 3px;
            }}
            QMenu::item:hover {{
                background-color: {theme["background_hover"]};
            }}
            QMenu::item:selected {{
                background-color: {theme["accent"]};
                color: #ffffff;
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {theme["border"]};
                margin: 5px 10px;
            }}
        """)

        dark_action = QAction("Dark", self)
        dark_action.setCheckable(True)
        dark_action.setChecked(self.current_theme == "dark")
        dark_action.triggered.connect(lambda: self.set_theme("dark"))
        menu.addAction(dark_action)

        light_action = QAction("Light", self)
        light_action.setCheckable(True)
        light_action.setChecked(self.current_theme == "light")
        light_action.triggered.connect(lambda: self.set_theme("light"))
        menu.addAction(light_action)

        matrix_action = QAction("Matrix", self)
        matrix_action.setCheckable(True)
        matrix_action.setChecked(self.current_theme == "matrix")
        matrix_action.triggered.connect(lambda: self.set_theme("matrix"))
        menu.addAction(matrix_action)

        menu.addSeparator()

        about_action = QAction("About...", self)
        about_action.triggered.connect(self.show_about_dialog)
        menu.addAction(about_action)

        menu.exec_(
            self.settings_btn.mapToGlobal(self.settings_btn.rect().bottomRight())
        )

    def set_theme(self, theme):
        self.current_theme = theme
        self.apply_theme()

    def show_about_dialog(self):
        icon_path = os.path.join(get_base_path(), "icons", "logo.png")

        msg = QMessageBox(self)
        msg.setWindowTitle("About FireSpecs")
        msg.setTextFormat(Qt.RichText)
        msg.setWindowIcon(QIcon(icon_path))
        msg.setIconPixmap(QPixmap(icon_path))

        # Apply theme to the dialog
        if self.current_theme == "dark":
            theme = ThemeManager.DARK
        elif self.current_theme == "light":
            theme = ThemeManager.LIGHT
        else:
            theme = ThemeManager.MATRIX
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {theme["background_main"]};
            }}
            QMessageBox QLabel {{
                color: {theme["text_primary"]};
            }}
            QMessageBox QPushButton {{
                background-color: {theme["button"]};
                color: {theme["text_primary"]};
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 60px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {theme["button_hover"]};
            }}
        """)

        about_text = f"""
        <center>
        <h2 style='color: {theme["text_primary"]};'>FireSpecs (v.3)</h2>
        <p style='color: {theme["text_primary"]};'>Hardware monitoring and system information tool</p>
        <p style='color: {theme["text_primary"]};'>Firekernel© 2025-2026. By Denis Oreshkin</p>
        <br>
        <a href='https://firespecs.sourceforge.io/' style='color: {theme["accent"]};'>https://firespecs.sourceforge.io/</a>
        </center>
        """
        msg.setText(about_text)
        msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def apply_theme(self):
        if self.current_theme == "dark":
            theme = ThemeManager.DARK
        elif self.current_theme == "light":
            theme = ThemeManager.LIGHT
        else:
            theme = ThemeManager.MATRIX

        # Matrix theme uses monospace font
        font_family = "monospace" if self.current_theme == "matrix" else "Arial"

        base_style = f"""
            QMainWindow {{ background-color: {theme["background_main"]}; }}
            QTabWidget::pane {{ border: 1px solid {theme["border"]}; }}
            QTabBar::tab {{
                background-color: {theme["header"]};
                color: {theme["text_primary"]};
                font-family: {font_family};
                padding: 12px 24px;
                margin-right: 2px;
                border: none;
            }}
            QTabBar::tab:hover {{ background-color: {theme["background_hover"]}; }}
            QTabBar::tab:selected {{ background-color: {theme["accent"]}; color: {theme.get("selected_tab_text", theme["text_primary"])}; font-family: {font_family}; }}
            QLabel {{ color: {theme["text_primary"]}; font-family: {font_family}; }}
            QLabel#info_title {{ color: {theme["text_primary"]}; font-family: {font_family}; padding-bottom: 10px; }}
            QLabel#secondary_label {{ color: {theme["text_secondary"]}; font-family: {font_family}; font-size: 14px; padding: 20px; }}
            QGroupBox {{
                color: {theme["text_primary"]};
                font-family: {font_family};
                border: 1px solid {theme["border"]};
                margin-top: 10px;
                font-weight: bold;
                border-radius: 6px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; }}
            QTableWidget {{
                background-color: {theme["background_tertiary"]};
                color: {theme["text_primary"]};
                font-family: {font_family};
                gridline-color: {theme["border"]};
                border: 1px solid {theme["border"]};
                border-radius: 8px;
            }}
            QTableWidget::item {{ padding: 5px; font-family: {font_family}; }}
            QTableWidget::item:selected {{ background-color: {theme["background_tertiary"]}; color: {theme["text_primary"]}; font-family: {font_family}; }}
            QHeaderView::section {{
                background-color: {theme["header"]};
                color: {theme["text_primary"]};
                font-family: {font_family};
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            QPushButton {{
                background-color: {theme["button"]};
                color: {theme["text_primary"]};
                font-family: {font_family};
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {theme["button_hover"]}; }}
            QPushButton:pressed {{ background-color: {theme["button_pressed"]}; }}
            QProgressBar {{
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                text-align: center;
                font-family: {font_family};
                background-color: {theme["background_tertiary"]};
            }}
            QProgressBar::chunk {{
                background-color: {theme["button"]};
                border-radius: 5px;
            }}
            QTabWidget QToolBar {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
            QListWidget {{
                background-color: {theme["header"]};
                border: none;
                outline: none;
                font-family: {font_family};
            }}
            QListWidget::item {{
                color: {theme["text_primary"]};
                font-family: {font_family};
                padding: 12px 20px;
                border: none;
            }}
            QListWidget::item:hover {{
                background-color: {theme["background_hover"]};
            }}
            QListWidget::item:selected {{
                background-color: {theme["accent"]};
                border: none;
            }}
            QTreeWidget {{
                background-color: {theme["background_tertiary"]};
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                outline: none;
                font-family: {font_family};
                selection-background-color: {theme["accent"]};
            }}
            QTreeWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {theme["border"]};
                color: {theme["text_primary"]};
                font-family: {font_family};
            }}
            QTreeWidget::item:selected {{
                background-color: transparent;
                color: {theme["text_primary"]};
                font-family: {font_family};
            }}
            QTreeWidget::item:focus {{
                background-color: transparent;
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {theme["background_tertiary"]};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {theme["border"]};
                min-height: 30px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {theme["text_secondary"]};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: {theme["background_tertiary"]};
                height: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {theme["border"]};
                min-width: 30px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {theme["text_secondary"]};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """

        self.setStyleSheet(base_style)

        transparent_btn_style = f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{ background-color: {theme["background_hover"]}; }}
            QPushButton:pressed {{ background-color: {theme["background_secondary"]}; }}
        """

        self.settings_btn.setStyleSheet(transparent_btn_style)
        if hasattr(self, "restart_as_root_btn"):
            self.restart_as_root_btn.setStyleSheet(transparent_btn_style)

        title_color = theme["text_primary"]
        secondary_text_color = theme["text_secondary"]

        if hasattr(self, "content_stack"):
            self.content_stack.setStyleSheet(
                f"background-color: {theme['background_main']};"
            )

        if hasattr(self, "sidebar"):
            self.sidebar.setStyleSheet(f"""
                QListWidget {{
                    background-color: {theme["header"]};
                    border: none;
                    outline: none;
                    font-family: {font_family};
                }}
                QListWidget::item {{
                    color: {theme["text_primary"]};
                    font-family: {font_family};
                    padding: 12px 20px;
                    border: none;
                }}
                QListWidget::item:hover {{
                    background-color: {theme["background_hover"]};
                }}
                QListWidget::item:selected {{
                    background-color: {theme["accent"]};
                    color: {theme.get("selected_tab_text", theme["text_primary"])};
                    font-family: {font_family};
                    border: none;
                }}
            """)

        if hasattr(self, "footer"):
            self.footer.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme["header"]};
                    border-top: 1px solid {theme["border"]};
                }}
                QLabel {{
                    color: {theme["text_primary"]};
                    font-family: {font_family};
                    font-size: 11px;
                    padding: 2px;
                }}
            """)

        is_root = os.geteuid() == 0
        if is_root:
            self.access_label.setStyleSheet(
                f"color: {theme['text_primary']}; font-weight: bold; margin-top: -4px;"
            )
        else:
            # In Matrix theme, Limited Access should be green, not red
            if self.current_theme == "matrix":
                self.access_label.setStyleSheet(
                    f"color: {theme['text_primary']}; font-weight: bold; margin-top: -4px;"
                )
            else:
                self.access_label.setStyleSheet(
                    "color: #ff5252; font-weight: bold; margin-top: -4px;"
                )

        if hasattr(self, "path_input"):
            self.path_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {theme["background_tertiary"]};
                    color: {theme["text_primary"]};
                    font-family: {font_family};
                    border: 1px solid {theme["border"]};
                    border-radius: 4px;
                    padding: 8px;
                }}
                QLineEdit:focus {{
                    border: 1px solid {theme["button"]};
                }}
            """)

        if hasattr(self, "cpu_graph"):
            self.cpu_graph.set_theme(self.current_theme)
        if hasattr(self, "gpu_graph"):
            self.gpu_graph.set_theme(self.current_theme)
        if hasattr(self, "ram_graph"):
            self.ram_graph.set_theme(self.current_theme)

        # Update scan button style based on theme
        if hasattr(self, "scan_btn") and not self.is_scanning:
            self.update_scan_button_idle_style()

        # Update graph colors
        if hasattr(self, "cpu_graph"):
            self.cpu_graph.set_color(theme["graph_cpu"])
        if hasattr(self, "gpu_graph"):
            self.gpu_graph.set_color(theme["graph_gpu"])
        if hasattr(self, "ram_graph"):
            self.ram_graph.set_color(theme["graph_ram"], theme["graph_swap"])

        self.refresh_tables_theme(theme)

        # Update button icons for Matrix theme
        if self.current_theme == "matrix":
            if hasattr(self, "settings_btn") and hasattr(self, "settings_icon_green"):
                self.settings_btn.setIcon(self.settings_icon_green)
            if hasattr(self, "restart_as_root_btn") and hasattr(
                self, "up_arrow_icon_green"
            ):
                self.restart_as_root_btn.setIcon(self.up_arrow_icon_green)
        else:
            # Reset to default icons
            if hasattr(self, "settings_btn"):
                self.settings_btn.setIcon(
                    QIcon(os.path.join(get_base_path(), "icons", "ui", "settings.png"))
                )
            if hasattr(self, "restart_as_root_btn"):
                self.restart_as_root_btn.setIcon(
                    QIcon(os.path.join(get_base_path(), "icons", "ui", "up-arrow.png"))
                )

        # Update tab icons immediately after theme change
        if hasattr(self, "tabs"):
            self.update_tab_icons(self.tabs.currentIndex())

    def refresh_tables_theme(self, theme):
        """Update button icons and styles in tables when theme changes."""
        # Update USB table buttons (remove buttons)
        if hasattr(self, "usb_table") and self.usb_table is not None:
            for row in range(self.usb_table.rowCount()):
                widget = self.usb_table.cellWidget(row, 7)
                if widget and widget.layout():
                    # Get buttons from layout
                    layout = widget.layout()
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item and item.widget():
                            btn = item.widget()
                            if (
                                isinstance(btn, QPushButton)
                                and btn.toolTip() == "Detach USB device"
                            ):
                                # Update icon
                                if self.current_theme == "matrix" and hasattr(
                                    self, "remove_icon_green"
                                ):
                                    btn.setIcon(self.remove_icon_green)
                                else:
                                    remove_icon_path = os.path.join(
                                        get_base_path(), "icons", "ui", "remove.png"
                                    )
                                    if os.path.exists(remove_icon_path):
                                        btn.setIcon(QIcon(remove_icon_path))
                                # Update style
                                if self.current_theme == "matrix":
                                    btn.setStyleSheet("""
                                        QPushButton {
                                            background-color: transparent;
                                            border: none;
                                            border-radius: 4px;
                                        }
                                        QPushButton:hover {
                                            background-color: #1a331a;
                                        }
                                    """)
                                elif self.current_theme == "light":
                                    btn.setStyleSheet("""
                                        QPushButton {
                                            background-color: transparent;
                                            border: none;
                                            border-radius: 4px;
                                        }
                                        QPushButton:hover {
                                            background-color: #e5e5e5;
                                        }
                                    """)
                                else:
                                    btn.setStyleSheet("""
                                        QPushButton {
                                            background-color: transparent;
                                            border: none;
                                            border-radius: 4px;
                                        }
                                        QPushButton:hover {
                                            background-color: #505050;
                                        }
                                    """)

        # Update Storage table buttons (folder and delete buttons)
        if hasattr(self, "files_table"):
            for row in range(self.files_table.rowCount()):
                widget = self.files_table.cellWidget(row, 2)
                if widget:
                    buttons = widget.findChildren(QPushButton)
                    for btn in buttons:
                        tooltip = btn.toolTip()
                        if tooltip == "Open folder":
                            # Update folder icon
                            if self.current_theme == "matrix" and hasattr(
                                self, "folder_icon_green"
                            ):
                                btn.setIcon(self.folder_icon_green)
                            else:
                                btn.setIcon(
                                    QIcon(
                                        os.path.join(
                                            get_base_path(), "icons", "ui", "folder.png"
                                        )
                                    )
                                )
                        elif tooltip == "Delete file":
                            # Update delete icon
                            if self.current_theme == "matrix" and hasattr(
                                self, "trash_icon_green"
                            ):
                                btn.setIcon(self.trash_icon_green)
                            else:
                                btn.setIcon(
                                    QIcon(
                                        os.path.join(
                                            get_base_path(), "icons", "ui", "trash.png"
                                        )
                                    )
                                )

                        # Update style based on theme
                        if self.current_theme == "matrix":
                            btn.setStyleSheet("""
                                QPushButton {
                                    background-color: transparent;
                                    border: none;
                                    border-radius: 3px;
                                }
                                QPushButton:hover {
                                    background-color: #1a331a;
                                }
                            """)
                        elif self.current_theme == "light":
                            btn.setStyleSheet("""
                                QPushButton {
                                    background-color: transparent;
                                    border: none;
                                    border-radius: 3px;
                                }
                                QPushButton:hover {
                                    background-color: #e5e5e5;
                                }
                            """)
                        else:
                            btn.setStyleSheet("""
                                QPushButton {
                                    background-color: transparent;
                                    border: none;
                                    border-radius: 3px;
                                }
                                QPushButton:hover {
                                    background-color: #404040;
                                }
                            """)

    def get_theme_color(self, key):
        if self.current_theme == "dark":
            theme = ThemeManager.DARK
        elif self.current_theme == "light":
            theme = ThemeManager.LIGHT
        else:
            theme = ThemeManager.MATRIX
        return theme.get(key, "#000000")

    def closeEvent(self, a0):
        self.stats_thread.stop()
        super().closeEvent(a0)
