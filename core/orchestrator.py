import os
import re
import time
import threading
from typing import Callable, Optional

from core.config import DeployConfig
from core import dependency, iso_mounter, kickstart_generator, tftp_manager, dnsmasq_manager, http_server


class DeployOrchestrator:
    STEPS = [
        "检查并安装依赖",
        "挂载 ISO",
        "准备 TFTP 引导文件",
        "生成 Kickstart 配置",
        "启动 HTTP 服务",
        "配置并启动 dnsmasq",
        "等待目标机 PXE 启动",
    ]

    def __init__(
        self,
        config: DeployConfig,
        log_callback: Callable,
        status_callback: Callable,
        done_callback: Callable = None,
    ):
        self.config = config
        self.log = log_callback
        self.set_status = status_callback
        self.done_callback = done_callback
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.log("正在停止部署服务 ...")
        self._cleanup()
        self.log("服务已完全停止")

    # ─────────────────────────── internal ────────────────────────────

    def _run(self):
        steps = [
            ("检查并安装依赖",    self._step_dependencies),
            ("挂载 ISO",          self._step_mount_iso),
            ("准备 TFTP 引导文件", self._step_tftp),
            ("生成 Kickstart 配置", self._step_kickstart),
            ("启动 HTTP 服务",    self._step_http),
            ("配置并启动 dnsmasq", self._step_dnsmasq),
            ("等待目标机 PXE 启动", self._step_monitor),
        ]

        for name, func in steps:
            if not self._running:
                break
            self.set_status(name, "running")
            try:
                func()
                self.set_status(name, "done")
            except Exception as e:
                self.set_status(name, "error")
                self.log(f"\n[错误] {name}: {e}")
                self._cleanup()
                return

    def _step_dependencies(self):
        dependency.install_dependencies(self.log)

    def _step_mount_iso(self):
        os.makedirs(self.config.work_dir, exist_ok=True)
        iso_mounter.mount_iso(self.config.iso_path, self.config.iso_mount_dir, self.log)

    def _step_tftp(self):
        tftp_manager.prepare_tftp(self.config, self.log)

    def _step_kickstart(self):
        kickstart_generator.generate_kickstart(self.config, self.log)

    def _step_http(self):
        http_server.start(self.config, self.log, on_install_done=self._on_install_done)

    def _step_dnsmasq(self):
        dnsmasq_manager.write_config(self.config, self.log)
        dnsmasq_manager.restart_service(self.log)

    def _step_monitor(self):
        self.log("")
        self.log("=" * 54)
        self.log("所有服务就绪，等待目标机通过 PXE 引导 ...")
        self.log("请确保目标机 BIOS/UEFI 已设置【网络启动优先】")
        self.log("=" * 54)

        log_file = "/var/log/syslog"
        last_pos = os.path.getsize(log_file) if os.path.exists(log_file) else 0

        while self._running:
            try:
                if os.path.exists(log_file):
                    with open(log_file, "r", errors="ignore") as f:
                        f.seek(last_pos)
                        chunk = f.read()
                        last_pos = f.tell()
                    for line in chunk.splitlines():
                        low = line.lower()
                        if "dnsmasq" in low and any(k in low for k in ("tftp", "pxe", "dhcp")):
                            # Extract the useful part after the timestamp
                            msg = re.sub(r'^.*?dnsmasq[^:]*:\s*', '', line)
                            self.log(f"[监控] {msg}")
            except Exception:
                pass
            time.sleep(2)

    def _on_install_done(self):
        self.log("")
        self.log("=" * 54)
        self.log("目标机已完成安装，正在执行清理 ...")
        self.log("=" * 54)

        # Switch PXE menu to localboot so the machine doesn't reinstall on next boot
        try:
            tftp_manager.switch_to_localboot(self.config, self.log)
        except Exception as e:
            self.log(f"切换 PXE 菜单失败: {e}")

        self._running = False
        self._cleanup()
        self.log("清理完成 ✓ 目标机将从本地硬盘启动")

        if self.done_callback:
            self.done_callback()

    def _cleanup(self):
        for fn, label in [
            (lambda: http_server.stop(self.log), "HTTP 服务"),
            (lambda: dnsmasq_manager.cleanup(self.log), "dnsmasq 配置"),
            (lambda: iso_mounter.unmount_iso(self.config.iso_mount_dir, self.log), "ISO 挂载"),
        ]:
            try:
                fn()
            except Exception as e:
                self.log(f"清理 {label} 失败: {e}")
