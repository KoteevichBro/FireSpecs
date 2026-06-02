from PyQt5.QtWidgets import (
    QApplication,
    QAbstractScrollArea,
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
import os
import shutil
import subprocess
import sys

from app.display_scale import scaled
from app.i18n import (
    LANGUAGE_NAMES,
    SIDEBAR_KEYS,
    SUPPORTED_LANGUAGES,
    Translator,
    normalize_language,
)
from app.privilege import PrivilegeManager
from app.ui_session import (
    capture_session_from_window,
    load_ui_session,
    resolve_window_geometry,
    save_ui_session,
)
from app.gpu_memory import collect_live_gpu_memory
from app.gpu_stats import collect_live_gpu_stats
from app.paths import get_base_path
from app.platform_users import get_desktop_env
from app.system_theme import resolve_startup_theme
from app.custom_title_bar import CustomTitleBar
from app import themed_dialogs
from app.window_chrome import (
    apply_native_window_chrome,
    setup_window_decorations,
    should_use_custom_title_bar,
)


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
                cpu_temp = 0.0
                try:
                    sensor_map = psutil.sensors_temperatures()
                    temps = []
                    for name, entries in (sensor_map or {}).items():
                        if "coretemp" in name or "cpu" in name.lower():
                            for entry in entries:
                                if hasattr(entry, "current") and entry.current is not None:
                                    temps.append(float(entry.current))
                    if temps:
                        cpu_temp = sum(temps) / len(temps)
                except (AttributeError, OSError, RuntimeError):
                    pass

                cpu_freq = psutil.cpu_freq()
                freq_text = ""
                if cpu_freq and cpu_freq.current:
                    freq_text = f" | Freq: {cpu_freq.current:.0f} MHz"

                ram = psutil.virtual_memory()
                swap = psutil.swap_memory()

                gpu_live = collect_live_gpu_stats()
                gpu_mem = collect_live_gpu_memory(
                    card_path=gpu_live.get("card_path"),
                )

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
                        "gpu_text": gpu_live["gpu_text"],
                        "gpu_percent": gpu_live["utilization"],
                        "gpu_temp": gpu_live.get("temp_c", 0.0),
                        "gpu_pci_slot": gpu_mem.get("pci_slot"),
                        "gpu_memory_used": gpu_mem.get("memory_used", ""),
                        "gpu_memory_free": gpu_mem.get("memory_free", ""),
                        "gpu_memory_percent": gpu_mem.get("memory_percent", ""),
                        "gpu_shared_memory_used": gpu_mem.get(
                            "shared_memory_used", ""
                        ),
                    }
                )

            except Exception:
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
    def __init__(self, color, show_temp=False, swap_color=None, ui_scale=1.0):
        super().__init__()
        self.color = color
        self.swap_color = swap_color
        self.history = [0] * 60
        self.swap_history = [0] * 60 if swap_color else None
        self.temperature = 0
        self.show_temp = show_temp
        self.ui_scale = ui_scale
        self.setFixedHeight(scaled(44, ui_scale))
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

        temp_gutter = scaled(58, self.ui_scale)
        graph_width = width
        if self.show_temp:
            graph_width = width - temp_gutter

        points = []
        for i, value in enumerate(self.history):
            x = (i / (len(self.history) - 1)) * graph_width
            y = height - (value / 100) * height
            points.append(QPointF(x, y))

        pen = QPen(self.color, max(2, scaled(2, self.ui_scale)))
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
            swap_pen = QPen(swap_color, max(2, scaled(2, self.ui_scale)))
            painter.setPen(swap_pen)
            painter.drawPolyline(QPolygonF(swap_points))

        if self.show_temp:
            rect_size = scaled(38, self.ui_scale)
            rect_x = width - rect_size - scaled(6, self.ui_scale)
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
            painter.setFont(QFont("Arial", scaled(11, self.ui_scale), QFont.Bold))
            fm = painter.fontMetrics()
            text_width = (
                fm.horizontalAdvance(temp_text)
                if hasattr(fm, "horizontalAdvance")
                else fm.width(temp_text)
            )
            text_height = fm.height()
            text_x = rect_x + (rect_size - text_width) / 2
            text_y = rect_y + (rect_size - text_height) / 2 + fm.ascent()
            painter.drawText(int(text_x), int(text_y), temp_text)


