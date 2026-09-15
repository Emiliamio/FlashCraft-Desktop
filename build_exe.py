# -*- coding: utf-8 -*-
"""
build_exe.py - 工业级一键 PyInstaller 编译打包流水线
作者: Emiliamio <mio2110767128@163.com>
"""

import os
import sys
import io
import shutil
import subprocess

# 彻底根治 Windows 控制台 GBK 编码引发的 Emoji 崩溃
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def build():
    print("=" * 70)
    print("  [*] 开始执行 FlashCraft 工业级免安装独立 .exe 编译打包...")
    print("=" * 70)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    icon_path = os.path.join("assets", "icon.ico")
    if not os.path.exists(icon_path):
        print(f"[!] 警告: 未找到图标文件 {icon_path}，将采用默认图标打包")
        icon_arg = []
    else:
        icon_arg = [f"--icon={icon_path}"]

    # 构造 PyInstaller 核心参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",                   # 单文件
        "--noconsole",                 # 隐藏控制台黑窗
        "--name=FlashCraft_桌面自动化工作台",
        f"--add-data=assets{os.pathsep}assets",
        "--collect-all=customtkinter",   # 必须：打包 CustomTkinter 全套主题 assets
    ] + icon_arg + [
        # 排除无关依赖，极限瘦身体积
        "--exclude-module=matplotlib",
        "--exclude-module=scipy",
        "--exclude-module=networkx",
        "--exclude-module=pytest",
        "--exclude-module=IPython",
        "--exclude-module=jupyter",
        "--exclude-module=tornado",
        "--exclude-module=sqlite3",
        "main.py"
    ]

    print("执行打包命令:")
    print(" ".join(cmd))
    print("-" * 70)

    res = subprocess.run(cmd)
    if res.returncode != 0:
        print("\n[FAIL] 打包失败，请检查上方日志。")
        sys.exit(res.returncode)

    dist_exe = os.path.join("dist", "FlashCraft_桌面自动化工作台.exe")
    if os.path.exists(dist_exe):
        size_mb = round(os.path.getsize(dist_exe) / (1024 * 1024), 2)
        print("=" * 70)
        print("  [SUCCESS] 编译打包 100% 成功！")
        print(f"  交付产物: {dist_exe}")
        print(f"  文件体积: {size_mb} MB")
        print("  特性保证: 双击即用 / 零环境依赖 / 暗黑科技界面 / 试用截断保护")
        print("=" * 70)
    else:
        print("[!] 未在 dist/ 目录下发现目标文件。")

if __name__ == "__main__":
    build()