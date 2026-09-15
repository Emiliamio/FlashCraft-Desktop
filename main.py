# -*- coding: utf-8 -*-
"""
main.py - FlashCraft 桌面自动化工作台主程序入口
作者: Emiliamio <mio2110767128@163.com>

程序主入口：实现高 DPI 清晰度适配、异常兜底防护与暗黑科技 UI 调度。
"""

import sys
import os
import ctypes

# 1. 尝试 Windows 高 DPI 清晰度感知适配 (杜绝 4K 屏幕模糊或组件错位)
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import customtkinter as ctk
from config import APPEARANCE_MODE, COLOR_THEME, ERROR_LOG_PATH
from core.logger import app_logger
from gui.app_window import AppWindow

def main():
    try:
        # 设置 CustomTkinter 主题
        ctk.set_appearance_mode(APPEARANCE_MODE)
        ctk.set_default_color_theme(COLOR_THEME)

        # 实例化主窗口
        app = AppWindow()
        app_logger.info("FlashCraft 桌面工作台 GUI 引擎已成功启动。")
        app.mainloop()

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[CRITICAL MAIN CRASH] {e}\n{tb}\n")
        except Exception:
            pass
        print(f"致命错误: {e}\n{tb}", file=sys.stderr)

if __name__ == "__main__":
    main()