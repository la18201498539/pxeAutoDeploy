import os
from dataclasses import dataclass, field


@dataclass
class DeployConfig:
    # Network
    interface: str = ""
    server_ip: str = ""

    # ISO
    iso_path: str = ""

    # Installation parameters
    hostname: str = "centos-node"
    root_password: str = ""
    timezone: str = "Asia/Shanghai"
    disk: str = "/dev/sda"
    post_install_action: str = "reboot"  # "reboot" or "poweroff"

    # Service config
    work_dir: str = "/tmp/pxedeploy"
    http_port: int = 8080

    @property
    def iso_mount_dir(self):
        return os.path.join(self.work_dir, "iso")

    @property
    def tftp_dir(self):
        return os.path.join(self.work_dir, "tftp")

    @property
    def http_root(self):
        return os.path.join(self.work_dir, "http")

    @property
    def ks_file_path(self):
        return os.path.join(self.http_root, "ks.cfg")

    def ks_url(self):
        return f"http://{self.server_ip}:{self.http_port}/ks.cfg"

    def repo_url(self):
        return f"http://{self.server_ip}:{self.http_port}/centos8/"

    def disk_short(self):
        """Return disk name without /dev/ prefix, e.g. sda"""
        return self.disk.replace("/dev/", "")

    def validate(self):
        errors = []
        if not self.interface:
            errors.append("请选择网络接口")
        if not self.server_ip:
            errors.append("无法获取服务器 IP")
        if not self.iso_path or not os.path.exists(self.iso_path):
            errors.append("ISO 文件路径无效")
        if not self.hostname:
            errors.append("请填写主机名")
        if not self.root_password or len(self.root_password) < 6:
            errors.append("root 密码至少 6 位")
        if not self.disk:
            errors.append("请选择安装磁盘")
        return errors
