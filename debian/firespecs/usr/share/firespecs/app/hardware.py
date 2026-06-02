import platform
import psutil
import subprocess
import re
import os
import socket
import time

# Instruction sets shown in CPU panel (flag tokens from /proc/cpuinfo or lscpu).
_CPU_INSTRUCTION_SETS = (
    ("x86-64", ("lm",)),
    ("MMX", ("mmx",)),
    ("SSE", ("sse",)),
    ("SSE2", ("sse2",)),
    ("SSE3", ("sse3",)),
    ("SSSE3", ("ssse3",)),
    ("SSE4.1", ("sse4_1",)),
    ("SSE4.2", ("sse4_2",)),
    ("AES-NI", ("aes",)),
    ("CLMUL", ("pclmulqdq",)),
    ("AVX", ("avx",)),
    ("FMA3", ("fma",)),
    ("AVX2", ("avx2",)),
    ("AVX-VNNI", ("avx_vnni",)),
    ("SHA", ("sha_ni",)),
    ("BMI1", ("bmi1",)),
    ("BMI2", ("bmi2",)),
    ("ADX", ("adx",)),
    ("VAES", ("vaes",)),
    ("VPCLMULQDQ", ("vpclmulqdq",)),
    ("AVX-512F", ("avx512f",)),
    ("AVX-512DQ", ("avx512dq",)),
    ("AVX-512CD", ("avx512cd",)),
    ("AVX-512BW", ("avx512bw",)),
    ("AVX-512VL", ("avx512vl",)),
    ("AVX-512BF16", ("avx512bf16",)),
    ("AVX-512VNNI", ("avx512vnni",)),
    ("Intel VT-x", ("vmx",)),
    ("AMD-V", ("svm",)),
)


