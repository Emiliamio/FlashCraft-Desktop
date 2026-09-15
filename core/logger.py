# -*- coding: utf-8 -*-
"""
core/logger.py - 双向日志记录系统
作者: Emiliamio <mio2110767128@163.com>

支持控制台标准输出、UI 滚动日志流实时推送与本地 error.log / app.log 文件持久化。
"""

import sys
import os
import time
from datetime import datetime
from gui.ui_queue import global_ui_queue
from config import LOG_FILE_PATH, ERROR_LOG_PATH

class AppLogger:
    def __init__(self, log_to_file: bool = True):
        self.log_to_file = log_to_file

    def _format_time(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _write_file(self, path: str, line: str):
        if not self.log_to_file:
            return
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def log(self, text: str, level: str = "INFO"):
        t_str = self._format_time()
        formatted = f"[{t_str}] [{level.upper()}] {text}"
        
        # 1. 终端打印
        print(formatted)
        
        # 2. 推送至 UI 队列
        global_ui_queue.put_log(text, level=level)
        
        # 3. 写入常规日志
        self._write_file(LOG_FILE_PATH, formatted)
        
        # 4. 若为错误额外写入 error.log
        if level.upper() in ("ERROR", "FATAL"):
            self._write_file(ERROR_LOG_PATH, formatted)

    def info(self, text: str):
        self.log(text, level="INFO")

    def success(self, text: str):
        self.log(text, level="SUCCESS")

    def warn(self, text: str):
        self.log(text, level="WARN")

    def error(self, text: str):
        self.log(text, level="ERROR")

# 全局日志单例
app_logger = AppLogger()