import threading
from typing import Callable

import customtkinter as ctk

_STEPS = [
    "检查并安装依赖",
    "挂载 ISO",
    "准备 TFTP 引导文件",
    "生成 Kickstart 配置",
    "启动 HTTP 服务",
    "配置并启动 dnsmasq",
    "等待目标机 PXE 启动",
]

_COLORS = {
    "pending": ("gray50", "gray60"),
    "running": ("#FFA726", "#FFA726"),
    "done":    ("#4CAF50", "#4CAF50"),
    "error":   ("#F44336", "#EF9A9A"),
}

_ICONS = {
    "pending": "○",
    "running": "⟳",
    "done":    "✓",
    "error":   "✗",
}


class ConsolePanel(ctk.CTkFrame):
    def __init__(self, parent, on_stop: Callable):
        super().__init__(parent, fg_color="transparent")
        self.on_stop = on_stop
        self._step_widgets: dict = {}
        self._build_ui()

    # ─────────────────────────── build ───────────────────────────────

    def _build_ui(self):
        # Progress steps
        steps_box = ctk.CTkFrame(self)
        steps_box.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            steps_box, text="部署进度",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 4))

        for step in _STEPS:
            row = ctk.CTkFrame(steps_box, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)

            icon = ctk.CTkLabel(row, text="○", width=22, text_color="gray50",
                                font=ctk.CTkFont(size=14))
            icon.pack(side="left")

            label = ctk.CTkLabel(row, text=step, anchor="w", text_color="gray60")
            label.pack(side="left", padx=6)

            self._step_widgets[step] = (icon, label)

        ctk.CTkFrame(steps_box, height=1, fg_color="gray35").pack(fill="x", padx=12, pady=(8, 0))

        # Log header + stop button
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            hdr, text="实时日志",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(side="left")

        self.stop_btn = ctk.CTkButton(
            hdr, text="停止服务", width=100,
            fg_color="#C62828", hover_color="#B71C1C",
            command=self._on_stop_click, state="disabled",
        )
        self.stop_btn.pack(side="right")

        # Log textbox
        self.log_box = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Courier New", size=12),
            state="disabled",
            wrap="word",
            activate_scrollbars=True,
        )
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ─────────────────────────── public API ──────────────────────────

    def set_step_status(self, step: str, status: str):
        """Thread-safe: update step icon and color."""
        def _update():
            if step not in self._step_widgets:
                return
            icon_w, label_w = self._step_widgets[step]
            icon_color, label_color = _COLORS.get(status, ("gray50", "gray60"))
            icon_w.configure(text=_ICONS.get(status, "○"), text_color=icon_color)
            label_w.configure(text_color=label_color)
        self.after(0, _update)

    def log(self, message: str):
        """Thread-safe: append a line to the log textbox."""
        def _update():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", message + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _update)

    def clear(self):
        for step in _STEPS:
            self.set_step_status(step, "pending")

        def _clear_log():
            self.log_box.configure(state="normal")
            self.log_box.delete("1.0", "end")
            self.log_box.configure(state="disabled")
        self.after(0, _clear_log)

    def set_deploy_active(self, active: bool):
        state = "normal" if active else "disabled"
        self.after(0, lambda: self.stop_btn.configure(state=state))

    # ─────────────────────────── events ──────────────────────────────

    def _on_stop_click(self):
        self.stop_btn.configure(state="disabled")
        self.on_stop()
