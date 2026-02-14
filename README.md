# FireSpecs

**Hardware monitoring tool with GUI for Linux**

<img width="1332" height="959" alt="1" src="https://github.com/user-attachments/assets/3be2b2c0-ea67-473f-bfc8-0c25dcd14643" />

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

### User Interface
- Three visual themes: Dark, Light, Matrix (terminal-style)
- Real-time graphs for CPU, GPU, and memory usage
- Tabbed interface: Hardware, USB Devices, Storage
- Responsive design with smooth theme switching

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

## License

MIT License - Open source

## Author

Denis Oreshkin <dm@koteevich.ru>
