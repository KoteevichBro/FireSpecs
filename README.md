# FireSpecs 4

**Hardware monitoring tool with GUI for Linux**

FireSpecs is a system information and hardware monitoring application built with Python and Qt5. It provides real-time monitoring and detailed hardware information for Linux systems.

## Overview

FireSpecs displays comprehensive system information through an intuitive tabbed interface. The application supports **English, German, and Russian**, multiple themes (Dark, Light, Matrix), automatic light/dark appearance based on OS settings, and detailed insights into hardware components, USB devices, and storage.

## Key Features

### Hardware Information
- **CPU**: Model, cores, frequencies, cache, instruction sets, real-time usage graphs
- **Memory**: RAM and swap statistics with usage visualization
- **GPU**: Detection, VRAM, live stats (AMD, NVIDIA, Intel)
- **Display**: Resolutions and EDID details when available
- **Motherboard**: Manufacturer, model, serial (Full Access)
- **BIOS**: Version, vendor, release date (Full Access)
- **Battery**: Status and capacity information

### USB Device Management
- Lists all connected USB devices
- Shows vendor, product, serial, and device class
- Detach/eject functionality for removable devices

### Storage Analysis
- Disk partitions and usage information
- File system type detection
- Largest files scanner with delete capability

### User Interface
- Languages: English, German, Russian
- Three visual themes: Dark, Light, Matrix (terminal-style)
- Startup theme can follow OS light/dark
- Custom title bar on Linux Wayland
- Real-time graphs for CPU, GPU, and memory usage
- Tabbed interface: Hardware, USB Devices, Storage
- Full Access via pkexec without restarting the app

## Technical Details

**Stack:**
- Python 3.7+
- PyQt5 for GUI
- psutil for system metrics
- dmidecode for hardware details (optional, Full Access)

**Architecture:**
- Modular design with separate modules for UI, hardware detection, and storage
- Theme manager for consistent styling across components
- Privileged helper for root actions while the GUI stays on the desktop session
- Asynchronous operations for scanning and monitoring

## Installation

### From Package

**Debian/Ubuntu:**
```bash
sudo dpkg -i firespecs_4.0_amd64.deb
sudo apt-get install -f  # Install dependencies
```

**Universal (AppImage):**
```bash
chmod +x FireSpecs-4.0-x86_64.AppImage
./FireSpecs-4.0-x86_64.AppImage
```

### From Source
```bash
pip3 install PyQt5 psutil
python3 firespecs.py
```

## Usage

Run without root for basic information:
```bash
python3 firespecs.py
```

Enable **Full Access** in the app (toolbar) for complete hardware details, USB detach, and protected file operations.

## Project Structure

```
Firespecs_v4/
├── app/
│   ├── ui.py              # Main interface
│   ├── hardware.py        # Hardware detection
│   ├── storage.py         # Storage analysis
│   ├── i18n.py            # Translations
│   ├── privilege.py       # Full Access (pkexec)
│   └── main.py            # Entry point
├── icons/                 # Application icons
├── build/                 # Pre-built packages
├── firespecs.py           # Launcher script
└── requirements.txt       # Dependencies
```

## Dependencies

- python3
- python3-pyqt5
- python3-psutil
- dmidecode (optional, for detailed hardware info)

## License

MIT License - Open source

## Author

Denis Oreshkin <dm@koteevich.ru>
