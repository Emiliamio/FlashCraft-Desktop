# -*- coding: utf-8 -*-
"""
gui/app_window.py - FlashCraft 现代暗黑美学主界面 (巅峰大厂级商业工作台)
作者: Emiliamio <mio2110767128@163.com>

巅峰特性：
1. 注入单机硬件指纹 (FC-XXXX-XXXX) 与授权防刷熔断器；
2. 全局工业级快捷键：F5 启动、Esc 强停、F1 帮助手册、Ctrl+L 清屏；
3. 智能屏幕正中居中、原生文件拖拽、日志一键复制、原生音效；
4. 业务场景一键热切换与多线程防卡死。
"""

import os
import sys
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from config import (
    APP_NAME, APP_VERSION, APP_SUBTITLE,
    IS_TRIAL, TRIAL_ROW_LIMIT,
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
    COLOR_BG_DARK, COLOR_CARD_DARK, COLOR_CARD_BORDER,
    COLOR_ACCENT_BLUE, COLOR_ACCENT_GREEN, COLOR_ACCENT_RED, COLOR_ACCENT_AMBER,
    COLOR_CONSOLE_BG, COLOR_CONSOLE_TEXT,
    ICON_PATH, LOGO_PATH,
    get_default_output_dir
)
from gui.ui_queue import global_ui_queue, MessageType
from core.license_guard import (
    get_machine_fingerprint,
    get_trial_status,
    record_trial_usage,
    is_officially_activated
)
from tasks.demo_excel_merger import ExcelMergerWorker
from tasks.demo_invoice_extractor import InvoiceExtractorWorker
from tasks.demo_web_autofill import WebAutofillWorker

TASK_MODES = [
    "📑 财务神器：电子发票PDF批量提取与查重汇总",
    "📊 电商神器：多店铺Excel账单核对与利润分析",
    "🌐 政企神器：Excel数据自动批量填表与上报"
]

