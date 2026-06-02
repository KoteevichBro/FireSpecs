"""Live GPU utilization and memory stats from sysfs and optional tools."""

import glob
import json
import os
import re
import shutil
import subprocess
import time
from collections import defaultdict

VENDOR_INTEL = "0x8086"
VENDOR_AMD = "0x1002"
VENDOR_NVIDIA = "0x10de"

# Prefer discrete GPUs over typical Intel iGPU when both are present.
_VENDOR_PRIORITY = {
    VENDOR_NVIDIA: 300,
    VENDOR_AMD: 200,
    VENDOR_INTEL: 100,
}

_INTEL_HWMON_NAMES = frozenset({"xe", "i915"})

# Previous gtidle samples for utilization between polls (card_path -> state).
_GTIDLE_SAMPLE_STATE = {}

# Previous DRM fdinfo aggregate for xe/i915 clients without sysfs busy.
_FDINFO_SAMPLE_STATE = None


def _read_int(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return None


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def _card_vendor(device_dir):
    vendor = _read_text(os.path.join(device_dir, "vendor")).lower()
    return vendor or "unknown"


def _is_render_only_card(card_path):
    name = os.path.basename(card_path)
    return "-" in name


def _intel_has_sysfs_marker(device_dir):
    if os.path.isdir(os.path.join(device_dir, "tile0")):
        return True
    if os.path.isdir(os.path.join(device_dir, "gt")):
        return True
    for name_path in glob.glob(os.path.join(device_dir, "hwmon", "hwmon*", "name")):
        if _read_text(name_path) in _INTEL_HWMON_NAMES:
            return True
    return False


def _read_intel_freq_mhz(device_dir):
    freq_mhz = 0

    for act_path in glob.glob(
        os.path.join(device_dir, "tile*", "gt*", "freq0", "act_freq")
    ):
        value = _read_int(act_path)
        if value is not None and value > 0:
            freq_mhz = max(freq_mhz, value)

    if freq_mhz > 0:
        return freq_mhz

    for cur_path in glob.glob(
        os.path.join(device_dir, "tile*", "gt*", "freq0", "cur_freq")
    ):
        value = _read_int(cur_path)
        if value is not None and value > 0:
            freq_mhz = max(freq_mhz, value)

    legacy_paths = [
        os.path.join(device_dir, "gt_act_freq_mhz"),
        os.path.join(device_dir, "gt_cur_freq_mhz"),
        os.path.join(device_dir, "gt", "gt0", "rps", "cur_freq_mhz"),
    ]
    for path in legacy_paths:
        value = _read_int(path)
        if value is not None and value > 0:
            freq_mhz = max(freq_mhz, value)

    return freq_mhz


def _temp_from_hwmon_dir(hwmon_dir, driver_name):
    if driver_name == "xe":
        label_path = os.path.join(hwmon_dir, "temp2_label")
        input_path = os.path.join(hwmon_dir, "temp2_input")
        if _read_text(label_path).lower() == "pkg" and os.path.exists(input_path):
            value = _read_int(input_path)
            if value is not None:
                return value / 1000.0

        for input_path in sorted(glob.glob(os.path.join(hwmon_dir, "temp*_input"))):
            value = _read_int(input_path)
            if value is not None and value > 0:
                return value / 1000.0
        return 0.0

    temp_input = os.path.join(hwmon_dir, "temp1_input")
    if os.path.exists(temp_input):
        value = _read_int(temp_input)
        if value is not None:
            return value / 1000.0
    return 0.0


def _read_intel_temp_c(device_dir):
    for hwmon_dir in sorted(glob.glob(os.path.join(device_dir, "hwmon", "hwmon*"))):
        name = _read_text(os.path.join(hwmon_dir, "name"))
        if name not in _INTEL_HWMON_NAMES:
            continue
        temp_c = _temp_from_hwmon_dir(hwmon_dir, name)
        if temp_c > 0:
            return temp_c
    return 0.0


def read_gpu_temp_from_device(device_dir):
    """Read GPU temperature in Celsius from a DRM device directory."""
    vendor = _card_vendor(device_dir)
    if vendor == VENDOR_INTEL:
        return _read_intel_temp_c(device_dir)

    for hwmon_dir in sorted(glob.glob(os.path.join(device_dir, "hwmon", "hwmon*"))):
        name = _read_text(os.path.join(hwmon_dir, "name"))
        if name in ("amdgpu", "radeon", "nvidia"):
            temp_input = os.path.join(hwmon_dir, "temp1_input")
            if os.path.exists(temp_input):
                value = _read_int(temp_input)
                if value is not None:
                    return value / 1000.0
    return 0.0


def _read_sysfs_utilization(device_dir):
    utilization = 0

    busy_candidates = [
        os.path.join(device_dir, "gpu_busy_percent"),
        os.path.join(device_dir, "gt_busy_percent"),
        os.path.join(device_dir, "busy_percent"),
    ]
    for busy_path in busy_candidates:
        value = _read_int(busy_path)
        if value is not None:
            return max(0, min(100, value))

    busy_globs = [
        os.path.join(device_dir, "gt", "gt*", "engines", "*", "busy"),
        os.path.join(device_dir, "tile*", "gt*", "engines", "*", "busy"),
    ]
    for pattern in busy_globs:
        for engine_busy in glob.glob(pattern):
            value = _read_int(engine_busy)
            if value is not None:
                utilization = max(utilization, max(0, min(100, value)))

    return utilization


def _pci_slot_name(device_dir):
    uevent = _read_text(os.path.join(device_dir, "uevent"))
    for line in uevent.splitlines():
        if line.startswith("PCI_SLOT_NAME="):
            return line.split("=", 1)[1].strip()
    return ""


def _device_driver_name(device_dir):
    driver_link = os.path.join(device_dir, "driver")
    if os.path.islink(driver_link):
        return os.path.basename(os.path.realpath(driver_link))
    return ""


def _drm_fdinfo_snapshot():
    """Aggregate drm-cycles per engine class from all DRM client fdinfo files."""
    engines = defaultdict(int)
    max_total = 0

    for path in glob.glob("/proc/[0-9]*/fdinfo/*"):
        try:
            with open(path, encoding="utf-8", errors="ignore") as handle:
                content = handle.read()
        except OSError:
            continue

        if "drm-cycles-" not in content:
            continue

        for line in content.splitlines():
            if line.startswith("drm-cycles-"):
                engine = line.split(":", 1)[0].replace("drm-cycles-", "").strip()
                try:
                    engines[engine] += int(line.split(":", 1)[1].strip())
                except ValueError:
                    continue
            elif line.startswith("drm-total-cycles-"):
                try:
                    value = int(line.split(":", 1)[1].strip())
                except ValueError:
                    continue
                max_total = max(max_total, value)

    if not engines and max_total == 0:
        return None

    return dict(engines), max_total


def _utilization_from_drm_fdinfo():
    """
    Estimate GPU busy percent from drm-cycles in /proc/*/fdinfo.

    Works for Intel xe (Arc) where intel_gpu_top only supports i915.
    """
    global _FDINFO_SAMPLE_STATE

    snapshot = _drm_fdinfo_snapshot()
    if snapshot is None:
        return None

    engines, max_total = snapshot
    now = time.monotonic()
    previous = _FDINFO_SAMPLE_STATE

    _FDINFO_SAMPLE_STATE = {
        "engines": engines,
        "total": max_total,
        "time": now,
    }

    if not previous:
        return None

    delta_total = max_total - previous["total"]
    if delta_total <= 0:
        return None

    utilizations = []
    all_engines = set(engines) | set(previous["engines"])
    for engine in all_engines:
        delta_active = engines.get(engine, 0) - previous["engines"].get(engine, 0)
        if delta_active < 0:
            continue
        utilizations.append((delta_active / delta_total) * 100.0)

    if not utilizations:
        return 0.0

    return max(0.0, min(100.0, max(utilizations)))


def _perf_event_prefix(device_dir):
    slot = _pci_slot_name(device_dir)
    if not slot:
        return ""
    return "xe_" + slot.replace(":", "_").replace(".", "_")


def _collect_busy_percent_values(payload, busy_values):
    if isinstance(payload, dict):
        busy = payload.get("busy")
        if busy is not None:
            try:
                busy_values.append(float(busy))
            except (TypeError, ValueError):
                pass
        for value in payload.values():
            _collect_busy_percent_values(value, busy_values)
    elif isinstance(payload, list):
        for item in payload:
            _collect_busy_percent_values(item, busy_values)


def _parse_intel_gpu_top_json(text):
    text = text.strip()
    if not text:
        return None

    if text.startswith("[") and not text.endswith("]"):
        text = text + "]"

    payload = None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                payload = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
        else:
            return None

    if isinstance(payload, list):
        if not payload:
            return None
        payload = payload[-1]

    busy_values = []
    _collect_busy_percent_values(payload, busy_values)
    if not busy_values:
        return None

    return max(0.0, min(100.0, max(busy_values)))


def _intel_gpu_top_binary():
    return shutil.which("intel_gpu_top")


def _utilization_from_intel_gpu_top(device_dir, card_path):
    # intel_gpu_top only supports the i915 PMU interface, not the xe driver (Arc).
    if _device_driver_name(device_dir) != "i915":
        return None

    binary = _intel_gpu_top_binary()
    if not binary:
        return None

    card_name = os.path.basename(card_path)
    drm_node = f"drm:/dev/dri/{card_name}"
    command_variants = [
        [binary, "-J", "-n", "1", "-s", "500", "-d", drm_node],
        [binary, "-J", "-n", "1", "-s", "500"],
        [binary, "-J", "-n", "1"],
    ]

    for command in command_variants:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=2,
            )
            output = (result.stdout or "").strip()
            if not output and result.stderr:
                output = result.stderr.strip()
            if not output:
                continue

            util = _parse_intel_gpu_top_json(output)
            if util is not None:
                return util
        except (OSError, subprocess.TimeoutExpired, ValueError):
            continue

    return None


