# -*- coding: utf-8 -*-
"""
tasks/demo_invoice_extractor.py - [Demo 1: 财务/行政] 电子发票批量提取与查重汇总神器
作者: Emiliamio <mio2110767128@163.com>

核心能力：
1. 批量遍历扫描指定目录下所有的 PDF 增值税普通/专用电子发票；
2. 毫秒级正则与版式文本解析：提取发票代码、发票号码、开票日期、购买方名称、税号、金额、税率、税额、价税合计；
3. 【智能查重与风险风控】：自动识别重复发票号码，标记“⚠️ 存在重复报销风险”；
4. 【商业试用锁】：当 IS_TRIAL=True 时只提取前 10 张发票并植入水印；
5. 自动导出结构化《电子发票批量报销汇总表_时间戳.xlsx》，含财务核心汇总指标。
"""

import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import pdfplumber

from core.base_worker import BaseWorker
from config import IS_TRIAL, TRIAL_ROW_LIMIT, TRIAL_WATERMARK, get_default_output_dir

class InvoiceExtractorWorker(BaseWorker):
    def __init__(self, params: Dict[str, Any]):
        super().__init__(task_name="电子发票PDF批量提取与查重汇总", params=params)

    def _parse_single_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """解析单张 PDF 增值税发票的关键字段"""
        text = ""
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"

        # 正则表达式抽取核心财务元数据
        def search_pattern(pattern: str, default: str = "未识别") -> str:
            m = re.search(pattern, text)
            return m.group(1).strip() if m else default

        inv_code = search_pattern(r"发票代码[：:]?\s*(\d{10,12})")
        inv_number = search_pattern(r"发票号码[：:]?\s*(\d{8})")
        inv_date = search_pattern(r"开票日期[：:]?\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{4}-[0-9]{2}-[0-9]{2})")
        check_code = search_pattern(r"校\s*验\s*码[：:]?\s*([0-9]{5,20})")
        
        buyer_name = search_pattern(r"购买方名称[：:]?\s*([^\n\r]+)")
        if buyer_name == "未识别":
            buyer_name = search_pattern(r"名\s*称[：:]?\s*([^\n\r]+)")
            
        buyer_tax_id = search_pattern(r"纳税人识别号[：:]?\s*([0-9A-Z]{15,20})")
        seller_name = search_pattern(r"销售方名称[：:]?\s*([^\n\r]+)")
        
        # 金额解析
        amount_str = search_pattern(r"合\s*计[：:]?\s*[¥￥]?\s*([0-9]+\.[0-9]{2})")
        tax_str = search_pattern(r"税额合计[：:]?\s*[¥￥]?\s*([0-9]+\.[0-9]{2})")
        total_str = search_pattern(r"（小写）[：:]?\s*[¥￥]?\s*([0-9]+\.[0-9]{2})")
        if total_str == "未识别":
            total_str = search_pattern(r"小写[：:]?\s*[¥￥]?\s*([0-9]+\.[0-9]{2})")

        amount = float(amount_str) if amount_str != "未识别" else 0.0
        tax = float(tax_str) if tax_str != "未识别" else 0.0
        total = float(total_str) if total_str != "未识别" else (amount + tax)

        # 项目名称
        item_match = re.search(r"(\*[^*]+\*[^\n\r\s]+)", text)
        item_name = item_match.group(1).strip() if item_match else "日常办公及技术服务"

        return {
            "源文件": pdf_path.name,
            "发票代码": inv_code,
            "发票号码": inv_number,
            "开票日期": inv_date,
            "校验码": check_code,
            "购买方名称": buyer_name,
            "购买方税号": buyer_tax_id,
            "销售方名称": seller_name,
            "项目内容": item_name,
            "不含税金额": amount,
            "税额": tax,
            "价税合计": total,
            "查重状态": "正常单据"
        }

    def execute(self) -> Dict[str, Any]:
        input_path = self.params.get("input_path", "").strip()
        
        # 若未提供路径，默认进入 mock_data/invoices 靶场演示
        if not input_path or not os.path.exists(input_path):
            mock_invoices_dir = Path("mock_data/invoices")
            if mock_invoices_dir.exists():
                input_path = str(mock_invoices_dir)
                self.emit_log(f"未指定发票目录，已自动切换至全真财务靶场: {input_path}", level="INFO")
            else:
                raise FileNotFoundError("未选择发票文件且未找到 mock_data/invoices 靶场数据。")

        p = Path(input_path)
        pdf_files: List[Path] = []
        if p.is_dir():
            pdf_files = sorted(list(p.glob("*.pdf")))
        elif p.is_file() and p.suffix.lower() == ".pdf":
            pdf_files = [p]

        total_files = len(pdf_files)
        if total_files == 0:
            raise FileNotFoundError(f"所选目录中未检索到任何 PDF 电子发票文件: {input_path}")

        self.emit_log(f"成功扫描到 {total_files} 份 PDF 发票，开始批量结构化提取与查重...", level="INFO")

        records: List[Dict[str, Any]] = []
        seen_numbers: set = set()
        duplicate_count = 0

        for idx, pdf_file in enumerate(pdf_files, start=1):
            self.check_stop_requested()
            self.emit_log(f"正在解析第 [{idx}/{total_files}] 张发票: {pdf_file.name}")
            
            try:
                row = self._parse_single_pdf(pdf_file)
                # 查重逻辑判断
                inv_num = row["发票号码"]
                if inv_num != "未识别":
                    if inv_num in seen_numbers:
                        row["查重状态"] = "⚠️ 重复报销 (发票号码相同)"
                        duplicate_count += 1
                        self.emit_log(f"🚨 发现重复报销发票！发票号: {inv_num}，已自动标记预警！", level="WARN")
                    else:
                        seen_numbers.add(inv_num)

                records.append(row)
            except Exception as e:
                self.emit_log(f"发票解析跳过 [{pdf_file.name}]: {e}", level="WARN")

            self.emit_progress(idx, total_files)
            time.sleep(0.04)

        df = pd.DataFrame(records)
        self.emit_log(f"发票全量解析提取完成！共读取 {len(df)} 张发票，识别重复报销 {duplicate_count} 张。")

        # 商业防御试用锁截断
        is_trial_triggered = False
        out_df = df.copy()
        if IS_TRIAL:
            is_trial_triggered = True
            self.emit_log(f"⚠️ 【商业试用保护锁】当前仅导出前 {TRIAL_ROW_LIMIT} 张发票明细，尾款结清后一键生成全量版！", level="WARN")
            out_df = out_df.head(TRIAL_ROW_LIMIT).copy()
            watermark_row = {col: "" for col in out_df.columns}
            watermark_row["源文件"] = TRIAL_WATERMARK
            out_df = pd.concat([out_df, pd.DataFrame([watermark_row])], ignore_index=True)

        # 写入 Excel 汇总结果
        out_dir = get_default_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_suffix = "试用版" if is_trial_triggered else "正式全量版"
        out_name = f"发票批量汇总导出表_{mode_suffix}_{ts}.xlsx"
        out_path = os.path.join(out_dir, out_name)

        self.emit_log(f"正在生成财务标准化报表: {out_name} ...", level="INFO")
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            out_df.to_excel(writer, sheet_name="发票明细汇总", index=False)
            
            # 汇总指标看板 Sheet
            sum_amount = df["不含税金额"].sum()
            sum_tax = df["税额"].sum()
            sum_total = df["价税合计"].sum()
            summary_df = pd.DataFrame([
                {"统计指标": "扫描发票总张数", "数值": total_files},
                {"统计指标": "成功解析张数", "数值": len(df)},
                {"统计指标": "疑似重复报销张数", "数值": duplicate_count},
                {"统计指标": "价税总金额合计 (元)", "数值": round(sum_total, 2)},
                {"统计指标": "不含税总额 (元)", "数值": round(sum_amount, 2)},
                {"统计指标": "税额总额 (元)", "数值": round(sum_tax, 2)},
            ])
            summary_df.to_excel(writer, sheet_name="财务总计看板", index=False)

        self.emit_log(f"🎉 报销汇总表生成完毕！文件保存在: {out_path}", level="SUCCESS")
        return {
            "output_file": out_path,
            "total_invoices": len(df),
            "duplicates": duplicate_count,
            "total_amount": round(df["价税合计"].sum(), 2)
        }