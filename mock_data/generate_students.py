# -*- coding: utf-8 -*-
"""
mock_data/generate_students.py - 生成学员上报名单 Excel 表格 (教培/政企靶场)
作者: Emiliamio <mio2110767128@163.com>
"""

import pandas as pd
from pathlib import Path

def generate_students():
    names = ["赵子龙", "诸葛孔明", "关云长", "张翼德", "周公瑾", "司马仲达", "鲁子敬", "黄汉升", "马孟起", "庞士元", "姜伯约", "魏文长", "徐元直", "郭奉孝", "荀文若"]
    courses = ["人工智能与大模型算法专班", "企业级全栈微服务架构班", "商业智能数据分析实战班", "数字化出纳与财税合规班"]
    
    rows = []
    for i, name in enumerate(names, start=1):
        rows.append({
            "序号": i,
            "学员姓名": name,
            "身份证号": f"110101199{i % 10 + 0}0315{1000 + i:04d}",
            "联系手机": f"1381234{5000 + i:04d}",
            "报读班型": courses[i % len(courses)],
            "实缴学费": 4800 + (i % 5) * 600
        })
    
    out_path = Path("mock_data/学员资料待录入花名册.xlsx")
    pd.DataFrame(rows).to_excel(out_path, index=False)
    print(f"[OK] 学员待录入表格已生成: {out_path}")

if __name__ == "__main__":
    generate_students()