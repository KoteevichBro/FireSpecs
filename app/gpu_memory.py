"""GPU memory detection across vendors (sysfs, DRM ioctl, tools)."""

import ctypes
import fcntl
import glob
import os
import re
import struct
import subprocess

VENDOR_NVIDIA = "0x10de"
VENDOR_AMD = "0x1002"
VENDOR_INTEL = "0x8086"

_DRM_COMMAND_BASE = 0x40
_DRM_XE_DEVICE_QUERY = 0x00
_DRM_XE_DEVICE_QUERY_MEM_REGIONS = 1
_DRM_XE_MEM_REGION_CLASS_SYSMEM = 0
_DRM_XE_MEM_REGION_CLASS_VRAM = 1
_DRM_XE_MEM_REGION_SIZE = 88


class _DrmXeDeviceQuery(ctypes.Structure):
    _fields_ = [
        ("extensions", ctypes.c_uint64),
        ("query", ctypes.c_uint32),
        ("size", ctypes.c_uint32),
        ("data", ctypes.c_uint64),
        ("reserved", ctypes.c_uint64 * 2),
    ]


def _drm_iowr(nr, size):
    return (3 << 30) | (size << 16) | (ord("d") << 8) | nr


def _ioctl_xe_device_query():
    return _drm_iowr(
        _DRM_COMMAND_BASE + _DRM_XE_DEVICE_QUERY,
        ctypes.sizeof(_DrmXeDeviceQuery),
    )


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def _read_int(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return None


def normalize_pci_slot(slot):
    """Normalize PCI slot to 0000:bb:dd.f form."""
    slot = (slot or "").strip().lower()
    if not slot:
        return ""
    if re.match(r"^[0-9a-f]{4}:", slot):
        return slot
    return f"0000:{slot}"


def _pci_slot_from_device_dir(device_dir):
    uevent = _read_text(os.path.join(device_dir, "uevent"))
    for line in uevent.splitlines():
        if line.startswith("PCI_SLOT_NAME="):
            return normalize_pci_slot(line.split("=", 1)[1])
    return ""


def _device_driver_name(device_dir):
    driver_link = os.path.join(device_dir, "driver")
    if os.path.islink(driver_link):
        return os.path.basename(os.path.realpath(driver_link))
    return ""


def _card_vendor(device_dir):
    return _read_text(os.path.join(device_dir, "vendor")).lower()


def enumerate_drm_gpus():
    """
    List DRM GPU cards with PCI slot, driver, vendor, and render node path.

    Returns list of dicts: card_path, pci_slot, vendor, driver, render_node
    """
    cards = []
    for card_path in sorted(glob.glob("/sys/class/drm/card*")):
        if "-" in os.path.basename(card_path):
            continue

        device_dir = os.path.join(card_path, "device")
        if not os.path.isdir(device_dir):
            continue

        pci_slot = _pci_slot_from_device_dir(device_dir)
        if not pci_slot:
            continue

        device_real = os.path.realpath(device_dir)
        render_node = ""
        for render_sys in glob.glob("/sys/class/drm/renderD*"):
            render_device = os.path.join(render_sys, "device")
            if os.path.exists(render_device) and os.path.realpath(
                render_device
            ) == device_real:
                render_node = os.path.join("/dev/dri", os.path.basename(render_sys))
                break

        cards.append(
            {
                "card_path": card_path,
                "pci_slot": pci_slot,
                "vendor": _card_vendor(device_dir),
                "driver": _device_driver_name(device_dir),
                "device_dir": device_dir,
                "render_node": render_node,
            }
        )

    return cards


def _format_bytes(num_bytes):
    if num_bytes is None or num_bytes <= 0:
        return None
    gib = num_bytes / (1024**3)
    if gib >= 1.0:
        return f"{gib:.2f} GB"
    mib = num_bytes / (1024**2)
    return f"{mib:.0f} MB"


def _memory_dict(total_bytes, used_bytes, label="VRAM"):
    if not total_bytes or total_bytes <= 0:
        return {}

    used_bytes = max(0, used_bytes or 0)
    free_bytes = max(0, total_bytes - used_bytes)
    percent = (used_bytes / total_bytes * 100.0) if total_bytes else 0.0

    return {
        "memory_label": label,
        "memory_total": _format_bytes(total_bytes),
        "memory_used": _format_bytes(used_bytes),
        "memory_free": _format_bytes(free_bytes),
        "memory_percent": f"{percent:.1f}%",
        "memory_total_bytes": total_bytes,
        "memory_used_bytes": used_bytes,
    }


def _memory_from_sysfs(device_dir):
    """AMD/NVIDIA/legacy Intel mem_info_vram sysfs."""
    total_path = os.path.join(device_dir, "mem_info_vram_total")
    used_path = os.path.join(device_dir, "mem_info_vram_used")
    if os.path.exists(total_path) and os.path.exists(used_path):
        total = _read_int(total_path)
        used = _read_int(used_path)
        if total and total > 0:
            return _memory_dict(total, used or 0, "VRAM")

    vis_total_path = os.path.join(device_dir, "mem_info_vis_vram_total")
    vis_used_path = os.path.join(device_dir, "mem_info_vis_vram_used")
    if os.path.exists(vis_total_path):
        total = _read_int(vis_total_path)
        used = _read_int(vis_used_path) if os.path.exists(vis_used_path) else 0
        if total and total > 0:
            return _memory_dict(total, used or 0, "Visible VRAM")

    gtt_total_path = os.path.join(device_dir, "mem_info_gtt_total")
    gtt_used_path = os.path.join(device_dir, "mem_info_gtt_used")
    if os.path.exists(gtt_total_path):
        total = _read_int(gtt_total_path)
        used = _read_int(gtt_used_path) if os.path.exists(gtt_used_path) else 0
        if total and total > 0:
            return _memory_dict(total, used or 0, "GTT")

    return {}


def _parse_xe_mem_regions(buffer, size):
    if size < 8:
        return []

    num_regions = struct.unpack_from("I", buffer, 0)[0]
    regions = []
    offset = 8
    for _ in range(num_regions):
        if offset + _DRM_XE_MEM_REGION_SIZE > size:
            break
        mem_class, _instance, _min_page = struct.unpack_from(
            "HHI", buffer, offset
        )
        total_size, used = struct.unpack_from("QQ", buffer, offset + 8)
        regions.append({"mem_class": mem_class, "total_size": total_size, "used": used})
        offset += _DRM_XE_MEM_REGION_SIZE

    return regions


def _memory_from_xe_ioctl(render_node):
    if not render_node or not os.path.exists(render_node):
        return {}

    fd = None
    try:
        ioctl = _ioctl_xe_device_query()
        fd = os.open(render_node, os.O_RDWR)

        query = _DrmXeDeviceQuery(
            query=_DRM_XE_DEVICE_QUERY_MEM_REGIONS, size=0, data=0
        )
        fcntl.ioctl(fd, ioctl, query)
        if query.size <= 0:
            return {}

        buffer = (ctypes.c_byte * query.size)()
        query.data = ctypes.addressof(buffer)
        query.size = ctypes.sizeof(buffer)
        fcntl.ioctl(fd, ioctl, query)

        regions = _parse_xe_mem_regions(buffer, query.size)
        if not regions:
            return {}

        vram_total = 0
        vram_used = 0
        sysmem_total = 0
        sysmem_used = 0

        for region in regions:
            if region["mem_class"] == _DRM_XE_MEM_REGION_CLASS_VRAM:
                vram_total += region["total_size"]
                vram_used += region["used"]
            elif region["mem_class"] == _DRM_XE_MEM_REGION_CLASS_SYSMEM:
                sysmem_total += region["total_size"]
                sysmem_used += region["used"]

        result = {}
        if vram_total > 0:
            result.update(_memory_dict(vram_total, vram_used, "VRAM"))
        elif len(regions) == 1 and regions[0]["total_size"] > 0:
            result.update(
                _memory_dict(
                    regions[0]["total_size"],
                    regions[0]["used"],
                    "Shared memory",
                )
            )

        if sysmem_total > 0 and vram_total > 0:
            result["shared_memory_total"] = _format_bytes(sysmem_total)
            if sysmem_used > 0:
                result["shared_memory_used"] = _format_bytes(sysmem_used)

        return result
    except OSError:
        return {}
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _nvidia_pci_bus_id(raw_bus):
    raw = (raw_bus or "").strip().lower()
    if raw.startswith("00000000:"):
        return normalize_pci_slot("0000:" + raw.split(":", 1)[1])
    return normalize_pci_slot(raw)


def _nvidia_smi_by_pci():
    """Map normalized PCI slot -> memory and driver details from nvidia-smi."""
    mapping = {}
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=pci.bus_id,driver_version,temperature.gpu,"
                "utilization.gpu,memory.total,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return mapping

        for line in result.stdout.strip().splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 6:
                continue
            pci = _nvidia_pci_bus_id(parts[0])
            try:
                total_mib = float(parts[4])
                used_mib = float(parts[5])
            except ValueError:
                continue

            entry = _memory_dict(
                int(total_mib * 1024 * 1024),
                int(used_mib * 1024 * 1024),
                "VRAM",
            )
            entry["driver"] = parts[1].strip()
            try:
                entry["temperature"] = f"{float(parts[2]):.0f}°C"
                entry["utilization"] = f"{float(parts[3]):.0f}%"
            except ValueError:
                pass
            mapping[pci] = entry
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass

    return mapping


def _nvidia_smi_memory_by_pci():
    """Backward-compatible memory-only map."""
    return {
        pci: {key: value for key, value in entry.items() if key.startswith("memory_")}
        for pci, entry in _nvidia_smi_by_pci().items()
    }


def _memory_from_glxinfo():
    try:
        result = subprocess.run(
            ["glxinfo"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {}
        match = re.search(r"Video memory:\s*(\d+)\s*MB", result.stdout)
        if match:
            total_bytes = int(match.group(1)) * 1024 * 1024
            return _memory_dict(total_bytes, 0, "VRAM (OpenGL)")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return {}


def merge_nvidia_details(gpu, pci_slot, nvidia_by_pci=None):
    if nvidia_by_pci is None:
        nvidia_by_pci = _nvidia_smi_by_pci()
    details = nvidia_by_pci.get(pci_slot)
    if not details:
        return gpu
    for key, value in details.items():
        if key.startswith("memory_") or key in ("driver", "temperature", "utilization"):
            gpu[key] = value
    return gpu


def collect_gpu_memory(card_meta, nvidia_by_pci=None):
    """
    Collect memory stats for one DRM GPU.

    card_meta: entry from enumerate_drm_gpus()
    Returns dict with memory_* fields or empty dict.
    """
    device_dir = card_meta.get("device_dir", "")
    driver = card_meta.get("driver", "")
    pci_slot = card_meta.get("pci_slot", "")
    render_node = card_meta.get("render_node", "")

    if driver == "xe":
        memory = _memory_from_xe_ioctl(render_node)
        if memory:
            return memory

    memory = _memory_from_sysfs(device_dir)
    if memory:
        return memory

    if nvidia_by_pci is None:
        nvidia_by_pci = _nvidia_smi_memory_by_pci()
    if pci_slot in nvidia_by_pci:
        return nvidia_by_pci[pci_slot]

    if driver == "nvidia":
        memory = _memory_from_sysfs(device_dir)
        if memory:
            return memory

    return {}


def enrich_gpu_entry(gpu, card_meta, nvidia_by_pci=None):
    """Merge driver and memory fields into a gpu dict from get_gpu_info."""
    if not card_meta:
        return gpu

    if card_meta.get("driver"):
        gpu["driver_kernel"] = card_meta["driver"]

    memory = collect_gpu_memory(card_meta, nvidia_by_pci)
    gpu.update(memory)
    return gpu


def collect_live_gpu_memory(card_path=None, pci_slot=None):
    """
    Live VRAM / shared memory usage for the hardware GPU panel.

    Prefer card_path (from collect_live_gpu_stats); falls back to pci_slot or
    the first DRM GPU.
    """
    cards = enumerate_drm_gpus()
    card_meta = None

    if card_path:
        for card in cards:
            if card.get("card_path") == card_path:
                card_meta = card
                break

    if not card_meta and pci_slot:
        pci_slot = normalize_pci_slot(pci_slot)
        for card in cards:
            if card.get("pci_slot") == pci_slot:
                card_meta = card
                break

    if not card_meta and cards:
        card_meta = cards[0]

    if not card_meta:
        return {}

    memory = collect_gpu_memory(card_meta)
    return {
        "pci_slot": card_meta.get("pci_slot"),
        "memory_used": memory.get("memory_used", ""),
        "memory_free": memory.get("memory_free", ""),
        "memory_percent": memory.get("memory_percent", ""),
        "shared_memory_used": memory.get("shared_memory_used", ""),
    }


def apply_glxinfo_fallback(gpu_list):
    """If no GPU has memory yet, try glxinfo once for the primary entry."""
    if not gpu_list:
        return gpu_list
    if any(gpu.get("memory_total") for gpu in gpu_list):
        return gpu_list

    glx_mem = _memory_from_glxinfo()
    if glx_mem and gpu_list:
        gpu_list[0].update(glx_mem)
    return gpu_list
