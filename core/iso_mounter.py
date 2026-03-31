import os
import subprocess
from typing import Callable


def mount_iso(iso_path: str, mount_point: str, log: Callable):
    os.makedirs(mount_point, exist_ok=True)

    # Already mounted?
    result = subprocess.run(["mountpoint", "-q", mount_point], capture_output=True)
    if result.returncode == 0:
        log(f"ISO 已挂载于 {mount_point}，跳过")
        return

    log(f"挂载 ISO: {iso_path}")
    subprocess.run(
        ["mount", "-o", "loop,ro", iso_path, mount_point],
        check=True
    )
    log(f"ISO 挂载成功 → {mount_point}")


def unmount_iso(mount_point: str, log: Callable):
    result = subprocess.run(["mountpoint", "-q", mount_point], capture_output=True)
    if result.returncode != 0:
        return
    log(f"卸载 ISO: {mount_point}")
    subprocess.run(["umount", "-l", mount_point], capture_output=True)
    log("ISO 已卸载")
