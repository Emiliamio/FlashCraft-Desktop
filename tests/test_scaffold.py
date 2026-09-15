# -*- coding: utf-8 -*-
"""
tests/test_scaffold.py - 脚手架与核心执行引擎自动化回归测试
作者: Emiliamio <mio2110767128@163.com>
"""

import os
import sys
import time
import pytest
import pandas as pd
from pathlib import Path

from config import get_resource_path, get_default_output_dir, IS_TRIAL, TRIAL_ROW_LIMIT
from gui.ui_queue import UIQueue, MessageType
from core.logger import AppLogger
from core.fail_safe import translate_error
from core.base_worker import BaseWorker
from tasks.demo_excel_merger import ExcelMergerWorker

def test_config_paths():
    """测试路径自适应与默认输出目录可用性"""
    res_path = get_resource_path("assets/icon.ico")
    assert os.path.isabs(res_path)
    out_dir = get_default_output_dir()
    assert os.path.exists(out_dir)
    assert os.path.isdir(out_dir)

def test_ui_queue_flow():
    """测试 UIQueue 线程安全消息队列"""
    q = UIQueue()
    q.put_log("测试日志", level="INFO")
    q.put_progress(50, 100)
    q.put_status("RUNNING", "处理中")
    
    msgs = q.get_messages(batch_limit=10)
    assert len(msgs) == 3
    assert msgs[0].msg_type == MessageType.LOG
    assert msgs[1].msg_type == MessageType.PROGRESS
    assert msgs[1].data == 0.5
    assert msgs[2].msg_type == MessageType.STATUS

def test_fail_safe_translation():
    """测试底层错误中文人性化转译"""
    perm_err = PermissionError("Permission denied: 'test.xlsx'")
    msg = translate_error(perm_err)
    assert "权限受限或文件被占用" in msg

    fnf_err = FileNotFoundError("No such file")
    msg = translate_error(fnf_err)
    assert "文件未找到" in msg

def test_excel_merger_worker_execution():
    """测试表格业务 Worker 核心清洗流程与试用锁截断机制"""
    worker = ExcelMergerWorker(params={"input_path": "", "remove_duplicates": True})
    # 直接在单线程测试环境下调用 execute()
    result = worker.execute()
    
    assert result is not None
    output_file = result["output_file"]
    assert os.path.exists(output_file)
    assert result["total_rows"] > 0
    
    # 验证导出的 Excel 内容
    df_out = pd.read_excel(output_file, sheet_name="对账标准化流水明细")
    if IS_TRIAL:
        # 试用模式下应只有 10 行有效数据 + 1 行水印
        assert len(df_out) == TRIAL_ROW_LIMIT + 1
        assert result["is_trial"] is True
    
    # 验证透视表 Sheet
    df_pivot = pd.read_excel(output_file, sheet_name="SKU商品利润透视")
    assert len(df_pivot) > 0
    assert "订单总营收" in df_pivot.columns

    # 清理测试产物
    if os.path.exists(output_file):
        os.remove(output_file)

def test_worker_stop_signal():
    """测试 Worker 优雅中断信号响应"""
    worker = ExcelMergerWorker(params={"input_path": ""})
    worker.request_stop()
    assert worker.is_stopped is True
    
    with pytest.raises(InterruptedError):
        worker.check_stop_requested()