from app.hardware import (
    get_all_hardware_info,
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


def create_icon_value_widget(text, icon_path=None):
    """
    Value cell: text on the left, logo immediately after the text (left-aligned).

    Every value cell in a table that contains a logo uses this same widget, so
    all rows share identical geometry and line up flush — no per-row indent.
    """
    widget = QWidget()
    widget.setObjectName("value_icon_cell")
    widget.setStyleSheet("background: transparent;")

    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 2, 8, 2)
    layout.setSpacing(8)

    label = QLabel(str(text))
    label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    label.setStyleSheet("background: transparent;")
    label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
    layout.addWidget(label, 0, Qt.AlignLeft | Qt.AlignVCenter)

    if icon_path and os.path.exists(icon_path):
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            scaled = pixmap.scaledToHeight(24, Qt.SmoothTransformation)
            icon_label = QLabel()
            icon_label.setPixmap(scaled)
            icon_label.setFixedSize(scaled.size())
            icon_label.setStyleSheet("background: transparent;")
            layout.addWidget(icon_label, 0, Qt.AlignLeft | Qt.AlignVCenter)

    layout.addStretch(1)

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
        session = load_ui_session()
        self._ui_session = session
        self.translator = Translator(session.get("language"))
        from app.display_scale import resolve_ui_scale

        self.ui_scale = resolve_ui_scale()
        self.privileges = PrivilegeManager()
        x, y, width, height = resolve_window_geometry()
        self.setGeometry(x, y, width, height)
        self.setMinimumSize(
            max(800, int(width * 0.8)), max(600, int(height * 0.75))
        )

        self.scan_animation_chars = ["|", "/", "-", "\\"]
        self.scan_animation_index = 0
        self.scan_animation_timer = QTimer()
        self.scan_animation_timer.timeout.connect(self.update_scan_button_animation)
        self.is_scanning = False
        self.scan_button_original_text = ""

        self._gpu_hardware_live_updates = []
        self._storage_i18n_widgets = {}

        self.stats_thread = StatsUpdateThread()
        self.stats_thread.stats_updated.connect(self.update_graphs)
        self.stats_thread.start()
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QTabWidget::pane { border: 1px solid #3d3d3d; }
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
            QTableWidget::item { padding: 4px 8px; }
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
        self.retranslate_ui(refresh_usb=False, rebuild_hardware=False)

    def tr(self, key, **kwargs):
        return self.translator.translate(key, **kwargs)

    def _set_tab_key(self, index, tab_key):
        widget = self.tabs.widget(index)
        if widget is not None:
            widget.setProperty("firespecs_tab", tab_key)

    def _tab_key(self, index):
        widget = self.tabs.widget(index)
        if widget is None:
            return None
        return widget.property("firespecs_tab")

    def _tab_index(self, tab_key):
        for i in range(self.tabs.count()):
            if self._tab_key(i) == tab_key:
                return i
        return -1

    def set_language(self, language_code):
        language_code = normalize_language(language_code)
        if language_code == self.translator.language:
            return
        self.translator.set_language(language_code)
        session = load_ui_session()
        session["language"] = language_code
        save_ui_session(session)
        self.retranslate_ui()

    def _apply_tab_labels(self):
        for i in range(self.tabs.count()):
            tab_key = self._tab_key(i)
            if tab_key == "hardware":
                self.tabs.setTabText(i, self.tr("tab.hardware"))
            elif tab_key == "usb":
                self.tabs.setTabText(i, self.tr("tab.usb_devices"))
            elif tab_key == "storage":
                self.tabs.setTabText(i, self.tr("tab.storage"))

    def _retranslate_usb_tab_in_place(self):
        """Update USB tab strings without rebuilding the whole tab."""
        usb_widgets = getattr(self, "_usb_i18n_widgets", None)
        if usb_widgets and usb_widgets.get("title") is not None:
            usb_widgets["title"].setText(self.tr("tab.usb_devices"))

        table = getattr(self, "usb_table", None)
        if table is None:
            return

        table.setHorizontalHeaderLabels(
            [
                self.tr("usb.header_number"),
                self.tr("usb.header_vendor"),
                self.tr("usb.header_product"),
                self.tr("usb.header_id"),
                self.tr("usb.header_serial"),
                self.tr("usb.header_class"),
                self.tr("usb.header_speed"),
                self.tr("usb.header_actions"),
            ]
        )
        for row in range(table.rowCount()):
            widget = table.cellWidget(row, 7)
            if not widget:
                continue
            for btn in widget.findChildren(QPushButton):
                if btn.property("firespecs_action") == "detach_usb":
                    btn.setToolTip(self.tr("usb.detach_tooltip"))

        QTimer.singleShot(0, self._refit_usb_table)

    def retranslate_ui(self, refresh_usb=True, rebuild_hardware=True):
        hardware_row = None
        if rebuild_hardware and hasattr(self, "sidebar"):
            hardware_row = self.sidebar.currentRow()

        self.setUpdatesEnabled(False)
        try:
            window_title = self.tr("app.window_title")
            if getattr(self, "custom_title_bar", None):
                self.custom_title_bar.set_title(window_title)
            else:
                self.setWindowTitle(window_title)
            if hasattr(self, "settings_btn"):
                self.settings_btn.setToolTip(self.tr("settings.tooltip"))
            self.scan_button_original_text = self.tr("storage.scan_button")
            if hasattr(self, "scan_btn") and not self.is_scanning:
                self.scan_btn.setText(self.scan_button_original_text)

            if hasattr(self, "sidebar"):
                for i, key in enumerate(SIDEBAR_KEYS):
                    if i < self.sidebar.count():
                        self.sidebar.item(i).setText(self.tr(key))

            if refresh_usb and self._tab_index("usb") >= 0:
                self._retranslate_usb_tab_in_place()

            storage = self._storage_i18n_widgets
            if storage.get("partitions_group"):
                storage["partitions_group"].setTitle(
                    self.tr("storage.disk_partitions")
                )
            if storage.get("files_group"):
                storage["files_group"].setTitle(self.tr("storage.largest_files"))
            if storage.get("scan_hint"):
                storage["scan_hint"].setText(self.tr("storage.scan_hint"))
            if storage.get("path_label"):
                storage["path_label"].setText(self.tr("storage.path_label"))
            if hasattr(self, "files_table"):
                self.files_table.setHorizontalHeaderLabels(
                    [
                        self.tr("storage.file_path"),
                        self.tr("storage.size"),
                        self.tr("storage.actions"),
                    ]
                )
                for row in range(self.files_table.rowCount()):
                    widget = self.files_table.cellWidget(row, 2)
                    if not widget:
                        continue
                    for btn in widget.findChildren(QPushButton):
                        action = btn.property("firespecs_action")
                        if action == "open_folder":
                            btn.setToolTip(self.tr("storage.open_folder"))
                        elif action == "delete_file":
                            btn.setToolTip(self.tr("storage.delete_file"))

            self._update_access_state()
            self._apply_tab_labels()
        finally:
            self.setUpdatesEnabled(True)

        if rebuild_hardware and hasattr(self, "content_stack"):
            self._populate_hardware_panels(self._fetch_hardware_info())
            if hasattr(self, "sidebar") and hardware_row is not None and hardware_row >= 0:
                self.sidebar.setCurrentRow(
                    min(hardware_row, self.sidebar.count() - 1)
                )
            QTimer.singleShot(0, self._refit_hardware_tables)

    def init_ui(self):
        setup_window_decorations(self)
        self._use_custom_title_bar = should_use_custom_title_bar()
        self.custom_title_bar = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if self._use_custom_title_bar:
            self.custom_title_bar = CustomTitleBar(self)
            self.custom_title_bar.set_title(self.tr("app.window_title"))
            layout.addWidget(self.custom_title_bar)

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

        access_widget = QWidget()
        access_widget.setStyleSheet("background: transparent;")
        access_layout = QHBoxLayout(access_widget)
        access_layout.setContentsMargins(12, 4, 15, 4)
        access_layout.setSpacing(10)
        access_layout.setAlignment(Qt.Alignment(Qt.AlignmentFlag.AlignVCenter))

        self.access_label = QLabel()
        self.access_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.access_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)

        self.privilege_btn = QPushButton()
        self.privilege_btn.setIcon(
            QIcon(os.path.join(get_base_path(), "icons", "ui", "up-arrow.png"))
        )
        self.privilege_btn.setFixedSize(28, 28)
        self.privilege_btn.setIconSize(QSize(14, 14))
        self.privilege_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #3d3d3d; }
            QPushButton:pressed { background-color: #2d2d2d; }
        """)
        self.privilege_btn.clicked.connect(self.toggle_full_access)

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
        self.settings_btn.clicked.connect(self.show_settings_menu)

        self.current_theme = resolve_startup_theme(self._ui_session.get("theme"))

        access_layout.addStretch()
        access_layout.addWidget(self.access_label, 0, Qt.AlignmentFlag.AlignVCenter)
        access_layout.addWidget(self.privilege_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        access_layout.addWidget(self.settings_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._update_access_state()

        layout.addWidget(self.tabs)
        self.tabs.setCornerWidget(access_widget)

        self.tabs.currentChanged.connect(self._on_main_tab_changed)

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

        for key in SIDEBAR_KEYS:
            self.sidebar.addItem(QListWidgetItem(self.tr(key)))

        self.content_stack = QStackedWidget()

        layout.addWidget(self.sidebar)
        layout.addWidget(self.content_stack)

        self.sidebar.currentRowChanged.connect(self.content_stack.setCurrentIndex)
        self.sidebar.currentRowChanged.connect(
            lambda _row: QTimer.singleShot(0, self._refit_hardware_tables)
        )
        self._populate_hardware_panels(self._fetch_hardware_info())
        self.sidebar.setCurrentRow(0)

        hw_index = self.tabs.addTab(
            hardware_tab,
            QIcon(os.path.join(get_base_path(), "icons", "ui", "hardware-icon.png")),
            self.tr("tab.hardware"),
        )
        self._set_tab_key(hw_index, "hardware")

    def _fetch_hardware_info(self):
        """Hardware snapshot; uses the root helper when full access is enabled."""
        if getattr(self, "privileges", None) and self.privileges.active:
            privileged = self.privileges.fetch_hardware_info()
            if privileged:
                return privileged
        return get_all_hardware_info()

    def _populate_hardware_panels(self, hw_info):
        """Build or rebuild all Hardware sidebar panels from a hardware snapshot."""
        if not hasattr(self, "content_stack"):
            return

        self._gpu_hardware_live_updates = []

        current_index = self.content_stack.currentIndex()
        while self.content_stack.count():
            widget = self.content_stack.widget(0)
            self.content_stack.removeWidget(widget)
            widget.deleteLater()

        system_widget = self.create_info_widget(
            self.tr("sidebar.system_information"),
            self.translator.tr_dict(
                {
                    "hw.distribution": hw_info["system"]["distribution"],
                    "hw.version": hw_info["system"]["version"],
                    "hw.kernel": hw_info["system"]["kernel"],
                    "hw.codename": hw_info["system"]["codename"],
                    "hw.hostname": hw_info["system"]["hostname"],
                    "hw.architecture": hw_info["system"]["architecture"],
                }
            ),
        )

        cpu_data = {
            "hw.model": hw_info["cpu"]["model"],
            "hw.physical_cores": hw_info["cpu"]["cores_physical"],
            "hw.logical_cores": hw_info["cpu"]["cores_logical"],
            "hw.max_frequency": hw_info["cpu"].get("frequency_max", "N/A"),
            "hw.min_frequency": hw_info["cpu"].get("frequency_min", "N/A"),
            "hw.current_frequency": hw_info["cpu"].get("frequency_current", "N/A"),
        }
        if "cache" in hw_info["cpu"]:
            cpu_data["hw.cache"] = hw_info["cpu"]["cache"]
        if hw_info["cpu"].get("instructions"):
            cpu_data["hw.instructions"] = hw_info["cpu"]["instructions"]
        cpu_widget = self.create_info_widget(
            self.tr("sidebar.cpu"),
            self.translator.tr_dict(cpu_data),
            icon_type="cpu",
            icon_key=self.tr("hw.model"),
        )

        memory_widget = self.create_memory_widget(
            hw_info["memory"], hw_info.get("ram_sticks", [])
        )

        mb_widget = self.create_info_widget(
            self.tr("sidebar.motherboard"),
            self.translator.tr_dict(
                {
                    "hw.manufacturer": hw_info["motherboard"]["manufacturer"],
                    "hw.product_name": hw_info["motherboard"]["product_name"],
                    "hw.version": hw_info["motherboard"]["version"],
                    "hw.serial_number": hw_info["motherboard"]["serial_number"],
                    "hw.asset_tag": hw_info["motherboard"]["asset_tag"],
                }
            ),
        )

        bios_widget = self.create_info_widget(
            self.tr("sidebar.bios_information"),
            self.translator.tr_dict(
                {
                    "hw.vendor": hw_info["bios"]["vendor"],
                    "hw.version": hw_info["bios"]["version"],
                    "hw.release_date": hw_info["bios"]["release_date"],
                    "hw.revision": hw_info["bios"]["revision"],
                }
            ),
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

        if 0 <= current_index < self.content_stack.count():
            self.content_stack.setCurrentIndex(current_index)

    def refresh_application_data(self):
        """Reload data that depends on root access (DMI, USB, etc.)."""
        if hasattr(self, "content_stack"):
            row = self.sidebar.currentRow() if hasattr(self, "sidebar") else 0
            self._populate_hardware_panels(self._fetch_hardware_info())
            if hasattr(self, "sidebar") and row >= 0:
                self.sidebar.setCurrentRow(min(row, self.sidebar.count() - 1))
        if hasattr(self, "usb_table"):
            self.refresh_usb_tab()
        QTimer.singleShot(0, self._refit_all_tables)

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

    def _configure_table_widget(self, table):
        """Tables scroll with the page, not inside each cell."""
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setWordWrap(True)
        table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        table.setViewportMargins(0, 0, 0, 0)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

    def fit_table_rows(self, table):
        """Resize each row to the height Qt assigns for its cell content."""
        if table.rowCount() == 0:
            return

        self._configure_table_widget(table)
        for row in range(table.rowCount()):
            table.resizeRowToContents(row)
        table.viewport().update()
        QApplication.processEvents()
        for row in range(table.rowCount()):
            table.resizeRowToContents(row)

    def _table_content_height(self, table):
        """Pixel-exact widget height: header + laid-out rows + frame (no slack)."""
        header = table.horizontalHeader()
        header_h = header.height()
        if header_h <= 0:
            header_h = header.sizeHint().height()

        if table.rowCount() == 0:
            return header_h + 2 * table.frameWidth()

        table.viewport().update()
        QApplication.processEvents()

        last_row = table.rowCount() - 1
        body_h = table.rowViewportPosition(last_row) + table.rowHeight(last_row)
        return header_h + body_h + 2 * table.frameWidth()

    def _prepare_table_for_height_measure(self, table):
        """Restore column widths before measuring two-column hardware tables while hidden."""
        if table.columnCount() != 2:
            return
        width = table.columnWidth(0)
        if 0 < width < 120:
            table.setColumnWidth(0, 180)

    def _table_layout_ready(self, table):
        """Return False when a hidden hardware table has a stale property-column width."""
        if table.columnCount() != 2:
            return True
        width = table.columnWidth(0)
        if width <= 0:
            return True
        return width >= 120

    def _refit_usb_table(self):
        """Resize the USB devices table to its content (headers, rows, action buttons)."""
        table = getattr(self, "usb_table", None)
        if table is None or table.rowCount() == 0:
            return
        try:
            self.set_table_fixed_height(table)
        except RuntimeError:
            return

    def _refit_hardware_tables(self):
        """Refit tables on the active Hardware sidebar page after layout is known."""
        if not hasattr(self, "content_stack"):
            return

        scroll = self.content_stack.currentWidget()
        if scroll is None:
            return

        inner = scroll.widget() if hasattr(scroll, "widget") else None
        if inner is None:
            return

        for table in inner.findChildren(QTableWidget):
            if table.rowCount() == 0:
                continue
            try:
                self._prepare_table_for_height_measure(table)
                self.set_table_fixed_height(table)
            except RuntimeError:
                continue

    def _sync_table_viewport_height(self, table):
        """Nudge fixed height so the viewport matches the last row (no clip or gap)."""
        if table.rowCount() == 0:
            return

        last_row = table.rowCount() - 1
        need = table.rowViewportPosition(last_row) + table.rowHeight(last_row)
        delta = need - table.viewport().height()
        if delta != 0:
            table.setFixedHeight(table.height() + delta)
            table.viewport().update()

    def set_table_fixed_height(self, table):
        """Crop the table widget to its content — no internal scrollbars or dead space."""
        self.fit_table_rows(table)
        total_height = self._table_content_height(table)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        table.setFixedHeight(total_height)
        table.viewport().update()
        QApplication.processEvents()
        if table.isVisible():
            self._sync_table_viewport_height(table)

    def _refit_all_tables(self):
        for table in self.findChildren(QTableWidget):
            try:
                if table.rowCount() == 0:
                    continue
                if not self._table_layout_ready(table):
                    continue
                self._prepare_table_for_height_measure(table)
                self.set_table_fixed_height(table)
            except RuntimeError:
                continue

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
        table.setHorizontalHeaderLabels(
            [self.tr("table.property"), self.tr("table.value")]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(data))
        table.setColumnWidth(0, 180)

        has_logo = bool(icon_type and icon_key)
        for i, (key, value) in enumerate(data.items()):
            table.setItem(i, 0, QTableWidgetItem(key))

            if has_logo:
                # Whole value column uses the same widget so every row aligns.
                icon_path = (
                    get_device_icon(str(value), icon_type) if key == icon_key else None
                )
                table.setCellWidget(i, 1, create_icon_value_widget(value, icon_path))
            else:
                value_item = QTableWidgetItem(str(value))
                if len(str(value)) > 48:
                    value_item.setTextAlignment(
                        Qt.AlignLeft | Qt.AlignVCenter
                    )
                    table.setItem(i, 1, value_item)
                    table.item(i, 1).setToolTip(str(value))
                else:
                    table.setItem(i, 1, value_item)

        self.set_table_fixed_height(table)

        layout.addWidget(table)
        layout.addStretch()
        return widget

    def create_memory_widget(self, memory_info, ram_sticks):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(self.tr("sidebar.ram"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        memory_data = {"hw.total_ram": memory_info["total"]}

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(
            [self.tr("table.property"), self.tr("table.value")]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(memory_data))
        table.setColumnWidth(0, 180)

        memory_rows = self.translator.tr_dict(memory_data)
        for i, (key, value) in enumerate(memory_rows.items()):
            table.setItem(i, 0, QTableWidgetItem(key))
            table.setItem(i, 1, QTableWidgetItem(str(value)))

        self.set_table_fixed_height(table)

        layout.addWidget(table)

        if ram_sticks:
            sticks_group = QGroupBox(self.tr("ram.sticks"))
            sticks_layout = QVBoxLayout()

            sticks_table = QTableWidget()
            sticks_table.setColumnCount(7)
            sticks_table.setHorizontalHeaderLabels(
                [
                    self.tr("ram.size"),
                    self.tr("ram.locator"),
                    self.tr("ram.type"),
                    self.tr("ram.speed"),
                    self.tr("hw.manufacturer"),
                    self.tr("ram.part_number"),
                    self.tr("ram.serial"),
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

        title_label = QLabel(self.tr("sidebar.gpu"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        for gpu in gpu_data:
            group = QGroupBox(
                self.tr("gpu.group", n=gpu_data.index(gpu) + 1)
            )
            group_layout = QVBoxLayout()

            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(
                [self.tr("table.property"), self.tr("table.value")]
            )
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)

            gpu_items = []

            def _gpu_row(label, value, live_key=None):
                gpu_items.append((label, value, live_key))

            _gpu_row(self.tr("gpu.device"), gpu.get("device", "Unknown"))
            _gpu_row(self.tr("gpu.bus"), gpu.get("bus", "Unknown"))
            if gpu.get("pci_slot"):
                _gpu_row(self.tr("gpu.pci_address"), gpu["pci_slot"])
            if gpu.get("driver_kernel"):
                _gpu_row(self.tr("gpu.kernel_driver"), gpu["driver_kernel"])
            if "renderer" in gpu:
                _gpu_row(self.tr("gpu.opengl_renderer"), gpu["renderer"])
            if "driver" in gpu:
                _gpu_row(self.tr("gpu.driver_version"), gpu["driver"])

            mem_label = gpu.get("memory_label", "Memory")
            has_vram = bool(gpu.get("memory_total") or gpu.get("memory_total_bytes"))
            live_row_map = {}

            if gpu.get("memory_total"):
                _gpu_row(
                    self.tr("gpu.memory_total", label=mem_label),
                    gpu["memory_total"],
                )
            if gpu.get("shared_memory_total"):
                _gpu_row(
                    self.tr("gpu.shared_memory_total"), gpu["shared_memory_total"]
                )
            if has_vram:
                _gpu_row(
                    self.tr("gpu.memory_used", label=mem_label),
                    gpu.get("memory_used", "—"),
                    "memory_used",
                )
                _gpu_row(
                    self.tr("gpu.memory_free", label=mem_label),
                    gpu.get("memory_free", "—"),
                    "memory_free",
                )
                _gpu_row(
                    self.tr("gpu.memory_usage", label=mem_label),
                    gpu.get("memory_percent", "—"),
                    "memory_percent",
                )
            if gpu.get("shared_memory_total"):
                _gpu_row(
                    self.tr("gpu.shared_memory_used"),
                    gpu.get("shared_memory_used", "—"),
                    "shared_memory_used",
                )

            table.setRowCount(len(gpu_items))

            for j, (key, value, live_key) in enumerate(gpu_items):
                table.setItem(j, 0, QTableWidgetItem(key))

                if key == self.tr("gpu.device"):
                    icon_path = get_device_icon(str(value), "gpu")
                    table.setCellWidget(
                        j, 1, create_icon_value_widget(value, icon_path)
                    )
                else:
                    value_item = QTableWidgetItem(str(value))
                    table.setItem(j, 1, value_item)
                    if live_key:
                        live_row_map[live_key] = value_item

            if live_row_map:
                self._gpu_hardware_live_updates.append(
                    {
                        "pci_slot": gpu.get("pci_slot"),
                        "rows": live_row_map,
                    }
                )

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

        title_label = QLabel(self.tr("sidebar.network"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(
            [
                self.tr("table.interface"),
                self.tr("table.ip_address"),
                self.tr("table.mac_address"),
            ]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setRowCount(len(network_data))
        table.setColumnWidth(0, 120)
        table.setColumnWidth(1, 150)

        for i, net in enumerate(network_data):
            table.setItem(i, 0, QTableWidgetItem(net["interface"]))
            table.setItem(i, 1, QTableWidgetItem(net["ip"]))
            table.setItem(i, 2, QTableWidgetItem(net["mac"]))

        self.set_table_fixed_height(table)

        layout.addWidget(table)
        layout.addStretch()

        return widget

    def create_display_widget(self, display_data):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(self.tr("sidebar.display"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        if not display_data or (
            len(display_data) == 1 and display_data[0].get("_placeholder")
        ):
            no_display_label = QLabel(self.tr("display.empty_message"))
            no_display_label.setObjectName("secondary_label")
            layout.addWidget(no_display_label)
        else:
            for i, display in enumerate(display_data, 1):
                group = QGroupBox(self.tr("display.group", n=i))
                group_layout = QVBoxLayout()

                table = QTableWidget()
                table.setColumnCount(2)
                table.setHorizontalHeaderLabels(
                    [self.tr("table.property"), self.tr("table.value")]
                )
                table.horizontalHeader().setStretchLastSection(True)
                table.verticalHeader().setVisible(False)
                table.setColumnWidth(0, 180)

                display_items = []
                display_items.append(
                    ("display.name", display.get("name", "Unknown"))
                )
                display_items.append(
                    ("display.model", display.get("model", "Unknown"))
                )
                vendor = display.get("vendor", "Unknown")
                if vendor != "Unknown":
                    display_items.append(("display.vendor_id", vendor))
                if "serial" in display and display["serial"] != "Unknown":
                    display_items.append(("display.serial", display["serial"]))
                if "native_resolution" in display:
                    display_items.append(
                        ("display.native_resolution", display["native_resolution"])
                    )
                elif "max_resolution" in display:
                    display_items.append(
                        ("display.native_resolution", display["max_resolution"])
                    )
                if "current_resolution" in display:
                    display_items.append(
                        ("display.active_resolution", display["current_resolution"])
                    )
                if "desktop_resolution" in display:
                    display_items.append(
                        ("display.desktop_scaled", display["desktop_resolution"])
                    )
                if "max_resolution" in display and "native_resolution" not in display:
                    display_items.append(
                        ("display.max_resolution", display["max_resolution"])
                    )
                if "max_refresh_rate" in display:
                    display_items.append(
                        ("display.max_refresh_rate", display["max_refresh_rate"])
                    )
                if "physical_size" in display:
                    display_items.append(
                        ("display.physical_size", display["physical_size"])
                    )
                if (
                    "manufacture_date" in display
                    and display["manufacture_date"] != "Unknown"
                ):
                    display_items.append(
                        ("display.manufacture_date", display["manufacture_date"])
                    )
                if "rotation" in display:
                    display_items.append(("display.rotation", display["rotation"]))
                if "primary" in display:
                    display_items.append(("display.primary", display["primary"]))

                table.setRowCount(len(display_items))

                for j, (key, value) in enumerate(display_items):
                    table.setItem(j, 0, QTableWidgetItem(self.tr(key)))
                    table.setItem(j, 1, QTableWidgetItem(str(value)))

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

        title_label = QLabel(self.tr("sidebar.drives"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        if not drives_data or (
            len(drives_data) == 1 and drives_data[0].get("_placeholder")
        ):
            no_drives_label = QLabel(self.tr("drive.empty_message"))
            no_drives_label.setObjectName("secondary_label")
            layout.addWidget(no_drives_label)
        else:
            for i, drive in enumerate(drives_data, 1):
                group = QGroupBox(self.tr("drive.group", n=i))
                group_layout = QVBoxLayout()

                table = QTableWidget()
                table.setColumnCount(2)
                table.setHorizontalHeaderLabels(
                    [self.tr("table.property"), self.tr("table.value")]
                )
                table.horizontalHeader().setStretchLastSection(True)
                table.verticalHeader().setVisible(False)

                drive_items = []
                drive_items.append(("drive.name", drive.get("name", "Unknown")))
                drive_items.append(("display.model", drive.get("model", "Unknown")))
                if "serial" in drive and drive["serial"] != "N/A":
                    drive_items.append(("drive.serial", drive["serial"]))
                if "size" in drive:
                    drive_items.append(("drive.size", drive["size"]))
                if "type" in drive:
                    drive_items.append(("drive.type", drive["type"]))
                if "mountpoint" in drive and drive["mountpoint"] != "N/A":
                    drive_items.append(("drive.mount_point", drive["mountpoint"]))
                if "readonly" in drive:
                    drive_items.append(("drive.read_only", drive["readonly"]))
                if "removable" in drive:
                    drive_items.append(("drive.removable", drive["removable"]))

                table.setRowCount(len(drive_items))

                for j, (key, value) in enumerate(drive_items):
                    table.setItem(j, 0, QTableWidgetItem(self.tr(key)))
                    table.setItem(j, 1, QTableWidgetItem(str(value)))

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

        title_label = QLabel(self.tr("sidebar.battery"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        if not battery_data.get("present", False):
            no_battery_label = QLabel(self.tr("battery.empty_message"))
            no_battery_label.setObjectName("secondary_label")
            layout.addWidget(no_battery_label)
        else:
            table = QTableWidget()
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(
                [self.tr("table.property"), self.tr("table.value")]
            )
            table.horizontalHeader().setStretchLastSection(True)
            table.verticalHeader().setVisible(False)
            table.setColumnWidth(0, 180)

            battery_items = []
            battery_items.append(
                ("battery.status", battery_data.get("status", "Unknown"))
            )
            battery_items.append(
                ("battery.charge_level", battery_data.get("percent", "Unknown"))
            )
            battery_items.append(
                ("battery.power_plugged", battery_data.get("power_plugged", "Unknown"))
            )
            battery_items.append(
                ("battery.time_remaining", battery_data.get("time_left", "Unknown"))
            )

            if battery_data.get("health") != "N/A":
                battery_items.append(("battery.health", battery_data.get("health")))
            if battery_data.get("technology") != "N/A":
                battery_items.append(
                    ("battery.technology", battery_data.get("technology"))
                )
            if battery_data.get("cycle_count") != "N/A":
                battery_items.append(
                    ("battery.cycle_count", battery_data.get("cycle_count"))
                )

            table.setRowCount(len(battery_items))

            for j, (key, value) in enumerate(battery_items):
                table.setItem(j, 0, QTableWidgetItem(self.tr(key)))
                table.setItem(j, 1, QTableWidgetItem(str(value)))

            self.set_table_fixed_height(table)
            layout.addWidget(table)

        layout.addStretch()
        return widget

    def create_usb_tab(self, insert_at_index=None):
        content = QWidget()
        layout = QVBoxLayout(content)

        usb_data = get_usb_devices()

        title_label = QLabel(self.tr("tab.usb_devices"))
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setObjectName("info_title")
        layout.addWidget(title_label)

        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            [
                self.tr("usb.header_number"),
                self.tr("usb.header_vendor"),
                self.tr("usb.header_product"),
                self.tr("usb.header_id"),
                self.tr("usb.header_serial"),
                self.tr("usb.header_class"),
                self.tr("usb.header_speed"),
                self.tr("usb.header_actions"),
            ]
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
        table.setColumnWidth(7, 72)

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
                remove_btn.setProperty("firespecs_action", "detach_usb")
                remove_btn.setToolTip(self.tr("usb.detach_tooltip"))
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

        self.set_table_fixed_height(table)

        # Save reference to table for theme updates
        self.usb_table = table
        layout.addWidget(table)

        usb_icon = QIcon(
            os.path.join(get_base_path(), "icons", "ui", "usb-devices.png")
        )
        usb_tab = self.wrap_in_scroll_area(content)

        if insert_at_index is not None:
            usb_index = self.tabs.insertTab(
                insert_at_index, usb_tab, usb_icon, self.tr("tab.usb_devices")
            )
        else:
            usb_index = self.tabs.addTab(usb_tab, usb_icon, self.tr("tab.usb_devices"))
        self._set_tab_key(usb_index, "usb")
        self._usb_i18n_widgets = {"title": title_label}

    def detach_usb_device_handler(self, bus, device):
        reply = themed_dialogs.question(
            self,
            self.tr("usb.detach_title"),
            self.tr(
                "usb.detach_confirm",
                bus=bus,
                device=device,
            ),
        )

        if reply == QMessageBox.Yes:
            if self.privileges.active and os.geteuid() != 0:
                success, message = self.privileges.detach_usb(bus, device)
            else:
                success, message = detach_usb_device(bus, device)
                if (
                    not success
                    and os.geteuid() != 0
                    and self._request_privileged_action(
                        self.tr("usb.admin_title"),
                        self.tr(
                            "usb.detach_admin_prompt",
                            bus=bus,
                            device=device,
                        ),
                    )
                ):
                    success, message = self.privileges.detach_usb(bus, device)

            if success:
                themed_dialogs.information(
                    self, self.tr("dialog.success"), message
                )
                self.refresh_usb_tab()
            else:
                themed_dialogs.warning(self, self.tr("dialog.error"), message)

    def refresh_usb_tab(self):
        usb_index = self._tab_index("usb")

        if usb_index < 0:
            return

        current_key = self._tab_key(self.tabs.currentIndex())

        old_tab = self.tabs.widget(usb_index)
        self.tabs.removeTab(usb_index)
        old_tab.deleteLater()
        self.create_usb_tab(insert_at_index=usb_index)
        self._apply_tab_labels()
        QTimer.singleShot(0, self._refit_usb_table)

        for i in range(self.tabs.count()):
            if self._tab_key(i) == current_key:
                self.tabs.setCurrentIndex(i)
                break

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

        partitions_group = QGroupBox()
        lsblk_tree = self.create_lsblk_tree(storage_info["lsblk"])
        partitions_layout = QVBoxLayout()
        partitions_layout.addWidget(lsblk_tree)
        partitions_layout.setContentsMargins(5, 5, 5, 5)
        partitions_group.setLayout(partitions_layout)
        partitions_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(partitions_group)

        files_group = QGroupBox()
        files_layout = QVBoxLayout()

        scan_hint = QLabel()
        files_layout.addWidget(scan_hint)

        path_input_layout = QHBoxLayout()
        path_label = QLabel()
        path_input_layout.addWidget(path_label)
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

        self.scan_btn = QPushButton()
        self.scan_btn.clicked.connect(self.scan_files)
        files_layout.addWidget(self.scan_btn)
        # Set initial style based on theme
        self.update_scan_button_idle_style()

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(3)
        self.files_table.setHorizontalHeaderLabels(["", "", ""])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        self.files_table.verticalHeader().setVisible(False)
        self._configure_table_widget(self.files_table)
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

        storage_index = self.tabs.addTab(
            storage_tab,
            QIcon(os.path.join(get_base_path(), "icons", "ui", "diskette.png")),
            self.tr("tab.storage"),
        )
        self._set_tab_key(storage_index, "storage")
        self._storage_i18n_widgets = {
            "partitions_group": partitions_group,
            "files_group": files_group,
            "scan_hint": scan_hint,
            "path_label": path_label,
        }

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
            self.scan_btn.setText(self.tr("storage.scanning", char=char))
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
            self.files_table.setItem(
                0, 0, QTableWidgetItem(self.tr("storage.no_files"))
            )
            self.files_table.setItem(0, 1, QTableWidgetItem(""))
            self.files_table.setItem(0, 2, QTableWidgetItem(""))
            self.files_table.setSpan(0, 0, 1, 3)
            self.set_table_fixed_height(self.files_table)
        else:
            # Display files
            self.files_table.setRowCount(len(files))
            for i, file_info in enumerate(files):
                self.files_table.setItem(i, 0, QTableWidgetItem(file_info["path"]))
                self.files_table.setItem(
                    i, 1, QTableWidgetItem(self.format_file_size(file_info["size_mb"]))
                )
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
                folder_btn.setProperty("firespecs_action", "open_folder")
                folder_btn.setToolTip(self.tr("storage.open_folder"))
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
                delete_btn.setProperty("firespecs_action", "delete_file")
                delete_btn.setToolTip(self.tr("storage.delete_file"))
                delete_btn.clicked.connect(
                    lambda checked, path=file_info["path"], row=i: self.delete_file(
                        path, row
                    )
                )

                actions_layout.addWidget(folder_btn)
                actions_layout.addWidget(delete_btn)

                self.files_table.setCellWidget(i, 2, actions_widget)

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
            themed_dialogs.warning(
                self,
                self.tr("dialog.error"),
                self.tr("dialog.file_not_found", path=file_path),
            )
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
                themed_dialogs.warning(
                    self, self.tr("dialog.error"), self.tr("dialog.no_file_manager")
                )
                return

            if os.geteuid() == 0:
                env, username = get_desktop_env(extra_display=True)
                try:
                    if username:
                        subprocess.Popen(
                            ["sudo", "-u", username, "-E", selected_fm, folder_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            env=env,
                        )
                    else:
                        subprocess.Popen(
                            [selected_fm, folder_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            env=env,
                        )
                except OSError as exc:
                    themed_dialogs.warning(
                        self,
                        self.tr("dialog.error"),
                        self.tr("dialog.failed_open_folder", detail=exc),
                    )
            else:
                subprocess.Popen(
                    [selected_fm, folder_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        except Exception as e:
            themed_dialogs.warning(
                self,
                self.tr("dialog.error"),
                self.tr("dialog.failed_open_folder", detail=str(e)),
            )

    def delete_file(self, file_path, row):
        file_path = os.path.expanduser(file_path)

        if not os.path.exists(file_path):
            themed_dialogs.warning(
                self,
                self.tr("dialog.error"),
                self.tr("dialog.file_not_found", path=file_path),
            )
            return

        reply = themed_dialogs.question(
            self,
            self.tr("dialog.confirm_delete"),
            self.tr("dialog.delete_confirm", path=file_path),
        )

        if reply == QMessageBox.Yes:
            try:
                if os.path.isdir(file_path) and not os.path.islink(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            except PermissionError:
                if not self._request_privileged_action(
                    self.tr("dialog.admin_required"),
                    self.tr("dialog.delete_admin_prompt", path=file_path),
                ):
                    return
                ok, message = self.privileges.delete_path(file_path)
                if not ok:
                    themed_dialogs.warning(
                        self,
                        self.tr("dialog.error"),
                        self.tr("dialog.failed_delete", detail=message),
                    )
                    return
            except Exception as e:
                themed_dialogs.warning(
                    self,
                    self.tr("dialog.error"),
                    self.tr("dialog.failed_delete", detail=str(e)),
                )
                return

            themed_dialogs.information(
                self, self.tr("dialog.success"), self.tr("dialog.file_deleted")
            )
            self.files_table.removeRow(row)

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

        self.set_table_fixed_height(table)
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
                ", ".join(str(m) for m in (device.get("mountpoints") or []) if m),
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
        scale = self.ui_scale

        self.footer = QWidget()
        self.footer.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-top: 1px solid #3d3d3d;
            }
        """)

        layout = QHBoxLayout(self.footer)
        layout.setContentsMargins(
            scaled(15, scale), scaled(12, scale), scaled(15, scale), scaled(12, scale)
        )
        layout.setSpacing(scaled(18, scale))

        def _metric_label(text):
            label = QLabel(text)
            label.setWordWrap(True)
            label.setMinimumHeight(scaled(34, scale))
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            return label

        cpu_layout = QVBoxLayout()
        cpu_layout.setSpacing(scaled(8, scale))
        cpu_layout.setStretch(1, 1)
        self.cpu_label = _metric_label(self.tr("footer.cpu", text="-"))
        self.cpu_graph = HistoryGraph(QColor("#ff6b00"), show_temp=True, ui_scale=scale)
        cpu_layout.addWidget(self.cpu_label)
        cpu_layout.addWidget(self.cpu_graph)

        gpu_layout = QVBoxLayout()
        gpu_layout.setSpacing(scaled(8, scale))
        gpu_layout.setStretch(1, 1)
        self.gpu_label = _metric_label(self.tr("footer.gpu", text="-"))
        self.gpu_graph = HistoryGraph(QColor("#2196F3"), show_temp=True, ui_scale=scale)
        gpu_layout.addWidget(self.gpu_label)
        gpu_layout.addWidget(self.gpu_graph)

        ram_layout = QVBoxLayout()
        ram_layout.setSpacing(scaled(8, scale))
        ram_layout.setStretch(1, 1)
        self.ram_label = _metric_label(
            self.tr(
                "footer.ram",
                used=0.0,
                total=0.0,
                swap_used=0.0,
                swap_total=0.0,
            )
        )
        self.ram_graph = HistoryGraph(
            QColor("#4CAF50"),
            show_temp=False,
            swap_color="#2E7D32",
            ui_scale=scale,
        )
        ram_layout.addWidget(self.ram_label)
        ram_layout.addWidget(self.ram_graph)

        layout.addLayout(cpu_layout)
        layout.addLayout(gpu_layout)
        layout.addLayout(ram_layout)
        self._apply_ui_scale(scale)

    def _apply_ui_scale(self, scale):
        """Apply footer/graph metrics (used on show and when scale changes)."""
        self.ui_scale = scale
        footer_font_px = scaled(11, scale)
        label_min_h = scaled(34, scale)
        footer_min_h = scaled(108, scale)

        self.footer_font_px = footer_font_px
        if hasattr(self, "footer"):
            self.footer.setMinimumHeight(footer_min_h)

        for label in (
            getattr(self, "cpu_label", None),
            getattr(self, "gpu_label", None),
            getattr(self, "ram_label", None),
        ):
            if label is not None:
                label.setMinimumHeight(label_min_h)

        for graph in (
            getattr(self, "cpu_graph", None),
            getattr(self, "gpu_graph", None),
            getattr(self, "ram_graph", None),
        ):
            if graph is not None:
                graph.ui_scale = scale
                graph.setFixedHeight(scaled(44, scale))

        if hasattr(self, "current_theme"):
            self.apply_theme()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "_session_synced", False):
            return
        self._session_synced = True
        capture_session_from_window(self)
        QTimer.singleShot(0, self._refit_all_tables)
        if not getattr(self, "custom_title_bar", None):
            QTimer.singleShot(
                0, lambda: apply_native_window_chrome(self, self.current_theme)
            )

    def _update_gpu_hardware_live(self, stats):
        entries = getattr(self, "_gpu_hardware_live_updates", None)
        if not entries:
            return

        pci_slot = stats.get("gpu_pci_slot")
        values = {
            "memory_used": stats.get("gpu_memory_used"),
            "memory_free": stats.get("gpu_memory_free"),
            "memory_percent": stats.get("gpu_memory_percent"),
            "shared_memory_used": stats.get("gpu_shared_memory_used"),
        }

        for entry in entries:
            if pci_slot and entry.get("pci_slot") and entry["pci_slot"] != pci_slot:
                continue
            for row_key, item in entry.get("rows", {}).items():
                text = values.get(row_key)
                if text is not None and item is not None:
                    item.setText(str(text))

    def update_graphs(self, stats):
        try:
            cpu_temp = stats.get("cpu_temp", 0)
            if not isinstance(cpu_temp, (int, float)):
                cpu_temp = 0

            self.cpu_label.setText(
                self.tr(
                    "footer.cpu",
                    text=f"{stats['cpu_percent']:.1f}%{stats['cpu_freq_text']}",
                )
            )
            self.cpu_graph.add_value(stats["cpu_percent"], cpu_temp)

            self.gpu_label.setText(self.tr("footer.gpu", text=stats["gpu_text"]))
            gpu_percent = stats.get("gpu_percent", 0)
            if stats["gpu_text"] != "N/A":
                self.gpu_graph.add_value(gpu_percent, stats.get("gpu_temp", 0))

            self._update_gpu_hardware_live(stats)

            self.ram_label.setText(
                self.tr(
                    "footer.ram",
                    used=stats["ram_used"],
                    total=stats["ram_total"],
                    swap_used=stats["swap_used"],
                    swap_total=stats["swap_total"],
                )
            )
            self.ram_graph.add_value(
                stats["ram_percent"], swap_value=stats["swap_percent"]
            )
        except:
            pass

    def _update_access_state(self, theme=None):
        """Reflect the current privilege level in the footer label and button."""
        if not hasattr(self, "access_label"):
            return

        active = self.privileges.active
        if theme is None:
            current = getattr(self, "current_theme", "dark")
            if current == "light":
                theme = ThemeManager.LIGHT
            elif current == "matrix":
                theme = ThemeManager.MATRIX
            else:
                theme = ThemeManager.DARK

        self.access_label.setMinimumWidth(0)
        self.access_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        if active:
            accent = theme.get("graph_ram", "#4caf50")
            self.access_label.setText(self.tr("access.full"))
            self.access_label.setStyleSheet(
                f"color: {accent}; font-weight: bold; padding: 2px 4px;"
            )
            self.privilege_btn.setToolTip(self.tr("access.disable_tooltip"))
        else:
            self.access_label.setText(self.tr("access.limited"))
            self.access_label.setStyleSheet(
                "color: #ff5252; font-weight: bold; padding: 2px 4px;"
            )
            self.privilege_btn.setToolTip(self.tr("access.enable_tooltip"))

        running_as_root = os.geteuid() == 0
        # Hide the upgrade control once full access is active (or process is already root).
        self.privilege_btn.setVisible(not active and not running_as_root)
        self.privilege_btn.setEnabled(not running_as_root)

    def toggle_full_access(self):
        """Grant or revoke administrative privileges without reopening the window."""
        if os.geteuid() == 0:
            return

        if self.privileges.active:
            self.privileges.lock()
            self._update_access_state()
            return

        ok, message = self.privileges.unlock()
        self._update_access_state()
        if not ok:
            themed_dialogs.warning(
                self,
                self.tr("dialog.full_access_not_enabled"),
                self.tr("dialog.could_not_enable_access", detail=message),
            )
        else:
            self.refresh_application_data()

    def _request_privileged_action(self, title, prompt):
        """Make sure full access is available, offering to enable it. Returns bool."""
        if self.privileges.active:
            return True
        reply = themed_dialogs.question(
            self,
            title,
            self.tr("dialog.enable_full_access_question", prompt=prompt),
        )
        if reply != QMessageBox.Yes:
            return False
        ok, message = self.privileges.unlock()
        self._update_access_state()
        if not ok:
            themed_dialogs.warning(
                self,
                title,
                self.tr("dialog.could_not_enable_full_access", detail=message),
            )
        else:
            self.refresh_application_data()
        return ok

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

    def _on_main_tab_changed(self, index):
        self.update_tab_icons(index)
        if self._tab_key(index) == "usb":
            QTimer.singleShot(0, self._refit_usb_table)

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

        dark_action = QAction(self.tr("theme.dark"), self)
        dark_action.setCheckable(True)
        dark_action.setChecked(self.current_theme == "dark")
        dark_action.triggered.connect(lambda: self.set_theme("dark"))
        menu.addAction(dark_action)

        light_action = QAction(self.tr("theme.light"), self)
        light_action.setCheckable(True)
        light_action.setChecked(self.current_theme == "light")
        light_action.triggered.connect(lambda: self.set_theme("light"))
        menu.addAction(light_action)

        matrix_action = QAction(self.tr("theme.matrix"), self)
        matrix_action.setCheckable(True)
        matrix_action.setChecked(self.current_theme == "matrix")
        matrix_action.triggered.connect(lambda: self.set_theme("matrix"))
        menu.addAction(matrix_action)

        menu.addSeparator()

        language_menu = menu.addMenu(self.tr("settings.language"))
        for code in SUPPORTED_LANGUAGES:
            lang_action = QAction(LANGUAGE_NAMES[code], self)
            lang_action.setCheckable(True)
            lang_action.setChecked(self.translator.language == code)
            lang_action.triggered.connect(
                lambda checked, lang=code: self.set_language(lang)
            )
            language_menu.addAction(lang_action)

        menu.addSeparator()

        about_action = QAction(self.tr("settings.about"), self)
        about_action.triggered.connect(self.show_about_dialog)
        menu.addAction(about_action)

        menu.exec_(
            self.settings_btn.mapToGlobal(self.settings_btn.rect().bottomRight())
        )

    def set_theme(self, theme):
        self.current_theme = theme
        session = load_ui_session()
        session["theme"] = theme
        save_ui_session(session)
        self._ui_session = session
        self.apply_theme()

    def show_about_dialog(self):
        themed_dialogs.show_about(self)

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
                padding: 10px 20px;
                min-height: 28px;
                margin-right: 2px;
                border: none;
            }}
            QTabBar::tab:hover {{ background-color: {theme["background_hover"]}; }}
            QTabBar::tab:selected {{
                background-color: {theme["accent"]};
                color: {theme.get("selected_tab_text", theme["text_primary"])};
                font-family: {font_family};
            }}
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
            QTableWidget::item {{ padding: 4px 8px; font-family: {font_family}; }}
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
        if hasattr(self, "privilege_btn"):
            self.privilege_btn.setStyleSheet(transparent_btn_style)

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
            footer_px = getattr(self, "footer_font_px", scaled(11, self.ui_scale))
            self.footer.setMinimumHeight(scaled(108, self.ui_scale))
            self.footer.setStyleSheet(f"""
                QWidget {{
                    background-color: {theme["header"]};
                    border-top: 1px solid {theme["border"]};
                }}
                QLabel {{
                    color: {theme["text_primary"]};
                    font-family: {font_family};
                    font-size: {footer_px}px;
                    padding: 6px 4px;
                }}
            """)

        self._update_access_state(theme)

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
            if hasattr(self, "privilege_btn") and hasattr(
                self, "up_arrow_icon_green"
            ):
                self.privilege_btn.setIcon(self.up_arrow_icon_green)
        else:
            # Reset to default icons
            if hasattr(self, "settings_btn"):
                self.settings_btn.setIcon(
                    QIcon(os.path.join(get_base_path(), "icons", "ui", "settings.png"))
                )
            if hasattr(self, "privilege_btn"):
                self.privilege_btn.setIcon(
                    QIcon(os.path.join(get_base_path(), "icons", "ui", "up-arrow.png"))
                )

        # Update tab icons immediately after theme change
        if hasattr(self, "tabs"):
            self.update_tab_icons(self.tabs.currentIndex())

        QTimer.singleShot(0, self._refit_all_tables)

        if getattr(self, "custom_title_bar", None):
            self.custom_title_bar.apply_theme(theme, font_family)
        else:
            apply_native_window_chrome(self, self.current_theme)

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
                                and btn.property("firespecs_action") == "detach_usb"
                            ):
                                btn.setToolTip(self.tr("usb.detach_tooltip"))
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
                        action = btn.property("firespecs_action")
                        if action == "open_folder":
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
                        elif action == "delete_file":
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

        QTimer.singleShot(0, self._refit_all_tables)

    def get_theme_color(self, key):
        if self.current_theme == "dark":
            theme = ThemeManager.DARK
        elif self.current_theme == "light":
            theme = ThemeManager.LIGHT
        else:
            theme = ThemeManager.MATRIX
        return theme.get(key, "#000000")

    def closeEvent(self, event):
        if hasattr(self, "privileges"):
            self.privileges.lock()
        self.stats_thread.stop()
        super().closeEvent(event)
