# -*- coding: utf-8 -*-
"""
gui/ui_queue.py - 线程安全 UI 调度队列
作者: Emiliamio <mio2110767128@163.com>

本模块解决多线程更新 Tkinter UI 导致的内存竞态、界面未响应与闪退崩溃问题。
后台 Worker 产生的日志、进度、状态统一经由队列削峰填谷，在 UI 主线程通过 after() 定时器平滑刷新。
"""

import queue
from enum import Enum
from typing import Any, NamedTuple

class MessageType(Enum):
    LOG = "LOG"                 # 控制台日志 (level, text, timestamp)
    PROGRESS = "PROGRESS"       # 进度更新 (0.0 ~ 1.0)
    STATUS = "STATUS"           # 状态徽章变更 ("IDLE", "RUNNING", "COMPLETED", "ERROR")
    POPUP = "POPUP"             # 弹窗提示 (title, message, is_error)
    TASK_DONE = "TASK_DONE"     # 任务完成信号 (summary_info)

class UIMessage(NamedTuple):
    msg_type: MessageType
    data: Any

class UIQueue:
    """全局线程安全 UI 调度中枢"""
    def __init__(self, maxsize: int = 5000):
        self._q: queue.Queue[UIMessage] = queue.Queue(maxsize=maxsize)

    def put_log(self, text: str, level: str = "INFO"):
        self._q.put(UIMessage(MessageType.LOG, (level, text)))

    def put_progress(self, current: float, total: float = 1.0):
        fraction = max(0.0, min(1.0, current / total if total > 0 else 0.0))
        self._q.put(UIMessage(MessageType.PROGRESS, fraction))

    def put_status(self, status: str, text: str = ""):
        self._q.put(UIMessage(MessageType.STATUS, (status, text)))

    def put_popup(self, title: str, message: str, is_error: bool = False):
        self._q.put(UIMessage(MessageType.POPUP, (title, message, is_error)))

    def put_done(self, summary: dict):
        self._q.put(UIMessage(MessageType.TASK_DONE, summary))

    def get_messages(self, batch_limit: int = 50):
        """主线程批量消费消息，避免单次处理过多耗尽 UI 刷新预算"""
        messages = []
        for _ in range(batch_limit):
            try:
                messages.append(self._q.get_nowait())
            except queue.Empty:
                break
        return messages

# 全局单例
global_ui_queue = UIQueue()