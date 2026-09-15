# -*- coding: utf-8 -*-
"""
tasks/demo_excel_merger.py - 标准示例任务：多表格批量清洗合并与核对器
作者: Emiliamio <mio2110767128@163.com>

本模块演示了工业级表格处理的标准形态：
1. 支持扫描目录下的所有 .xlsx / .xls / .csv 文件；
2. 自动对齐列名、去除首尾空格、智能填充与数值清洗；
3. 内置【防白嫖试用锁】：当 IS_TRIAL=True 时只截取前 10 行并植入水印提示；
4. 自动在桌面或输出目录生成《数据清洗合并结果_带时间戳.xlsx》。
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

from core.base_worker import BaseWorker
from config import IS_TRIAL, TRIAL_ROW_LIMIT, TRIAL_WATERMARK, get_default_output_dir

class ExcelMergerWorker(BaseWorker):
    def __init__(self, params: Dict[str, Any]):
        super().__init__(task_name="多表格批量清洗与合并引擎", params=params)

    def _generate_mock_data(self) -> pd.DataFrame:
        """若用户未选文件夹，自动生成模拟的 50 条电商杂乱订单用于全功能演示"""
        self.emit_log("检测到未指定输入源，已自动启用内置工业级全真模拟靶场数据...", level="INFO")
        data = []
        categories = ["数码办公", "服装鞋帽", "家居百货", "食品生鲜"]
        for i in range(1, 51):
            data.append({
                "订单编号": f"ORD-2026{i:04d} ",
                "商品名称": f"高品质智能硬件_{i}型",
                "商品品类": categories[i % len(categories)],
                "销售单价": round(19.9 * (i % 7 + 1), 2),
                "销售数量": (i % 5) + 1,
                "客户姓名": f"客户_{chr(65 + i % 26)}",
                "备注信息": " 已付款 " if i % 2 == 0 else " 待核销 "
            })
        return pd.DataFrame(data)

    def execute(self) -> Dict[str, Any]:
        input_path = self.params.get("input_path", "").strip()
        remove_duplicates = self.params.get("remove_duplicates", True)
        
        all_dfs: List[pd.DataFrame] = []
        
        # 1. 扫描与读取数据
        if input_path and os.path.exists(input_path):
            p = Path(input_path)
            files = []
            if p.is_dir():
                files = list(p.glob("*.xlsx")) + list(p.glob("*.xls")) + list(p.glob("*.csv"))
            elif p.is_file():
                files = [p]
            
            total_files = len(files)
            if total_files == 0:
                raise FileNotFoundError(f"所选路径下未发现 Excel 或 CSV 表格: {input_path}")
            
            self.emit_log(f"已探测到待处理表格清单，共 {total_files} 个文件", level="INFO")
            
            for idx, file_path in enumerate(files, start=1):
                self.check_stop_requested() # 检查中断信号
                self.emit_log(f"正在解析第 [{idx}/{total_files}] 个表格: {file_path.name}")
                
                try:
                    if file_path.suffix.lower() == ".csv":
                        df = pd.read_csv(file_path, encoding="utf-8-sig")
                    else:
                        df = pd.read_excel(file_path)
                    
                    df["来源文件"] = file_path.name
                    all_dfs.append(df)
                except Exception as read_err:
                    self.emit_log(f"文件读取跳过 (非标准格式): {file_path.name}, 原因: {read_err}", level="WARN")
                
                # 平滑步进进度
                self.emit_progress(idx, total_files * 2)
                time.sleep(0.05) # 保证多线程平滑可中断
        else:
            # 仿真模拟模式
            df_mock = self._generate_mock_data()
            all_dfs.append(df_mock)
            self.emit_progress(50, 100)

        self.check_stop_requested()

        # 2. 数据清洗与合并
        self.emit_log("开始执行核心清洗算法：列名对齐、空格修剪与类型纠正...", level="INFO")
        combined_df = pd.concat(all_dfs, ignore_index=True)
        initial_count = len(combined_df)
        self.emit_log(f"数据纵向拼接完成，共汇聚原始记录 {initial_count} 行")

        # 字符串字段剥离首尾多余空格
        for col in combined_df.select_dtypes(include=["object", "string"]).columns:
            combined_df[col] = combined_df[col].astype(str).str.strip()

        # 去重处理
        if remove_duplicates and "订单编号" in combined_df.columns:
            combined_df = combined_df.drop_duplicates(subset=["订单编号"], keep="first")
            dedup_count = initial_count - len(combined_df)
            if dedup_count > 0:
                self.emit_log(f"智能去重完成：剔除重复记录 {dedup_count} 行", level="INFO")

        # 自动计算金额衍生字段
        if "销售单价" in combined_df.columns and "销售数量" in combined_df.columns:
            combined_df["销售单价"] = pd.to_numeric(combined_df["销售单价"], errors="coerce").fillna(0.0)
            combined_df["销售数量"] = pd.to_numeric(combined_df["销售数量"], errors="coerce").fillna(0)
            combined_df["订单总金额"] = (combined_df["销售单价"] * combined_df["销售数量"]).round(2)
            self.emit_log("自动完成跨列公式计算：已衍生 [订单总金额] = 单价 × 数量")

        total_cleaned = len(combined_df)

        # 3. 商业防御：试用锁截断 (IS_TRIAL 熔断)
        out_df = combined_df.copy()
        is_trial_triggered = False
        
        if IS_TRIAL:
            is_trial_triggered = True
            self.emit_log(f"⚠️ 【商业试用模式激活】已触发试用行数截断：仅导出前 {TRIAL_ROW_LIMIT} 行！", level="WARN")
            self.emit_log(f"⚠️ 提示客户：结清尾款后可立即交付 100% 全量数据正式版！", level="WARN")
            out_df = out_df.head(TRIAL_ROW_LIMIT).copy()
            # 在尾部追加水印提示行
            watermark_row = {col: "" for col in out_df.columns}
            first_col = out_df.columns[0]
            watermark_row[first_col] = TRIAL_WATERMARK
            out_df = pd.concat([out_df, pd.DataFrame([watermark_row])], ignore_index=True)

        self.emit_progress(85, 100)
        self.check_stop_requested()

        # 4. 产物交付与持久化落盘
        out_dir = get_default_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_suffix = "试用演示版" if is_trial_triggered else "正式全量版"
        out_filename = f"业务数据处理成果_{mode_suffix}_{ts}.xlsx"
        out_filepath = os.path.join(out_dir, out_filename)

        self.emit_log(f"正在写入工业级 Excel 成果文档: {out_filename} ...", level="INFO")
        
        with pd.ExcelWriter(out_filepath, engine="openpyxl") as writer:
            out_df.to_excel(writer, sheet_name="清洗汇总表", index=False)
            
            # 附带透视分析 Sheet
            if "商品品类" in combined_df.columns and "订单总金额" in combined_df.columns:
                pivot_df = combined_df.groupby("商品品类")["订单总金额"].agg(["count", "sum"]).reset_index()
                pivot_df.columns = ["商品品类", "订单数量", "销售总金额"]
                pivot_df.to_excel(writer, sheet_name="品类维度透视", index=False)

        self.emit_progress(100, 100)
        self.emit_log(f"🎉 导出成功！文件已存入: {out_filepath}", level="SUCCESS")
        
        return {
            "output_file": out_filepath,
            "total_rows": initial_count,
            "exported_rows": len(out_df),
            "is_trial": is_trial_triggered,
            "out_dir": out_dir
        }