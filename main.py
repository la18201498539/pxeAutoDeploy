#!/usr/bin/env python3
"""
PXE 自动装机工具
================
需要 root 权限（操作 dnsmasq、mount、TFTP 目录）

用法:
    sudo python3 main.py
"""

import os
import sys


def _check_root():
    if os.geteuid() != 0:
        print("[错误] 此程序需要 root 权限运行")
        print(f"  请执行: sudo python3 {sys.argv[0]}")
        sys.exit(1)


def _check_display():
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("[错误] 未检测到图形显示环境 (DISPLAY/WAYLAND_DISPLAY)")
        print("  请在桌面环境中运行，或通过 SSH X11 转发:")
        print("  ssh -X root@<server_ip>  然后执行 sudo -E python3 main.py")
        sys.exit(1)


if __name__ == "__main__":
    _check_root()
    _check_display()

    from ui.app import App
    app = App()
    app.mainloop()
