# -*- coding: utf-8 -*-
"""
core/base_worker.py - 通用业务执行 Worker 基类
作者: Emiliamio <mio2110767128@163.com>

所有的业务任务（如表格合并、发票抓取、网页录入）统一继承自此类。
提供独立守护线程生命周期、优雅中断信号传递、进度平滑计算与防死锁保护。
"""

import threading
import time
import traceback
from typing import Any, Dict, Optional
from core.logger import app_logger
from core.fail_safe import translate_error
from gui.ui_queue import global_ui_queue

class BaseWorker(threading.Thread):
    def __init__(self, task_name: str, params: Optional[Dict[str, Any]] = None):
        super().__init__(name=f"Worker-{task_name}", daemon=True)
        self.task_name = task_name
        self.params = params or {}
        self._stop_event = threading.Event()
        self.is_running = False

    def request_stop(self):
        """外部调用：请求优雅中断当前任务"""
        app_logger.warn(f"接收到用户中断指令，正在通知任务 [{self.task_name}] 停止...")
        self._stop_event.set()

    @property
    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def check_stop_requested(self):
        """Worker 循环中显式调用：若收到中断则抛出异常以便快速收敛"""
        if self._stop_event.is_set():
            raise InterruptedError(f"任务 [{self.task_name}] 已被用户强行终止。")

    def emit_progress(self, current: float, total: float):
        """发射进度更新"""
        global_ui_queue.put_progress(current, total)

    def emit_log(self, text: str, level: str = "INFO"):
        """发射业务日志"""
        app_logger.log(text, level=level)

    def run(self):
        """线程核心生命周期包装"""
        self.is_running = True
        global_ui_queue.put_status("RUNNING", f"正在执行: {self.task_name}")
        self.emit_progress(0, 100)
        start_time = time.time()
        
        self.emit_log(f"====== 开始启动自动化任务: [{self.task_name}] ======", level="INFO")
        try:
            summary = self.execute()
            cost_sec = round(time.time() - start_time, 2)
            
            if self.is_stopped:
                self.emit_log(f"任务已中止，总耗时 {cost_sec} 秒", level="WARN")
                global_ui_queue.put_status("IDLE", "已中止")
            else:
                self.emit_progress(100, 100)
                self.emit_log(f"任务执行圆满完成！总耗时: {cost_sec} 秒", level="SUCCESS")
                global_ui_queue.put_status("COMPLETED", "执行完成")
                global_ui_queue.put_done(summary or {"status": "success", "cost_sec": cost_sec})
                
        except InterruptedError as ie:
            cost_sec = round(time.time() - start_time, 2)
            self.emit_log(str(ie), level="WARN")
            global_ui_queue.put_status("IDLE", "已由用户停止")
        except Exception as ex:
            cost_sec = round(time.time() - start_time, 2)
            err_msg = translate_error(ex)
            tb = traceback.format_exc()
            self.emit_log(f"致命异常中断 (耗时 {cost_sec}s): {err_msg}", level="ERROR")
            app_logger.error(f"异常堆栈:\n{tb}")
            global_ui_queue.put_status("ERROR", "发生异常")
            global_ui_queue.put_popup("运行遇到异常", err_msg, is_error=True)
        finally:
            self.is_running = False

    def execute(self) -> Dict[str, Any]:
        """子类必须覆写的核心业务方法"""
        raise NotImplementedError("子类必须实现 execute() 业务方法")