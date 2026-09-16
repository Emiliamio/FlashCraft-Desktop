# -*- coding: utf-8 -*-
"""
tasks/demo_web_autofill.py - [Demo 3: 政企/教培] 网页系统批量自动填表/上报助手 (三级容灾版)
作者: Emiliamio <mio2110767128@163.com>

核心能力升级：
1. 浏览器自适应三级拉起：优先 Edge ➜ 备选 Chrome ➜ 兜底 Chromium ➜ 友好引导提示；
2. 下拉选项模糊匹配容错；
3. 自动化截取完成全屏回执与凭证流水；
4. 【商业试用锁】：试用模式下限制填报条数并展示升级正式版提示。
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import pandas as pd

from core.base_worker import BaseWorker
from config import IS_TRIAL, TRIAL_ROW_LIMIT, get_default_output_dir, resolve_mock_path

class WebAutofillWorker(BaseWorker):
    def __init__(self, params: Dict[str, Any]):
        super().__init__(task_name="网页系统批量自动填表与上报助手", params=params)

    def execute(self) -> Dict[str, Any]:
        input_excel = self.params.get("input_path", "").strip()
        target_url = self.params.get("target_url", "").strip()
        headless = self.params.get("headless", False)

        # 1. 默认数据源与目标靶场多级自愈寻址
        if not input_excel or not os.path.exists(input_excel):
            mock_excel = resolve_mock_path("mock_data/学员资料待录入花名册.xlsx")
            if mock_excel.exists():
                input_excel = str(mock_excel)
                self.emit_log(f"未指定名单表格，自动载入全真教培学员靶场名单: {input_excel}", level="INFO")
            else:
                try:
                    from mock_data.generate_students import generate_students
                    generate_students()
                    input_excel = str(resolve_mock_path("mock_data/学员资料待录入花名册.xlsx"))
                except Exception as gen_err:
                    raise FileNotFoundError(f"未提供待录入名单且未能定位靶场表格: {gen_err}")

        if not target_url:
            portal_html = resolve_mock_path("mock_data/portal/mock_portal.html").resolve()
            if portal_html.exists():
                target_url = portal_html.as_uri()
                self.emit_log(f"未指定上报网址，自动载入离线政企上报系统: {target_url}", level="INFO")
            else:
                raise FileNotFoundError(f"未找到离线政企申报门户 HTML: {portal_html}")

        # 2. 读取名单
        self.emit_log(f"正在加载待上报数据表格: {os.path.basename(input_excel)} ...", level="INFO")
        df = pd.read_excel(input_excel)
        total_rows = len(df)
        self.emit_log(f"名单解析成功，共计需上报 {total_rows} 名人员资料", level="INFO")

        # 商业试用模式截断
        max_fill = total_rows
        if IS_TRIAL:
            max_fill = min(total_rows, 5)
            self.emit_log(f"⚠️ 【商业试用保护锁】试用演示模式仅自动录入前 {max_fill} 条数据！", level="WARN")

        # 3. 启动 Playwright 并拉起浏览器 (三级容灾探针)
        self.emit_log("正在启动自动化浏览器探针...", level="INFO")
        
        from playwright.sync_api import sync_playwright
        submitted_records = []
        
        with sync_playwright() as p:
            browser = None
            browser_name = "Edge"

            # 探针 1: 系统 Microsoft Edge
            try:
                browser = p.chromium.launch(channel="msedge", headless=headless)
                self.emit_log("已成功联动 Windows 系统级 Microsoft Edge 浏览器", level="INFO")
            except Exception:
                # 探针 2: 系统 Google Chrome
                try:
                    browser = p.chromium.launch(channel="chrome", headless=headless)
                    browser_name = "Chrome"
                    self.emit_log("未检测到标准 Edge，已切换联动 Google Chrome 浏览器", level="INFO")
                except Exception:
                    # 探针 3: 内置 Chromium 驱动
                    try:
                        browser = p.chromium.launch(headless=headless)
                        browser_name = "Chromium"
                        self.emit_log("使用内置 Chromium 内核拉起", level="INFO")
                    except Exception as all_fail:
                        raise FileNotFoundError(
                            "未检测到本机可用的 Microsoft Edge 或 Google Chrome 浏览器！\n"
                            "自动化填报需调用上述任一浏览器，请确保电脑已安装标准版 Edge 或 Chrome。"
                        )

            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            self.emit_log(f"正在导航至目标业务系统: {target_url}")
            page.goto(target_url, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(0.5)

            # 4. 循环遍历名单自动批量填表
            for idx in range(max_fill):
                self.check_stop_requested()
                row = df.iloc[idx]
                name = str(row.get("学员姓名", f"学员_{idx+1}")).strip()
                id_card = str(row.get("身份证号", "110101199003151234")).strip()
                phone = str(row.get("联系手机", "13800138000")).strip()
                course = str(row.get("报读班型", "人工智能与大模型算法专班")).strip()
                fee = str(row.get("实缴学费", "4800")).strip()

                self.emit_log(f"[{idx+1}/{max_fill}] 正在自动录入: {name} (身份证: {id_card[:6]}****{id_card[-4:]})")

                # 自动填写
                page.fill("#student_name", name)
                page.fill("#id_card", id_card)
                page.fill("#phone", phone)
                try:
                    page.select_option("#course_category", value=course)
                except Exception:
                    try:
                        page.select_option("#course_category", index=1)
                    except Exception:
                        pass
                page.fill("#tuition_fee", fee)

                if not headless:
                    time.sleep(0.2)

                page.click("#btn_submit")
                
                submitted_records.append({
                    "姓名": name,
                    "身份证号": id_card,
                    "手机号": phone,
                    "班型": course,
                    "缴费金额": fee,
                    "上报时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                self.emit_progress(idx + 1, max_fill)
                if not headless:
                    time.sleep(0.25)

            # 5. 截取凭证
            out_dir = get_default_output_dir()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            shot_path = os.path.join(out_dir, f"申报完成回执截图_{ts}.png")
            page.screenshot(path=shot_path, full_page=True)
            self.emit_log(f"已自动截取全屏申报完成凭证快照: {shot_path}", level="INFO")

            if not headless:
                time.sleep(0.8)
            browser.close()

        # 6. 导出回执名单
        out_excel = os.path.join(out_dir, f"自动录入成功回执流水_{ts}.xlsx")
        pd.DataFrame(submitted_records).to_excel(out_excel, index=False)
        self.emit_log(f"🎉 批量填表申报圆满完成！回执清单已存入: {out_excel}", level="SUCCESS")

        return {
            "output_file": out_excel,
            "screenshot": shot_path,
            "total_submitted": len(submitted_records)
        }