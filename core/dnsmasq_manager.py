import os
import subprocess
from typing import Callable

from core.config import DeployConfig

_CONF_FILE = "/etc/dnsmasq.d/pxe-deploy.conf"

_CONF_TEMPLATE = """\
# ============================================================
# PXE Auto Deploy - dnsmasq configuration
# Generated automatically - do not edit manually
# ============================================================

# Disable DNS to avoid conflict with systemd-resolved
port=0

# Only listen on the deployment interface
interface={interface}
bind-interfaces

# Proxy DHCP: adds PXE boot info without replacing existing DHCP server
# Compatible with bridged network where a router already does DHCP
dhcp-range={server_ip},proxy

# PXE boot service (BIOS only; UEFI can be added later)
pxe-service=x86PC,"Install CentOS 8.1",pxelinux

# TFTP server
enable-tftp
tftp-root={tftp_dir}

# Log DHCP/TFTP events to syslog for monitoring
log-dhcp
"""


def write_config(config: DeployConfig, log: Callable):
    content = _CONF_TEMPLATE.format(
        interface=config.interface,
        server_ip=config.server_ip,
        tftp_dir=config.tftp_dir,
    )
    log(f"写入 dnsmasq 配置: {_CONF_FILE}")
    with open(_CONF_FILE, "w") as f:
        f.write(content)


def restart_service(log: Callable):
    log("重启 dnsmasq 服务 ...")
    subprocess.run(["systemctl", "restart", "dnsmasq"], check=True)
    log("dnsmasq 已就绪 (Proxy DHCP + TFTP)")


def cleanup(log: Callable):
    if os.path.exists(_CONF_FILE):
        os.remove(_CONF_FILE)
        log("已移除 PXE dnsmasq 配置")
        try:
            subprocess.run(["systemctl", "reload", "dnsmasq"], check=True)
            log("dnsmasq 已恢复默认配置")
        except Exception as e:
            log(f"重载 dnsmasq 失败: {e}")