class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 1. 窗口规格与智能屏幕居中
        self.title(f"{APP_NAME} {APP_VERSION}")
        self._center_window()
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=COLOR_BG_DARK)
        
        # 图标适配
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass

        # 状态管理
        self.current_worker = None
        self.output_dir = get_default_output_dir()
        self._is_trial_active = IS_TRIAL and not is_officially_activated()
        self.machine_code = get_machine_fingerprint()

        # 2. 构建界面组件
        self._setup_layout()

        # 3. 挂载 Windows 原生拖拽
        self._setup_drag_and_drop()

        # 4. 绑定全局极客快捷键
        self._setup_shortcuts()

        # 5. 启动后台 UI 队列消费者 (每 50ms 轮询一次)
        self.after(50, self._poll_ui_queue)

    def _center_window(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - WINDOW_WIDTH) // 2)
        y = max(0, (sh - WINDOW_HEIGHT) // 2)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _setup_drag_and_drop(self):
        try:
            import windnd
            def on_drop_files(files):
                if files:
                    first = files[0]
                    if isinstance(first, bytes):
                        for enc in ("utf-8", "gbk", "cp936"):
                            try:
                                first = first.decode(enc)
                                break
                            except Exception:
                                pass
                    path_str = str(first)
                    self.path_entry.delete(0, "end")
                    self.path_entry.insert(0, path_str)
                    self._append_console_log(f"已通过拖拽载入路径: {path_str}", "INFO")

            windnd.hook_dropfiles(self, func=on_drop_files)
        except Exception:
            pass

    def _setup_shortcuts(self):
        """绑定全局极客快捷键"""
        self.bind("<F5>", lambda e: self._on_start_task())
        self.bind("<Escape>", lambda e: self._on_stop_task())
        self.bind("<F1>", lambda e: self._show_help_dialog())
        self.bind("<Control-l>", lambda e: self._clear_console())
        self.bind("<Control-L>", lambda e: self._clear_console())

    def _show_help_dialog(self):
        """F1 快捷键呼出用户指南弹窗"""
        guide_text = (
            "【FlashCraft 快捷键与操作指南】\n\n"
            "• [F5] 键：快速启动当前选中的自动化任务\n"
            "• [Esc] 键：紧急强行终止后台任务\n"
            "• [F1] 键：呼出本帮助说明指南\n"
            "• [Ctrl + L]：一键清屏当前日志终端\n"
            "• [文件拖拽]：支持从微信或桌面直接拖入文件/文件夹\n\n"
            f"本机硬件指纹: {self.machine_code}\n"
            "专属技术支持: Emiliamio <mio2110767128@163.com>"
        )
        messagebox.showinfo("FlashCraft 操作指南 (F1)", guide_text)

    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header(row=0)
        self._build_config_card(row=1)
        self._build_console_card(row=2)
        self._build_action_bar(row=3)

    def _build_header(self, row: int):
        header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        header_frame.grid(row=row, column=0, padx=20, pady=(15, 8), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        title_label = ctk.CTkLabel(
            title_box, 
            text=APP_NAME, 
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color="#FFFFFF"
        )
        title_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            title_box, 
            text=f"{APP_SUBTITLE} • {APP_VERSION} • 设备码: {self.machine_code}", 
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#94A3B8"
        )
        sub_label.pack(anchor="w")

        badge_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        badge_box.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        allowed, count, max_runs = get_trial_status()
        if self._is_trial_active:
            rem = max(0, max_runs - count)
            trial_text = f"🛡️ 试用保护锁 (限{TRIAL_ROW_LIMIT}条 | 剩{rem}次)"
            trial_color = COLOR_ACCENT_AMBER
            fg_badge = "#2D2B1B"
        else:
            trial_text = "⭐ 商业永久正式版 (已授权)"
            trial_color = COLOR_ACCENT_GREEN
            fg_badge = "#1A2E26"

        self.trial_badge = ctk.CTkLabel(
            badge_box,
            text=trial_text,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11, weight="bold"),
            fg_color=fg_badge,
            text_color=trial_color,
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.trial_badge.pack(side="left", padx=(0, 10))

        self.status_badge = ctk.CTkLabel(
            badge_box,
            text="● 待机就绪",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11, weight="bold"),
            fg_color="#1E293B",
            text_color=COLOR_ACCENT_BLUE,
            corner_radius=6,
            padx=10,
            pady=4
        )
        self.status_badge.pack(side="left")

    def _build_config_card(self, row: int):
        config_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        config_frame.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
        config_frame.grid_columnconfigure(1, weight=1)

        mode_label = ctk.CTkLabel(config_frame, text="业务场景选择:", font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"), text_color="#E2E8F0")
        mode_label.grid(row=0, column=0, padx=(15, 10), pady=(10, 5), sticky="w")

        self.mode_menu = ctk.CTkOptionMenu(
            config_frame,
            values=TASK_MODES,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11, weight="bold"),
            dropdown_font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color="#0284C7",
            button_color="#0369A1",
            width=380,
            command=self._on_change_mode
        )
        self.mode_menu.grid(row=0, column=1, columnspan=2, padx=(0, 15), pady=(10, 5), sticky="w")

        path_label = ctk.CTkLabel(config_frame, text="数据输入源:", font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"), text_color="#E2E8F0")
        path_label.grid(row=1, column=0, padx=(15, 10), pady=8, sticky="w")

        self.path_entry = ctk.CTkEntry(
            config_frame,
            placeholder_text="支持将表格/文件夹直接拖拽入本窗口；留空则自动载入内置全真靶场；[F5]一键启动...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color="#161822",
            border_color="#334155"
        )
        self.path_entry.grid(row=1, column=1, padx=(0, 10), pady=8, sticky="ew")

        btn_box = ctk.CTkFrame(config_frame, fg_color="transparent")
        btn_box.grid(row=1, column=2, padx=(0, 15), pady=8, sticky="e")

        btn_file = ctk.CTkButton(btn_box, text="选择文件", width=75, height=28, font=ctk.CTkFont(family="Microsoft YaHei", size=11), command=self._on_choose_file)
        btn_file.pack(side="left", padx=(0, 5))

        btn_dir = ctk.CTkButton(btn_box, text="选择目录", width=75, height=28, font=ctk.CTkFont(family="Microsoft YaHei", size=11), command=self._on_choose_dir)
        btn_dir.pack(side="left")

        opt_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        opt_frame.grid(row=2, column=0, columnspan=3, padx=15, pady=(2, 10), sticky="ew")

        self.chk_dedup = ctk.CTkCheckBox(opt_frame, text="自动查重/去重 (唯一号识别)", font=ctk.CTkFont(family="Microsoft YaHei", size=11), text_color="#CBD5E1")
        self.chk_dedup.select()
        self.chk_dedup.pack(side="left", padx=(0, 20))

        self.chk_auto_open = ctk.CTkCheckBox(opt_frame, text="完成后自动打开结果文件夹", font=ctk.CTkFont(family="Microsoft YaHei", size=11), text_color="#CBD5E1")
        self.chk_auto_open.select()
        self.chk_auto_open.pack(side="left", padx=(0, 20))

        # 帮助提示标签
        hint_label = ctk.CTkLabel(opt_frame, text="💡 提示: 按 [F5] 启动 | [Esc] 停止 | [F1] 帮助", font=ctk.CTkFont(family="Consolas", size=11), text_color="#64748B")
        hint_label.pack(side="right")

    def _build_console_card(self, row: int):
        console_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        console_frame.grid(row=row, column=0, padx=20, pady=5, sticky="nsew")
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)

        bar = ctk.CTkFrame(console_frame, fg_color="transparent")
        bar.grid(row=0, column=0, padx=15, pady=(8, 4), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        con_title = ctk.CTkLabel(bar, text="💻 工业级实时执行控制台 (Live Console)", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#94A3B8")
        con_title.grid(row=0, column=0, sticky="w")

        btn_copy = ctk.CTkButton(bar, text="📋 复制日志", width=70, height=22, font=ctk.CTkFont(family="Microsoft YaHei", size=10), fg_color="#334155", hover_color="#475569", command=self._copy_console_log)
        btn_copy.grid(row=0, column=1, padx=(0, 5))

        btn_clear = ctk.CTkButton(bar, text="清屏 (Ctrl+L)", width=80, height=22, font=ctk.CTkFont(family="Microsoft YaHei", size=10), fg_color="#334155", hover_color="#475569", command=self._clear_console)
        btn_clear.grid(row=0, column=2, padx=(0, 5))

        btn_open_out = ctk.CTkButton(bar, text="📁 输出目录", width=75, height=22, font=ctk.CTkFont(family="Microsoft YaHei", size=10), fg_color="#334155", hover_color="#475569", command=self._open_output_dir)
        btn_open_out.grid(row=0, column=3)

        self.console_text = ctk.CTkTextbox(console_frame, fg_color=COLOR_CONSOLE_BG, text_color=COLOR_CONSOLE_TEXT, font=ctk.CTkFont(family="Consolas", size=11), corner_radius=8, wrap="word")
        self.console_text.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="nsew")
        self.console_text.configure(state="disabled")

        self._append_console_log(f"FlashCraft 商业控制台已就绪。设备物理指纹: {self.machine_code}", "INFO")
        self._append_console_log("支持快捷键: [F5] 启动任务 / [Esc] 中止 / [F1] 帮助手册", "INFO")
        if self._is_trial_active:
            allowed, count, max_runs = get_trial_status()
            rem = max(0, max_runs - count)
            self._append_console_log(f"【商业授权锁激活】单机试用模式已生效，剩余可用执行配额: {rem}/{max_runs} 次。", "WARN")

    def _build_action_bar(self, row: int):
        action_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        action_frame.grid(row=row, column=0, padx=20, pady=(5, 15), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        progress_box = ctk.CTkFrame(action_frame, fg_color="transparent")
        progress_box.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 5), sticky="ew")
        progress_box.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(progress_box, height=10, corner_radius=5, progress_color=COLOR_ACCENT_BLUE, fg_color="#1E293B")
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.progress_bar.set(0.0)

        self.progress_label = ctk.CTkLabel(progress_box, text="0%", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color="#94A3B8", width=45)
        self.progress_label.grid(row=0, column=1)

        btn_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=(5, 12), sticky="ew")

        self.btn_run = ctk.CTkButton(btn_frame, text="🚀 开始执行任务 (F5)", font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"), fg_color="#0284C7", hover_color="#0369A1", height=36, command=self._on_start_task)
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_stop = ctk.CTkButton(btn_frame, text="🛑 强行停止 (Esc)", font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"), fg_color="#991B1B", hover_color="#7F1D1D", height=36, state="disabled", command=self._on_stop_task)
        self.btn_stop.pack(side="left", padx=(0, 0))

    def _on_change_mode(self, choice: str):
        self._append_console_log(f"已切换当前业务模式至: {choice}", "INFO")

    def _on_choose_file(self):
        mode = self.mode_menu.get()
        ftypes = [("PDF 发票文件", "*.pdf"), ("所有文件", "*.*")] if "发票" in mode else [("Excel/CSV 表格", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
        file_path = filedialog.askopenfilename(title="选择待处理的文件", filetypes=ftypes)
        if file_path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, file_path)

    def _on_choose_dir(self):
        dir_path = filedialog.askdirectory(title="选择包含待处理文件的目录")
        if dir_path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, dir_path)

    def _copy_console_log(self):
        logs = self.console_text.get("1.0", "end-1c")
        if logs.strip():
            self.clipboard_clear()
            self.clipboard_append(logs)
            old_text = self.status_badge.cget("text")
            old_fg = self.status_badge.cget("fg_color")
            old_color = self.status_badge.cget("text_color")
            self.status_badge.configure(text="📋 日志已复制", fg_color="#1E293B", text_color=COLOR_ACCENT_GREEN)
            self.after(2000, lambda: self.status_badge.configure(text=old_text, fg_color=old_fg, text_color=old_color))

    def _clear_console(self):
        self.console_text.configure(state="normal")
        self.console_text.delete("1.0", "end")
        self.console_text.configure(state="disabled")

    def _open_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        try:
            os.startfile(self.output_dir)
        except Exception as e:
            messagebox.showwarning("打开失败", f"无法打开输出目录: {e}")

    def _play_beep(self):
        if sys.platform == "win32":
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

    def _append_console_log(self, text: str, level: str = "INFO"):
        t_str = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{t_str}] [{level.upper()}] {text}\n"
        self.console_text.configure(state="normal")
        self.console_text.insert("end", formatted)
        self.console_text.see("end")
        self.console_text.configure(state="disabled")

    def _on_start_task(self):
        if self.current_worker and self.current_worker.is_running:
            return

        # 商业授权配额检查
        allowed, count, max_runs = get_trial_status()
        if not allowed:
            err_msg = (
                f"【试用授权已耗尽】\n\n"
                f"当前单机试用配额已达上限 ({count}/{max_runs} 次)。\n"
                f"为保护技术知识产权，已触发安全熔断。\n\n"
                f"您的设备机器码: {self.machine_code}\n"
                f"请联系作者 Emiliamio (mio2110767128@163.com) 结清尾款获取正式商用激活卡密！"
            )
            messagebox.showwarning("商业授权受限", err_msg)
            self._append_console_log(f"🚨 试用次数已超限 ({count}/{max_runs})，运行已被安全拦截。", "ERROR")
            return

        # 记录一次试用
        record_trial_usage()

        mode = self.mode_menu.get()
        input_path = self.path_entry.get().strip()
        params = {
            "input_path": input_path,
            "remove_duplicates": bool(self.chk_dedup.get()),
            "headless": False
        }

        if "发票" in mode:
            self.current_worker = InvoiceExtractorWorker(params=params)
        elif "电商" in mode or "账单" in mode:
            self.current_worker = ExcelMergerWorker(params=params)
        elif "填表" in mode or "上报" in mode:
            self.current_worker = WebAutofillWorker(params=params)
        else:
            self.current_worker = ExcelMergerWorker(params=params)

        self.btn_run.configure(state="disabled", text="⚡ 正在运行中...")
        self.btn_stop.configure(state="normal")
        self.status_badge.configure(text="● 运行中...", fg_color="#1E3A8A", text_color="#60A5FA")
        self.current_worker.start()

    def _on_stop_task(self):
        if self.current_worker and self.current_worker.is_running:
            self.current_worker.request_stop()
            self.btn_stop.configure(state="disabled", text="正在中止...")

    def _poll_ui_queue(self):
        messages = global_ui_queue.get_messages(batch_limit=50)
        for msg in messages:
            if msg.msg_type == MessageType.LOG:
                level, text = msg.data
                self._append_console_log(text, level=level)

            elif msg.msg_type == MessageType.PROGRESS:
                fraction = msg.data
                self.progress_bar.set(fraction)
                pct = int(fraction * 100)
                self.progress_label.configure(text=f"{pct}%")

            elif msg.msg_type == MessageType.STATUS:
                status, text = msg.data
                if status == "RUNNING":
                    self.status_badge.configure(text=f"● {text}", fg_color="#1E3A8A", text_color="#60A5FA")
                elif status == "COMPLETED":
                    self.status_badge.configure(text="✔ 已完成", fg_color="#064E3B", text_color=COLOR_ACCENT_GREEN)
                    self.btn_run.configure(state="normal", text="🚀 开始执行任务 (F5)")
                    self.btn_stop.configure(state="disabled", text="🛑 强行停止 (Esc)")
                    self._play_beep()
                elif status == "ERROR":
                    self.status_badge.configure(text="✖ 异常中断", fg_color="#7F1D1D", text_color=COLOR_ACCENT_RED)
                    self.btn_run.configure(state="normal", text="🚀 开始执行任务 (F5)")
                    self.btn_stop.configure(state="disabled", text="🛑 强行停止 (Esc)")
                elif status == "IDLE":
                    self.status_badge.configure(text="● 待机就绪", fg_color="#1E293B", text_color=COLOR_ACCENT_BLUE)
                    self.btn_run.configure(state="normal", text="🚀 开始执行任务 (F5)")
                    self.btn_stop.configure(state="disabled", text="🛑 强行停止 (Esc)")

            elif msg.msg_type == MessageType.POPUP:
                title, message, is_error = msg.data
                if is_error:
                    messagebox.showerror(title, message)
                else:
                    messagebox.showinfo(title, message)

            elif msg.msg_type == MessageType.TASK_DONE:
                if self.chk_auto_open.get():
                    self._open_output_dir()

        self.after(50, self._poll_ui_queue)