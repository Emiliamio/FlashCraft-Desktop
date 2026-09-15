# -*- coding: utf-8 -*-
"""
core/fail_safe.py - 全局异常捕获与熔断器 (极限防御版)
作者: Emiliamio <mio2110767128@163.com>

升级：覆盖加密 PDF、只读文件、公式损坏与空文件等极限异常，转译为高情商白话建议。
"""

import sys
import traceback
from core.logger import app_logger
from gui.ui_queue import global_ui_queue

def translate_error(e: Exception) -> str:
    """将底层 Python 异常转译为小白客户可理解的操作建议"""
    msg = str(e)
    if isinstance(e, PermissionError):
        return f"【权限受限或文件被占用】目标文件可能正在被 Excel/WPS 打开，请关闭相关表格窗口后再试。\n底层细节: {msg}"
    elif isinstance(e, FileNotFoundError):
        return f"【文件未找到】请检查输入的文件或目录路径是否已被移动、重命名或删除。\n底层细节: {msg}"
    elif "password" in msg.lower() or "encrypted" in msg.lower() or "PasswordError" in str(type(e)):
        return f"【文件受密码保护】选中的 PDF 发票或 Excel 文件已被加密，请输入正确密码解除保护后再试。\n底层细节: {msg}"
    elif "Invalid openpyxl" in msg or "zipfile.BadZipFile" in msg:
        return f"【文件格式损坏】选中的 Excel 文件损坏或扩展名不匹配（如将旧版 xls 直接强制改名为 xlsx）。\n底层细节: {msg}"
    elif isinstance(e, KeyError):
        return f"【缺少必须的表头列名】表格中未检索到核心列: {msg}，请核对是否与模板一致。"
    elif isinstance(e, MemoryError):
        return f"【内存溢出】单次读取数据量过大，请分批次拆分后处理。\n底层细节: {msg}"
    else:
        return f"【执行发生未预料异常】{msg}\n完整错误记录已安全保存至 error.log，可将该日志一键复制提供给专属工程师。"

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