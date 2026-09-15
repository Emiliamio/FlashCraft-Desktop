# -*- coding: utf-8 -*-
"""
core/fail_safe.py - 全局异常捕获与熔断器
作者: Emiliamio <mio2110767128@163.com>

本模块负责捕获运行中不可预知的业务与系统异常，将复杂的 Traceback 转译为客户能看懂的白话原因，
并同时写入本地 error.log，保障软件界面绝对不闪退、不崩溃。
"""

import sys
import traceback
from core.logger import app_logger
from gui.ui_queue import global_ui_queue

def translate_error(e: Exception) -> str:
    """将底层 Python 异常转译为小白客户可理解的操作建议"""
    msg = str(e)
    if isinstance(e, PermissionError):
        return f"【权限受限或文件被占用】目标文件可能正在被 Excel/WPS 打开，请关闭该文件后再试。\n底层细节: {msg}"
    elif isinstance(e, FileNotFoundError):
        return f"【文件未找到】请检查输入的文件或目录路径是否已被移动或删除。\n底层细节: {msg}"
    elif "Invalid openpyxl" in msg or "zipfile.BadZipFile" in msg:
        return f"【文件格式损坏】选中的 Excel 文件损坏或扩展名不匹配（如将 xls 直接改名为 xlsx）。\n底层细节: {msg}"
    elif isinstance(e, KeyError):
        return f"【缺少必须的表头列名】表格中未找到列名: {msg}，请核对是否与模板一致。"
    elif isinstance(e, MemoryError):
        return f"【内存溢出】单次读取数据量过大，请分批次处理。\n底层细节: {msg}"
    else:
        return f"【执行发生未预料异常】{msg}\n完整错误信息已保存至 error.log，可将该日志提供给技术人员。"

def safe_execute(action_name: str = "执行业务"):
    """业务函数装饰器：遇错不崩溃，弹窗提醒并记录日志"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as ex:
                err_summary = translate_error(ex)
                tb = traceback.format_exc()
                app_logger.error(f"{action_name}失败: {err_summary}")
                app_logger.error(f"详细堆栈:\n{tb}")
                global_ui_queue.put_status("ERROR", "处理异常中断")
                global_ui_queue.put_popup("运行遇到问题", err_summary, is_error=True)
                return None
        return wrapper
    return decorator