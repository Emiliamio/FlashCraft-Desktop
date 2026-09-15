# -*- coding: utf-8 -*-
"""
tests/test_three_demos.py - 3 大核心商业 Demo 端到端自动化回归测试
作者: Emiliamio <mio2110767128@163.com>
"""

import os
import pytest
import pandas as pd
from pathlib import Path

from tasks.demo_invoice_extractor import InvoiceExtractorWorker
from tasks.demo_excel_merger import ExcelMergerWorker
from tasks.demo_web_autofill import WebAutofillWorker

def test_demo1_invoice_extractor():
    """测试发票批量提取、智能查重与报表生成"""
    worker = InvoiceExtractorWorker(params={"input_path": "mock_data/invoices"})
    res = worker.execute()
    
    assert res is not None
    assert os.path.exists(res["output_file"])
    assert res["total_invoices"] == 15
    assert res["duplicates"] == 1 # 验证靶场特意埋下的重复发票成功抓出
    assert res["total_amount"] > 0
    
    # 验证 Excel 格式
    df_out = pd.read_excel(res["output_file"], sheet_name="财务总计看板")
    assert len(df_out) >= 5

    if os.path.exists(res["output_file"]):
        os.remove(res["output_file"])

def test_demo2_multi_store_excel_merger():
    """测试多平台电商跨店铺表头映射与利润分析"""
    worker = ExcelMergerWorker(params={"input_path": "mock_data/excel_bills", "remove_duplicates": True})
    res = worker.execute()
    
    assert res is not None
    assert os.path.exists(res["output_file"])
    assert res["total_raw"] > 40
    assert res["valid_orders"] > 30
    assert res["total_revenue"] > 0
    assert res["total_profit"] > 0
    
    # 验证三维透视表
    with pd.ExcelFile(res["output_file"]) as excel_file:
        assert "对账标准化流水明细" in excel_file.sheet_names
        assert "SKU商品利润透视" in excel_file.sheet_names
        assert "各店铺业绩对比" in excel_file.sheet_names

    if os.path.exists(res["output_file"]):
        os.remove(res["output_file"])

def test_demo3_web_autofill_headless():
    """测试 Playwright 驱动 Edge/Chromium 批量自动填表与截图凭证"""
    portal_uri = Path("mock_data/portal/mock_portal.html").resolve().as_uri()
    excel_path = "mock_data/学员资料待录入花名册.xlsx"
    
    worker = WebAutofillWorker(params={
        "input_path": excel_path,
        "target_url": portal_uri,
        "headless": True # 测试模式无头运行
    })
    res = worker.execute()
    
    assert res is not None
    assert os.path.exists(res["output_file"])
    assert os.path.exists(res["screenshot"])
    assert res["total_submitted"] >= 1
    
    # 清理测试生成的文件
    if os.path.exists(res["output_file"]):
        os.remove(res["output_file"])
    if os.path.exists(res["screenshot"]):
        os.remove(res["screenshot"])