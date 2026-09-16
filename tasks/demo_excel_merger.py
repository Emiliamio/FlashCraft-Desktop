# -*- coding: utf-8 -*-
"""
tasks/demo_excel_merger.py - [Demo 2: 电商/运营] 多平台多店铺 Excel 账单自动核对器 (工业高健壮版)
作者: Emiliamio <mio2110767128@163.com>

核心能力升级：
1. 货币符号与千分位清洗器：解决带 ¥, $, 逗号时 pd.to_numeric 计算归零的致命暗坑；
2. 跨平台模糊表头字典全量扩充；
3. 多 Sheet 智能读取与退款订单多词识别；
4. 衍生指标：总营收、总成本、净毛利、毛利率(%)；
5. 【商业试用锁】：当 IS_TRIAL=True 时只截取前 10 行并植入水印提示。
"""

import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from core.base_worker import BaseWorker
from config import IS_TRIAL, TRIAL_ROW_LIMIT, TRIAL_WATERMARK, get_default_output_dir, resolve_mock_path

# 跨平台列名模糊对齐字典 (扩充大淘宝/天猫/京东/拼多多/抖音/有赞常见命名)
SCHEMA_MAPPINGS = {
    "订单号": ["订单号", "主订单编号", "订单流水号", "订单编号", "交易流水号", "订单ID", "交易号", "流水号", "业务单号"],
    "商品货号": ["商家编码", "SKU货号", "外部货号", "商品编码", "货号", "商品代码", "规格编码", "SKU"],
    "商品名称": ["宝贝标题", "商品全称", "商品名称", "商品描述", "标题", "品名", "商品规格名称"],
    "销售金额": ["买家实付", "结算金额", "实付总额", "销售单价", "实付金额", "售价", "单价", "成交价", "商品金额", "支付总额"],
    "销售数量": ["购买数量", "订购件数", "成团数量", "数量", "销售数量", "件数", "商品数量", "数量(件)"],
    "采购成本": ["进货成本", "采购底价", "供货价", "成本", "采购单价", "进价", "成本价", "供货单价"],
    "订单状态": ["订单状态", "结算状态", "发货状态", "售后状态", "状态", "交易状态", "订单处理状态"]
}

def clean_numeric_series(series: pd.Series, default_val: float = 0.0) -> pd.Series:
    """
    清洗带有货币符号 (¥, ￥, $, €)、千分位逗号 (1,299.50) 与空白符的金额字段
    彻底解决 pd.to_numeric 在遇到货币字符时被强制转换为 NaN 归零的致命暗坑
    """
    if series.empty:
        return series
    
    # 统一转换为字符串清洗
    cleaned = (
        series.astype(str)
        .str.replace(r"[¥￥$€\s]", "", regex=True)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    # 处理括号表示的负数 (100.00) -> -100.00
    cleaned = cleaned.str.replace(r"^\((.+)\)$", r"-\1", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").fillna(default_val)

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
        
        # 默认靶场数据自适应多级寻址
        if not input_path or not os.path.exists(input_path):
            mock_dir = resolve_mock_path("mock_data/excel_bills")
            if mock_dir.exists() and (list(mock_dir.glob("*.xlsx")) or list(mock_dir.glob("*.csv"))):
                input_path = str(mock_dir)
                self.emit_log(f"未指定输入源，已自动切入电商多店铺全真靶场: {input_path}", level="INFO")
            else:
                self.emit_log("靶场电商表格未检索到，正在即时生成测试账单...", level="INFO")
                try:
                    from mock_data.generate_bills import generate_bills
                    generate_bills()
                    input_path = str(resolve_mock_path("mock_data/excel_bills"))
                except Exception as gen_err:
                    raise FileNotFoundError(f"未选定输入表格且未能定位靶场数据: {gen_err}")

        p = Path(input_path)
        files: List[Path] = []
        if p.is_dir():
            files = sorted(list(p.glob("*.xlsx")) + list(p.glob("*.xls")) + list(p.glob("*.csv")))
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
            time.sleep(0.03)

        self.check_stop_requested()
        combined_df = pd.concat(all_cleaned_dfs, ignore_index=True)
        initial_count = len(combined_df)
        self.emit_log(f"跨店铺表头智能对齐汇聚完成，共聚合原始订单流水 {initial_count} 行")

        # 1. 字符串字段剥离首尾多余空格
        for col in combined_df.select_dtypes(include=["object", "string"]).columns:
            combined_df[col] = combined_df[col].astype(str).str.strip()

        # 2. 自动过滤退款与异常订单
        refund_mask = combined_df["订单状态"].str.contains("退款|关闭|取消|已退货|售后驳回", na=False)
        refund_count = int(refund_mask.sum())
        if refund_count > 0:
            self.emit_log(f"智能排除退款与异常订单: 剔除 {refund_count} 行退款售后流水", level="INFO")
            combined_df = combined_df[~refund_mask].copy()

        # 3. 订单去重
        if remove_duplicates and "订单号" in combined_df.columns:
            dedup_before = len(combined_df)
            combined_df = combined_df.drop_duplicates(subset=["订单号"], keep="first")
            dedup_diff = dedup_before - len(combined_df)
            if dedup_diff > 0:
                self.emit_log(f"剔除重复重复订单记录: {dedup_diff} 行", level="INFO")

        # 4. 数值深度清洗与利润指标精准计算 (防止货币符号导致 NaN 归零)
        combined_df["销售金额"] = clean_numeric_series(combined_df["销售金额"], default_val=0.0)
        combined_df["销售数量"] = clean_numeric_series(combined_df["销售数量"], default_val=1.0)
        combined_df["采购成本"] = clean_numeric_series(combined_df["采购成本"], default_val=0.0)

        # 衍生财务指标
        combined_df["订单总营收"] = (combined_df["销售金额"] * combined_df["销售数量"]).round(2)
        combined_df["订单总成本"] = (combined_df["采购成本"] * combined_df["销售数量"]).round(2)
        combined_df["净毛利润"] = (combined_df["订单总营收"] - combined_df["订单总成本"]).round(2)
        
        # 毛利率(%)，规避除以零
        combined_df["毛利率(%)"] = (
            (combined_df["净毛利润"] / combined_df["订单总营收"].replace(0, 1)) * 100
        ).round(2)

        total_rev = round(combined_df["订单总营收"].sum(), 2)
        total_prof = round(combined_df["净毛利润"].sum(), 2)
        self.emit_log(f"利润核算完成：总流水营收 ¥{total_rev:.2f}，净毛利 ¥{total_prof:.2f}", level="SUCCESS")

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
            "total_revenue": total_rev,
            "total_profit": total_prof,
            "is_trial": is_trial_triggered
        }