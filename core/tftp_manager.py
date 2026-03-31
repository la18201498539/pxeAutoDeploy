import os
import shutil
from typing import Callable

from core.config import DeployConfig

# Ubuntu 24 package paths
_PXELINUX_SRC = "/usr/lib/PXELINUX/pxelinux.0"
_SYSLINUX_BIOS = "/usr/lib/syslinux/modules/bios"
_REQUIRED_MODULES = [
    "ldlinux.c32",
    "libcom32.c32",
    "libutil.c32",
    "menu.c32",
]

_PXE_MENU_TEMPLATE = """\
DEFAULT menu.c32
PROMPT 0
TIMEOUT 50
ONTIMEOUT auto

MENU TITLE  PXE Auto Deploy - CentOS 8.1

LABEL auto
  MENU LABEL ^Auto Install CentOS 8.1
  KERNEL vmlinuz
  APPEND initrd=initrd.img inst.ks={ks_url} inst.repo={repo_url} quiet

LABEL local
  MENU LABEL ^Boot from Local Disk
  LOCALBOOT 0
"""

_PXE_MENU_LOCALBOOT = """\
DEFAULT local
PROMPT 0
TIMEOUT 10
ONTIMEOUT local

LABEL local
  MENU LABEL Boot from Local Disk
  LOCALBOOT 0
"""


def prepare_tftp(config: DeployConfig, log: Callable):
    tftp = config.tftp_dir
    cfg_dir = os.path.join(tftp, "pxelinux.cfg")
    os.makedirs(cfg_dir, exist_ok=True)

    # pxelinux.0
    log("复制 pxelinux.0 ...")
    if not os.path.exists(_PXELINUX_SRC):
        raise FileNotFoundError(f"找不到 pxelinux.0: {_PXELINUX_SRC}")
    shutil.copy2(_PXELINUX_SRC, os.path.join(tftp, "pxelinux.0"))

    # syslinux modules
    log("复制 syslinux 模块 ...")
    for mod in _REQUIRED_MODULES:
        src = os.path.join(_SYSLINUX_BIOS, mod)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(tftp, mod))
        else:
            log(f"  警告: 找不到 {mod}，跳过")

    # Kernel + initrd from ISO
    log("复制内核文件 ...")
    vmlinuz = os.path.join(config.iso_mount_dir, "isolinux", "vmlinuz")
    initrd = os.path.join(config.iso_mount_dir, "isolinux", "initrd.img")
    if not os.path.exists(vmlinuz):
        raise FileNotFoundError(f"ISO 中找不到 vmlinuz: {vmlinuz}")
    if not os.path.exists(initrd):
        raise FileNotFoundError(f"ISO 中找不到 initrd.img: {initrd}")
    shutil.copy2(vmlinuz, os.path.join(tftp, "vmlinuz"))
    shutil.copy2(initrd, os.path.join(tftp, "initrd.img"))
    log("内核文件复制完成 ✓")

    # PXE boot menu
    _write_install_menu(config, log)


def _write_install_menu(config: DeployConfig, log: Callable):
    menu = _PXE_MENU_TEMPLATE.format(
        ks_url=config.ks_url(),
        repo_url=config.repo_url(),
    )
    path = os.path.join(config.tftp_dir, "pxelinux.cfg", "default")
    with open(path, "w") as f:
        f.write(menu)
    log(f"PXE 引导菜单已写入: {path}")


def switch_to_localboot(config: DeployConfig, log: Callable = None):
    """Called after successful install to prevent reinstall loop."""
    path = os.path.join(config.tftp_dir, "pxelinux.cfg", "default")
    with open(path, "w") as f:
        f.write(_PXE_MENU_LOCALBOOT)
    if log:
        log("PXE 菜单已切换为本地硬盘启动（防止重装循环）")
