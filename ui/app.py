from tkinter import messagebox

import customtkinter as ctk

from core.config import DeployConfig
from core.orchestrator import DeployOrchestrator
from ui.config_panel import ConfigPanel
from ui.console_panel import ConsolePanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PXE 自动装机工具 v1.0")
        self.geometry("940x700")
        self.minsize(800, 600)

        self._orchestrator: DeployOrchestrator = None
        self._build_ui()

    # ─────────────────────────── build ───────────────────────────────

    def _build_ui(self):
        # Header
        ctk.CTkLabel(
            self,
            text="PXE 自动装机工具",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(16, 2))
        ctk.CTkLabel(
            self,
            text="无人值守自动安装 CentOS 8.1  |  Proxy DHCP 模式（桥接网络兼容）",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(pady=(0, 8))

        # Tabs
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        tab_cfg = self.tabs.add("⚙ 配置")
        tab_con = self.tabs.add("🖥 部署控制台")

        self.config_panel = ConfigPanel(tab_cfg, on_deploy=self._on_deploy)
        self.config_panel.pack(fill="both", expand=True)

        self.console_panel = ConsolePanel(tab_con, on_stop=self._on_stop)
        self.console_panel.pack(fill="both", expand=True)

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─────────────────────────── events ──────────────────────────────

    def _on_deploy(self, config: DeployConfig):
        errors = config.validate()
        if errors:
            messagebox.showerror("配置错误", "\n".join(f"• {e}" for e in errors))
            return

        # Switch to console tab
        self.tabs.set("🖥 部署控制台")
        self.console_panel.clear()
        self.console_panel.set_deploy_active(True)

        self._orchestrator = DeployOrchestrator(
            config=config,
            log_callback=self.console_panel.log,
            status_callback=self.console_panel.set_step_status,
            done_callback=self._on_install_done,
        )
        self._orchestrator.start()

    def _on_stop(self):
        if self._orchestrator:
            self._orchestrator.stop()
            self._orchestrator = None
        self.console_panel.set_deploy_active(False)

    def _on_install_done(self):
        self.console_panel.set_deploy_active(False)
        self.after(0, lambda: messagebox.showinfo(
            "安装完成",
            "目标机已成功完成 CentOS 8.1 安装！\n\n"
            "PXE 菜单已切换为本地硬盘启动，所有临时服务已清理。"
        ))

    def _on_close(self):
        if self._orchestrator:
            if messagebox.askyesno("退出确认", "部署服务仍在运行，确认退出并停止所有服务？"):
                self._orchestrator.stop()
            else:
                return
        self.destroy()
