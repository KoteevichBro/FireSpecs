# FireSpecs v3.0

**Hardware monitoring tool with GUI for Linux**

FireSpecs is a system information and hardware monitoring application built with Python and Qt5. It provides real-time monitoring and detailed hardware information for Linux systems.

## Overview

FireSpecs displays comprehensive system information through an intuitive tabbed interface. The application supports multiple themes (Dark, Light, Matrix) and provides detailed insights into hardware components, USB devices, and storage.

## Key Features

### Hardware Information
- **CPU**: Model, cores, frequencies, cache, real-time usage graphs
- **Memory**: RAM and swap statistics with usage visualization
- **GPU**: Graphics card detection and monitoring
- **Motherboard**: Manufacturer, model, serial (requires root)
- **BIOS**: Version, vendor, release date (requires root)
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
- Three visual themes: Dark, Light, Matrix (terminal-style)
- Real-time graphs for CPU, GPU, and memory usage
- Tabbed interface: Hardware, USB Devices, Storage
- Responsive design with smooth theme switching

## Technical Details

**Stack:**
- Python 3.7+
- PyQt5 for GUI
- psutil for system metrics
- dmidecode for hardware details (optional, requires root)

**Architecture:**
- Modular design with separate modules for UI, hardware detection, and storage
- Theme manager for consistent styling across components
- Asynchronous operations for scanning and monitoring

## Installation

### From Package

**Debian/Ubuntu:**
```bash
sudo dpkg -i firespecs_3.0_amd64.deb
sudo apt-get install -f  # Install dependencies
```

**Universal (AppImage):**
```bash
chmod +x FireSpecs-3.0-x86_64.AppImage
./FireSpecs-3.0-x86_64.AppImage
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

Run with root for complete hardware details:
```bash
sudo python3 firespecs.py
```

## Project Structure

```
Firespecs_v3/
├── app/
│   ├── ui.py        # Main interface (2,799 lines)
│   ├── hardware.py  # Hardware detection (1,485 lines)
│   ├── storage.py   # Storage analysis (118 lines)
│   └── main.py      # Entry point (22 lines)
├── icons/           # Application icons
├── build/           # Pre-built packages
├── firespecs.py     # Launcher script
└── requirements.txt # Dependencies
```

**Total codebase:** ~4,424 lines of Python

## Dependencies

- python3
- python3-pyqt5
- python3-psutil
- dmidecode (optional, for detailed hardware info)

## License

MIT License - Open source

## Author

Denis Oreshkin <dm@koteevich.ru>
