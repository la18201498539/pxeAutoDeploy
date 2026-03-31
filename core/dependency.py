import subprocess
from typing import Callable

REQUIRED_PACKAGES = [
    "dnsmasq",
    "syslinux-common",
    "pxelinux",
]


def _is_installed(pkg: str) -> bool:
    result = subprocess.run(
        ["dpkg", "-l", pkg],
        capture_output=True, text=True
    )
    return result.returncode == 0 and "ii" in result.stdout


def install_dependencies(log: Callable):
    missing = []
    for pkg in REQUIRED_PACKAGES:
        if _is_installed(pkg):
            log(f"  ✓ {pkg}")
        else:
            log(f"  ✗ {pkg} (缺失)")
            missing.append(pkg)

    if not missing:
        log("所有依赖已满足")
        return

    log(f"正在安装: {', '.join(missing)} ...")
    subprocess.run(["apt-get", "update", "-qq"], check=True, capture_output=True)
    subprocess.run(
        ["apt-get", "install", "-y"] + missing,
        check=True, capture_output=True
    )
    log("依赖安装完成 ✓")
