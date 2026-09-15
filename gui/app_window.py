# -*- coding: utf-8 -*-
"""
gui/app_window.py - FlashCraft 现代暗黑美学主界面
作者: Emiliamio <mio2110767128@163.com>

基于 CustomTkinter 打造的大厂高质感暗黑界面：
- 顶部 Header：Logo、品牌标题、运行状态 Badge 与商业试用模式指示牌；
- 输入控制区：文件/目录选择器、业务参数勾选卡片；
- 实时日志终端：滚动控制台，支持时间戳、彩色级别区分、清空与日志一键导出；
- 底部行动栏：平滑百分比进度条、【开始执行】、【强行停止】与【打开输出目录】。
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

class AppWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # 1. 窗口基础规格
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.configure(fg_color=COLOR_BG_DARK)
        
        # 图标适配
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass

        # 状态管理
        self.current_worker: ExcelMergerWorker = None
        self.output_dir = get_default_output_dir()
        self._is_trial_active = IS_TRIAL

        # 2. 构建界面组件
        self._setup_layout()

        # 3. 启动后台 UI 队列消费者 (每 50ms 轮询一次)
        self.after(50, self._poll_ui_queue)

    def _setup_layout(self):
        """网格布局规划"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # 让日志控制台自适应垂直扩展

        # 1. 顶部 Header
        self._build_header(row=0)

        # 2. 参数与文件选择卡片
        self._build_config_card(row=1)

        # 3. 实时终端控制台
        self._build_console_card(row=2)

        # 4. 底部行动与进度卡片
        self._build_action_bar(row=3)

    def _build_header(self, row: int):
        header_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        header_frame.grid(row=row, column=0, padx=20, pady=(15, 10), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # 标题与副标题区
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=20, pady=12, sticky="w")

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
        badge_box.grid(row=0, column=2, padx=20, pady=12, sticky="e")

        # 商业试用模式指示牌
        trial_text = f"🛡️ 试用保护锁 (限{TRIAL_ROW_LIMIT}行)" if self._is_trial_active else "⭐ 商业正式版"
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

        # 运行状态指示器
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

        # 1. 路径选择行
        path_label = ctk.CTkLabel(config_frame, text="数据输入源:", font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"), text_color="#E2E8F0")
        path_label.grid(row=0, column=0, padx=(15, 10), pady=12, sticky="w")

        self.path_entry = ctk.CTkEntry(
            config_frame,
            placeholder_text="留空则自动加载内置仿真数据进行演示；或点击右侧按钮选择文件/文件夹...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color="#161822",
            border_color="#334155"
        )
        self.path_entry.grid(row=0, column=1, padx=(0, 10), pady=12, sticky="ew")

        btn_box = ctk.CTkFrame(config_frame, fg_color="transparent")
        btn_box.grid(row=0, column=2, padx=(0, 15), pady=12, sticky="e")

        btn_file = ctk.CTkButton(
            btn_box, 
            text="选择单个表格", 
            width=90, 
            height=28,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            command=self._on_choose_file
        )
        btn_file.pack(side="left", padx=(0, 5))

        btn_dir = ctk.CTkButton(
            btn_box, 
            text="选择批量目录", 
            width=90, 
            height=28,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            command=self._on_choose_dir
        )
        btn_dir.pack(side="left")

        # 2. 业务参数开关行
        opt_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        opt_frame.grid(row=1, column=0, columnspan=3, padx=15, pady=(0, 12), sticky="ew")

        self.chk_dedup = ctk.CTkCheckBox(
            opt_frame, 
            text="自动去重 (按订单/唯一号)", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color="#CBD5E1"
        )
        self.chk_dedup.select()
        self.chk_dedup.pack(side="left", padx=(0, 20))

        self.chk_clean_spaces = ctk.CTkCheckBox(
            opt_frame, 
            text="自动剥离字段首尾空格与乱码字符", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color="#CBD5E1"
        )
        self.chk_clean_spaces.select()
        self.chk_clean_spaces.pack(side="left", padx=(0, 20))

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

        # 终端卡片顶部工具栏
        bar = ctk.CTkFrame(console_frame, fg_color="transparent")
        bar.grid(row=0, column=0, padx=15, pady=(8, 4), sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        con_title = ctk.CTkLabel(
            bar, 
            text="💻 业务处理实时控制台 (Live Execution Console)", 
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color="#94A3B8"
        )
        con_title.grid(row=0, column=0, sticky="w")

        btn_clear = ctk.CTkButton(
            bar, 
            text="清屏", 
            width=50, 
            height=22, 
            font=ctk.CTkFont(family="Microsoft YaHei", size=10),
            fg_color="#334155",
            hover_color="#475569",
            command=self._clear_console
        )
        btn_clear.grid(row=0, column=1, padx=(0, 5))

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
        btn_open_out.grid(row=0, column=2)

        # 滚动多行文本框 (Console Box)
        self.console_text = ctk.CTkTextbox(
            console_frame,
            fg_color=COLOR_CONSOLE_BG,
            text_color=COLOR_CONSOLE_TEXT,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=8,
            wrap="word"
        )
        self.console_text.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="nsew")
        self.console_text.configure(state="disabled")

        # 打印欢迎语
        self._append_console_log(f"FlashCraft 桌面自动化工作台已就绪。当前运行环境: Python {sys.version.split()[0]}", "INFO")
        if self._is_trial_active:
            self._append_console_log(f"【商业安全锁开启】当前为客户试用体验模式，处理结果将限制前 {TRIAL_ROW_LIMIT} 行。", "WARN")

    def _build_action_bar(self, row: int):
        action_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD_DARK, corner_radius=12, border_width=1, border_color=COLOR_CARD_BORDER)
        action_frame.grid(row=row, column=0, padx=20, pady=(5, 15), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        # 1. 进度条与数字百分比
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
    def _on_choose_file(self):
        file_path = filedialog.askopenfilename(
            title="选择要处理的表格数据文件",
            filetypes=[("Excel/CSV 表格", "*.xlsx *.xls *.csv"), ("所有文件", "*.*")]
        )
        if file_path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, file_path)

    def _on_choose_dir(self):
        dir_path = filedialog.askdirectory(title="选择包含待处理表格的文件夹")
        if dir_path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, dir_path)

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

    def _append_console_log(self, text: str, level: str = "INFO"):
        t_str = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{t_str}] [{level.upper()}] {text}\n"
        
        self.console_text.configure(state="normal")
        self.console_text.insert("end", formatted)
        self.console_text.see("end")
        self.console_text.configure(state="disabled")

    def _on_start_task(self):
        """点击开始任务：启动守护线程，更新界面状态"""
        if self.current_worker and self.current_worker.is_running:
            return

        input_path = self.path_entry.get().strip()
        params = {
            "input_path": input_path,
            "remove_duplicates": bool(self.chk_dedup.get()),
            "clean_spaces": bool(self.chk_clean_spaces.get())
        }

        # 更新按钮状态
        self.btn_run.configure(state="disabled", text="⚡ 正在运行中...")
        self.btn_stop.configure(state="normal")
        self.status_badge.configure(text="● 运行中...", fg_color="#1E3A8A", text_color="#60A5FA")

        # 创建并启动独立 Worker 线程（杜绝界面假死无响应）
        self.current_worker = ExcelMergerWorker(params=params)
        self.current_worker.start()

    def _on_stop_task(self):
        """用户点击强行停止"""
        if self.current_worker and self.current_worker.is_running:
            self.current_worker.request_stop()
            self.btn_stop.configure(state="disabled", text="正在中止...")

    def _poll_ui_queue(self):
        """消费后台 Worker 产生的 UI 消息流 (削峰填谷，彻底免疫闪退)"""
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
                summary = msg.data
                if self.chk_auto_open.get():
                    self._open_output_dir()

        # 持续循环监听
        self.after(50, self._poll_ui_queue)