def _read_cpu_flags():
    """Return CPU feature flags as a set of tokens (from cpuinfo or lscpu)."""
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.lower().startswith("flags"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        return set(parts[1].split())
    except OSError:
        pass

    try:
        result = subprocess.run(
            ["lscpu"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.lower().startswith("flags:"):
                    return set(line.split(":", 1)[1].split())
    except (OSError, subprocess.TimeoutExpired):
        pass

    return set()


def format_cpu_instruction_sets(flags):
    """
    Turn raw CPU flags into a readable comma-separated instruction list.

    Returns empty string if no flags are known.
    """
    if not flags:
        return ""

    if isinstance(flags, str):
        flags = set(flags.split())

    detected = []
    for label, tokens in _CPU_INSTRUCTION_SETS:
        if any(token in flags for token in tokens):
            detected.append(label)

    return ", ".join(detected)


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

    except OSError:
        cpu["model"] = platform.processor() or "Unknown CPU"

    flags = _read_cpu_flags()
    if flags:
        cpu["instructions"] = format_cpu_instruction_sets(flags)
        cpu["flags"] = " ".join(sorted(flags))

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
                try:
                    with open(serial_file, "r") as f:
                        serial = f.read().strip()
                        if (
                            serial
                            and serial != "Not Specified"
                            and serial != "Default string"
                        ):
                            mb_info["serial_number"] = serial
                except (OSError, PermissionError):
                    pass

            if os.path.exists(asset_file):
                try:
                    with open(asset_file, "r") as f:
                        asset = f.read().strip()
                        if (
                            asset
                            and asset != "Not Specified"
                            and asset != "Default string"
                        ):
                            mb_info["asset_tag"] = asset
                except (OSError, PermissionError):
                    pass
        except (OSError, PermissionError):
            pass

    # Fallback to dmidecode for any field still missing (requires root)
    needs_dmi = any(
        mb_info[key] in ("Unknown", "Not available")
        for key in (
            "manufacturer",
            "product_name",
            "version",
            "serial_number",
            "asset_tag",
        )
    )
    if needs_dmi:
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


def get_gpu_info():
    from app.gpu_memory import (
        apply_glxinfo_fallback,
        enrich_gpu_entry,
        enumerate_drm_gpus,
        merge_nvidia_details,
        normalize_pci_slot,
        _nvidia_smi_by_pci,
    )
    from app.gpu_stats import read_gpu_temp_from_device

    drm_cards = {card["pci_slot"]: card for card in enumerate_drm_gpus()}
    nvidia_by_pci = _nvidia_smi_by_pci()
    gpu_info = []

    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                device_type = re.search(r"[^:]+:\s*(.+?):\s", line)
                if not device_type:
                    continue
                device_type_str = device_type.group(1).strip()
                if (
                    "VGA compatible controller" not in device_type_str
                    and "3D controller" not in device_type_str
                    and "Display" not in device_type_str
                ):
                    continue

                bus_match = re.match(
                    r"^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F])\s+(.+?):\s+(.+)$",
                    line,
                )
                if not bus_match:
                    continue

                gpu = {
                    "bus": bus_match.group(1).strip(),
                    "device": bus_match.group(3).strip(),
                }
                gpu["pci_slot"] = normalize_pci_slot(gpu["bus"])
                card_meta = drm_cards.get(gpu["pci_slot"])
                enrich_gpu_entry(gpu, card_meta, nvidia_by_pci)
                merge_nvidia_details(gpu, gpu["pci_slot"], nvidia_by_pci)
                gpu_info.append(gpu)
    except (OSError, subprocess.TimeoutExpired):
        pass

    listed_pcis = {gpu.get("pci_slot") for gpu in gpu_info if gpu.get("pci_slot")}
    for pci_slot, card_meta in drm_cards.items():
        if pci_slot in listed_pcis:
            continue
        bus_label = pci_slot[5:] if pci_slot.startswith("0000:") else pci_slot
        gpu = {
            "bus": bus_label,
            "device": f"Graphics device ({pci_slot})",
            "pci_slot": pci_slot,
        }
        enrich_gpu_entry(gpu, card_meta, nvidia_by_pci)
        merge_nvidia_details(gpu, pci_slot, nvidia_by_pci)
        gpu_info.append(gpu)

    try:
        result = subprocess.run(["glxinfo"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            renderer_match = re.search(
                r"OpenGL renderer string:\s*(.+)", result.stdout
            )
            if renderer_match:
                if not gpu_info:
                    gpu_info.append(
                        {
                            "bus": "Primary GPU",
                            "device": renderer_match.group(1).strip(),
                        }
                    )
                elif "renderer" not in gpu_info[0]:
                    gpu_info[0]["renderer"] = renderer_match.group(1).strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    apply_glxinfo_fallback(gpu_info)

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


def _edid_bytes_to_data(edid_data):
    if isinstance(edid_data, (bytes, bytearray)):
        return bytes(edid_data)
    return bytes(edid_data)


def parse_edid_native_resolution(edid_data):
    """Preferred panel resolution from the first valid EDID detailed timing block."""
    data = _edid_bytes_to_data(edid_data)
    if len(data) < 72:
        return None

    for descriptor_index in range(4):
        offset = 54 + (18 * descriptor_index)
        dtd = data[offset : offset + 18]
        pixel_clock = dtd[0] | (dtd[1] << 8)
        if pixel_clock == 0:
            continue
        h_active = dtd[2] | ((dtd[4] & 0xF0) << 4)
        v_active = dtd[5] | ((dtd[7] & 0xF0) << 4)
        if h_active >= 320 and v_active >= 240:
            return h_active, v_active
    return None


def _drm_connector_name(conn_dir):
    match = re.match(r"card\d+-(.+)", conn_dir)
    return match.group(1) if match else conn_dir


def _connector_match_key(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _read_drm_connector_status(conn_path):
    status_path = os.path.join(conn_path, "status")
    if not os.path.exists(status_path):
        return "unknown"
    try:
        with open(status_path, "r", encoding="utf-8") as handle:
            return handle.read().strip().lower()
    except OSError:
        return "unknown"


def _read_drm_active_mode(conn_path):
    """Current kernel mode for this connector (physical pixels, not desktop scale)."""
    mode_path = os.path.join(conn_path, "mode")
    if not os.path.exists(mode_path):
        return None
    try:
        with open(mode_path, "r", encoding="utf-8") as handle:
            mode = handle.read().strip()
        if re.match(r"^\d+x\d+$", mode):
            return mode
    except OSError:
        pass
    return None


def _read_drm_modes(conn_path):
    modes_path = os.path.join(conn_path, "modes")
    modes = []
    if not os.path.exists(modes_path):
        return modes
    try:
        with open(modes_path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                match = re.match(r"^(\d+)x(\d+)$", line)
                if match:
                    modes.append((int(match.group(1)), int(match.group(2))))
    except OSError:
        pass
    return modes


def _build_display_from_drm(conn_dir):
    if "Virtual" in conn_dir or "Writeback" in conn_dir:
        return None

    conn_path = os.path.join("/sys/class/drm", conn_dir)
    status = _read_drm_connector_status(conn_path)
    if status not in ("connected", "unknown"):
        return None
    if status == "unknown":
        edid_path = os.path.join(conn_path, "edid")
        if not os.path.exists(edid_path) or os.path.getsize(edid_path) == 0:
            return None

    display = {
        "name": _drm_connector_name(conn_dir),
        "drm_connector": conn_dir,
        "primary": "Unknown",
        "vendor": "Unknown",
        "model": "Unknown",
        "serial": "Unknown",
        "manufacture_date": "Unknown",
    }

    active_mode = _read_drm_active_mode(conn_path)
    if active_mode:
        display["current_resolution"] = active_mode

    edid_path = os.path.join(conn_path, "edid")
    if os.path.exists(edid_path):
        try:
            with open(edid_path, "rb") as handle:
                edid_raw = handle.read()
            if edid_raw:
                edid_info = parse_edid(list(edid_raw))
                display["vendor"] = edid_info.get("vendor", "Unknown")
                display["model"] = edid_info.get("model", "Unknown")
                display["serial"] = edid_info.get("serial", "Unknown")
                display["manufacture_date"] = edid_info.get(
                    "manufacture_date", "Unknown"
                )
                native = parse_edid_native_resolution(edid_raw)
                if native:
                    native_text = f"{native[0]}x{native[1]}"
                    display["native_resolution"] = native_text
                    display["max_resolution"] = native_text
        except OSError:
            pass

    if "max_resolution" not in display:
        modes = _read_drm_modes(conn_path)
        if modes:
            width, height = max(modes, key=lambda item: item[0] * item[1])
            display["max_resolution"] = f"{width}x{height}"

    if "current_resolution" not in display and "native_resolution" in display:
        display["current_resolution"] = display["native_resolution"]

    return display if status == "connected" or "native_resolution" in display else None


def _enrich_displays_from_xrandr(displays):
    """Add primary / scaled desktop resolution; does not replace EDID/kernel modes."""
    if not displays or not os.environ.get("DISPLAY"):
        return

    try:
        result = subprocess.run(
            ["xrandr"],
            capture_output=True,
            text=True,
            timeout=5,
            env=os.environ,
        )
    except (OSError, subprocess.TimeoutExpired):
        return
    if result.returncode != 0:
        return

    keyed = {_connector_match_key(item["name"]): item for item in displays}
    drm_keyed = {
        _connector_match_key(_drm_connector_name(item.get("drm_connector", ""))): item
        for item in displays
        if item.get("drm_connector")
    }

    current = None
    for line in result.stdout.splitlines():
        if " connected" in line:
            match = re.match(r"(.+?)\s+connected(\s+primary)?", line)
            if not match:
                continue
            x_name = match.group(1).strip()
            current = keyed.get(_connector_match_key(x_name))
            if current is None:
                for drm_key, display in drm_keyed.items():
                    if drm_key and (
                        drm_key in _connector_match_key(x_name)
                        or _connector_match_key(x_name) in drm_key
                    ):
                        current = display
                        break
            if current is None:
                current = None
                continue
            if match.group(2):
                current["primary"] = "Yes"
            elif current.get("primary") == "Unknown":
                current["primary"] = "No"

            res_match = re.search(r"(\d+)x(\d+)\+\d+\+\d+", line)
            if res_match:
                desktop = f"{res_match.group(1)}x{res_match.group(2)}"
                native = current.get("native_resolution")
                if native and desktop != native:
                    current["desktop_resolution"] = desktop
                elif "current_resolution" not in current:
                    current["current_resolution"] = desktop

            size_match = re.search(r"(\d+)mm\s+x\s+(\d+)mm", line)
            if size_match and "physical_size" not in current:
                current["physical_size"] = (
                    f"{size_match.group(1)}mm x {size_match.group(2)}mm"
                )
        elif current and line.startswith("\t") and "*" in line:
            mode_match = re.match(r"\s*(\d+)x(\d+)\s+([\d.]+)\*", line)
            if mode_match:
                current["max_refresh_rate"] = f"{mode_match.group(3)} Hz"


def get_display_info():
    """
    Display information from DRM sysfs + EDID (works as user and via pkexec).

    xrandr is only used optionally for primary flag and scaled desktop size on X11;
    it is not required and must not define the panel's native resolution.
    """
    display_info = []

    try:
        for conn_dir in sorted(os.listdir("/sys/class/drm")):
            if "card" not in conn_dir or "-" not in conn_dir or conn_dir.endswith("-"):
                continue
            display = _build_display_from_drm(conn_dir)
            if display:
                display_info.append(display)
    except OSError:
        pass

    if display_info:
        _enrich_displays_from_xrandr(display_info)

    if not display_info:
        display_info.append(
            {
                "name": "No displays detected",
                "current_resolution": "N/A",
                "vendor": "N/A",
                "model": "N/A",
                "_placeholder": True,
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
                "_placeholder": True,
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
        "gpu": get_gpu_info(),
        "network": get_network_info(),
        "display": get_display_info(),
        "drives": get_drives_info(),
        "battery": get_battery_info(),
    }
