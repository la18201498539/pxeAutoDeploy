import os
from typing import Callable

import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.config import DeployConfig
from core.network_utils import get_interfaces, get_disks

_TIMEZONES = [
    "Asia/Shanghai",
    "Asia/Chongqing",
    "Asia/Hong_Kong",
    "Asia/Tokyo",
    "UTC",
    "America/New_York",
    "Europe/London",
]


class ConfigPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, on_deploy: Callable):
        super().__init__(parent)
        self.on_deploy = on_deploy
        self._interfaces: dict = {}
        self._build_ui()
        self._load_system_info()

    # ─────────────────────────── build ───────────────────────────────

    def _build_ui(self):
        # ── Network ──────────────────────────────────────────────────
        self._section("网络配置")

        self.iface_var = ctk.StringVar()
        self._row("网络接口", lambda p: self._iface_combo(p))

        self.server_ip_var = ctk.StringVar(value="检测中 ...")
        self._row("部署服务器 IP", lambda p: ctk.CTkLabel(
            p, textvariable=self.server_ip_var, text_color="#4CAF50", anchor="w"
        ))

        # ── ISO ───────────────────────────────────────────────────────
        self._section("系统镜像")

        self.iso_var = ctk.StringVar()
        self.iso_var.trace_add("write", self._on_iso_change)
        self._row("ISO 路径", self._iso_row)

        self.iso_info = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=12), text_color="gray"
        )
        self.iso_info.pack(anchor="w", padx=(118, 0), pady=(0, 4))

        # ── Install params ────────────────────────────────────────────
        self._section("安装参数")

        self.hostname_var = ctk.StringVar(value="centos-node")
        self._labeled_entry("主机名", self.hostname_var)

        self.password_var = ctk.StringVar()
        self._labeled_entry("root 密码", self.password_var, show="*")

        self.confirm_var = ctk.StringVar()
        self._labeled_entry("确认密码", self.confirm_var, show="*")

        self.timezone_var = ctk.StringVar(value="Asia/Shanghai")
        self._row("时区", lambda p: ctk.CTkComboBox(
            p, variable=self.timezone_var, values=_TIMEZONES, width=220
        ))

        self.disk_var = ctk.StringVar()
        self._row("安装磁盘", self._disk_row)

        self.action_var = ctk.StringVar(value="reboot")
        self._row("完成后", lambda p: self._action_radios(p))

        # ── Deploy button ─────────────────────────────────────────────
        ctk.CTkFrame(self, height=1, fg_color="gray35").pack(fill="x", padx=10, pady=15)
        self.deploy_btn = ctk.CTkButton(
            self,
            text="一键部署",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=46,
            command=self._on_deploy_click,
        )
        self.deploy_btn.pack(padx=10, pady=(0, 15), fill="x")

    # ─────────────────────────── helpers ─────────────────────────────

    def _section(self, text: str):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=(12, 2))
        ctk.CTkLabel(f, text=text, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkFrame(f, height=1, fg_color="gray35").pack(fill="x", pady=(3, 0))

    def _row(self, label: str, widget_factory: Callable):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(f, text=f"{label}:", width=105, anchor="w").pack(side="left")
        w = widget_factory(f)
        if w:
            w.pack(side="left", padx=5)
        return f

    def _labeled_entry(self, label: str, var, show=None):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(f, text=f"{label}:", width=105, anchor="w").pack(side="left")
        kwargs = {"textvariable": var, "width": 280}
        if show:
            kwargs["show"] = show
        ctk.CTkEntry(f, **kwargs).pack(side="left", padx=5)

    def _iface_combo(self, parent):
        self.iface_combo = ctk.CTkComboBox(
            parent,
            variable=self.iface_var,
            width=180,
            command=self._on_iface_change,
        )
        return self.iface_combo

    def _iso_row(self, parent):
        ctk.CTkEntry(parent, textvariable=self.iso_var, width=300).pack(side="left", padx=5)
        ctk.CTkButton(parent, text="浏览", width=65, command=self._browse_iso).pack(side="left")
        return None  # already packed

    def _disk_row(self, parent):
        self.disk_combo = ctk.CTkComboBox(parent, variable=self.disk_var, width=180)
        self.disk_combo.pack(side="left", padx=5)
        ctk.CTkLabel(
            parent, text="⚠ 磁盘内容将被全部清除",
            text_color="#FF7043", font=ctk.CTkFont(size=11)
        ).pack(side="left", padx=8)
        return None

    def _action_radios(self, parent):
        ctk.CTkRadioButton(parent, text="自动重启", variable=self.action_var, value="reboot").pack(side="left", padx=(5, 15))
        ctk.CTkRadioButton(parent, text="关机", variable=self.action_var, value="poweroff").pack(side="left")
        return None

    # ─────────────────────────── events ──────────────────────────────

    def _load_system_info(self):
        self._interfaces = get_interfaces()
        iface_list = list(self._interfaces.keys())
        if iface_list:
            self.iface_combo.configure(values=iface_list)
            self.iface_var.set(iface_list[0])
            self._on_iface_change(iface_list[0])
        else:
            self.server_ip_var.set("未检测到网卡")

        disks = get_disks()
        self.disk_combo.configure(values=disks)
        if disks:
            self.disk_var.set(disks[0])

    def _on_iface_change(self, iface: str):
        ip = self._interfaces.get(iface, "")
        self.server_ip_var.set(ip if ip else "未知")

    def _browse_iso(self):
        path = filedialog.askopenfilename(
            title="选择 CentOS 8.1 ISO 文件",
            filetypes=[("ISO 镜像", "*.iso"), ("所有文件", "*.*")],
        )
        if path:
            self.iso_var.set(path)

    def _on_iso_change(self, *_):
        path = self.iso_var.get()
        if os.path.isfile(path):
            size = os.path.getsize(path) / (1024 ** 3)
            self.iso_info.configure(
                text=f"✓  {os.path.basename(path)}  ({size:.1f} GB)", text_color="#4CAF50"
            )
        elif path:
            self.iso_info.configure(text="✗  文件不存在", text_color="#FF5252")
        else:
            self.iso_info.configure(text="")

    def _on_deploy_click(self):
        if self.password_var.get() != self.confirm_var.get():
            messagebox.showerror("密码不一致", "两次输入的密码不匹配，请重新输入")
            return

        iface = self.iface_var.get()
        config = DeployConfig(
            interface=iface,
            server_ip=self._interfaces.get(iface, ""),
            iso_path=self.iso_var.get(),
            hostname=self.hostname_var.get().strip(),
            root_password=self.password_var.get(),
            timezone=self.timezone_var.get(),
            disk=self.disk_var.get(),
            post_install_action=self.action_var.get(),
        )
        self.on_deploy(config)
