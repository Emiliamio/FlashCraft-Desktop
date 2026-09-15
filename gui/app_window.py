# -*- coding: utf-8 -*-
"""
gui/app_window.py - FlashCraft 现代暗黑美学主界面 (3合1多场景商业工作台)
作者: Emiliamio <mio2110767128@163.com>

三大吸金业务场景一键切换：
1. 📑 财务神器：电子发票 PDF 批量提取与查重汇总
2. 📊 电商神器：多店铺 Excel 账单核对与利润分析
3. 🌐 政企神器：Excel 数据自动批量填表与上报 (驱动系统 Edge)
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
from tasks.demo_excel_merger import ExcelMergerWorker
from tasks.demo_invoice_extractor import InvoiceExtractorWorker
from tasks.demo_web_autofill import WebAutofillWorker

# 场景定义
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
        self._is_trial_active = IS_TRIAL

        # 2. 构建界面组件
        self._setup_layout()

        # 3. 挂载 Windows 原生文件/目录拖拽钩子 (Drag & Drop)
        self._setup_drag_and_drop()

        # 4. 启动后台 UI 队列消费者 (每 50ms 轮询一次)
        self.after(50, self._poll_ui_queue)

    def _center_window(self):
        """让窗口在屏幕正中央优雅弹出"""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = max(0, (sw - WINDOW_WIDTH) // 2)
        y = max(0, (sh - WINDOW_HEIGHT) // 2)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _setup_drag_and_drop(self):
        """通过 windnd 挂载原生拖拽监听"""
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
                    self._append_console_log(f"已通过拖拽快捷载入目标路径: {path_str}", "INFO")

            windnd.hook_dropfiles(self, func=on_drop_files)
        except Exception:
            pass

    def _setup_layout(self):
        """网格布局规划"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # 让日志控制台自适应垂直扩展

        # 1. 顶部 Header
        self._build_header(row=0)

        # 2. 参数与业务卡片
        self._build_config_card(row=1)

        # 3. 实时终端控制台
        self._build_console_card(row=2)

        # 4. 底部行动与进度卡片
        self._build_action_bar(row=3)

    def _build_header(self, row: int):
        header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        header_frame.grid(row=row, column=0, padx=20, pady=(15, 8), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # 标题与副标题区
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
            text=f"{APP_SUBTITLE} • {APP_VERSION}", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color="#94A3B8"
        )
        sub_label.pack(anchor="w")

        # 状态指示徽章区
        badge_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        badge_box.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        trial_text = f"🛡️ 试用保护锁 (限{TRIAL_ROW_LIMIT}条)" if self._is_trial_active else "⭐ 商业正式版"
        trial_color = COLOR_ACCENT_AMBER if self._is_trial_active else COLOR_ACCENT_GREEN
        self.trial_badge = ctk.CTkLabel(
            badge_box,
            text=trial_text,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11, weight="bold"),
            fg_color="#2D2B1B" if self._is_trial_active else "#1A2E26",
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

        # 1. 业务场景切换下拉框
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

        # 2. 输入源选择行
        path_label = ctk.CTkLabel(config_frame, text="数据输入源:", font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"), text_color="#E2E8F0")
        path_label.grid(row=1, column=0, padx=(15, 10), pady=8, sticky="w")

        self.path_entry = ctk.CTkEntry(
            config_frame,
            placeholder_text="留空则自动加载该场景对应的内置全真靶场数据；也可直接拖入文件或点击右侧选择...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color="#161822",
            border_color="#334155"
        )
        self.path_entry.grid(row=1, column=1, padx=(0, 10), pady=8, sticky="ew")

        btn_box = ctk.CTkFrame(config_frame, fg_color="transparent")
        btn_box.grid(row=1, column=2, padx=(0, 15), pady=8, sticky="e")

        btn_file = ctk.CTkButton(
            btn_box, 
            text="选择文件", 
            width=75, 
            height=28,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            command=self._on_choose_file
        )
        btn_file.pack(side="left", padx=(0, 5))

        btn_dir = ctk.CTkButton(
            btn_box, 
            text="选择目录", 
            width=75, 
            height=28,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            command=self._on_choose_dir
        )
        btn_dir.pack(side="left")

        # 3. 业务参数开关行
        opt_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        opt_frame.grid(row=2, column=0, columnspan=3, padx=15, pady=(2, 10), sticky="ew")

        self.chk_dedup = ctk.CTkCheckBox(
            opt_frame, 
            text="自动查重/去重 (唯一号识别)", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color="#CBD5E1"
        )
        self.chk_dedup.select()
        self.chk_dedup.pack(side="left", padx=(0, 20))

        self.chk_auto_open = ctk.CTkCheckBox(
            opt_frame, 
            text="完成后自动打开结果文件夹", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color="#CBD5E1"
        )
        self.chk_auto_open.select()
        self.chk_auto_open.pack(side="left")

    def _build_console_card(self, row: int):
        console_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        console_frame.grid(row=row, column=0, padx=20, pady=5, sticky="nsew")
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)

        # 终端顶部工具栏
        bar = ctk.CTkFrame(console_frame, fg_color="transparent")
        bar.grid(row=0, column=0, padx=15, pady=(8, 4), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        con_title = ctk.CTkLabel(
            bar, 
            text="💻 实时执行控制台 (Live Execution Console)", 
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color="#94A3B8"
        )
        con_title.grid(row=0, column=0, sticky="w")

        btn_copy = ctk.CTkButton(
            bar,
            text="📋 复制日志",
            width=70,
            height=22,
            font=ctk.CTkFont(family="Microsoft YaHei", size=10),
            fg_color="#334155",
            hover_color="#475569",
            command=self._copy_console_log
        )
        btn_copy.grid(row=0, column=1, padx=(0, 5))

        btn_clear = ctk.CTkButton(
            bar, 
            text="清屏", 
            width=45, 
            height=22, 
            font=ctk.CTkFont(family="Microsoft YaHei", size=10),
            fg_color="#334155",
            hover_color="#475569",
            command=self._clear_console
        )
        btn_clear.grid(row=0, column=2, padx=(0, 5))

        btn_open_out = ctk.CTkButton(
            bar, 
            text="📁 打开输出目录", 
            width=90, 
            height=22, 
            font=ctk.CTkFont(family="Microsoft YaHei", size=10),
            fg_color="#334155",
            hover_color="#475569",
            command=self._open_output_dir
        )
        btn_open_out.grid(row=0, column=3)

        # 滚动多行文本框
        self.console_text = ctk.CTkTextbox(
            console_frame,
            fg_color=COLOR_CONSOLE_BG,
            text_color=COLOR_CONSOLE_TEXT,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            wrap="word"
        )
        self.console_text.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="nsew")
        self.console_text.configure(state="disabled")

        # 欢迎语
        self._append_console_log(f"FlashCraft 桌面自动化工作台已就绪。运行环境: Python {sys.version.split()[0]}", "INFO")
        self._append_console_log("【三合一工作台】支持发票批量提取、电商跨店对账与网页系统批量填报，可在上方下拉切换。", "INFO")
        if self._is_trial_active:
            self._append_console_log(f"【商业安全锁开启】当前为客户试用体验模式，处理结果将限制前 {TRIAL_ROW_LIMIT} 条/张。", "WARN")

    def _build_action_bar(self, row: int):
        action_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        action_frame.grid(row=row, column=0, padx=20, pady=(5, 15), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        # 1. 进度条
        progress_box = ctk.CTkFrame(action_frame, fg_color="transparent")
        progress_box.grid(row=0, column=0, columnspan=2, padx=20, pady=(10, 5), sticky="ew")
        progress_box.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(
            progress_box,
            height=10,
            corner_radius=5,
            progress_color=COLOR_ACCENT_BLUE,
            fg_color="#1E293B"
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.progress_bar.set(0.0)

        self.progress_label = ctk.CTkLabel(
            progress_box, 
            text="0%", 
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#94A3B8",
            width=45
        )
        self.progress_label.grid(row=0, column=1)

        # 2. 按钮栏
        btn_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=(5, 12), sticky="ew")

        self.btn_run = ctk.CTkButton(
            btn_frame,
            text="🚀 开始执行任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=36,
            command=self._on_start_task
        )
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_stop = ctk.CTkButton(
            btn_frame,
            text="🛑 强行停止",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color="#991B1B",
            hover_color="#7F1D1D",
            height=36,
            state="disabled",
            command=self._on_stop_task
        )
        self.btn_stop.pack(side="left", padx=(0, 0))

    # ==========================================================================
    # 交互回调处理
    # ==========================================================================
    def _on_change_mode(self, choice: str):
        self._append_console_log(f"已切换当前业务模式至: {choice}", "INFO")

    def _on_choose_file(self):
        mode = self.mode_menu.get()
        if "发票" in mode:
            ftypes = [("PDF 发票文件", "*.pdf"), ("所有文件", "*.*")]
        else:
            ftypes = [("Excel/CSV 表格", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
            
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

        mode = self.mode_menu.get()
        input_path = self.path_entry.get().strip()
        params = {
            "input_path": input_path,
            "remove_duplicates": bool(self.chk_dedup.get()),
            "headless": False
        }

        # 派发具体 Worker
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
                    self.btn_run.configure(state="normal", text="🚀 开始执行任务")
                    self.btn_stop.configure(state="disabled", text="🛑 强行停止")
                    self._play_beep()
                elif status == "ERROR":
                    self.status_badge.configure(text="✖ 异常中断", fg_color="#7F1D1D", text_color=COLOR_ACCENT_RED)
                    self.btn_run.configure(state="normal", text="🚀 开始执行任务")
                    self.btn_stop.configure(state="disabled", text="🛑 强行停止")
                elif status == "IDLE":
                    self.status_badge.configure(text="● 待机就绪", fg_color="#1E293B", text_color=COLOR_ACCENT_BLUE)
                    self.btn_run.configure(state="normal", text="🚀 开始执行任务")
                    self.btn_stop.configure(state="disabled", text="🛑 强行停止")

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