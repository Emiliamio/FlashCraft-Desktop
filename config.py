# -*- coding: utf-8 -*-
"""
config.py - FlashCraft 桌面自动化工作台全局配置
作者: Emiliamio <mio2110767128@163.com>

本模块统领软件的核心标识、商业防御试用锁、主题调色与资源路径自适应解析。
"""

import os
import sys
from pathlib import Path

# ==============================================================================
# 1. 商业品牌与基础信息
# ==============================================================================
APP_NAME = "FlashCraft 桌面自动化工作台"
APP_VERSION = "v1.0.0 Pro"
APP_SUBTITLE = "工业级数据批处理与业务自动化引擎"

# ==============================================================================
# 2. 商业防御铁律：防白嫖试用锁 (Commercial Trial Defense)
# ==============================================================================
# 当交付演示或试用给客户时保持 True；尾款结清后一键改为 False 并重新编译正式版
IS_TRIAL = True
TRIAL_ROW_LIMIT = 10
TRIAL_WATERMARK = "【试用版仅导出前10行，结清尾款获取正式版】"

# ==============================================================================
# 3. 视觉与美学设定 (CustomTkinter)
# ==============================================================================
APPEARANCE_MODE = "Dark"      # "Dark" | "Light" | "System"
COLOR_THEME = "blue"          # "blue" | "green" | "dark-blue"
WINDOW_WIDTH = 920
WINDOW_HEIGHT = 680
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 600

# 自定义主题色系 (Hex)
COLOR_BG_DARK = "#12131A"         # 主背景深炭黑
COLOR_CARD_DARK = "#1E202E"       # 卡片底板
COLOR_CARD_BORDER = "#2B2E42"     # 边框勾勒
COLOR_ACCENT_BLUE = "#38BDF8"     # 电光青蓝 (Sky-400)
COLOR_ACCENT_GREEN = "#34D399"    # 翡翠绿 (Emerald-400)
COLOR_ACCENT_RED = "#F87171"      # 珊瑚红 (Rose-400)
COLOR_ACCENT_AMBER = "#FBBF24"    # 琥珀黄 (Amber-400)
COLOR_CONSOLE_BG = "#0D0E15"      # 终端黑
COLOR_CONSOLE_TEXT = "#E2E8F0"    # 终端文字灰白

# ==============================================================================
# 4. 路径自适应与多环境适配 (PyInstaller _MEIPASS 兼容)
# ==============================================================================
def get_resource_path(relative_path: str) -> str:
    """
    获取资源的绝对路径。
    自动兼容 PyInstaller 单文件打包解压目录 (_MEIPASS) 与本地直接源码运行模式。
    """
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.normpath(os.path.join(base_path, relative_path))

def get_default_output_dir() -> str:
    """
    获取默认输出目录：优先定位用户桌面上的 'FlashCraft_输出成果' 目录。
    若桌面不可写则回退到当前工作目录同级 output/。
    """
    desktop = Path.home() / "Desktop"
    if desktop.exists() and os.access(desktop, os.W_OK):
        out_dir = desktop / "FlashCraft_处理结果"
    else:
        out_dir = Path(os.getcwd()) / "output"
    
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir)

# 图标路径
ICON_PATH = get_resource_path(os.path.join("assets", "icon.ico"))
LOGO_PATH = get_resource_path(os.path.join("assets", "app_logo.png"))
LOG_FILE_PATH = os.path.join(os.getcwd(), "app.log")
ERROR_LOG_PATH = os.path.join(os.getcwd(), "error.log")