def _utilization_from_perf(device_dir):
    prefix = _perf_event_prefix(device_dir)
    if not prefix:
        return None

    active_event = f"{prefix}/engine-active-ticks/"
    total_event = f"{prefix}/engine-total-ticks/"

    try:
        result = subprocess.run(
            [
                "perf",
                "stat",
                "-e",
                f"{active_event},{total_event}",
                "-x,",
                "--",
                "sleep",
                "0.25",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        output = (result.stderr or "") + (result.stdout or "")
        active = None
        total = None
        for line in output.splitlines():
            if active_event in line or "engine-active-ticks" in line:
                match = re.match(r"^\s*([0-9,]+)", line)
                if match:
                    active = int(match.group(1).replace(",", ""))
            if total_event in line or "engine-total-ticks" in line:
                match = re.match(r"^\s*([0-9,]+)", line)
                if match:
                    total = int(match.group(1).replace(",", ""))

        if active is not None and total and total > 0:
            return max(0.0, min(100.0, (active / total) * 100.0))
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None

    return None


def _utilization_from_gtidle_delta(device_dir, card_path):
    residency_paths = glob.glob(
        os.path.join(device_dir, "tile*", "gt*", "gtidle", "idle_residency_ms")
    )
    if not residency_paths:
        return None

    total_residency = 0
    for path in residency_paths:
        value = _read_int(path)
        if value is not None:
            total_residency += value

    now = time.monotonic()
    previous = _GTIDLE_SAMPLE_STATE.get(card_path)
    _GTIDLE_SAMPLE_STATE[card_path] = {
        "residency_ms": total_residency,
        "time": now,
    }

    if not previous:
        return None

    delta_ms = total_residency - previous["residency_ms"]
    delta_s = now - previous["time"]
    if delta_s < 0.2 or delta_ms < 0:
        return None

    idle_fraction = delta_ms / (delta_s * 1000.0)
    return max(0.0, min(100.0, 100.0 - idle_fraction * 100.0))


def _utilization_for_intel(device_dir, card_path, sysfs_utilization):
    if sysfs_utilization > 0:
        return float(sysfs_utilization)

    for reader in (
        lambda: _utilization_from_drm_fdinfo(),
        lambda: _utilization_from_perf(device_dir),
        lambda: _utilization_from_intel_gpu_top(device_dir, card_path),
        lambda: _utilization_from_gtidle_delta(device_dir, card_path),
    ):
        util = reader()
        if util is not None:
            return util

    return float(sysfs_utilization)


def _stats_from_sysfs_card(card_path):
    device_dir = os.path.join(card_path, "device")
    if not os.path.isdir(device_dir):
        return None

    vendor = _card_vendor(device_dir)
    utilization = _read_sysfs_utilization(device_dir)
    vram_used_bytes = 0
    vram_total_bytes = 0

    vram_total_path = os.path.join(device_dir, "mem_info_vram_total")
    vram_used_path = os.path.join(device_dir, "mem_info_vram_used")
    if os.path.exists(vram_total_path) and os.path.exists(vram_used_path):
        total = _read_int(vram_total_path)
        used = _read_int(vram_used_path)
        if total and total > 0 and used is not None:
            vram_total_bytes = total
            vram_used_bytes = used

    freq_mhz = 0
    temp_c = 0.0
    if vendor == VENDOR_INTEL:
        freq_mhz = _read_intel_freq_mhz(device_dir)
        temp_c = _read_intel_temp_c(device_dir)
        utilization = int(
            round(_utilization_for_intel(device_dir, card_path, utilization))
        )

    has_signal = utilization > 0 or vram_total_bytes > 0
    if vendor == VENDOR_INTEL:
        has_signal = has_signal or _intel_has_sysfs_marker(device_dir)
    elif vendor in (VENDOR_AMD, VENDOR_NVIDIA):
        has_signal = has_signal or os.path.isdir(
            os.path.join(device_dir, "hwmon")
        )

    if not has_signal:
        return None

    priority = _VENDOR_PRIORITY.get(vendor, 50)
    if vram_total_bytes > 0:
        priority += 20

    return {
        "vendor": vendor,
        "utilization": float(utilization),
        "vram_used_gb": vram_used_bytes / (1024**3),
        "vram_total_gb": vram_total_bytes / (1024**3),
        "freq_mhz": freq_mhz,
        "temp_c": temp_c,
        "card_path": card_path,
        "priority": priority,
        "source": "sysfs",
    }


def _stats_from_nvidia_smi():
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None

        parts = [part.strip() for part in result.stdout.strip().split(",")]
        if len(parts) < 3:
            return None

        utilization = float(parts[0])
        used_mib = float(parts[1])
        total_mib = float(parts[2])
        temp_c = float(parts[3]) if len(parts) > 3 else 0.0

        return {
            "vendor": VENDOR_NVIDIA,
            "utilization": max(0.0, min(100.0, utilization)),
            "vram_used_gb": used_mib / 1024,
            "vram_total_gb": total_mib / 1024 if total_mib > 0 else 0,
            "freq_mhz": 0,
            "temp_c": temp_c,
            "card_path": None,
            "priority": _VENDOR_PRIORITY[VENDOR_NVIDIA] + 10,
            "source": "nvidia-smi",
        }
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def _format_gpu_text(stats):
    util = stats["utilization"]
    total_gb = stats["vram_total_gb"]
    used_gb = stats["vram_used_gb"]
    freq_mhz = stats.get("freq_mhz") or 0

    freq_part = f" | Freq: {freq_mhz:.0f} MHz" if freq_mhz > 0 else ""

    if total_gb > 0.01:
        return f"{util:.1f}% | VRAM: {used_gb:.2f}/{total_gb:.2f} GB{freq_part}"
    if stats["vendor"] == VENDOR_INTEL:
        return f"{util:.1f}%{freq_part} | Intel GPU"
    return f"{util:.1f}%{freq_part}"


def _empty_stats():
    return {
        "utilization": 0.0,
        "vram_used_gb": 0.0,
        "vram_total_gb": 0.0,
        "gpu_text": "N/A",
        "vendor": None,
        "freq_mhz": 0,
        "temp_c": 0.0,
        "card_path": None,
    }


def collect_live_gpu_stats():
    """
    Return live GPU metrics for the footer graph.

    Dict keys: utilization, vram_used_gb, vram_total_gb, gpu_text, vendor,
    freq_mhz, temp_c, card_path
    """
    candidates = []

    nvidia_stats = _stats_from_nvidia_smi()
    if nvidia_stats:
        candidates.append(nvidia_stats)

    for card_path in sorted(glob.glob("/sys/class/drm/card*")):
        if _is_render_only_card(card_path):
            continue
        card_stats = _stats_from_sysfs_card(card_path)
        if card_stats:
            candidates.append(card_stats)

    if not candidates:
        return _empty_stats()

    best = max(
        candidates,
        key=lambda item: (item["priority"], item["utilization"], item["vram_total_gb"]),
    )

    return {
        "utilization": best["utilization"],
        "vram_used_gb": best["vram_used_gb"],
        "vram_total_gb": best["vram_total_gb"],
        "gpu_text": _format_gpu_text(best),
        "vendor": best["vendor"],
        "freq_mhz": best.get("freq_mhz", 0),
        "temp_c": best.get("temp_c", 0.0),
        "card_path": best.get("card_path"),
    }
