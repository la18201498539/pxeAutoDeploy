#!/usr/bin/env python3
"""
PXE 自动装机工具 v1.0 - CLI 模式
用法: sudo python3 main.py
"""

import os
import sys
import getpass
import threading

# ── ANSI 颜色 ────────────────────────────────────────────────────────
R    = "\033[31m"
G    = "\033[32m"
Y    = "\033[33m"
C    = "\033[36m"
BOLD = "\033[1m"
RST  = "\033[0m"

from core.config import DeployConfig
from core.network_utils import get_interfaces, get_disks
from core.orchestrator import DeployOrchestrator

_orchestrator: DeployOrchestrator = None


# ── 前置检查 ──────────────────────────────────────────────────────────

def check_root():
    if os.geteuid() != 0:
        print(f"{R}[错误]{RST} 需要 root 权限运行")
        print(f"  sudo python3 {sys.argv[0]}")
        sys.exit(1)


# ── 输入工具 ──────────────────────────────────────────────────────────

def ask(prompt: str, default: str = None, secret: bool = False) -> str:
    hint = f" [{default}]" if default else ""
    full = f"  {prompt}{hint}: "
    val = getpass.getpass(full) if secret else input(full).strip()
    return val if val else (default or "")


def choose(prompt: str, options: list, default: int = 1) -> str:
    for i, o in enumerate(options, 1):
        print(f"    {i}) {o}")
    while True:
        raw = input(f"  {prompt} [{default}]: ").strip()
        idx = int(raw) if raw.isdigit() else default
        if 1 <= idx <= len(options):
            return options[idx - 1]
        print(f"  {Y}请输入 1-{len(options)} 之间的数字{RST}")


def section(title: str):
    print(f"\n{BOLD}{C}── {title} {'─' * (40 - len(title))}{RST}")


# ── 配置收集 ──────────────────────────────────────────────────────────

def collect_config() -> DeployConfig:

    # 网络
    section("网络配置")
    interfaces = get_interfaces()
    if not interfaces:
        print(f"{R}未检测到可用网卡，退出{RST}")
        sys.exit(1)

    iface_items = [f"{k}   IP: {v}" for k, v in interfaces.items()]
    print("  检测到以下网卡:")
    raw_iface = choose("请选择网卡编号", iface_items)
    iface_name = raw_iface.split()[0]
    server_ip = interfaces[iface_name]
    print(f"  部署服务器 IP: {G}{server_ip}{RST}")

    # ISO
    section("系统镜像")
    default_iso = "/opt/CentOS-8.1.1911-x86_64-dvd1.iso"
    while True:
        iso_path = ask("ISO 文件路径", default_iso)
        if os.path.isfile(iso_path):
            size = os.path.getsize(iso_path) / 1024 ** 3
            print(f"  {G}✓ {os.path.basename(iso_path)}  ({size:.1f} GB){RST}")
            break
        print(f"  {R}✗ 文件不存在，请重新输入{RST}")

    # 安装参数
    section("安装参数")

    hostname = ask("目标机主机名", "centos-node")

    while True:
        pwd = ask("root 密码 (输入不回显)", secret=True)
        pwd2 = ask("确认 root 密码", secret=True)
        if len(pwd) < 6:
            print(f"  {R}密码至少 6 位{RST}")
        elif pwd != pwd2:
            print(f"  {R}两次输入不一致{RST}")
        else:
            break

    timezone = ask("时区", "Asia/Shanghai")

    disks = get_disks()
    print(f"  {Y}注意: 以下是本机(部署服务器)的磁盘，目标机磁盘名可能不同{RST}")
    print("  常见目标机磁盘名: /dev/sda (SATA/SAS)  /dev/nvme0n1 (NVMe)  /dev/vda (KVM)")
    print("  参考列表(本机):")
    for i, d in enumerate(disks, 1):
        print(f"    {i}) {d}")
    disk_raw = ask("目标机安装磁盘 (直接输入完整路径)", "/dev/sda")
    disk = disk_raw.strip()
    if not disk.startswith("/dev/"):
        disk = "/dev/" + disk
    print(f"  {Y}⚠  警告: {disk} 上的所有数据将被清除！{RST}")

    action_raw = ask("安装完成后操作 (reboot/poweroff)", "reboot")
    post_action = "poweroff" if "power" in action_raw.lower() else "reboot"

    return DeployConfig(
        interface=iface_name,
        server_ip=server_ip,
        iso_path=iso_path,
        hostname=hostname,
        root_password=pwd,
        timezone=timezone,
        disk=disk,
        post_install_action=post_action,
    )


# ── 确认 ──────────────────────────────────────────────────────────────

def confirm(cfg: DeployConfig):
    sep = "─" * 50
    print(f"""
{BOLD}{sep}
  配置确认
{sep}{RST}
  网卡      {cfg.interface}  ({cfg.server_ip})
  ISO       {cfg.iso_path}
  主机名    {cfg.hostname}
  磁盘      {cfg.disk}  {Y}(将被清空){RST}
  时区      {cfg.timezone}
  完成后    {cfg.post_install_action}
{BOLD}{sep}{RST}
""")
    ans = input("  确认开始部署? [y/N]: ").strip().lower()
    if ans != "y":
        print("  已取消")
        sys.exit(0)


# ── 状态回调 ─────────────────────────────────────────────────────────

def status_cb(step: str, status: str):
    icons = {
        "running": f"{Y}●{RST}",
        "done":    f"{G}✓{RST}",
        "error":   f"{R}✗{RST}",
    }
    icon = icons.get(status, " ")
    if status == "running":
        print(f"\n[{icon}] {BOLD}{step}{RST} ...")
    else:
        print(f"[{icon}] {step}")


def log_cb(msg: str):
    print(f"    {msg}")


# ── 部署 ──────────────────────────────────────────────────────────────

def deploy(cfg: DeployConfig):
    global _orchestrator

    done_event = threading.Event()

    def on_done():
        done_event.set()

    _orchestrator = DeployOrchestrator(
        config=cfg,
        log_callback=log_cb,
        status_callback=status_cb,
        done_callback=on_done,
    )

    print(f"\n{Y}部署开始 —— 按 Ctrl+C 随时停止服务{RST}")
    _orchestrator.start()

    try:
        _orchestrator._thread.join()
    except KeyboardInterrupt:
        print(f"\n{Y}[中断] 正在停止所有服务 ...{RST}")
        _orchestrator.stop()
        sys.exit(0)

    if done_event.is_set():
        sep = "─" * 50
        print(f"\n{G}{BOLD}{sep}")
        print(f"  ✓  CentOS 8.1 安装完成！")
        print(f"  所有临时服务已自动清理")
        print(f"{sep}{RST}\n")
    else:
        print(f"\n{R}部署过程中发生错误，请检查上方日志{RST}\n")


# ── 入口 ──────────────────────────────────────────────────────────────

def banner():
    print(f"""
{BOLD}{C}{'═' * 50}
   PXE 自动装机工具 v1.0
   无人值守安装 CentOS 8.1
{'═' * 50}{RST}""")


if __name__ == "__main__":
    check_root()
    banner()
    cfg = collect_config()
    confirm(cfg)
    deploy(cfg)
