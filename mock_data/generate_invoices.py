# -*- coding: utf-8 -*-
"""
mock_data/generate_invoices.py - 电子发票批量生成器 (全真测试靶场)
作者: Emiliamio <mio2110767128@163.com>

利用 reportlab 生成 15 张逼真的增值税电子发票 PDF 文件，包含标准表头、税号、金额、税额与防伪码。
特意植入 1 组重复发票号，用于验证批量提取时的自动查重与标红报警功能。
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def register_chinese_font():
    font_path = "C:/Windows/Fonts/simsun.ttc"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/msyh.ttc"
    pdfmetrics.registerFont(TTFont("ChineseFont", font_path))

def create_mock_invoice(output_path: str, data: dict):
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    c.setFont("ChineseFont", 16)
    
    # 标题
    title = "增值税电子普通发票"
    c.drawCentredString(width / 2, height - 70, title)
    
    # 装饰线
    c.setLineWidth(1)
    c.line(50, height - 85, width - 50, height - 85)
    
    c.setFont("ChineseFont", 10)
    
    # 右上角元数据
    c.drawString(width - 240, height - 105, f"发票代码: {data['code']}")
    c.drawString(width - 240, height - 120, f"发票号码: {data['number']}")
    c.drawString(width - 240, height - 135, f"开票日期: {data['date']}")
    c.drawString(width - 240, height - 150, f"校 验 码: {data['check_code']}")

    # 购买方信息框
    c.rect(50, height - 230, width - 100, 70)
    c.drawString(60, height - 180, f"购买方名称: {data['buyer_name']}")
    c.drawString(60, height - 195, f"纳税人识别号: {data['buyer_tax_id']}")
    c.drawString(60, height - 210, f"地址、电话: 北京市海淀区中关村南大街1号 010-88886666")

    # 项目明细表头
    c.rect(50, height - 370, width - 100, 130)
    c.drawString(60, height - 250, "货物或应税劳务、服务名称")
    c.drawString(240, height - 250, "规格型号")
    c.drawString(300, height - 250, "数量")
    c.drawString(350, height - 250, "单价")
    c.drawString(420, height - 250, "金额")
    c.drawString(480, height - 250, "税率")
    c.drawString(520, height - 250, "税额")
    c.line(50, height - 258, width - 50, height - 258)

    # 项目明细内容
    c.drawString(60, height - 280, data['item_name'])
    c.drawString(240, height - 280, "标准版")
    c.drawString(300, height - 280, "1")
    c.drawString(350, height - 280, f"{data['amount']:.2f}")
    c.drawString(420, height - 280, f"{data['amount']:.2f}")
    c.drawString(480, height - 280, f"{data['tax_rate']}")
    c.drawString(520, height - 280, f"{data['tax_amount']:.2f}")

    # 合计行
    c.line(50, height - 340, width - 50, height - 340)
    c.drawString(60, height - 360, f"合 计: ¥{data['amount']:.2f}")
    c.drawString(450, height - 360, f"税额合计: ¥{data['tax_amount']:.2f}")

    # 价税合计大写与小写
    c.rect(50, height - 410, width - 100, 35)
    c.drawString(60, height - 395, f"价税合计（大写）: {data['total_words']}")
    c.drawString(380, height - 395, f"（小写）: ¥{data['total_amount']:.2f}")

    # 销售方信息框
    c.rect(50, height - 490, width - 100, 70)
    c.drawString(60, height - 440, f"销售方名称: {data['seller_name']}")
    c.drawString(60, height - 455, f"纳税人识别号: {data['seller_tax_id']}")
    c.drawString(60, height - 470, f"开户行及账号: 招商银行深圳分行 755912345678901")

    # 底部盖章与防伪提示
    c.drawString(60, height - 515, "收款人: 李会计      复核: 张财务      开票人: 王专员")
    c.drawString(width - 200, height - 515, "销售方:(电子发票监制章)")

    c.showPage()
    c.save()

def main():
    register_chinese_font()
    out_dir = Path("mock_data/invoices")
    out_dir.mkdir(parents=True, exist_ok=True)

    items = [
        ("*信息技术服务*软件开发费", 5000.0, 0.06),
        ("*信息技术服务*云服务器租赁费", 1200.0, 0.06),
        ("*咨询服务*数字化转型技术顾问费", 8000.0, 0.06),
        ("*办公用品*A4复印纸与耗材", 350.0, 0.13),
        ("*通信服务*企业宽带接入服务费", 2400.0, 0.09),
        ("*餐饮服务*商务招待餐费", 860.0, 0.06),
        ("*交通运输*市内快递与物流托运费", 450.0, 0.09),
        ("*技术服务*数据库安全审计服务", 6500.0, 0.06)
    ]

    print("[*] 正在生成 15 张高仿真增值税电子发票 PDF ...")
    for i in range(1, 16):
        item_name, amount, rate = items[i % len(items)]
        tax_amount = round(amount * rate, 2)
        total_amount = round(amount + tax_amount, 2)
        
        # 特别在第 8 张和第 3 张使用相同发票号码，用于验证重复查重功能
        inv_num = "82911003" if i == 8 else f"8291{1000 + i:04d}"
        
        data = {
            "code": f"04400200{100 + (i % 5):03d}",
            "number": inv_num,
            "date": f"2026年01月{10 + (i % 18):02d}日",
            "check_code": f"{10293847561029384750 + i}",
            "buyer_name": "北京华盛科技有限公司" if i % 2 == 0 else "上海极光数字创新有限公司",
            "buyer_tax_id": "91110108MA00ABC12X" if i % 2 == 0 else "91310115MA1H78903Y",
            "seller_name": "深圳迅捷信息技术服务有限公司",
            "seller_tax_id": "91440300MA5DEF345Y",
            "item_name": item_name,
            "amount": amount,
            "tax_rate": f"{int(rate * 100)}%",
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "total_words": "伍仟叁佰元整" if total_amount == 5300 else "肆仟零捌拾元整"
        }
        
        pdf_path = out_dir / f"电子发票_{inv_num}_{i}.pdf"
        create_mock_invoice(str(pdf_path), data)

    print(f"[OK] 15 张发票全部生成至 {out_dir}")

if __name__ == "__main__":
    main()