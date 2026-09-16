# -*- coding: utf-8 -*-
"""
tasks/demo_invoice_extractor.py - [Demo 1: 财务/行政] 电子发票批量提取与查重汇总 (双向风控穿透版)
作者: Emiliamio <mio2110767128@163.com>

核心能力升级：
1. 双向查重回溯：当发生号码重复时，新旧两张/多张冲突发票全部高亮标红并互注行号；
2. 跨层级穿透扫描：支持递归遍历子目录 (rglob) 下的所有发票文件；
3. 纯图片发票防呆检测：针对无文本层的纯扫描版发票友好标记并引导 OCR；
4. 宽容度正则：支持 年月日、-、/、. 等多种日期分隔符与复杂货币格式；
5. 【商业试用锁】：当 IS_TRIAL=True 时只提取前 10 张发票并植入水印。
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
from config import IS_TRIAL, TRIAL_ROW_LIMIT, TRIAL_WATERMARK, get_default_output_dir, resolve_mock_path

class InvoiceExtractorWorker(BaseWorker):
    def __init__(self, params: Dict[str, Any]):
        super().__init__(task_name="电子发票PDF批量提取与查重汇总", params=params)

    def _parse_single_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """解析单张 PDF 增值税发票的关键字段"""
        text = ""
        try:
            with pdfplumber.open(str(pdf_path)) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as open_err:
            text = ""

        # 扫描件空文本层防御检测
        if len(text.strip()) < 20:
            return {
                "源文件": pdf_path.name,
                "发票代码": "未识别",
                "发票号码": "未识别",
                "开票日期": "未识别",
                "校验码": "未识别",
                "购买方名称": "未识别",
                "购买方税号": "未识别",
                "销售方名称": "未识别",
                "项目内容": "未识别",
                "不含税金额": 0.0,
                "税额": 0.0,
                "价税合计": 0.0,
                "查重状态": "⚠️ 纯图片扫描发票(无文本层需OCR)"
            }

        def search_pattern(pattern: str, default: str = "未识别") -> str:
            m = re.search(pattern, text)
            return m.group(1).strip() if m else default

        inv_code = search_pattern(r"发票代码[：:]?\s*(\d{10,12})")
        inv_number = search_pattern(r"发票号码[：:]?\s*(\d{8})")
        
        # 兼容 2026年01月15日 / 2026-01-15 / 2026/01/15 / 2026.01.15
        inv_date = search_pattern(r"开票日期[：:]?\s*([0-9]{4}[年\-\/\.][0-9]{1,2}[月\-\/\.][0-9]{1,2}日?)")
        check_code = search_pattern(r"校\s*验\s*码[：:]?\s*([0-9]{5,20})")
        
        buyer_name = search_pattern(r"购买方名称[：:]?\s*([^\n\r]+)")
        if buyer_name == "未识别":
            buyer_name = search_pattern(r"名\s*称[：:]?\s*([^\n\r]+)")
            
        buyer_tax_id = search_pattern(r"纳税人识别号[：:]?\s*([0-9A-Z]{15,20})")
        seller_name = search_pattern(r"销售方名称[：:]?\s*([^\n\r]+)")
        
        # 金额解析 (剥离货币字符)
        amount_str = search_pattern(r"合\s*计[：:]?\s*[¥￥$]?\s*([0-9,]+\.[0-9]{2})").replace(",", "")
        tax_str = search_pattern(r"税额合计[：:]?\s*[¥￥$]?\s*([0-9,]+\.[0-9]{2})").replace(",", "")
        total_str = search_pattern(r"（小写）[：:]?\s*[¥￥$]?\s*([0-9,]+\.[0-9]{2})").replace(",", "")
        if total_str == "未识别":
            total_str = search_pattern(r"小写[：:]?\s*[¥￥$]?\s*([0-9,]+\.[0-9]{2})").replace(",", "")

        amount = float(amount_str) if amount_str != "未识别" else 0.0
        tax = float(tax_str) if tax_str != "未识别" else 0.0
        total = float(total_str) if total_str != "未识别" else round(amount + tax, 2)

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
        
        # 自适应多级寻址与自愈定位
        if not input_path or not os.path.exists(input_path):
            mock_invoices_dir = resolve_mock_path("mock_data/invoices")
            if mock_invoices_dir.exists() and list(mock_invoices_dir.glob("*.pdf")):
                input_path = str(mock_invoices_dir)
                self.emit_log(f"未指定发票目录，已自动切换至全真财务靶场: {input_path}", level="INFO")
            else:
                self.emit_log("靶场发票未检索到，正在即时动态生成 15 份全真仿真发票...", level="INFO")
                try:
                    from mock_data.generate_invoices import main as gen_inv_main
                    gen_inv_main()
                    input_path = str(resolve_mock_path("mock_data/invoices"))
                except Exception as gen_err:
                    raise FileNotFoundError(f"未选择发票文件且未能定位靶场数据: {gen_err}")

        p = Path(input_path)
        pdf_files: List[Path] = []
        if p.is_dir():
            # 递归 + 同级穿透去重扫描
            direct = list(p.glob("*.pdf"))
            sub = list(p.rglob("*.pdf"))
            seen_f = set()
            for f in direct + sub:
                if f.resolve() not in seen_f:
                    seen_f.add(f.resolve())
                    pdf_files.append(f)
            pdf_files = sorted(pdf_files)
        elif p.is_file() and p.suffix.lower() == ".pdf":
            pdf_files = [p]

        total_files = len(pdf_files)
        if total_files == 0:
            raise FileNotFoundError(f"所选目录中未检索到任何 PDF 电子发票文件: {input_path}")

        self.emit_log(f"成功扫描到 {total_files} 份 PDF 发票，开始批量结构化提取与双向查重...", level="INFO")

        records: List[Dict[str, Any]] = []
        seen_map: Dict[str, int] = {} # 发票号码 -> 首次出现的索引
        duplicate_count = 0

        for idx, pdf_file in enumerate(pdf_files, start=1):
            self.check_stop_requested()
            self.emit_log(f"正在解析第 [{idx}/{total_files}] 张发票: {pdf_file.name}")
            
            try:
                row = self._parse_single_pdf(pdf_file)
                inv_num = row["发票号码"]
                
                # 双向查重联动
                if inv_num != "未识别":
                    if inv_num in seen_map:
                        first_idx = seen_map[inv_num]
                        row["查重状态"] = f"⚠️ 重复报销 (与第 {first_idx + 1} 张单号相同)"
                        # 回溯标记首发单据，实现双向标红
                        records[first_idx]["查重状态"] = f"⚠️ 重复报销 (与第 {idx} 张单号相同)"
                        duplicate_count += 1
                        self.emit_log(f"🚨 抓出重复报销发票！单号: {inv_num} (与第 {first_idx + 1} 张互锁冲突)", level="WARN")
                    else:
                        seen_map[inv_num] = len(records) # 记录下标

                records.append(row)
            except Exception as e:
                self.emit_log(f"发票解析跳过 [{pdf_file.name}]: {e}", level="WARN")

            self.emit_progress(idx, total_files)
            time.sleep(0.03)

        df = pd.DataFrame(records)
        self.emit_log(f"发票全量解析提取完成！共读取 {len(df)} 张发票，识别重复报销 {duplicate_count} 次。")

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
                {"统计指标": "疑似重复报销异常次数", "数值": duplicate_count},
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