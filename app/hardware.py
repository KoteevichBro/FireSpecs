import platform
import psutil
import subprocess
import re
import os
import socket
import time


def get_cpu_info():
    cpu = {}

    # Try to get CPU info from /proc/cpuinfo
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
            # Try to find model name
            model_match = re.search(r"model name\s*:\s*(.+)", cpuinfo)
            if model_match:
                cpu["model"] = model_match.group(1).strip()
            else:
                # Fallback to vendor + family
                vendor = re.search(r"vendor_id\s*:\s*(.+)", cpuinfo)
                family = re.search(r"cpu family\s*:\s*(.+)", cpuinfo)
                model = re.search(r"model\s*:\s*(.+)", cpuinfo)
                if vendor and family and model:
                    cpu["model"] = (
                        f"{vendor.group(1).strip()} Family {family.group(1).strip()} Model {model.group(1).strip()}"
                    )
                else:
                    cpu["model"] = "Unknown CPU"

            # Try to get CPU flags/features
            flags_match = re.search(r"flags\s*:\s*(.+)", cpuinfo)
            if flags_match:
                cpu["features"] = flags_match.group(1).strip()[:100] + "..."
    except:
        cpu["model"] = platform.processor() or "Unknown CPU"

    # Get core information
    cpu["cores_physical"] = psutil.cpu_count(logical=False)
    cpu["cores_logical"] = psutil.cpu_count(logical=True)

    # Try to get frequency from lscpu
    try:
        result = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            max_match = re.search(r"CPU max MHz:\s*(.+)", result.stdout)
            min_match = re.search(r"CPU min MHz:\s*(.+)", result.stdout)
            current_match = re.search(r"CPU MHz:\s*(.+)", result.stdout)

            if max_match:
                cpu["frequency_max"] = f"{float(max_match.group(1).strip()):.0f} MHz"
            else:
                cpu["frequency_max"] = (
                    f"{psutil.cpu_freq().max:.2f} MHz" if psutil.cpu_freq() else "N/A"
                )

            if min_match:
                cpu["frequency_min"] = f"{float(min_match.group(1).strip()):.0f} MHz"

            if current_match:
                cpu["frequency_current"] = (
                    f"{float(current_match.group(1).strip()):.0f} MHz"
                )
    except:
        cpu["frequency_max"] = (
            f"{psutil.cpu_freq().max:.2f} MHz" if psutil.cpu_freq() else "N/A"
        )

    cpu["usage_percent"] = f"{psutil.cpu_percent(interval=0.1):.1f}%"

    # Try to get cache info from lscpu
    try:
        result = subprocess.run(["lscpu"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            l1d = re.search(r"L1d cache:\s*(.+)", result.stdout)
            l1i = re.search(r"L1i cache:\s*(.+)", result.stdout)
            l2 = re.search(r"L2 cache:\s*(.+)", result.stdout)
            l3 = re.search(r"L3 cache:\s*(.+)", result.stdout)

            cache_info = []
            if l1d:
                cache_info.append(f"L1d: {l1d.group(1).strip()}")
            if l1i:
                cache_info.append(f"L1i: {l1i.group(1).strip()}")
            if l2:
                cache_info.append(f"L2: {l2.group(1).strip()}")
            if l3:
                cache_info.append(f"L3: {l3.group(1).strip()}")

            if cache_info:
                cpu["cache"] = ", ".join(cache_info)
    except:
        pass

    return cpu


def get_memory_info():
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "total": f"{mem.total / (1024**3):.2f} GB",
        "swap_total": f"{swap.total / (1024**3):.2f} GB",
        "swap_used": f"{swap.used / (1024**3):.2f} GB",
    }


def get_ram_sticks():
    ram_sticks = []

    try:
        result = subprocess.run(
            ["dmidecode", "-t", "memory"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            dmi_output = result.stdout
            devices = dmi_output.split("\n\n")

            for device in devices:
                if "Memory Device" in device:
                    size_match = re.search(r"Size:\s*(.+)", device)
                    locator_match = re.search(r"Locator:\s*(.+)", device)
                    type_match = re.search(r"Type:\s*(.+)", device)
                    speed_match = re.search(r"Speed:\s*(.+)", device)
                    manufacturer_match = re.search(r"Manufacturer:\s*(.+)", device)
                    part_number_match = re.search(r"Part Number:\s*(.+)", device)
                    serial_match = re.search(r"Serial Number:\s*(.+)", device)

                    if size_match:
                        size = size_match.group(1).strip()
                        if size != "No Module Installed":
                            stick = {
                                "size": size,
                                "locator": locator_match.group(1).strip()
                                if locator_match
                                else "Unknown",
                                "type": type_match.group(1).strip()
                                if type_match
                                else "Unknown",
                                "speed": speed_match.group(1).strip()
                                if speed_match
                                else "Unknown",
                                "manufacturer": manufacturer_match.group(1).strip()
                                if manufacturer_match
                                else "Unknown",
                                "part_number": part_number_match.group(1).strip()
                                if part_number_match
                                else "Unknown",
                                "serial": serial_match.group(1).strip()
                                if serial_match
                                else "Unknown",
                            }
                            ram_sticks.append(stick)
    except:
        pass

    if not ram_sticks:
        try:
            import glob

            dimm_paths = glob.glob("/sys/bus/edac/devices/mce*")
            if not dimm_paths:
                dimm_paths = glob.glob("/sys/devices/system/edac/mc/mc*/*")

            if dimm_paths:
                for i, dimm_path in enumerate(dimm_paths[:16], 1):
                    ram_sticks.append(
                        {
                            "size": "Unknown",
                            "locator": f"DIMM {i}",
                            "type": "Unknown",
                            "speed": "Unknown",
                            "manufacturer": "Unknown",
                            "part_number": "Unknown",
                            "serial": "Unknown",
                        }
                    )
        except:
            pass

    return ram_sticks


def get_os_info():
    os_info = {
        "kernel": f"{platform.system()} {platform.release()}",
        "hostname": platform.node(),
        "architecture": platform.machine(),
        "distribution": "Unknown",
        "version": "Unknown",
        "codename": "Unknown",
    }

    # Try /etc/os-release (most modern Linux distributions)
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r") as f:
                os_release = f.read()

                name_match = re.search(r'^NAME="?([^"\n]+)"?', os_release)
                version_match = re.search(r'^VERSION="?([^"\n]+)"?', os_release)
                version_id_match = re.search(r'^VERSION_ID="?([^"\n]+)"?', os_release)
                pretty_name_match = re.search(r'^PRETTY_NAME="?([^"\n]+)"?', os_release)

                if pretty_name_match:
                    os_info["distribution"] = pretty_name_match.group(1)
                elif name_match:
                    os_info["distribution"] = name_match.group(1)

                if version_match:
                    os_info["version"] = version_match.group(1)

                if version_id_match:
                    os_info["version_id"] = version_id_match.group(1)
        except:
            pass

    # Try lsb_release
    try:
        result = subprocess.run(
            ["lsb_release", "-a"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            distro_match = re.search(r"Distributor ID:\s*(.+)", result.stdout)
            release_match = re.search(r"Release:\s*(.+)", result.stdout)
            codename_match = re.search(r"Codename:\s*(.+)", result.stdout)

            if distro_match and os_info["distribution"] == "Unknown":
                os_info["distribution"] = distro_match.group(1).strip()
            if release_match:
                os_info["version"] = release_match.group(1).strip()
            if codename_match:
                os_info["codename"] = codename_match.group(1).strip()
    except:
        pass

    # Try /etc/issue for older systems
    if os_info["distribution"] == "Unknown" and os.path.exists("/etc/issue"):
        try:
            with open("/etc/issue", "r") as f:
                issue = f.read().strip()
                os_info["distribution"] = issue.split("\\")[0].strip()
        except:
            pass

    return os_info


def get_motherboard_info():
    mb_info = {
        "manufacturer": "Unknown",
        "product_name": "Unknown",
        "version": "Unknown",
        "serial_number": "Not available",
        "asset_tag": "Not available",
    }

    # Try sysfs first (doesn't require root)
    sysfs_path = "/sys/class/dmi/id"
    if os.path.exists(sysfs_path):
        try:
            vendor_file = os.path.join(sysfs_path, "board_vendor")
            product_file = os.path.join(sysfs_path, "board_name")
            version_file = os.path.join(sysfs_path, "board_version")
            serial_file = os.path.join(sysfs_path, "board_serial")
            asset_file = os.path.join(sysfs_path, "board_asset_tag")

            if os.path.exists(vendor_file):
                with open(vendor_file, "r") as f:
                    vendor = f.read().strip()
                    if vendor and vendor != "Not Specified":
                        mb_info["manufacturer"] = vendor

            if os.path.exists(product_file):
                with open(product_file, "r") as f:
                    product = f.read().strip()
                    if product and product != "Not Specified":
                        mb_info["product_name"] = product

            if os.path.exists(version_file):
                with open(version_file, "r") as f:
                    version = f.read().strip()
                    if version and version != "Not Specified":
                        mb_info["version"] = version

            if os.path.exists(serial_file):
                with open(serial_file, "r") as f:
                    serial = f.read().strip()
                    if (
                        serial
                        and serial != "Not Specified"
                        and serial != "Default string"
                    ):
                        mb_info["serial_number"] = serial

            if os.path.exists(asset_file):
                with open(asset_file, "r") as f:
                    asset = f.read().strip()
                    if asset and asset != "Not Specified" and asset != "Default string":
                        mb_info["asset_tag"] = asset
        except:
            pass

    # Fallback to dmidecode if sysfs didn't work (requires root)
    if mb_info["manufacturer"] == "Unknown" or mb_info["product_name"] == "Unknown":
        try:
            result = subprocess.run(
                ["dmidecode", "-t", "baseboard"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                dmi = result.stdout
                manufacturer = re.search(r"Manufacturer:\s*(.+)", dmi)
                product = re.search(r"Product Name:\s*(.+)", dmi)
                version = re.search(r"Version:\s*(.+)", dmi)
                serial = re.search(r"Serial Number:\s*(.+)", dmi)
                asset = re.search(r"Asset Tag:\s*(.+)", dmi)
                location = re.search(r"Location In Chassis:\s*(.+)", dmi)

                if manufacturer and mb_info["manufacturer"] == "Unknown":
                    mb_info["manufacturer"] = manufacturer.group(1).strip()
                if product and mb_info["product_name"] == "Unknown":
                    mb_info["product_name"] = product.group(1).strip()
                if version and mb_info["version"] == "Unknown":
                    mb_info["version"] = version.group(1).strip()
                if serial and mb_info["serial_number"] == "Not available":
                    mb_info["serial_number"] = serial.group(1).strip()
                if asset and mb_info["asset_tag"] == "Not available":
                    mb_info["asset_tag"] = asset.group(1).strip()
        except:
            pass

    return mb_info


def get_bios_info():
    bios_info = {
        "vendor": "Unknown",
        "version": "Unknown",
        "release_date": "Unknown",
        "revision": "Unknown",
    }

    # Try sysfs first (doesn't require root)
    sysfs_path = "/sys/class/dmi/id"
    if os.path.exists(sysfs_path):
        try:
            vendor_file = os.path.join(sysfs_path, "bios_vendor")
            version_file = os.path.join(sysfs_path, "bios_version")
            date_file = os.path.join(sysfs_path, "bios_date")
            release_file = os.path.join(sysfs_path, "bios_release")

            if os.path.exists(vendor_file):
                with open(vendor_file, "r") as f:
                    vendor = f.read().strip()
                    if vendor and vendor != "Not Specified":
                        bios_info["vendor"] = vendor

            if os.path.exists(version_file):
                with open(version_file, "r") as f:
                    version = f.read().strip()
                    if version and version != "Not Specified":
                        bios_info["version"] = version

            if os.path.exists(date_file):
                with open(date_file, "r") as f:
                    date = f.read().strip()
                    if date and date != "Not Specified":
                        bios_info["release_date"] = date

            if os.path.exists(release_file):
                with open(release_file, "r") as f:
                    release = f.read().strip()
                    if release and release != "Not Specified":
                        bios_info["revision"] = release
        except:
            pass

    # Fallback to dmidecode if sysfs didn't work (requires root)
    if bios_info["vendor"] == "Unknown" or bios_info["version"] == "Unknown":
        try:
            result = subprocess.run(
                ["dmidecode", "-t", "bios"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                dmi = result.stdout
                vendor = re.search(r"Vendor:\s*(.+)", dmi)
                version = re.search(r"Version:\s*(.+)", dmi)
                date = re.search(r"Release Date:\s*(.+)", dmi)
                revision = re.search(r"Bios Revision:\s*(.+)", dmi)

                if vendor and bios_info["vendor"] == "Unknown":
                    bios_info["vendor"] = vendor.group(1).strip()
                if version and bios_info["version"] == "Unknown":
                    bios_info["version"] = version.group(1).strip()
                if date and bios_info["release_date"] == "Unknown":
                    bios_info["release_date"] = date.group(1).strip()
                if revision and bios_info["revision"] == "Unknown":
                    bios_info["revision"] = revision.group(1).strip()
        except:
            pass

    return bios_info


def get_chassis_info():
    chassis_info = {
        "manufacturer": "Unknown",
        "type": "Unknown",
        "version": "Unknown",
        "serial_number": "Not available",
    }

    try:
        result = subprocess.run(
            ["dmidecode", "-t", "chassis"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            dmi = result.stdout
            manufacturer = re.search(r"Manufacturer:\s*(.+)", dmi)
            chassis_type = re.search(r"Type:\s*(.+)", dmi)
            version = re.search(r"Version:\s*(.+)", dmi)
            serial = re.search(r"Serial Number:\s*(.+)", dmi)
            lock = re.search(r"Lock:\s*(.+)", dmi)

            if manufacturer:
                chassis_info["manufacturer"] = manufacturer.group(1).strip()
            if chassis_type:
                chassis_info["type"] = chassis_type.group(1).strip()
            if version:
                chassis_info["version"] = version.group(1).strip()
            if serial:
                chassis_info["serial_number"] = serial.group(1).strip()
            if lock:
                chassis_info["lock"] = lock.group(1).strip()
    except:
        pass

    return chassis_info


def get_gpu_temp():
    gpu_temp = 0

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            gpu_temp = float(result.stdout.strip())
            return gpu_temp
    except:
        pass

    try:
        import glob

        hwmon_paths = glob.glob("/sys/class/hwmon/hwmon*")
        for hwmon_path in hwmon_paths:
            name_file = os.path.join(hwmon_path, "name")
            if not os.path.exists(name_file):
                continue

            try:
                with open(name_file, "r") as f:
                    name = f.read().strip()

                if name in ["amdgpu", "radeon", "i915", "nvidia"]:
                    temp_input_file = os.path.join(hwmon_path, "temp1_input")

                    if os.path.exists(temp_input_file):
                        with open(temp_input_file, "r") as f:
                            temp_millidegrees = int(f.read().strip())
                            gpu_temp = temp_millidegrees / 1000
                        break
            except:
                continue
    except:
        pass

    return gpu_temp


def get_gpu_temp_from_hwmon():
    return get_gpu_temp()


def get_gpu_info():
    gpu_info = []

    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.split("\n")
            for line in lines:
                device_type = re.search(r"[^:]+:\s*(.+?):\s", line)
                if device_type:
                    device_type_str = device_type.group(1).strip()
                    if (
                        "VGA compatible controller" in device_type_str
                        or "3D controller" in device_type_str
                        or "Display" in device_type_str
                    ):
                        gpu = {}
                        match = re.search(r"(.+?): (.+)", line)
                        if match:
                            gpu["bus"] = match.group(1).strip()
                            gpu["device"] = match.group(2).strip()
                            gpu_info.append(gpu)
    except:
        pass

    try:
        result = subprocess.run(["glxinfo"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            match = re.search(r"OpenGL renderer string:\s*(.+)", result.stdout)
            if match and not gpu_info:
                gpu_info.append(
                    {"bus": "Primary GPU", "device": match.group(1).strip()}
                )
            elif match and gpu_info:
                if "renderer" not in gpu_info[0]:
                    gpu_info[0]["renderer"] = match.group(1).strip()

            vram_match = re.search(r"Video memory:\s*(.+)", result.stdout)
            if vram_match and gpu_info:
                if "memory_total" not in gpu_info[0]:
                    gpu_info[0]["memory_total"] = vram_match.group(1).strip()
    except:
        pass

    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,temperature.gpu,utilization.gpu,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.split("\n")
            if lines[0]:
                data = lines[0].split(", ")
                if gpu_info and len(data) >= 6:
                    gpu_info[0]["driver"] = data[1].strip()
                    gpu_info[0]["temperature"] = f"{data[2].strip()}°C"
                    gpu_info[0]["utilization"] = f"{data[3].strip()}%"
                    gpu_info[0]["memory_total"] = f"{int(data[4].strip()) // 1024} GB"
                    gpu_info[0]["memory_used"] = f"{int(data[5].strip()) // 1024} GB"
    except:
        pass

    try:
        if gpu_info and "memory_used" not in gpu_info[0]:
            try:
                import glob

                card_paths = glob.glob("/sys/class/drm/card*")
                for card_path in card_paths:
                    if not card_path.endswith("-"):
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

                                gpu_info[0]["memory_total"] = (
                                    f"{vram_total / (1024**3):.2f} GB"
                                )
                                gpu_info[0]["memory_used"] = (
                                    f"{vram_used / (1024**3):.2f} GB"
                                )
                                gpu_info[0]["memory_percent"] = (
                                    f"{(vram_used / vram_total * 100):.1f}%"
                                )
                                break
                            except:
                                continue
            except:
                pass
    except:
        pass

    if gpu_info and "temperature" not in gpu_info[0]:
        gpu_temp = get_gpu_temp_from_hwmon()
        if gpu_temp > 0:
            gpu_info[0]["temperature"] = f"{gpu_temp:.1f}°C"

    if not gpu_info:
        return [{"bus": "Unknown", "device": "No GPU detected"}]

    return gpu_info


def get_network_info():
    network_info = []

    try:
        interfaces = psutil.net_if_addrs()

        for interface_name, addresses in interfaces.items():
            if interface_name == "lo":
                continue

            ip_address = "N/A"
            mac_address = "N/A"

            for addr in addresses:
                if addr.family == socket.AF_INET:
                    ip_address = addr.address
                elif addr.family == psutil.AF_LINK:
                    mac_address = addr.address

            if ip_address != "N/A" or mac_address != "N/A":
                network_info.append(
                    {
                        "interface": interface_name,
                        "ip": ip_address,
                        "mac": mac_address,
                    }
                )
    except:
        pass

    if not network_info:
        network_info.append(
            {
                "interface": "No network interfaces",
                "ip": "N/A",
                "mac": "N/A",
            }
        )

    return network_info


def find_usb_sysfs_path(bus, device):
    """Find the correct sysfs path for a USB device by matching busnum and devnum."""
    import glob

    bus_int = int(bus)
    device_int = int(device)

    # Search all USB device directories
    for sys_path in glob.glob("/sys/bus/usb/devices/*-*"):
        # Skip interface directories (contain colon)
        if ":" in os.path.basename(sys_path):
            continue

        busnum_path = os.path.join(sys_path, "busnum")
        devnum_path = os.path.join(sys_path, "devnum")

        if os.path.exists(busnum_path) and os.path.exists(devnum_path):
            try:
                with open(busnum_path, "r") as f:
                    path_bus = int(f.read().strip())
                with open(devnum_path, "r") as f:
                    path_dev = int(f.read().strip())

                if path_bus == bus_int and path_dev == device_int:
                    return sys_path
            except:
                continue

    return None


def get_usb_devices():
    usb_devices = []

    usb_device_names = {
        "046d:c52d": {"vendor": "Kingston", "product": "K280e Keyboard"},
        "046d:c52c": {"vendor": "Kingston", "product": "K280e Keyboard"},
        "093a:2510": {"vendor": "Pixart Imaging", "product": "Optical Mouse"},
        "093a:2521": {"vendor": "Pixart Imaging", "product": "Optical Mouse"},
        "05e3:0610": {"vendor": "Synaptics", "product": "TouchPad"},
        "045e:028c": {"vendor": "Dell", "product": "Keyboard"},
        "046d:c31c": {"vendor": "Logitech", "product": "M-BT96a"},
        "046d:c31f": {"vendor": "Logitech", "product": "G105"},
        "1532:0116": {"vendor": "Razer", "product": "DeathAdder"},
    }

    try:
        result = subprocess.run(
            ["lsusb", "-v"], capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            lines = result.stdout.split("\n")
            device = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                bus_device_match = re.match(r"Bus\s+(\d+)\s+Device\s+(\d+):", line)
                if bus_device_match:
                    if device:
                        usb_devices.append(device)

                    bus_num = bus_device_match.group(1)
                    device_num = bus_device_match.group(2)
                    # Remove leading zeros for cleaner display
                    bus_num_clean = str(int(bus_num))
                    device_num_clean = str(int(device_num))

                    # Find actual sysfs path
                    sysfs_path = find_usb_sysfs_path(bus_num_clean, device_num_clean)

                    device = {
                        "bus": bus_num_clean,
                        "device": device_num_clean,
                        "vendor": "N/A",
                        "product": "N/A",
                        "speed": "N/A",
                        "serial": "N/A",
                        "device_class": "N/A",
                        "id": "N/A",
                        "sys_path": sysfs_path
                        if sysfs_path
                        else f"/sys/bus/usb/devices/{bus_num_clean}-{device_num_clean}",
                        "removable": "N/A",
                        "power": "N/A",
                        "bcd_device": "N/A",
                        "protocol": "N/A",
                        "subclass": "N/A",
                    }

                    id_match = re.search(r"ID\s+([a-fA-F0-9]{4}:[a-fA-F0-9]{4})", line)
                    if id_match:
                        device["id"] = id_match.group(1)

                if device:
                    id_match = re.search(r"ID\s+([a-fA-F0-9]{4}:[a-fA-F0-9]{4})", line)
                    if id_match:
                        device["id"] = id_match.group(1)

                        device_info = usb_device_names.get(
                            id_match.group(1).lower(), {}
                        )
                        if device_info:
                            device["vendor"] = device_info.get(
                                "vendor", device["vendor"]
                            )
                            device["product"] = device_info.get("product", "N/A")

                    manufacturer_match = re.search(r"iManufacturer\s+\d+\s+(.+)", line)
                    if manufacturer_match and device["vendor"] == "N/A":
                        device["vendor"] = manufacturer_match.group(1).strip()

                    product_match = re.search(r"iProduct\s+\d+\s+(.+)", line)
                    if product_match and device["product"] == "N/A":
                        device["product"] = product_match.group(1).strip()

                    serial_match = re.search(r"iSerial\s+\d+\s+(.+)", line)
                    if serial_match:
                        device["serial"] = serial_match.group(1).strip()

                    class_match = re.search(r"bDeviceClass\s+(\d+)\s+([^\(]+)", line)
                    if class_match:
                        device["device_class"] = (
                            f"{class_match.group(1).strip()} {class_match.group(2).strip()}"
                        )

                    subclass_match = re.search(r"bDeviceSubClass\s+(\d+)\s+(.+)", line)
                    if subclass_match:
                        device["subclass"] = (
                            f"{subclass_match.group(1).strip()} {subclass_match.group(2).strip()}"
                        )

                    protocol_match = re.search(r"bDeviceProtocol\s+(\d+)\s+(.+)", line)
                    if protocol_match:
                        device["protocol"] = (
                            f"{protocol_match.group(1).strip()} {protocol_match.group(2).strip()}"
                        )

                    bcd_match = re.search(r"bcdDevice\s+([0-9.]+)", line)
                    if bcd_match:
                        device["bcd_device"] = bcd_match.group(1)

                    speed_match = re.search(r"Negotiated speed:\s+(.+)", line)
                    if speed_match:
                        device["speed"] = speed_match.group(1).strip()

                    speed_match_alt = re.search(r"bcdUSB\s+([0-9.]+)", line)
                    if speed_match_alt and device["speed"] == "N/A":
                        usb_version = speed_match_alt.group(1)
                        speed_map = {
                            "1.00": "Low Speed (1.5 Mbps)",
                            "1.10": "Full Speed (12 Mbps)",
                            "2.00": "High Speed (480 Mbps)",
                            "3.00": "SuperSpeed (5 Gbps)",
                            "3.10": "SuperSpeed+ (10 Gbps)",
                            "3.20": "SuperSpeed+ (20 Gbps)",
                        }
                        device["speed"] = speed_map.get(
                            usb_version, f"USB {usb_version}"
                        )

            if device:
                # Verify device actually exists in sysfs before adding
                # This filters out devices that were detached but still in lsusb output
                if device.get("bus") != "N/A" and device.get("device") != "N/A":
                    sysfs_path = find_usb_sysfs_path(device["bus"], device["device"])
                    if sysfs_path and os.path.exists(sysfs_path):
                        device["sys_path"] = sysfs_path
                        usb_devices.append(device)
                else:
                    usb_devices.append(device)
    except:
        pass

    if not usb_devices:
        usb_devices.append(
            {
                "bus": "N/A",
                "device": "N/A",
                "vendor": "N/A",
                "product": "N/A",
                "speed": "N/A",
                "serial": "N/A",
                "device_class": "N/A",
                "id": "N/A",
                "sys_path": "N/A",
                "removable": "N/A",
                "power": "N/A",
                "bcd_device": "N/A",
                "protocol": "N/A",
                "subclass": "N/A",
            }
        )

    for idx, device in enumerate(usb_devices, 1):
        device["number"] = idx

    return usb_devices


def detach_usb_device(bus, device):
    """Detach USB device using unbind from USB driver."""
    try:
        # Find the correct sysfs path
        sys_path = find_usb_sysfs_path(bus, device)

        if not sys_path:
            return (
                False,
                f"Device {bus}-{device} not found in sysfs.",
            )

        device_path = os.path.basename(sys_path)

        # Check if it's a root hub (cannot be detached)
        bDeviceClass_path = os.path.join(sys_path, "bDeviceClass")
        if os.path.exists(bDeviceClass_path):
            try:
                with open(bDeviceClass_path, "r") as f:
                    device_class = f.read().strip()
                    if device_class == "09":  # Hub class
                        # Check devnum - root hubs usually have devnum 1
                        devnum_path = os.path.join(sys_path, "devnum")
                        if os.path.exists(devnum_path):
                            with open(devnum_path, "r") as f:
                                devnum = int(f.read().strip())
                                if devnum == 1:
                                    return (
                                        False,
                                        f"Cannot detach root USB hub {device_path}. It is a system device.",
                                    )
            except:
                pass

        # Use unbind to detach the device from USB driver
        unbind_path = "/sys/bus/usb/drivers/usb/unbind"
        if os.path.exists(unbind_path):
            with open(unbind_path, "w") as f:
                f.write(device_path)

            # Verify device was actually unbound
            time.sleep(0.3)  # Give system time to process

            # Check if device is still bound (driver symlink exists)
            driver_path = os.path.join(sys_path, "driver")
            if not os.path.exists(driver_path):
                return True, f"Device {device_path} successfully detached"
            else:
                # Try alternative: authorized=0
                authorized_path = os.path.join(sys_path, "authorized")
                if os.path.exists(authorized_path):
                    with open(authorized_path, "w") as f:
                        f.write("0")
                    time.sleep(0.3)

                    if not os.path.exists(driver_path):
                        return True, f"Device {device_path} successfully disabled"
                    else:
                        return (
                            False,
                            f"Device {device_path} could not be detached. It may be a system device or in use.",
                        )
                else:
                    return False, f"Device {device_path} could not be detached"
        else:
            # Fallback to remove file if unbind doesn't exist
            remove_path = os.path.join(sys_path, "remove")
            if os.path.exists(remove_path):
                with open(remove_path, "w") as f:
                    f.write("1")
                time.sleep(0.3)

                if not os.path.exists(sys_path):
                    return True, f"Device {device_path} successfully removed"
                else:
                    return False, f"Device {device_path} could not be removed"
            else:
                return (
                    False,
                    f"Cannot access unbind/remove files for device {device_path}",
                )

    except PermissionError:
        return False, "Permission denied. Run as root to detach USB devices."
    except Exception as e:
        return False, f"Error detaching device: {str(e)}"


def parse_edid(edid_data):
    edid_info = {
        "vendor": "Unknown",
        "model": "Unknown",
        "serial": "Unknown",
        "manufacture_date": "Unknown",
        "serial_text": "Unknown",
    }

    try:
        if len(edid_data) >= 128:
            bytes_data = edid_data

            if (
                bytes_data[8] == 0x00
                and bytes_data[9] == 0xFF
                and bytes_data[10] == 0xFF
                and bytes_data[11] == 0xFF
            ):
                pass
            else:
                manufacturer_byte1 = bytes_data[8]
                manufacturer_byte2 = bytes_data[9]

                bit_value = ((manufacturer_byte1 & 0x7C) >> 2) | (
                    (manufacturer_byte2 & 0xF0) >> 2
                )

                manufacturer_chars = []
                for shift in range(10, -1, -2):
                    char_bits = (bit_value >> shift) & 0x1F
                    if char_bits != 0:
                        manufacturer_chars.append(chr(char_bits + ord("@") + 1))

                edid_info["vendor"] = "".join(manufacturer_chars).upper()

            product_code = (bytes_data[11] << 8) | bytes_data[10]
            edid_info["model"] = str(product_code)

            serial = (
                (bytes_data[15] << 24)
                | (bytes_data[14] << 16)
                | (bytes_data[13] << 8)
                | bytes_data[12]
            )
            if serial != 0:
                edid_info["serial"] = str(serial)

            week = bytes_data[16]
            year = bytes_data[17]

            if week != 0:
                full_year = 1990 + year
                edid_info["manufacture_date"] = f"Week {week}, {full_year}"

            descriptor_start = 54
            for descriptor_num in range(4):
                descriptor_start_offset = descriptor_start + (18 * descriptor_num)
                if descriptor_start_offset + 18 > len(bytes_data):
                    continue

                descriptor = bytes_data[
                    descriptor_start_offset : descriptor_start_offset + 18
                ]
                if len(descriptor) >= 18:
                    if (
                        descriptor[0] == 0
                        and descriptor[1] == 0
                        and descriptor[2] == 0
                        and descriptor[3] == 0xFC
                    ):
                        model_name = ""
                        for i in range(5, 18):
                            if descriptor[i] in [0, 10, 13]:
                                break
                            model_name += chr(descriptor[i])
                        model_name = model_name.strip()
                        if model_name and model_name != "Unknown":
                            edid_info["model"] = model_name
                    elif (
                        descriptor[0] == 0
                        and descriptor[1] == 0
                        and descriptor[2] == 0
                        and descriptor[3] == 0xFF
                    ):
                        serial_text = ""
                        for i in range(5, 18):
                            if descriptor[i] in [0, 10, 13]:
                                break
                            serial_text += chr(descriptor[i])
                        serial_text = serial_text.strip()
                        if serial_text and serial_text != "Unknown":
                            edid_info["serial_text"] = serial_text
                            edid_info["serial"] = serial_text
    except:
        pass

    return edid_info


def get_display_info():
    display_info = []

    edid_cache = {}

    try:
        for conn_dir in os.listdir("/sys/class/drm"):
            if "card" in conn_dir and "-" in conn_dir and not conn_dir.endswith("-"):
                edid_path = os.path.join("/sys/class/drm", conn_dir, "edid")
                if os.path.exists(edid_path):
                    try:
                        with open(edid_path, "rb") as f:
                            edid_data = f.read()
                            edid_info = parse_edid(list(edid_data))
                            edid_cache[conn_dir] = edid_info
                    except:
                        pass
    except:
        pass

    try:
        result = subprocess.run(["xrandr"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split("\n")
            current_display = None
            available_modes = []

            for line in lines:
                if " connected" in line:
                    if current_display:
                        current_display["available_modes"] = available_modes
                        if available_modes:
                            max_mode = max(
                                available_modes,
                                key=lambda m: (m["width"], m["height"], m["rate"]),
                            )
                            current_display["max_resolution"] = (
                                f"{max_mode['width']}x{max_mode['height']}"
                            )
                            current_display["max_refresh_rate"] = (
                                f"{max_mode['rate']} Hz"
                            )
                        display_info.append(current_display)

                    current_display = {}
                    available_modes = []

                    conn_match = re.match(r"(.+?)\s+connected\s+(primary\s+)?", line)
                    if conn_match:
                        conn_name = conn_match.group(1).strip()
                        current_display["name"] = conn_name
                        current_display["primary"] = (
                            "Yes" if conn_match.group(2) else "No"
                        )
                    else:
                        continue

                    res_match = re.search(
                        r"(\d+)x(\d+)\+\d+\+\d+\s+\(([^)]+)\)\s+(\d+)mm\s+x\s+(\d+)mm",
                        line,
                    )
                    if res_match:
                        current_display["current_resolution"] = (
                            f"{res_match.group(1)}x{res_match.group(2)}"
                        )
                        rotation_info = res_match.group(3).strip()
                        if rotation_info:
                            rotation = rotation_info.split()[0]
                            current_display["rotation"] = rotation
                        current_display["physical_size"] = (
                            f"{res_match.group(4)}mm x {res_match.group(5)}mm"
                        )
                    else:
                        res_match_fallback = re.search(r"(\d+)x(\d+)\+\d+\+\d+", line)
                        if res_match_fallback:
                            current_display["current_resolution"] = (
                                f"{res_match_fallback.group(1)}x{res_match_fallback.group(2)}"
                            )

                    edid_key = None
                    for key in edid_cache:
                        if (
                            conn_name.replace("-", "-") in key
                            or key.replace("-", "-") in conn_name
                        ):
                            edid_key = key
                            break

                    if edid_key:
                        edid_data = edid_cache[edid_key]
                        current_display["vendor"] = edid_data.get("vendor", "Unknown")
                        current_display["model"] = edid_data.get("model", "Unknown")
                        current_display["serial"] = edid_data.get("serial", "Unknown")
                        current_display["manufacture_date"] = edid_data.get(
                            "manufacture_date", "Unknown"
                        )
                    else:
                        current_display["vendor"] = "Unknown"
                        current_display["model"] = "Unknown"
                        current_display["serial"] = "Unknown"
                        current_display["manufacture_date"] = "Unknown"

                elif current_display and "   " in line:
                    mode_match = re.match(r"\s*(\d+)x(\d+)\s+(\d+\.\d+)", line)
                    if mode_match:
                        available_modes.append(
                            {
                                "width": int(mode_match.group(1)),
                                "height": int(mode_match.group(2)),
                                "rate": float(mode_match.group(3)),
                            }
                        )

            if current_display:
                current_display["available_modes"] = available_modes
                if available_modes:
                    max_mode = max(
                        available_modes,
                        key=lambda m: (m["width"], m["height"], m["rate"]),
                    )
                    current_display["max_resolution"] = (
                        f"{max_mode['width']}x{max_mode['height']}"
                    )
                    current_display["max_refresh_rate"] = f"{max_mode['rate']} Hz"
                display_info.append(current_display)
    except:
        pass

    try:
        result = subprocess.run(
            ["ddcutil", "detect"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and "Display" in result.stdout:
            result = subprocess.run(
                ["ddcutil", "--brief", "getvcp", "0x01"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and display_info:
                pass
    except:
        pass

    try:
        result = subprocess.run(
            ["edid-decode"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            pass
    except:
        pass

    if not display_info:
        display_info.append(
            {
                "name": "No displays detected",
                "current_resolution": "N/A",
                "vendor": "N/A",
                "model": "N/A",
            }
        )

    return display_info


def get_drives_info():
    drives_info = []

    try:
        result = subprocess.run(
            [
                "lsblk",
                "-J",
                "-d",
                "-o",
                "NAME,SIZE,TYPE,VENDOR,MODEL,SERIAL,MOUNTPOINT,RO,RM",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            if "blockdevices" in data:
                for device in data["blockdevices"]:
                    drive = {}

                    drive["name"] = f"/dev/{device.get('name', 'Unknown')}"

                    size_str = device.get("size", "0")
                    size_str = size_str.replace(",", ".")
                    if size_str and size_str != "0":
                        if "T" in size_str:
                            size_val = float(size_str.replace("T", ""))
                            drive["size"] = f"{size_val:.2f} TB"
                        elif "G" in size_str:
                            size_val = float(size_str.replace("G", ""))
                            drive["size"] = f"{size_val:.2f} GB"
                        elif "M" in size_str:
                            size_val = float(size_str.replace("M", ""))
                            drive["size"] = f"{size_val:.2f} MB"
                        else:
                            drive["size"] = size_str
                    else:
                        drive["size"] = "Unknown"

                    drive["type"] = device.get("type", "disk")

                    vendor = device.get("vendor")
                    if vendor and vendor.strip():
                        drive["vendor"] = vendor.strip()
                    else:
                        drive["vendor"] = "Unknown"

                    model = device.get("model")
                    if model and model.strip():
                        drive["model"] = model.strip()
                    else:
                        drive["model"] = "Unknown"

                    serial = device.get("serial")
                    if serial and serial.strip():
                        drive["serial"] = serial.strip()
                    else:
                        drive["serial"] = "N/A"

                    mountpoint = device.get("mountpoint")
                    if mountpoint and mountpoint.strip():
                        drive["mountpoint"] = mountpoint.strip()
                    else:
                        drive["mountpoint"] = "N/A"

                    drive["readonly"] = "Yes" if device.get("ro") == "1" else "No"
                    drive["removable"] = "Yes" if device.get("rm") == "1" else "No"

                    if drive["type"] == "disk" and drive["model"] != "Unknown":
                        drives_info.append(drive)
    except:
        pass

    if not drives_info:
        try:
            import glob

            block_devices = glob.glob("/sys/block/*")
            for device_path in block_devices:
                if "loop" in device_path or "ram" in device_path:
                    continue

                device_name = os.path.basename(device_path)
                drive = {}
                drive["name"] = f"/dev/{device_name}"

                try:
                    with open(os.path.join(device_path, "size"), "r") as f:
                        size_bytes = int(f.read().strip())
                        drive["size"] = f"{size_bytes / (1024**3):.2f} GB"
                except:
                    drive["size"] = "Unknown"

                try:
                    with open(os.path.join(device_path, "device/type"), "r") as f:
                        device_type = f.read().strip()
                        if device_type == "0":
                            drive["type"] = "disk"
                        elif device_type == "7":
                            drive["type"] = "loop"
                        else:
                            drive["type"] = "unknown"
                except:
                    drive["type"] = "disk"

                try:
                    with open(os.path.join(device_path, "ro"), "r") as f:
                        ro = int(f.read().strip())
                        drive["readonly"] = "Yes" if ro == 1 else "No"
                except:
                    drive["readonly"] = "No"

                try:
                    with open(os.path.join(device_path, "removable"), "r") as f:
                        rm = int(f.read().strip())
                        drive["removable"] = "Yes" if rm == 1 else "No"
                except:
                    drive["removable"] = "No"

                try:
                    with open(os.path.join(device_path, "device/vendor"), "r") as f:
                        drive["vendor"] = f.read().strip()
                except:
                    drive["vendor"] = "Unknown"

                try:
                    with open(os.path.join(device_path, "device/model"), "r") as f:
                        drive["model"] = f.read().strip()
                except:
                    drive["model"] = "Unknown"

                try:
                    with open(os.path.join(device_path, "device/serial"), "r") as f:
                        drive["serial"] = f.read().strip()
                except:
                    drive["serial"] = "N/A"

                drive["mountpoint"] = "N/A"

                if drive["type"] == "disk" and drive["model"] != "Unknown":
                    drives_info.append(drive)
        except:
            pass

    if not drives_info:
        drives_info.append(
            {
                "name": "No drives detected",
                "model": "N/A",
                "vendor": "N/A",
                "size": "N/A",
                "serial": "N/A",
                "type": "N/A",
                "readonly": "N/A",
                "removable": "N/A",
            }
        )

    return drives_info


def get_battery_info():
    battery_info = {
        "present": False,
        "status": "No battery detected",
        "percent": "N/A",
        "time_left": "N/A",
        "power_plugged": "N/A",
        "health": "N/A",
        "cycle_count": "N/A",
        "technology": "N/A",
    }

    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            battery_info["present"] = True
            battery_info["percent"] = f"{battery.percent}%"
            battery_info["power_plugged"] = "Yes" if battery.power_plugged else "No"

            if battery.secsleft == psutil.POWER_TIME_UNLIMITED:
                battery_info["time_left"] = (
                    "Charging" if battery.power_plugged else "Unlimited"
                )
            elif battery.secsleft == psutil.POWER_TIME_UNKNOWN:
                battery_info["time_left"] = "Calculating..."
            else:
                hours = battery.secsleft // 3600
                minutes = (battery.secsleft % 3600) // 60
                battery_info["time_left"] = f"{hours}h {minutes}m"

            if battery.power_plugged:
                battery_info["status"] = (
                    "Charging" if battery.percent < 100 else "Fully Charged"
                )
            else:
                battery_info["status"] = "Discharging"

            # Try to get additional battery info from sysfs
            try:
                import glob

                power_supply_paths = glob.glob("/sys/class/power_supply/BAT*")
                if power_supply_paths:
                    bat_path = power_supply_paths[0]

                    # Try to get technology
                    tech_path = os.path.join(bat_path, "technology")
                    if os.path.exists(tech_path):
                        with open(tech_path, "r") as f:
                            tech = f.read().strip()
                            if tech and tech != "Unknown":
                                battery_info["technology"] = tech

                    # Try to get cycle count
                    cycle_path = os.path.join(bat_path, "cycle_count")
                    if os.path.exists(cycle_path):
                        with open(cycle_path, "r") as f:
                            cycles = f.read().strip()
                            if cycles and cycles != "0":
                                battery_info["cycle_count"] = cycles

                    # Try to get health info from energy_full vs energy_full_design
                    energy_full_path = os.path.join(bat_path, "energy_full")
                    energy_design_path = os.path.join(bat_path, "energy_full_design")

                    if os.path.exists(energy_full_path) and os.path.exists(
                        energy_design_path
                    ):
                        try:
                            with open(energy_full_path, "r") as f:
                                energy_full = int(f.read().strip())
                            with open(energy_design_path, "r") as f:
                                energy_design = int(f.read().strip())

                            if energy_design > 0:
                                health_percent = (energy_full / energy_design) * 100
                                battery_info["health"] = f"{health_percent:.1f}%"
                        except:
                            pass
            except:
                pass
    except:
        pass

    return battery_info


def get_all_hardware_info():
    return {
        "system": get_os_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "ram_sticks": get_ram_sticks(),
        "motherboard": get_motherboard_info(),
        "bios": get_bios_info(),
        "chassis": get_chassis_info(),
        "gpu": get_gpu_info(),
        "network": get_network_info(),
        "usb": get_usb_devices(),
        "display": get_display_info(),
        "drives": get_drives_info(),
        "battery": get_battery_info(),
    }
