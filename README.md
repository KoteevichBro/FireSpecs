# FireSpecs 4

**Hardware monitoring tool with GUI for Linux**

FireSpecs is a system information and hardware monitoring application built with Python and Qt5. It provides real-time monitoring and detailed hardware information for Linux systems.

## Overview

FireSpecs displays comprehensive system information through an intuitive tabbed interface. The application supports **English, German, and Russian**, multiple themes (Dark, Light, Matrix), automatic light/dark appearance based on OS settings, and detailed insights into hardware components, USB devices, and storage.

## Key Features

### Hardware Information
- **CPU**: Model, cores, frequencies, cache, instruction sets, real-time usage graphs
- **Memory**: RAM modules, totals, and swap statistics with usage visualization
- **GPU**: Detection, VRAM/shared memory, live load and temperature (AMD, NVIDIA, Intel i915/xe)
- **Display**: Resolutions (native, active, scaled), EDID details when available
- **Network**: Interfaces, IP and MAC addresses
- **Motherboard**: Manufacturer, model, serial (Full Access for blocked sysfs)
- **BIOS**: Version, vendor, release date (Full Access for blocked sysfs)
- **Battery**: Status, health, and capacity information

### USB Device Management
- Lists all connected USB devices
- Shows vendor, product, serial, and device class
- Detach/eject functionality for removable devices

### Storage Analysis
- Disk partitions and usage information
- File system type detection
- Largest files scanner with delete capability

### User Interface
- Localized UI: English, German, Russian (Settings → Language)
- Three visual themes: Dark, Light, Matrix (terminal-style); startup theme follows OS when set to System
- Custom title bar and themed dialogs on Linux Wayland
- Real-time graphs for CPU, GPU, and memory usage
- Tabbed interface: Hardware, USB Devices, Storage
- In-app **Full Access** (pkexec helper) without restarting the application

## Requirements

- Python 3.7+
- PyQt5
- psutil
- Optional: `dmidecode`, `lsblk`, `xrandr`, `nvidia-smi`, `pkexec` (for Full Access and extended hardware data)

## Quick Start

```bash
git clone https://github.com/firekernel/firespecs.git
cd firespecs
pip3 install -r requirements.txt
python3 firespecs.py
```

Or use the helper script:

```bash
./run.sh
```

## Installation

### From Package

**Debian/Ubuntu:** download the `.deb` from [Releases](https://github.com/firekernel/firespecs/releases), then:

```bash
sudo dpkg -i firespecs_4.0_amd64.deb
sudo apt-get install -f
```

**Universal (AppImage):**

```bash
chmod +x FireSpecs-4.0-x86_64.AppImage
./FireSpecs-4.0-x86_64.AppImage
```

### From Source

```bash
pip3 install -r requirements.txt
python3 firespecs.py
```

## Usage

Most information is available without root. Enable **Full Access** from the toolbar (pkexec) for DMI fields, USB detach, and deleting protected files — the app stays open.

```bash
python3 firespecs.py
```

## Project Structure

```
├── app/
│   ├── main.py              # Application entry point
│   ├── ui.py                # Main window, tabs, graphs
│   ├── hardware.py          # Hardware detection (CPU, GPU, DMI, EDID, …)
│   ├── storage.py           # Partitions and largest-files scan
│   ├── gpu_stats.py         # Live GPU utilization and temperature
│   ├── gpu_memory.py        # VRAM / shared memory detection
│   ├── privilege.py         # Full Access (pkexec helper client)
│   ├── privileged_helper.py # Root worker process
│   ├── i18n.py              # Translations (en, de, ru)
│   ├── system_theme.py        # OS light/dark detection
│   ├── window_chrome.py       # Native / custom window decorations
│   ├── custom_title_bar.py    # In-window title bar (Wayland)
│   ├── themed_dialogs.py      # Themed message and About dialogs
│   ├── ui_session.py          # Window geometry and preferences
│   ├── display_scale.py       # UI scaling helper
│   ├── platform_users.py      # Desktop user detection (pkexec)
│   └── paths.py               # Install and resource paths
├── icons/                   # UI and device icons
├── tests/                   # Unit tests
├── debian/                  # Debian package metadata
├── build/                   # Local release artifacts (not in git)
├── firespecs.py             # Launcher script
├── run.sh                   # Dev launcher (sets PYTHONPATH)
├── requirements.txt
├── changelog.txt
├── LICENSE
└── attribution.txt          # Third-party icon credits
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Building Packages

See `debian/` for `.deb` packaging and place built `.deb` / AppImage files under `build/` (ignored by git). Example names: `firespecs_4.0_amd64.deb`, `FireSpecs-4.0-x86_64.AppImage`.

## License

MIT License — see [LICENSE](LICENSE).

## Author

Denis Oreshkin — [dm@koteevich.ru](mailto:dm@koteevich.ru)

Project site: [firespecs.sourceforge.io](https://firespecs.sourceforge.io/)
