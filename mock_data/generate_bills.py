# -*- coding: utf-8 -*-
"""
mock_data/generate_bills.py - 多平台多店铺 Excel 账单生成器 (电商全真靶场)
作者: Emiliamio <mio2110767128@163.com>
"""

import os
from pathlib import Path
import pandas as pd

def generate_bills():
    out_dir = Path("mock_data/excel_bills")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 淘宝店铺
    tb_data = [
        {
            "主订单编号": f"TB-998810{i:02d} ",
            "商家编码": f"SKU-A{100 + i % 5}",
            "宝贝标题": f" 极光无线游戏鼠标_款式{i % 5 + 1} ",
            "买家实付": 129.0 + i * 2,
            "购买数量": 1,
            "进货成本": 65.0,
            "订单状态": "交易成功" if i != 3 else "已退款"
        }
        for i in range(1, 16)
    ]
    tb_data.append(tb_data[0].copy()) # 重复订单
    pd.DataFrame(tb_data).to_excel(out_dir / "淘宝旗舰店_1月订单流水.xlsx", index=False)

    # 2. 京东自营
    jd_data = [
        {
            "订单号": f"JD-772230{i:02d}",
            "SKU货号": f" SKU-A{100 + i % 5} ",
            "商品全称": f"极光无线静音办公鼠标-定制款{i % 5 + 1}",
            "结算金额": 139.0 + i * 3,
            "订购件数": 1 + i % 2,
            "采购底价": 68.0,
            "结算状态": "已完成" if i != 5 else "售后退款"
        }
        for i in range(1, 16)
    ]
    pd.DataFrame(jd_data).to_excel(out_dir / "京东自营店_1月对账结算单.xlsx", index=False)

    # 3. 拼多多品牌店
    pdd_data = [
        {
            "订单流水号": f"PDD-551120{i:02d} ",
            "外部货号": f"SKU-A{100 + i % 5}",
            "商品名称": f"极光电竞机械键盘_RGB版{i % 5 + 1} ",
            "实付总额": 99.0 + i,
            "成团数量": 1,
            "供货价": 48.0,
            "发货状态": "已签收" if i != 2 else "退款已关闭"
        }
        for i in range(1, 16)
    ]
    pd.DataFrame(pdd_data).to_excel(out_dir / "拼多多官方店_1月销售明细.xlsx", index=False)

    print(f"[OK] 3 家店铺测试表格已生成至: {out_dir}")

if __name__ == "__main__":
    generate_bills()