# -*- coding: utf-8 -*-
"""
tasks/demo_excel_merger.py - [Demo 2: 电商/运营] 多平台多店铺 Excel 账单自动核对器
作者: Emiliamio <mio2110767128@163.com>

核心能力：
1. 智能表头模糊映射：自动兼容淘宝、京东、拼多多、抖音等不同平台的字段名；
2. 脏数据自愈：自动剥离空格、纠正数据类型、过滤退款/售后脏订单；
3. 核心商业算法：按商品 SKU 货号聚合，自动核算销售总额、总成本、净毛利润与毛利率；
4. 【商业试用锁】：当 IS_TRIAL=True 时只截取前 10 行并植入水印提示；
5. 输出多维度财务报表：标准化明细表 + SKU利润透视表 + 店铺业绩对比表。
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from core.base_worker import BaseWorker
from config import IS_TRIAL, TRIAL_ROW_LIMIT, TRIAL_WATERMARK, get_default_output_dir

# 跨平台列名模糊对齐字典
SCHEMA_MAPPINGS = {
    "订单号": ["订单号", "主订单编号", "订单流水号", "订单编号", "交易流水号"],
    "商品货号": ["商家编码", "SKU货号", "外部货号", "商品编码", "货号"],
    "商品名称": ["宝贝标题", "商品全称", "商品名称", "商品描述", "标题"],
    "销售金额": ["买家实付", "结算金额", "实付总额", "销售单价", "实付金额"],
    "销售数量": ["购买数量", "订购件数", "成团数量", "数量", "销售数量"],
    "采购成本": ["进货成本", "采购底价", "供货价", "成本", "采购单价"],
    "订单状态": ["订单状态", "结算状态", "发货状态", "售后状态", "状态"]
}

class ExcelMergerWorker(BaseWorker):
    def __init__(self, params: Dict[str, Any]):
        super().__init__(task_name="多店铺Excel账单核对与利润分析", params=params)

    def _normalize_dataframe(self, df: pd.DataFrame, source_name: str) -> pd.DataFrame:
        """对原始不同平台的 DataFrame 执行智能列名归一化映射"""
        col_rename_map = {}
        for target_col, candidate_cols in SCHEMA_MAPPINGS.items():
            for c in df.columns:
                clean_c = str(c).strip()
                if clean_c in candidate_cols:
                    col_rename_map[c] = target_col
                    break
        
        normalized = df.rename(columns=col_rename_map).copy()
        
        # 确保关键列存在，若缺失则赋予默认值
        for req_col in SCHEMA_MAPPINGS.keys():
            if req_col not in normalized.columns:
                normalized[req_col] = 0.0 if req_col in ("销售金额", "销售数量", "采购成本") else "无"
        
        # 保留标准核心列
        std_cols = list(SCHEMA_MAPPINGS.keys())
        normalized = normalized[std_cols].copy()
        normalized["来源店铺"] = source_name.replace(".xlsx", "").replace(".xls", "").replace(".csv", "")
        return normalized

    def execute(self) -> Dict[str, Any]:
        input_path = self.params.get("input_path", "").strip()
        remove_duplicates = self.params.get("remove_duplicates", True)
        
        # 默认靶场数据引导
        if not input_path or not os.path.exists(input_path):
            mock_dir = Path("mock_data/excel_bills")
            if mock_dir.exists():
                input_path = str(mock_dir)
                self.emit_log(f"未指定输入源，已自动切入电商多店铺全真靶场: {input_path}", level="INFO")
            else:
                raise FileNotFoundError("未选定输入表格且未找到 mock_data/excel_bills 靶场数据。")

        p = Path(input_path)
        files: List[Path] = []
        if p.is_dir():
            files = list(p.glob("*.xlsx")) + list(p.glob("*.xls")) + list(p.glob("*.csv"))
        elif p.is_file():
            files = [p]

        total_files = len(files)
        if total_files == 0:
            raise FileNotFoundError(f"所选路径中未找到有效表格: {input_path}")

        self.emit_log(f"扫描到 {total_files} 个店铺账单表格，开始执行跨平台智能对齐...", level="INFO")

        all_cleaned_dfs: List[pd.DataFrame] = []
        for idx, file_path in enumerate(files, start=1):
            self.check_stop_requested()
            self.emit_log(f"正在对齐第 [{idx}/{total_files}] 个店铺: {file_path.name}")
            
            try:
                if file_path.suffix.lower() == ".csv":
                    raw_df = pd.read_csv(file_path, encoding="utf-8-sig")
                else:
                    raw_df = pd.read_excel(file_path)
                
                norm_df = self._normalize_dataframe(raw_df, file_path.name)
                all_cleaned_dfs.append(norm_df)
            except Exception as read_err:
                self.emit_log(f"表格读取跳过: {file_path.name}, 原因: {read_err}", level="WARN")

            self.emit_progress(idx, total_files * 2)
            time.sleep(0.04)

        self.check_stop_requested()
        combined_df = pd.concat(all_cleaned_dfs, ignore_index=True)
        initial_count = len(combined_df)
        self.emit_log(f"跨店铺表头智能对齐汇聚完成，共聚合原始订单流水 {initial_count} 行")

        # 1. 字符串多余空格清除
        for col in combined_df.select_dtypes(include=["object", "string"]).columns:
            combined_df[col] = combined_df[col].astype(str).str.strip()

        # 2. 自动过滤退款与异常订单
        refund_mask = combined_df["订单状态"].str.contains("退款|关闭|取消", na=False)
        refund_count = int(refund_mask.sum())
        if refund_count > 0:
            self.emit_log(f"智能排除退款与异常订单: 剔除 {refund_count} 行退款流水", level="INFO")
            combined_df = combined_df[~refund_mask].copy()

        # 3. 订单去重
        if remove_duplicates and "订单号" in combined_df.columns:
            dedup_before = len(combined_df)
            combined_df = combined_df.drop_duplicates(subset=["订单号"], keep="first")
            dedup_diff = dedup_before - len(combined_df)
            if dedup_diff > 0:
                self.emit_log(f"剔除重复重复订单记录: {dedup_diff} 行", level="INFO")

        # 4. 数值纠偏与利润指标计算
        combined_df["销售金额"] = pd.to_numeric(combined_df["销售金额"], errors="coerce").fillna(0.0)
        combined_df["销售数量"] = pd.to_numeric(combined_df["销售数量"], errors="coerce").fillna(1)
        combined_df["采购成本"] = pd.to_numeric(combined_df["采购成本"], errors="coerce").fillna(0.0)

        # 衍生财务指标
        combined_df["订单总营收"] = (combined_df["销售金额"] * combined_df["销售数量"]).round(2)
        combined_df["订单总成本"] = (combined_df["采购成本"] * combined_df["销售数量"]).round(2)
        combined_df["净毛利润"] = (combined_df["订单总营收"] - combined_df["订单总成本"]).round(2)
        
        # 避免除以零
        combined_df["毛利率(%)"] = (
            (combined_df["净毛利润"] / combined_df["订单总营收"].replace(0, 1)) * 100
        ).round(2)

        self.emit_log(f"利润核算完成：总流水营收 ¥{combined_df['订单总营收'].sum():.2f}，净毛利 ¥{combined_df['净毛利润'].sum():.2f}", level="SUCCESS")

        # 5. 商业试用锁截断
        is_trial_triggered = False
        out_df = combined_df.copy()
        if IS_TRIAL:
            is_trial_triggered = True
            self.emit_log(f"⚠️ 【商业试用保护锁】已触发：仅展示前 {TRIAL_ROW_LIMIT} 条对账流水！", level="WARN")
            out_df = out_df.head(TRIAL_ROW_LIMIT).copy()
            watermark_row = {col: "" for col in out_df.columns}
            watermark_row["订单号"] = TRIAL_WATERMARK
            out_df = pd.concat([out_df, pd.DataFrame([watermark_row])], ignore_index=True)

        # 6. 生成多维报表 Excel
        out_dir = get_default_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_suffix = "试用演示版" if is_trial_triggered else "正式全量版"
        out_filename = f"多店铺对账与利润分析汇总_{mode_suffix}_{ts}.xlsx"
        out_filepath = os.path.join(out_dir, out_filename)

        self.emit_log(f"正在写入全维度电商分析报表: {out_filename} ...", level="INFO")
        with pd.ExcelWriter(out_filepath, engine="openpyxl") as writer:
            out_df.to_excel(writer, sheet_name="对账标准化流水明细", index=False)

            # Sheet 2: SKU 货号维度的利润分析透视
            sku_pivot = combined_df.groupby(["商品货号", "商品名称"]).agg({
                "销售数量": "sum",
                "订单总营收": "sum",
                "净毛利润": "sum"
            }).reset_index()
            sku_pivot["SKU毛利率(%)"] = ((sku_pivot["净毛利润"] / sku_pivot["订单总营收"].replace(0, 1)) * 100).round(2)
            sku_pivot.sort_values(by="净毛利润", ascending=False, inplace=True)
            sku_pivot.to_excel(writer, sheet_name="SKU商品利润透视", index=False)

            # Sheet 3: 店铺维度的营收对比
            shop_pivot = combined_df.groupby("来源店铺").agg({
                "订单号": "count",
                "订单总营收": "sum",
                "净毛利润": "sum"
            }).reset_index().rename(columns={"订单号": "有效订单量"})
            shop_pivot.to_excel(writer, sheet_name="各店铺业绩对比", index=False)

        self.emit_progress(100, 100)
        self.emit_log(f"🎉 电商报表已成功生成！文件路径: {out_filepath}", level="SUCCESS")

        return {
            "output_file": out_filepath,
            "total_raw": initial_count,
            "total_rows": initial_count,
            "valid_orders": len(combined_df),
            "total_revenue": round(combined_df["订单总营收"].sum(), 2),
            "total_profit": round(combined_df["净毛利润"].sum(), 2),
            "is_trial": is_trial_triggered
        }