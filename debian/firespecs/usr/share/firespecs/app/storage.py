import json
import os
import pathlib
import subprocess

import psutil


def get_disk_partitions():
    partitions = []
    for part in psutil.disk_partitions(all=False):
        if os.path.exists(part.mountpoint):
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": f"{usage.total / (1024**3):.2f} GB",
                    "used": f"{usage.used / (1024**3):.2f} GB",
                    "free": f"{usage.free / (1024**3):.2f} GB",
                    "percent": f"{usage.percent:.1f}%",
                }
            )
    return partitions


def get_disk_info():
    disks = []
    for disk in psutil.disk_partitions(all=True):
        try:
            disk_usage = psutil.disk_usage(disk.mountpoint)
            disks.append(
                {
                    "device": disk.device,
                    "mountpoint": disk.mountpoint,
                    "fstype": disk.fstype,
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "percent": disk_usage.percent,
                }
            )
        except (OSError, PermissionError):
            continue
    return disks


def get_largest_files(path, limit=10, min_size_mb=1):
    largest_files = []

    try:
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.exists(path) or not os.path.isdir(path):
            return []
    except OSError:
        return []

    try:
        # Only exclude virtual/system trees when the scan root is outside them.
        # Using -not -path '/tmp/*' while scanning under /tmp would skip every file.
        norm_path = os.path.normpath(path)
        find_cmd = ["find", path, "-type", "f"]
        for prefix in ("/proc", "/sys", "/dev", "/run", "/tmp"):
            if not norm_path.startswith(prefix + os.sep) and norm_path != prefix:
                find_cmd.extend(["-not", "-path", prefix + "/*"])
        find_cmd.extend(["-exec", "du", "-b", "{}", "+"])

        result = subprocess.run(
            find_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=60,
        )

        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split("\n")

            for line in lines:
                try:
                    line = line.strip()
                    if not line:
                        continue
                    first_space_idx = line.find("\t")
                    if first_space_idx == -1:
                        first_space_idx = line.find(" ")
                    if first_space_idx == -1:
                        continue

                    size_bytes = int(line[:first_space_idx])
                    file_path = line[first_space_idx:].strip()
                    size_mb = size_bytes / (1024 * 1024)

                    if size_mb >= min_size_mb:
                        largest_files.append(
                            {
                                "path": file_path,
                                "size_mb": round(size_mb, 2),
                            }
                        )
                except (ValueError, IndexError):
                    continue

            largest_files.sort(key=lambda item: item["size_mb"], reverse=True)
            return largest_files[:limit]

    except subprocess.TimeoutExpired:
        pass
    except OSError:
        pass

    return []


def get_lsblk_info():
    try:
        result = subprocess.run(
            [
                "lsblk",
                "-J",
                "-o",
                "NAME,MAJ:MIN,RM,SIZE,RO,TYPE,MOUNTPOINTS,FSTYPE,LABEL,UUID,MODEL,SERIAL",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get("blockdevices", [])
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return []


def get_all_storage_info():
    return {
        "partitions": get_disk_partitions(),
        "disks": get_disk_info(),
        "lsblk": get_lsblk_info(),
    }
