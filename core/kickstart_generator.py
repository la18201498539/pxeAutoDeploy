import os
from typing import Callable

from core.config import DeployConfig

_TEMPLATE = """\
#version=RHEL8
# ============================================================
# PXE Auto Deploy - CentOS 8.1 Kickstart
# ============================================================

# Installation source
url --url="{repo_url}"

# Text mode (no GUI during install)
text

# Disable firstboot wizard
firstboot --disabled

# Keyboard & Language
keyboard --vckeymap=cn --xlayouts='cn'
lang zh_CN.UTF-8

# Network - use DHCP, set hostname
network --bootproto=dhcp --device=link --activate
network --hostname={hostname}

# Root password (plaintext, will be hashed by installer)
rootpw --plaintext {root_password}

# Security
selinux --disabled
firewall --disabled

# Services
services --enabled="chronyd"

# Timezone
timezone {timezone} --isUtc

# Disk configuration
ignoredisk --only-use={disk}
clearpart --all --initlabel --drives={disk}
autopart --type=lvm
bootloader --location=mbr --boot-drive={disk}

%packages
@^minimal-environment
chrony
wget
vim
net-tools
%end

%post --log=/root/ks-post.log
echo "=== PXE Auto Deploy ===" > /root/deploy_info.txt
echo "Deployed at: $(date)" >> /root/deploy_info.txt
echo "Hostname: {hostname}" >> /root/deploy_info.txt

# Notify PXE server that installation is complete so it can clean up
curl -s --max-time 5 "http://{server_ip}:{http_port}/api/done" || true
%end

{post_install_action}
"""


def generate_kickstart(config: DeployConfig, log: Callable = None) -> str:
    os.makedirs(os.path.dirname(config.ks_file_path), exist_ok=True)

    content = _TEMPLATE.format(
        repo_url=config.repo_url(),
        hostname=config.hostname,
        root_password=config.root_password,
        timezone=config.timezone,
        disk=config.disk_short(),
        server_ip=config.server_ip,
        http_port=config.http_port,
        post_install_action=config.post_install_action,
    )

    with open(config.ks_file_path, "w") as f:
        f.write(content)

    if log:
        log(f"Kickstart 文件已生成: {config.ks_file_path}")

    return content
